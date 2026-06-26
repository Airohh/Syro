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

def normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        # Valeur neutre, pas 1.0 : un résultat unique (ou des ex æquo) ne doit
        # pas se voir attribuer le score maximal — sinon un domaine pauvre en
        # résultats écrase les domaines riches lors de la fusion multi-domaine.
        return [0.5] * len(scores)
    return [(s - min_score) / (max_score - min_score) for s in scores]

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
    if alpha is None:
        alpha = settings.hybrid_search_alpha
    
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
    
    chunk_map: dict[str, dict[str, Any]] = {}
    
    if vector_results:
        vector_scores = [r["score"] for r in vector_results]
        normalized_vector_scores = normalize_scores(vector_scores)
        for i, result in enumerate(vector_results):
            chunk_id = str(result["chunk_id"])
            chunk_map[chunk_id] = {
                "chunk_id": result["chunk_id"],
                "text": result["text"],
                "metadata": result["metadata"],
                "vector_score": normalized_vector_scores[i],
                "bm25_score": 0.0,
            }
    
    if bm25_results:
        bm25_scores = [r["score"] for r in bm25_results]
        normalized_bm25_scores = normalize_scores(bm25_scores)
        for i, result in enumerate(bm25_results):
            chunk_id = str(result["chunk_id"])
            if chunk_id in chunk_map:
                chunk_map[chunk_id]["bm25_score"] = normalized_bm25_scores[i]
            else:
                chunk_map[chunk_id] = {
                    "chunk_id": result["chunk_id"],
                    "text": result["text"],
                    "metadata": result["metadata"],
                    "vector_score": 0.0,
                    "bm25_score": normalized_bm25_scores[i],
                }
    
    final_results = []
    for chunk_data in chunk_map.values():
        hybrid_score = (
            alpha * chunk_data["vector_score"]
            + (1 - alpha) * chunk_data["bm25_score"]
        )
        final_results.append({
            "chunk_id": chunk_data["chunk_id"],
            "text": chunk_data["text"],
            "score": hybrid_score,
            "metadata": chunk_data["metadata"],
            "vector_score": chunk_data["vector_score"],
            "bm25_score": chunk_data["bm25_score"],
        })
    
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

