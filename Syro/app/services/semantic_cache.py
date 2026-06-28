"""Cache sémantique retrieval (T4.5) — hit si similarité embedding ≥ seuil."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..config import settings

logger = logging.getLogger(__name__)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _scope_key(
    organization_id: int,
    domain: str | None,
    allowed_document_ids: frozenset[int] | None,
) -> tuple[int, str, frozenset[int] | None]:
    return (organization_id, domain or "", allowed_document_ids)


@dataclass
class _CacheEntry:
    query: str
    embedding: np.ndarray
    chunks: list[dict[str, Any]]
    created_at: float = field(default_factory=time.time)


class SemanticCache:
    """Cache in-process par org/domain/permissions (Redis = évolution future)."""

    def __init__(self) -> None:
        self._entries: dict[tuple, list[_CacheEntry]] = {}

    def lookup_retrieval(
        self,
        organization_id: int,
        query: str,
        query_embedding: np.ndarray,
        *,
        domain: str | None = None,
        allowed_document_ids: frozenset[int] | None = None,
    ) -> tuple[list[dict[str, Any]] | None, str]:
        """Retourne (chunks, status) avec status hit|miss|disabled."""
        if not settings.enable_semantic_cache:
            return None, "disabled"

        key = _scope_key(organization_id, domain, allowed_document_ids)
        now = time.time()
        ttl = settings.semantic_cache_ttl_seconds
        threshold = settings.semantic_cache_similarity_threshold

        entries = self._entries.get(key, [])
        alive: list[_CacheEntry] = []
        best: _CacheEntry | None = None
        best_sim = -1.0

        for entry in entries:
            if now - entry.created_at > ttl:
                continue
            alive.append(entry)
            sim = _cosine_similarity(query_embedding, entry.embedding)
            if sim >= threshold and sim > best_sim:
                best = entry
                best_sim = sim

        self._entries[key] = alive

        if best is not None:
            logger.debug(
                "Semantic cache HIT (sim=%.3f) org=%s query=%r",
                best_sim,
                organization_id,
                query[:60],
            )
            return [dict(c) for c in best.chunks], "hit"

        return None, "miss"

    def store_retrieval(
        self,
        organization_id: int,
        query: str,
        query_embedding: np.ndarray,
        chunks: list[dict[str, Any]],
        *,
        domain: str | None = None,
        allowed_document_ids: frozenset[int] | None = None,
    ) -> None:
        if not settings.enable_semantic_cache or not chunks:
            return

        key = _scope_key(organization_id, domain, allowed_document_ids)
        entry = _CacheEntry(
            query=query,
            embedding=query_embedding.copy(),
            chunks=[dict(c) for c in chunks],
        )
        bucket = self._entries.setdefault(key, [])
        bucket.append(entry)

        max_entries = settings.semantic_cache_max_entries
        if len(bucket) > max_entries:
            bucket.sort(key=lambda e: e.created_at)
            del bucket[: len(bucket) - max_entries]

    def invalidate_organization(self, organization_id: int) -> None:
        keys = [k for k in self._entries if k[0] == organization_id]
        for key in keys:
            del self._entries[key]

    def invalidate_domain(self, organization_id: int, domain: str) -> None:
        key_prefix = (organization_id, domain, None)
        keys = [k for k in self._entries if k[0] == key_prefix[0] and k[1] == domain]
        for key in keys:
            del self._entries[key]


semantic_cache = SemanticCache()
