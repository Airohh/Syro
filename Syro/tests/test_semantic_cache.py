"""Tests cache sémantique retrieval (T4.5)."""

import time
from unittest.mock import patch

import numpy as np

from app.services.semantic_cache import SemanticCache, _cosine_similarity


def _chunk(cid: str) -> dict:
    return {"chunk_id": cid, "text": f"text {cid}", "score": 0.1, "metadata": {}}


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = np.array([1.0, 0.0, 0.0])
        assert _cosine_similarity(v, v) == 1.0


class TestSemanticCache:
    @patch("app.services.semantic_cache.settings")
    def test_disabled_returns_miss(self, mock_settings):
        mock_settings.enable_semantic_cache = False
        cache = SemanticCache()
        vec = np.array([1.0, 0.0])
        hit, status = cache.lookup_retrieval(1, "q", vec)
        assert hit is None
        assert status == "disabled"

    @patch("app.services.semantic_cache.settings")
    def test_hit_on_similar_query(self, mock_settings):
        mock_settings.enable_semantic_cache = True
        mock_settings.semantic_cache_similarity_threshold = 0.99
        mock_settings.semantic_cache_ttl_seconds = 3600
        mock_settings.semantic_cache_max_entries = 100

        cache = SemanticCache()
        base = np.array([1.0, 0.0, 0.0])
        cache.store_retrieval(1, "kubernetes pods", base, [_chunk("1")])

        similar = np.array([0.99, 0.01, 0.0])
        similar = similar / np.linalg.norm(similar)
        hit, status = cache.lookup_retrieval(1, "k8s pods", similar)

        assert status == "hit"
        assert hit is not None
        assert hit[0]["chunk_id"] == "1"

    @patch("app.services.semantic_cache.settings")
    def test_miss_on_different_query(self, mock_settings):
        mock_settings.enable_semantic_cache = True
        mock_settings.semantic_cache_similarity_threshold = 0.95
        mock_settings.semantic_cache_ttl_seconds = 3600
        mock_settings.semantic_cache_max_entries = 100

        cache = SemanticCache()
        cache.store_retrieval(1, "java spring", np.array([1.0, 0.0]), [_chunk("1")])

        orthogonal = np.array([0.0, 1.0])
        hit, status = cache.lookup_retrieval(1, "python django", orthogonal)

        assert status == "miss"
        assert hit is None

    @patch("app.services.semantic_cache.settings")
    def test_invalidate_domain_clears(self, mock_settings):
        mock_settings.enable_semantic_cache = True
        mock_settings.semantic_cache_similarity_threshold = 0.9
        mock_settings.semantic_cache_ttl_seconds = 3600
        mock_settings.semantic_cache_max_entries = 100

        cache = SemanticCache()
        vec = np.array([1.0, 0.0])
        cache.store_retrieval(1, "q", vec, [_chunk("1")], domain="tech")
        cache.invalidate_domain(1, "tech")

        hit, status = cache.lookup_retrieval(1, "q", vec, domain="tech")
        assert hit is None
        assert status == "miss"

    @patch("app.services.semantic_cache.settings")
    def test_expired_entry_is_miss(self, mock_settings):
        mock_settings.enable_semantic_cache = True
        mock_settings.semantic_cache_similarity_threshold = 0.9
        mock_settings.semantic_cache_ttl_seconds = 1
        mock_settings.semantic_cache_max_entries = 100

        cache = SemanticCache()
        vec = np.array([1.0, 0.0])
        cache.store_retrieval(1, "q", vec, [_chunk("1")])
        # Forcer expiration
        key = (1, "", None)
        cache._entries[key][0].created_at = time.time() - 10

        hit, _ = cache.lookup_retrieval(1, "q", vec)
        assert hit is None
