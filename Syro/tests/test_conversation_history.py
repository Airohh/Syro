"""Tests historique conversationnel (T2.5)."""

import sqlite3

from app.services.chat import load_conversation_history


def test_load_conversation_history_order():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            sender_type TEXT,
            sender_id INTEGER,
            content TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO messages (conversation_id, sender_type, content) VALUES (1, 'user', 'Q1')"
    )
    conn.execute(
        "INSERT INTO messages (conversation_id, sender_type, content) VALUES (1, 'assistant', 'A1')"
    )
    conn.execute(
        "INSERT INTO messages (conversation_id, sender_type, content) VALUES (1, 'user', 'Q2')"
    )

    history = load_conversation_history(conn, conversation_id=1, limit=6)

    assert history == ["user: Q1", "assistant: A1", "user: Q2"]
    conn.close()
