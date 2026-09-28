"""API de chat : isolation des conversations, erreurs maîtrisées, abstention."""

import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.services.chat import NOT_FOUND_ANSWER, load_conversation_history
from app.services.llm import LLMUnavailableError


def _user(db_path, user_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def _conversation(db_path, org_id, user_id):
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "INSERT INTO conversations (organization_id, user_id, title) VALUES (?, ?, 't')",
        (org_id, user_id),
    )
    conn.execute(
        "INSERT INTO messages (conversation_id, sender_type, content) "
        "VALUES (?, 'user', 'secret question')",
        (cur.lastrowid,),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def _count_messages(db_path):
    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    return n


@pytest.fixture
def client_as(syro_db):
    def _make(user_id):
        app.dependency_overrides[get_current_user] = lambda: _user(syro_db, user_id)
        return TestClient(app, raise_server_exceptions=False)

    return _make


class TestConversationIsolation:
    @patch("app.routers.chat.build_answer", return_value=("ok", 3, []))
    def test_other_org_conversation_is_404(self, _build, syro_db, client_as):
        foreign = _conversation(syro_db, org_id=2, user_id=3)
        resp = client_as(1).post(
            "/chat/message", json={"content": "q", "conversation_id": foreign}
        )
        assert resp.status_code == 404
        _build.assert_not_called()

    @patch("app.routers.chat.build_answer", return_value=("ok", 3, []))
    def test_other_user_conversation_is_404(self, _build, syro_db, client_as):
        owners = _conversation(syro_db, org_id=1, user_id=1)
        resp = client_as(2).post(
            "/chat/message", json={"content": "q", "conversation_id": owners}
        )
        assert resp.status_code == 404

    @patch("app.routers.chat.build_answer", return_value=("ok", 3, []))
    def test_own_conversation_keeps_history(self, build, syro_db, client_as):
        mine = _conversation(syro_db, org_id=1, user_id=1)
        resp = client_as(1).post(
            "/chat/message", json={"content": "suite ?", "conversation_id": mine}
        )
        assert resp.status_code == 200
        assert resp.json()["conversation_id"] == mine
        history = build.call_args.kwargs["conversation_history"]
        assert history == [{"role": "user", "content": "secret question"}]


class TestErrors:
    @patch(
        "app.routers.chat.build_answer",
        side_effect=RuntimeError("ollama exploded: secret detail"),
    )
    def test_unexpected_error_is_500_without_leak_and_rolled_back(
        self, _build, syro_db, client_as
    ):
        resp = client_as(1).post("/domains/tech/chat/message", json={"content": "q"})
        assert resp.status_code == 500
        assert "secret detail" not in resp.text
        assert _count_messages(syro_db) == 0

    @patch("app.routers.chat.build_answer", side_effect=LLMUnavailableError("down"))
    def test_llm_down_is_503(self, _build, syro_db, client_as):
        resp = client_as(1).post("/chat/message", json={"content": "q"})
        assert resp.status_code == 503
        assert "Ollama" in resp.json()["detail"]
        assert _count_messages(syro_db) == 0

    def test_unknown_domain_is_404(self, syro_db, client_as):
        resp = client_as(1).post("/domains/nope/chat/message", json={"content": "q"})
        assert resp.status_code == 404

    def test_empty_message_rejected(self, syro_db, client_as):
        resp = client_as(1).post("/chat/message", json={"content": ""})
        assert resp.status_code == 422


class TestAbstention:
    @patch("app.services.chat.answer_from_context")
    @patch("app.services.chat.retrieve_chunks_with_metadata", return_value=[])
    def test_no_context_answers_not_found_without_llm(
        self, _retrieve, llm, syro_db, client_as
    ):
        resp = client_as(1).post("/chat/message", json={"content": "météo à Paris ?"})
        assert resp.status_code == 200
        assert resp.json()["message"] == NOT_FOUND_ANSWER
        llm.assert_not_called()


class TestStreaming:
    @patch("app.routers.chat.build_answer_stream")
    def test_stream_sends_sources_then_tokens(self, stream, syro_db, client_as):
        sources = [{"text": "t", "score": 0.9, "metadata": {"source": 1}}]
        stream.return_value = (sources, iter(["Bon", "jour\nligne 2"]))
        resp = client_as(1).post("/chat/message/stream", json={"content": "q"})
        body = resp.text
        assert body.startswith("event: sources\n")
        assert "data: Bon\n\n" in body
        assert "data: jour\ndata: ligne 2\n\n" in body
        assert body.rstrip().endswith("data: [DONE]")
        assert _count_messages(syro_db) == 2  # question + réponse


def test_load_conversation_history_order():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, conversation_id INT, "
        "sender_type TEXT, sender_id INT, content TEXT)"
    )
    for sender, content in [("user", "Q1"), ("assistant", "A1"), ("user", "Q2")]:
        conn.execute(
            "INSERT INTO messages (conversation_id, sender_type, content) VALUES (1, ?, ?)",
            (sender, content),
        )
    assert load_conversation_history(conn, 1) == [
        {"role": "user", "content": "Q1"},
        {"role": "assistant", "content": "A1"},
        {"role": "user", "content": "Q2"},
    ]
