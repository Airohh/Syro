"""Recherche hybride : dense (Qdrant) + lexicale (BM25), fusion RRF, reranking.

    question ─┬─► embedding ─► Qdrant ─┐
              └─► BM25 ────────────────┼─► RRF ─► top-N candidats ─► cross-encoder ─► top-k
    (+ reformulations / HyDE optionnelles = listes supplémentaires dans la RRF)
"""

from __future__ import annotations

import atexit
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

from ..config import settings
from .bm25_search import bm25_search
from .hyde import get_hyde_embedding_vector
from .llm import get_embedding_vector, get_embedding_vectors
from .query_rewriter import expand_queries
from .reranker import reranker
from .vector_store import VectorStore, VectorStoreError

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)
atexit.register(_executor.shutdown, wait=False)


def _vector_search(
    query_vector: np.ndarray,
    organization_id: int,
    top_k: int,
    filters: dict[str, Any] | None,
    domain: str | None,
    allowed_document_ids: frozenset[int] | None,
) -> list[dict[str, Any]]:
    try:
        return VectorStore().search(
            query_vector=query_vector,
            organization_id=organization_id,
            top_k=top_k,
            filters=filters,
            domain=domain,
            allowed_document_ids=allowed_document_ids,
        )
    except VectorStoreError as e:
        logger.warning("Vector search failed, continuing with BM25 only: %s", e)
        return []


def _build_query_vectors(
    queries: list[str],
    original_query: str,
    query_embedding: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Embeddings par variante ; réutilise query_embedding pour la question d'origine."""
    vectors: dict[str, np.ndarray] = {}
    pending: list[str] = []
    for q in queries:
        if query_embedding is not None and q == original_query:
            vectors[q] = query_embedding
        else:
            pending.append(q)
    if len(pending) == 1:
        vectors[pending[0]] = get_embedding_vector(pending[0])
    elif pending:
        vectors.update(zip(pending, get_embedding_vectors(pending)))
    return vectors


def fuse_rrf(
    result_lists: list[tuple[str, list[dict[str, Any]]]],
    rrf_k: int | None = None,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion : score = Σ 1 / (k + rang), rang à partir de 1.

    N'utilise que l'ordre des listes, jamais les scores bruts : pas de
    problème d'échelles incompatibles (cosinus vs BM25) ni d'outliers.
    `result_lists` = [(source, résultats triés)], source ∈ {vector, bm25}.
    """
    k = settings.rrf_k if rrf_k is None else rrf_k
    fused: dict[str, dict[str, Any]] = {}
    for source, results in result_lists:
        for rank, result in enumerate(results, start=1):
            key = str(result["chunk_id"])
            entry = fused.get(key)
            if entry is None:
                entry = {
                    "chunk_id": result["chunk_id"],
                    "text": result["text"],
                    "metadata": dict(result.get("metadata") or {}),
                    "rrf_score": 0.0,
                    "vector_score": None,
                    "bm25_score": None,
                }
                fused[key] = entry
            entry["rrf_score"] += 1.0 / (k + rank)
            score_field = f"{source}_score"
            if score_field in entry and entry[score_field] is None:
                entry[score_field] = result.get("score")
    ranked = sorted(fused.values(), key=lambda e: e["rrf_score"], reverse=True)
    for entry in ranked:
        entry["score"] = entry["rrf_score"]
    return ranked


def rerank_or_truncate(
    query: str, candidates: list[dict[str, Any]], top_k: int
) -> list[dict[str, Any]]:
    """Cross-encoder si activé et disponible ; sinon ordre RRF."""
    if settings.enable_reranking and candidates:
        reranked = reranker.rerank(query, candidates, top_k=top_k)
        if reranked is not None:
            return reranked
    return candidates[:top_k]


def hybrid_search(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    domain: str | None = None,
    history: list[str] | None = None,
    allowed_document_ids: frozenset[int] | None = None,
    queries: list[str] | None = None,
    query_embedding: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    """Retourne au plus `top_k` chunks, triés par pertinence décroissante."""
    if top_k is None:
        top_k = settings.rerank_top_k
    # Plus de candidats que le top_k final : c'est le reranker qui tranche.
    candidates_k = max(settings.retrieval_top_k, top_k)

    if queries is None:
        queries = expand_queries(query, history=history)

    query_vectors: dict[str, np.ndarray] = {}
    try:
        query_vectors = _build_query_vectors(queries, query, query_embedding)
    except Exception as e:
        logger.warning("Embedding failed, degrading to BM25-only search: %s", e)

    hyde_vector = (
        get_hyde_embedding_vector(query, history=history)
        if settings.enable_hyde
        else None
    )

    vector_args = (organization_id, candidates_k, filters, domain, allowed_document_ids)
    futures: list[tuple[str, Any]] = []
    for q in queries:
        if q in query_vectors:
            futures.append(
                (
                    "vector",
                    _executor.submit(_vector_search, query_vectors[q], *vector_args),
                )
            )
        futures.append(
            (
                "bm25",
                _executor.submit(
                    bm25_search.search,
                    organization_id=organization_id,
                    query=q,
                    top_k=candidates_k,
                    filters=filters,
                    allowed_document_ids=allowed_document_ids,
                    domain=domain,
                ),
            )
        )
    if hyde_vector is not None:
        futures.append(
            ("vector", _executor.submit(_vector_search, hyde_vector, *vector_args))
        )

    result_lists = [(source, future.result()) for source, future in futures]
    candidates = fuse_rrf(result_lists)[:candidates_k]
    return rerank_or_truncate(query, candidates, top_k)
