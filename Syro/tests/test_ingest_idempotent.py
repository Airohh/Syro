"""Non-régression : l'ingestion du corpus d'éval est idempotente (pas de
doublons Qdrant/DB sur re-run)."""

from unittest.mock import MagicMock, patch

from evaluation import ingest_corpus


class TestDomainFromTags:
    def test_extracts_domain_tag(self):
        assert ingest_corpus._domain_from_tags('["domain:tech"]') == "tech"

    def test_picks_domain_among_others(self):
        assert ingest_corpus._domain_from_tags('["x", "domain:legal"]') == "legal"

    def test_none_and_garbage_return_none(self):
        assert ingest_corpus._domain_from_tags(None) is None
        assert ingest_corpus._domain_from_tags("[]") is None
        assert ingest_corpus._domain_from_tags("not-json") is None


class TestClearPreviousCorpus:
    @patch.object(ingest_corpus, "VectorStore")
    @patch.object(ingest_corpus, "db_session")
    def test_purges_prior_docs_chunks_and_rows(self, mock_db_session, mock_vs):
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = [
            {"id": 1, "tags": '["domain:tech"]'},
            {"id": 2, "tags": '["domain:mlops"]'},
        ]
        store = mock_vs.return_value

        ingest_corpus.clear_previous_corpus()

        # Chunks Qdrant supprimés par document, avec le bon domaine.
        assert store.delete_chunks_by_document.call_count == 2
        store.delete_chunks_by_document.assert_any_call(1, domain="tech")
        store.delete_chunks_by_document.assert_any_call(2, domain="mlops")
        # Lignes DB supprimées.
        assert any("DELETE" in str(c) for c in mock_db.execute.call_args_list)

    @patch.object(ingest_corpus, "VectorStore")
    @patch.object(ingest_corpus, "db_session")
    def test_noop_when_no_prior_docs(self, mock_db_session, mock_vs):
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = []

        ingest_corpus.clear_previous_corpus()

        mock_vs.assert_not_called()  # pas de client Qdrant si rien à purger
