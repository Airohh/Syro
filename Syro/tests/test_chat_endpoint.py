"""
Tests unitaires pour les endpoints de chat.
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.schemas import MessageCreate
from app.db import get_db
from app.dependencies import get_current_user, get_current_org


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_db_path(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            credit_balance REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            max_members INTEGER DEFAULT 10
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            organization_id INTEGER,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT DEFAULT 'member',
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY,
            organization_id INTEGER,
            title TEXT
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            conversation_id INTEGER,
            sender_type TEXT,
            sender_id INTEGER,
            content TEXT
        );
        CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY,
            organization_id INTEGER NOT NULL,
            user_id INTEGER,
            event_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO organizations (id, name, status) VALUES (1, 'Test Org', 'active');
        INSERT INTO users (id, organization_id, email, role) VALUES (1, 1, 'test@example.com', 'member');
    """)
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def mock_user():
    return {"id": 1, "email": "test@example.com", "role": "member", "organization_id": 1, "is_active": True}


@pytest.fixture
def mock_org():
    return {"id": 1, "name": "Test Org", "status": "active", "credit_balance": 100.0}


class TestChatEndpoint:
    """Tests pour l'endpoint /chat/message."""

    @patch("app.routers.chat.build_answer")
    def test_send_message_creates_conversation(
        self,
        mock_build_answer,
        client,
        test_db_path,
        mock_user,
        mock_org,
    ):
        """Test que l'envoi d'un message sans conversation_id en crée une nouvelle."""
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

        mock_build_answer.return_value = ("Réponse", 5, [])

        conn = sqlite3.connect(test_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        count_before = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        conn.close()

        try:
            response = client.post(
                "/chat/message",
                json={"content": "Test question"},
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200

            conn = sqlite3.connect(test_db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            count_after = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            conn.close()
            assert count_after == count_before + 1
        finally:
            app.dependency_overrides.clear()


class TestChatDomainEndpoint:
    """Tests pour l'endpoint /domains/{domain}/chat/message."""

    @patch("app.routers.chat.build_answer")
    def test_send_message_for_domain(
        self,
        mock_build_answer,
        client,
        test_db_path,
        mock_user,
        mock_org,
    ):
        """Test envoi de message pour un domaine spécifique."""
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

        mock_build_answer.return_value = (
            "Réponse médicale",
            15,
            [{"text": "Source médicale", "score": 0.95}],
        )

        try:
            response = client.post(
                "/domains/medical/chat/message",
                json={"content": "Question médicale"},
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200
            mock_build_answer.assert_called_once()
            call_kwargs = mock_build_answer.call_args[1]
            assert call_kwargs.get("domain") == "medical"
            assert call_kwargs.get("auto_detect_domain") is False
        finally:
            app.dependency_overrides.clear()


class TestChatValidation:
    """Tests de validation pour les endpoints de chat."""

    def test_message_create_schema(self):
        valid_msg = MessageCreate(content="Test", conversation_id=1)
        assert valid_msg.content == "Test"
        assert valid_msg.conversation_id == 1

        valid_msg_no_conv = MessageCreate(content="Test")
        assert valid_msg_no_conv.content == "Test"
        assert valid_msg_no_conv.conversation_id is None

    def test_message_response_schema(self):
        from app.schemas import MessageResponse

        response = MessageResponse(
            conversation_id=1,
            message="Réponse",
            usage=10,
            sources=[{"text": "Source", "score": 0.9}],
        )
        assert response.conversation_id == 1
        assert response.message == "Réponse"
        assert response.usage == 10
        assert len(response.sources) == 1
