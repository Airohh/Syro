"""Helpers partagés pour scorer la pertinence retrieval (CRAG, Self-RAG)."""

from __future__ import annotations

# Score RRF typique d'un bon hit ; sert à normaliser en [0, 1].
RRF_STRONG_SCORE = 0.05


def normalize_rrf_score(score: float) -> float:
    return min(float(score) / RRF_STRONG_SCORE, 1.0)
