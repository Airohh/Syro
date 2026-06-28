"""Self-RAG — filtrage de pertinence par chunk (T3.2).

Score IsRel heuristique (overlap lexical + force retrieval) ; drop sous seuil ;
garde entre min et max chunks pour réduire le bruit dans le prompt.
"""

from __future__ import annotations

import logging
from typing import Any

from ..config import settings
from .crag import lexical_overlap

logger = logging.getLogger(__name__)

_RRF_STRONG_SCORE = 0.05


def chunk_relevance_score(query: str, chunk: dict[str, Any]) -> float:
    """Proxy IsRel [0–1] : overlap question↔chunk + score retrieval normalisé."""
    overlap = lexical_overlap(query, [chunk["text"]])
    strength = min(float(chunk.get("score", 0.0)) / _RRF_STRONG_SCORE, 1.0)
    return 0.6 * overlap + 0.4 * strength


def filter_relevant_chunks(
    query: str,
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Filtre les chunks peu pertinents avant injection dans le prompt LLM.

    - Drop si score < self_rag_min_relevance
    - Garde au moins self_rag_min_chunks (meilleurs scores)
    - Plafonne à self_rag_max_chunks
    """
    if not settings.enable_self_rag or not chunks:
        return chunks

    scored = [(chunk_relevance_score(query, c), c) for c in chunks]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    min_k = settings.self_rag_min_chunks
    max_k = settings.self_rag_max_chunks
    threshold = settings.self_rag_min_relevance

    above = [pair for pair in scored if pair[0] >= threshold]
    kept_pairs = above[:max_k] if len(above) >= min_k else scored[:min_k]

    dropped = len(chunks) - len(kept_pairs)
    if dropped:
        logger.info(
            "Self-RAG filtered %d/%d chunks (kept %d, threshold=%.2f)",
            dropped,
            len(chunks),
            len(kept_pairs),
            threshold,
        )

    for rel, chunk in kept_pairs:
        chunk["metadata"] = {**(chunk.get("metadata") or {}), "self_rag_relevance": round(rel, 4)}

    return [chunk for _, chunk in kept_pairs]
