"""Hybrid search combining vector similarity and BM25 lexical search."""

from __future__ import annotations

import atexit
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

from ..config import settings
from .llm import get_embedding_vector
from .vector_store import VectorStore, VectorStoreError
from .bm25_search import bm25_search
from .reranker import reranker

_executor = ThreadPoolExecutor(max_workers=4)
atexit.register(_executor.shutdown, wait=False)

def _vector_search_sync(
    query_vector: np.ndarray,
    organization_id: int,
    top_k: int,
    filters: dict[str, Any] | None,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    vector_store = VectorStore()
    try:
        return vector_store.search(
            query_vector=query_vector,
            organization_id=organization_id,
            top_k=top_k,
            filters=filters,
            domain=domain,
        )
    except VectorStoreError:
        return []

def _bm25_search_sync(
    organization_id: int,
    query: str,
    top_k: int,
    filters: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    return bm25_search.search(
        organization_id=organization_id,
        query=query,
        top_k=top_k,
        filters=filters,
    )

def hybrid_search(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    alpha: float | None = None,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    if top_k is None:
        top_k = settings.retrieval_top_k
    # `alpha` est déprécié et ignoré : la fusion utilise désormais RRF (rang).
    search_top_k = top_k * 2

    # Embedding failure (LLM provider down, timeout) must not kill the request:
    # degrade to BM25-only lexical search.
    try:
        query_vector = get_embedding_vector(query)
    except Exception as e:
        logger.warning("Embedding failed, degrading to BM25-only search: %s", e)
        query_vector = None

    future_vector = None
    if query_vector is not None:
        future_vector = _executor.submit(
            _vector_search_sync,
            query_vector,
            organization_id,
            search_top_k,
            filters,
            domain,
        )
    future_bm25 = _executor.submit(
        _bm25_search_sync,
        organization_id,
        query,
        search_top_k,
        filters,
    )

    vector_results = future_vector.result() if future_vector else []
    bm25_results = future_bm25.result()
    
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
                    "metadata": result["metadata"],
                    "rrf_score": 0.0,
                    "vector_score": 0.0,
                    "bm25_score": 0.0,
                }
                chunk_map[chunk_id] = entry
            entry["rrf_score"] += 1.0 / (rrf_k + rank)
            # Score brut conservé pour debug/observabilité (non utilisé au tri).
            entry[score_field] = result.get("score", 0.0)

    _accumulate(vector_results, "vector_score")
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

