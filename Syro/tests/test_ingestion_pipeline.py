"""Ingestion : domaine en base (source unique), tout-ou-rien SQLite/Qdrant."""

import sqlite3
from unittest.mock import patch

import numpy as np
import pytest

from app.services.ingestion import create_document_entry, ingest_document
from app.services.vector_store import VectorStoreError

MLOPS_TEXT = """# Suivi d'expériences avec MLflow

MLflow permet le tracking des runs, le model registry et le serving.
Le monitoring du drift et l'observabilité complètent le déploiement MLOps.
"""


def _create(db_path, tmp_path, text, domain=None, name="doc.md"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    conn = sqlite3.connect(db_path)
    doc_id, _ = create_document_entry(
        conn,
        organization_id=1,
        filename=name,
        storage_path=str(path),
        mime_type="text/markdown",
        checksum="x",
        tags=None,
        source_type="md",
        domain=domain,
    )
    conn.commit()
    conn.close()
    return doc_id


def _row(db_path, doc_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    n = conn.execute(
        "SELECT COUNT(*) FROM doc_chunks WHERE document_id = ?", (doc_id,)
    ).fetchone()[0]
    conn.close()
    return row, n


def _fake_embeddings(texts):
    return [np.ones(4, dtype=np.float32) for _ in texts]


@patch("app.services.rag.get_document_embeddings", side_effect=_fake_embeddings)
@patch("app.services.rag.VectorStore")
class TestIngestDocument:
    def test_detects_and_stores_domain(self, mock_vs, _emb, syro_db, tmp_path):
        doc_id = _create(syro_db, tmp_path, MLOPS_TEXT)

        n = ingest_document(doc_id)

        row, n_chunks = _row(syro_db, doc_id)
        assert row["ingestion_status"] == "complete"
        assert row["domain"] == "mlops"
        assert n == n_chunks == row["chunk_count"] >= 1
        points = mock_vs.return_value.upsert_chunks.call_args.args[0]
        assert {p["payload"]["domain"] for p in points} == {"mlops"}
        assert {p["payload"]["filename"] for p in points} == {"doc.md"}

    def test_explicit_domain_wins(self, mock_vs, _emb, syro_db, tmp_path):
        doc_id = _create(syro_db, tmp_path, MLOPS_TEXT, domain="tech")
        ingest_document(doc_id)
        row, _ = _row(syro_db, doc_id)
        assert row["domain"] == "tech"

    def test_qdrant_failure_marks_failed_and_rolls_back(
        self, mock_vs, _emb, syro_db, tmp_path
    ):
        mock_vs.return_value.upsert_chunks.side_effect = VectorStoreError("down")
        doc_id = _create(syro_db, tmp_path, MLOPS_TEXT)

        with pytest.raises(VectorStoreError):
            ingest_document(doc_id)

        row, n_chunks = _row(syro_db, doc_id)
        assert row["ingestion_status"] == "failed"
        assert "down" in row["ingestion_error"]
        assert n_chunks == 0  # pas de chunks SQLite sans vecteurs

    def test_empty_document_fails(self, mock_vs, _emb, syro_db, tmp_path):
        doc_id = _create(syro_db, tmp_path, "   \n ")
        with pytest.raises(ValueError):
            ingest_document(doc_id)
        row, _ = _row(syro_db, doc_id)
        assert row["ingestion_status"] == "failed"

    def test_reingestion_replaces_chunks(self, mock_vs, _emb, syro_db, tmp_path):
        doc_id = _create(syro_db, tmp_path, MLOPS_TEXT)
        first = ingest_document(doc_id)
        second = ingest_document(doc_id)
        _, n_chunks = _row(syro_db, doc_id)
        assert first == second == n_chunks
        mock_vs.return_value.delete_document.assert_called_with(doc_id)
