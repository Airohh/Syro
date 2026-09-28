"""Cache sémantique retrieval (T4.5) — hit si similarité embedding ≥ seuil."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..config import settings

logger = logging.getLogger(__name__)

CacheScopeKey = tuple[Any, ...]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _copy_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Copier aussi le metadata imbriqué : self_rag y écrit en place (self_rag_relevance),
    # sinon la mutation contamine les entrées cachées partagées entre requêtes.
    return [{**c, "metadata": dict(c.get("metadata") or {})} for c in chunks]


def _filters_key(filters: dict[str, Any] | None) -> tuple[tuple[str, Any], ...]:
    if not filters:
        return ()
    return tuple(sorted(filters.items()))


def _history_key(history: Sequence[str] | None) -> tuple[str, ...]:
    if not history:
        return ()
    return tuple(history[-3:])


def _pipeline_key() -> tuple[Any, ...]:
    """Dimensions qui changent le résultat du retrieval hybride."""
    return (
        settings.enable_query_rewriting,
        settings.enable_hyde,
        settings.enable_crag,
        settings.enable_query_decomposition,
        settings.enable_reranking,
        settings.rerank_min_score,
        settings.rrf_k,
        settings.retrieval_top_k,
        settings.rerank_top_k,
    )


def _scope_key(
    organization_id: int,
    domain: str | None,
    allowed_document_ids: frozenset[int] | None,
    filters: dict[str, Any] | None = None,
    history: Sequence[str] | None = None,
    version: Any = None,
) -> CacheScopeKey:
    # `version` = empreinte du contenu indexé : une ingestion faite par le
    # worker (autre processus) change la clé → pas de résultat périmé servi.
    return (
        organization_id,
        domain or "",
        allowed_document_ids,
        _filters_key(filters),
        _history_key(history),
        _pipeline_key(),
        version,
    )


@dataclass
class _CacheEntry:
    query: str
    embedding: np.ndarray
    chunks: list[dict[str, Any]]
    created_at: float = field(default_factory=time.time)


class SemanticCache:
    """Cache in-process par org/domain/permissions (Redis = évolution future)."""

    def __init__(self) -> None:
        self._entries: dict[CacheScopeKey, list[_CacheEntry]] = {}
        self._lock = threading.Lock()  # requêtes servies en parallèle (threadpool)

    def lookup_retrieval(
        self,
        organization_id: int,
        query: str,
        query_embedding: np.ndarray,
        *,
        domain: str | None = None,
        allowed_document_ids: frozenset[int] | None = None,
        filters: dict[str, Any] | None = None,
        history: Sequence[str] | None = None,
        version: Any = None,
    ) -> tuple[list[dict[str, Any]] | None, str]:
        """Retourne (chunks, status) avec status hit|miss|disabled."""
        if not settings.enable_semantic_cache:
            return None, "disabled"

        key = _scope_key(
            organization_id,
            domain,
            allowed_document_ids,
            filters=filters,
            history=history,
            version=version,
        )
        now = time.time()
        ttl = settings.semantic_cache_ttl_seconds
        threshold = settings.semantic_cache_similarity_threshold

        best: _CacheEntry | None = None
        best_sim = -1.0
        with self._lock:
            alive = [e for e in self._entries.get(key, []) if now - e.created_at <= ttl]
            self._entries[key] = alive
        for entry in alive:
            sim = _cosine_similarity(query_embedding, entry.embedding)
            if sim >= threshold and sim > best_sim:
                best = entry
                best_sim = sim

        if best is not None:
            logger.debug(
                "Semantic cache HIT (sim=%.3f) org=%s query=%r",
                best_sim,
                organization_id,
                query[:60],
            )
            return _copy_chunks(best.chunks), "hit"

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
        filters: dict[str, Any] | None = None,
        history: Sequence[str] | None = None,
        version: Any = None,
    ) -> None:
        if not settings.enable_semantic_cache or not chunks:
            return

        key = _scope_key(
            organization_id,
            domain,
            allowed_document_ids,
            filters=filters,
            history=history,
            version=version,
        )
        entry = _CacheEntry(
            query=query,
            embedding=query_embedding.copy(),
            chunks=_copy_chunks(chunks),
        )
        with self._lock:
            bucket = self._entries.setdefault(key, [])
            bucket.append(entry)
            max_entries = settings.semantic_cache_max_entries
            if len(bucket) > max_entries:
                del bucket[: len(bucket) - max_entries]  # entrées ajoutées dans l'ordre

    def invalidate_organization(self, organization_id: int) -> None:
        with self._lock:
            for key in [k for k in self._entries if k[0] == organization_id]:
                del self._entries[key]


semantic_cache = SemanticCache()
