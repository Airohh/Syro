"""Non-régression résilience chat : une panne en aval ne doit ni fuiter le
détail d'exception, ni laisser la conversation dans un état partiel."""

import sqlite3

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.db import get_db
from app.dependencies import get_current_user, get_current_org


@pytest.fixture
def test_db_path(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE organizations (
            id INTEGER PRIMARY KEY, name TEXT, credit_balance REAL DEFAULT 0,
            status TEXT DEFAULT 'active', max_members INTEGER DEFAULT 10
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, organization_id INTEGER, email TEXT,
            role TEXT DEFAULT 'member', is_active INTEGER DEFAULT 1
        );
        CREATE TABLE conversations (id INTEGER PRIMARY KEY, organization_id INTEGER, title TEXT);
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY, conversation_id INTEGER, sender_type TEXT,
            sender_id INTEGER, content TEXT
        );
        CREATE TABLE usage_events (
            id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, user_id INTEGER,
            event_type TEXT NOT NULL, amount INTEGER NOT NULL, metadata TEXT
        );
        INSERT INTO organizations (id, name, status, credit_balance) VALUES (1, 'Org', 'active', 100);
        INSERT INTO users (id, organization_id, email) VALUES (1, 1, 'a@b.c');
        """
    )
    conn.commit()
    conn.close()
    return str(db_path)


def _override_db(test_db_path):
    def _gen():
        conn = sqlite3.connect(test_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    return _gen


@patch("app.routers.chat.build_answer", side_effect=RuntimeError("ollama exploded: secret detail"))
def test_domain_endpoint_does_not_500_with_leak_and_rolls_back(
    mock_build, test_db_path, mock_user, mock_org
):
    client = TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides[get_db] = _override_db(test_db_path)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_org] = lambda: mock_org

    resp = client.post(
        "/domains/tech/chat/message",
        json={"content": "question"},
        headers={"Authorization": "Bearer t"},
    )

    # 500 maîtrisé, pas de crash brut, et le détail d'exception ne fuite pas.
    assert resp.status_code == 500
    assert "secret detail" not in resp.text
    assert "ollama exploded" not in resp.text
    # Pin le handler explicite (sans try/except, Starlette renverrait
    # "Internal Server Error" et ce message serait absent).
    assert resp.json()["detail"] == "Erreur lors du traitement du message. Consultez les logs serveur."

    # Rollback : aucun message persisté malgré le store_message(user) initial.
    conn = sqlite3.connect(test_db_path, check_same_thread=False)
    n_msgs = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    assert n_msgs == 0


def test_unknown_domain_returns_404(mock_user, mock_org, test_db_path):
    client = TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides[get_db] = _override_db(test_db_path)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_org] = lambda: mock_org

    resp = client.post(
        "/domains/nope/chat/message",
        json={"content": "q"},
        headers={"Authorization": "Bearer t"},
    )
    assert resp.status_code == 404
