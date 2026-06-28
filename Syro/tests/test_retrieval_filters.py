"""Tests filtrage retrieval (T2.4) et historique (T2.5)."""

from unittest.mock import Mock, patch

import numpy as np

from app.services.bm25_search import BM25Search, _domain_from_tags
from app.services.retrieval_filters import build_retrieval_scope


class TestDomainFromTags:
    def test_json_array(self):
        assert _domain_from_tags('["tech", "mlops"]') == "tech"

    def test_plain_string(self):
        assert _domain_from_tags("tech") == "tech"


class TestBuildRetrievalScope:
    def test_without_user_skips_permissions(self):
        scope = build_retrieval_scope(None, organization_id=1)
        assert scope.allowed_document_ids is None

    @patch("app.services.retrieval_filters.get_accessible_document_ids")
    def test_with_user_applies_permissions(self, mock_ids):
        mock_ids.return_value = frozenset({1, 2})
        scope = build_retrieval_scope(user_id=5, organization_id=1)
        assert scope.allowed_document_ids == frozenset({1, 2})


class TestBm25PreFilter:
    def test_empty_allowed_returns_nothing(self):
        bm25 = BM25Search()
        bm25._indexes[1] = (Mock(), [{"chunk_id": 1, "text": "x", "document_id": 9, "source_type": "", "tags": "", "domain": ""}])
        bm25._fingerprints[1] = (1, 1)
        assert bm25.search(1, "q", allowed_document_ids=frozenset()) == []

    @patch.object(BM25Search, "_content_fingerprint", return_value=(3, 3))
    def test_filters_by_document_and_domain(self, _fp):
        bm25 = BM25Search()
        mock_bm25 = Mock()
        chunk_data = [
            {"chunk_id": 1, "text": "a", "document_id": 10, "source_type": "", "tags": '["tech"]', "domain": "tech"},
            {"chunk_id": 2, "text": "b", "document_id": 11, "source_type": "", "tags": '["mlops"]', "domain": "mlops"},
            {"chunk_id": 3, "text": "c", "document_id": 12, "source_type": "", "tags": '["tech"]', "domain": "tech"},
        ]
        mock_bm25.get_scores.return_value = [0.1, 0.9, 0.5]
        bm25._indexes[1] = (mock_bm25, chunk_data)
        bm25._fingerprints[1] = (3, 3)

        results = bm25.search(
            1,
            "q",
            allowed_document_ids=frozenset({10, 12}),
            domain="tech",
        )
        assert [r["chunk_id"] for r in results] == [3, 1]


class TestVectorStoreAllowedDocs:
    @patch("app.services.vector_store._get_shared_client")
    def test_empty_allowed_skips_qdrant(self, mock_client):
        from app.services.vector_store import VectorStore

        vs = VectorStore()
        out = vs.search(
            query_vector=np.array([0.1, 0.2]),
            organization_id=1,
            allowed_document_ids=frozenset(),
        )
        assert out == []
        mock_client.assert_not_called()
