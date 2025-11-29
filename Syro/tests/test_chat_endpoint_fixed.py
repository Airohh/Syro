"""
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.schemas import MessageCreate
from app.services.chat import build_answer, create_conversation_if_needed, store_message
from app.db import get_db
from app.dependencies import get_current_user, get_current_org, require_active_org

@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)

@pytest.fixture
def test_db(tmp_path):
    """Base de données de test en mémoire."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Créer une conversation
        conv_id = create_conversation_if_needed(test_db, 1, None)
        
        try:
            # Envoyer un message
            response = client.post(
                "/chat/message",
                json={
                    "content": "Test question",
                    "conversation_id": conv_id
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 500
            assert "erreur" in response.json()["detail"].lower()
        finally:
            # Nettoyer les overrides
            app.dependency_overrides.clear()

