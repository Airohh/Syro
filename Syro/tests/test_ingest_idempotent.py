"""L'ingestion du corpus d'éval est idempotente (pas de doublons sur re-run)."""

from unittest.mock import MagicMock, patch

from evaluation import ingest_corpus


class TestClearPreviousCorpus:
    @patch.object(ingest_corpus, "VectorStore")
    @patch.object(ingest_corpus, "db_session")
    def test_purges_prior_docs_vectors_and_rows(self, mock_db_session, mock_vs):
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = [{"id": 1}, {"id": 2}]
        store = mock_vs.return_value

        ingest_corpus.clear_previous_corpus()

        assert store.delete_document.call_count == 2
        store.delete_document.assert_any_call(1)
        store.delete_document.assert_any_call(2)
        assert any("DELETE" in str(c) for c in mock_db.execute.call_args_list)

    @patch.object(ingest_corpus, "VectorStore")
    @patch.object(ingest_corpus, "db_session")
    def test_noop_when_no_prior_docs(self, mock_db_session, mock_vs):
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = []

        ingest_corpus.clear_previous_corpus()

        mock_vs.assert_not_called()
