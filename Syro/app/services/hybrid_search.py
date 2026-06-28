"""Hybrid search combining vector similarity and BM25 lexical search."""

from __future__ import annotations

import atexit
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

from ..config import settings
from .llm import get_embedding_vector, get_embedding_vectors
from .vector_store import VectorStore, VectorStoreError
from .bm25_search import bm25_search
from .reranker import reranker
from .query_rewriter import expand_queries
from .hyde import get_hyde_embedding_vector

_executor = ThreadPoolExecutor(max_workers=4)
atexit.register(_executor.shutdown, wait=False)

def _vector_search_sync(
    query_vector: np.ndarray,
    organization_id: int,
    top_k: int,
    filters: dict[str, Any] | None,
    domain: str | None = None,
    allowed_document_ids: frozenset[int] | None = None,
) -> list[dict[str, Any]]:
    vector_store = VectorStore()
    try:
        return vector_store.search(
            query_vector=query_vector,
            organization_id=organization_id,
            top_k=top_k,
            filters=filters,
            domain=domain,
            allowed_document_ids=allowed_document_ids,
        )
    except VectorStoreError:
        return []

def _bm25_search_sync(
    organization_id: int,
    query: str,
    top_k: int,
    filters: dict[str, Any] | None,
    allowed_document_ids: frozenset[int] | None = None,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    return bm25_search.search(
        organization_id=organization_id,
        query=query,
        top_k=top_k,
        filters=filters,
        allowed_document_ids=allowed_document_ids,
        domain=domain,
    )

def _build_query_vectors(
    queries: list[str],
    original_query: str,
    query_embedding: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Embeddings par variante ; réutilise query_embedding pour la requête d'origine."""
    vectors: dict[str, np.ndarray] = {}
    pending: list[str] = []
    for q in queries:
        if query_embedding is not None and q == original_query:
            vectors[q] = query_embedding
        else:
            pending.append(q)
    if not pending:
        return vectors
    if len(pending) == 1:
        vectors[pending[0]] = get_embedding_vector(pending[0])
    else:
        for q, vec in zip(pending, get_embedding_vectors(pending)):
            vectors[q] = vec
    return vectors


def hybrid_search(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    alpha: float | None = None,
    domain: str | None = None,
    history: list[str] | None = None,
    allowed_document_ids: frozenset[int] | None = None,
    queries: list[str] | None = None,
    query_embedding: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    if top_k is None:
        top_k = settings.retrieval_top_k
    # `alpha` est déprécié et ignoré : la fusion utilise désormais RRF (rang).
    search_top_k = top_k * 2

    if queries is None:
        queries = expand_queries(query, history=history)

    # Embeddings : batch si plusieurs variantes (T2.1 query rewriting).
    query_vectors: dict[str, np.ndarray] = {}
    try:
        query_vectors = _build_query_vectors(queries, query, query_embedding)
    except Exception as e:
        logger.warning("Embedding failed, degrading to BM25-only search: %s", e)

    # HyDE : vecteur additionnel depuis un passage hypothétique (T2.2).
    hyde_vector: np.ndarray | None = None
    if settings.enable_hyde:
        hyde_vector = get_hyde_embedding_vector(query, history=history)

    futures: list[tuple[str, Any]] = []
    for q in queries:
        qv = query_vectors.get(q)
        if qv is not None:
            futures.append(
                (
                    "vector",
                    _executor.submit(
                        _vector_search_sync,
                        qv,
                        organization_id,
                        search_top_k,
                        filters,
                        domain,
                        allowed_document_ids,
                    ),
                )
            )
        futures.append(
            (
                "bm25",
                _executor.submit(
                    _bm25_search_sync,
                    organization_id,
                    q,
                    search_top_k,
                    filters,
                    allowed_document_ids,
                    domain,
                ),
            )
        )

    if hyde_vector is not None:
        futures.append(
            (
                "vector",
                _executor.submit(
                    _vector_search_sync,
                    hyde_vector,
                    organization_id,
                    search_top_k,
                    filters,
                    domain,
                    allowed_document_ids,
                ),
            )
        )

    vector_result_lists: list[list[dict[str, Any]]] = []
    bm25_result_lists: list[list[dict[str, Any]]] = []
    for kind, future in futures:
        results = future.result()
        if kind == "vector":
            vector_result_lists.append(results)
        else:
            bm25_result_lists.append(results)
    
    # Reciprocal Rank Fusion (RRF) : score = somme sur chaque liste de
    # 1 / (k + rang). Les listes vector_results et bm25_results sont déjà
    # triées par score décroissant -> le rang = l'index. RRF n'utilise que
    # l'ordre, jamais les scores bruts : immune aux outliers (un score BM25
    # extrême ne peut plus écraser le reste, contrairement à la normalisation
    # min-max), et pas de problème d'échelles incompatibles cosinus vs BM25.
    rrf_k = settings.rrf_k
    chunk_map: dict[str, dict[str, Any]] = {}

    def _accumulate(results: list[dict[str, Any]], score_field: str) -> None:
        for rank, result in enumerate(results):
            chunk_id = str(result["chunk_id"])
            entry = chunk_map.get(chunk_id)
            if entry is None:
                entry = {
                    "chunk_id": result["chunk_id"],
                    "text": result["text"],
                    "metadata": dict(result.get("metadata") or {}),
                    "rrf_score": 0.0,
                    "vector_score": 0.0,
                    "bm25_score": 0.0,
                }
                chunk_map[chunk_id] = entry
            entry["rrf_score"] += 1.0 / (rrf_k + rank)
            # Score brut conservé pour debug/observabilité (non utilisé au tri).
            entry[score_field] = result.get("score", 0.0)

    for vector_results in vector_result_lists:
        _accumulate(vector_results, "vector_score")
    for bm25_results in bm25_result_lists:
        _accumulate(bm25_results, "bm25_score")

    final_results = [
        {
            "chunk_id": e["chunk_id"],
            "text": e["text"],
            "score": e["rrf_score"],
            "metadata": e["metadata"],
            "vector_score": e["vector_score"],
            "bm25_score": e["bm25_score"],
        }
        for e in chunk_map.values()
    ]

    final_results.sort(key=lambda x: x["score"], reverse=True)
    
    if settings.enable_reranking and len(final_results) > 1:
        try:
            reranked = reranker.rerank(
                query=query,
                passages=final_results,
                top_k=top_k,
            )
            for result in reranked:
                if "final_score" in result:
                    result["score"] = result["final_score"]
            final_results = reranked
        except Exception:
            final_results = final_results[:top_k]
    else:
        final_results = final_results[:top_k]
    
    return final_results

