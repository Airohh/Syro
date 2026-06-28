"""Non-régression T0.3 : cœur d'ingestion partagé (infer_metadata + run_ingestion)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.ingestion import infer_metadata, run_ingestion


class TestInferMetadata:
    def test_type_from_filename_and_forced_domain(self):
        md = infer_metadata("snowflake_guide.md", [], "corpus", domain="tech")
        assert md["type"] == "snowflake"
        assert md["domain"] == "tech"
        assert md["source_type"] == "corpus"
        assert md["difficulty"] == "intermediate"

    def test_difficulty_from_tags(self):
        assert infer_metadata("x.md", ["Beginner"], "u")["difficulty"] == "beginner"
        assert infer_metadata("x.md", ["expert"], "u")["difficulty"] == "expert"

    def test_type_general_fallback_and_no_domain_key(self):
        md = infer_metadata("notes.md", [], "u")
        assert md["type"] == "general"
        assert "domain" not in md


class TestRunIngestion:
    @patch("app.services.ingestion.index_document_content", return_value=7)
    @patch("app.services.ingestion.db_session")
    def test_indexes_with_inferred_metadata(self, mock_db_session, mock_index, tmp_path):
        f = tmp_path / "airflow_dag.md"
        f.write_text("contenu non vide", encoding="utf-8")
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.fetchone.return_value = {
            "filename": "airflow_dag.md",
            "source_type": "corpus",
            "tags": '["beginner"]',
        }

        n = run_ingestion(1, 1, str(f), "text/markdown", domain="tech")

        assert n == 7
        md = mock_index.call_args.kwargs["metadata"]
        assert md["type"] == "airflow"
        assert md["difficulty"] == "beginner"
        assert md["domain"] == "tech"

    @patch("app.services.ingestion.index_document_content")
    @patch("app.services.ingestion.db_session")
    def test_empty_text_raises(self, mock_db_session, mock_index, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("   \n  ", encoding="utf-8")
        with pytest.raises(ValueError):
            run_ingestion(1, 1, str(f), "text/markdown")
        mock_index.assert_not_called()

    @patch("app.services.ingestion.index_document_content")
    @patch("app.services.ingestion.db_session")
    def test_missing_doc_row_raises(self, mock_db_session, mock_index, tmp_path):
        f = tmp_path / "x.md"
        f.write_text("ok", encoding="utf-8")
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.fetchone.return_value = None
        with pytest.raises(ValueError):
            run_ingestion(1, 1, str(f), "text/markdown")
        mock_index.assert_not_called()
