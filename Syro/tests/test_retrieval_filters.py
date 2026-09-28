"""Filtres de retrieval (permissions, domaine) et BM25 sur une vraie base."""

from unittest.mock import patch

import numpy as np

from app.services.bm25_search import BM25Search, tokenize
from app.services.retrieval_filters import build_retrieval_scope
from app.services.vector_store import build_filter
from tests.conftest import add_document


class TestTokenize:
    def test_folds_accents_and_drops_stopwords(self):
        assert tokenize("L'Évaluation des modèles de la RAG") == [
            "evaluation",
            "modeles",
            "rag",
        ]


class TestBuildRetrievalScope:
    def test_without_user_skips_permissions(self):
        assert build_retrieval_scope(None, organization_id=1).allowed_document_ids is None

    @patch("app.services.retrieval_filters.get_accessible_document_ids")
    def test_with_user_applies_permissions(self, mock_ids):
        mock_ids.return_value = frozenset({1, 2})
        scope = build_retrieval_scope(user_id=5, organization_id=1)
        assert scope.allowed_document_ids == frozenset({1, 2})


class TestBm25:
    def test_domain_filter_uses_document_domain(self, syro_db):
        tech = add_document(syro_db, 1, "qdrant.md", "Qdrant stocke les vecteurs", "tech")
        add_document(syro_db, 1, "mlflow.md", "MLflow stocke les runs", "mlops")
        bm25 = BM25Search()

        hits = bm25.search(1, "stocke", domain="tech")
        assert [h["metadata"]["document_id"] for h in hits] == [tech]
        # general / None = tous les documents
        assert len(bm25.search(1, "stocke", domain="general")) == 2
        assert len(bm25.search(1, "stocke")) == 2

    def test_user_tags_do_not_affect_domain(self, syro_db):
        """Régression : le 1er tag (« python ») était pris pour le domaine."""
        import sqlite3

        doc = add_document(syro_db, 1, "a.md", "fastapi et pydantic", "tech")
        conn = sqlite3.connect(syro_db)
        conn.execute("UPDATE documents SET tags = '[\"python\"]' WHERE id = ?", (doc,))
        conn.commit()
        conn.close()
        assert len(BM25Search().search(1, "fastapi", domain="tech")) == 1

    def test_no_shared_term_returns_nothing(self, syro_db):
        add_document(syro_db, 1, "a.md", "Qdrant stocke les vecteurs")
        assert BM25Search().search(1, "kubernetes helm") == []

    def test_single_chunk_corpus_still_matches(self, syro_db):
        """BM25Okapi a un IDF négatif sur 1 document : on ne filtre pas sur score > 0."""
        add_document(syro_db, 1, "a.md", "Qdrant stocke les vecteurs")
        assert len(BM25Search().search(1, "qdrant")) == 1

    def test_permissions_and_org_isolation(self, syro_db):
        allowed = add_document(syro_db, 1, "a.md", "secret roadmap")
        add_document(syro_db, 1, "b.md", "secret salaries")
        add_document(syro_db, 2, "c.md", "secret other org")
        bm25 = BM25Search()
        hits = bm25.search(1, "secret", allowed_document_ids=frozenset({allowed}))
        assert [h["metadata"]["document_id"] for h in hits] == [allowed]
        assert bm25.search(1, "secret", allowed_document_ids=frozenset()) == []

    def test_index_refreshes_when_another_process_ingests(self, syro_db):
        bm25 = BM25Search()
        assert bm25.search(1, "helm") == []
        add_document(syro_db, 1, "k8s.md", "helm charts kubernetes")  # « worker »
        assert len(bm25.search(1, "helm")) == 1


class TestQdrantFilter:
    def _keys(self, flt):
        return {c.key for c in flt.must}

    def test_general_domain_has_no_domain_condition(self):
        assert self._keys(build_filter(1, "general")) == {"organization_id"}
        assert self._keys(build_filter(1, None)) == {"organization_id"}

    def test_domain_and_permissions(self):
        flt = build_filter(1, "tech", frozenset({3, 1}))
        assert self._keys(flt) == {"organization_id", "domain", "document_id"}

    @patch("app.services.vector_store._get_shared_client")
    def test_empty_allowed_skips_qdrant(self, mock_client):
        from app.services.vector_store import VectorStore

        out = VectorStore().search(
            query_vector=np.array([0.1, 0.2]),
            organization_id=1,
            allowed_document_ids=frozenset(),
        )
        assert out == []
        mock_client.assert_not_called()
