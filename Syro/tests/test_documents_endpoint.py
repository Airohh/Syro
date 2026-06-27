"""Tests unitaires pour les endpoints de documents.

Cible les routes réelles :
- GET  /documents                                  (list_documents)
- GET  /domains/{domain}/documents/{id}/status     (get_document_status_domain)

Override de la dépendance stable get_current_org (et non de la factory
require_active_org(), dont chaque appel produit une instance différente non
matchée par dependency_overrides).
"""

import sqlite3

import pytest

from app.main import app
from app.db import get_db
from app.dependencies import get_current_user, get_current_org


@pytest.fixture
def test_db_path(tmp_path):
    db_path = tmp_path / "test_documents.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            organization_id INTEGER NOT NULL,
            filename TEXT,
            mime_type TEXT,
            ingestion_status TEXT DEFAULT 'queued',
            ingestion_error TEXT,
            chunk_count INTEGER DEFAULT 0,
            tags TEXT,
            source_type TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO documents
            (id, organization_id, filename, mime_type, ingestion_status, chunk_count, source_type, status)
        VALUES
            (1, 1, 'test.pdf', 'application/pdf', 'complete', 10, 'pdf', 'active');
        """
    )
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def _overrides(test_db_path, mock_user, mock_org):
    def override_get_db():
        conn = sqlite3.connect(test_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_org] = lambda: mock_org
    yield
    app.dependency_overrides.clear()


class TestListDocuments:
    def test_list_returns_active_documents(self, client, _overrides):
        response = client.get(
            "/documents", headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 200
        docs = response.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["id"] == 1
        assert docs[0]["filename"] == "test.pdf"


class TestDocumentStatusDomain:
    def test_status_success(self, client, _overrides):
        response = client.get(
            "/domains/tech/documents/1/status",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == 1
        assert data["status"] == "complete"
        assert data["chunk_count"] == 10
        assert data["domain"] == "tech"

    def test_status_document_not_found(self, client, _overrides):
        response = client.get(
            "/domains/tech/documents/999/status",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 404
        assert "non trouvé" in response.json()["detail"].lower()

    def test_status_invalid_domain(self, client, _overrides):
        response = client.get(
            "/domains/not_a_domain/documents/1/status",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
