"""Pertinence d'un chunk en [0, 1], quelle que soit l'étape qui l'a scoré."""

from __future__ import annotations

from typing import Any

from ..config import settings


def rrf_strong_score() -> float:
    """Score RRF d'un chunk classé 1er par le dense ET par BM25 (= pertinence 1.0)."""
    return 2.0 / (settings.rrf_k + 1)


def chunk_relevance(chunk: dict[str, Any]) -> float:
    """Score cross-encoder s'il existe (déjà une probabilité), sinon RRF normalisé."""
    if chunk.get("rerank_score") is not None:
        return float(chunk["rerank_score"])
    rrf = chunk.get("rrf_score", chunk.get("score", 0.0))
    return min(float(rrf) / rrf_strong_score(), 1.0)
