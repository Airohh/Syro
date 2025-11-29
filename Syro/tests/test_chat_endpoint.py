"""
Tests unitaires pour les endpoints de chat.
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from app.main import app
from app.schemas import MessageCreate
from app.services.chat import build_answer, create_conversation_if_needed, store_message
from app.db import get_db
from app.dependencies import get_current_user, require_active_org
from app.dependencies import get_current_user, require_active_org

@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)

@pytest.fixture
def test_db_path(tmp_path):
    """Chemin de la base de données de test."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # Créer une conversation dans la DB de test
        test_db = sqlite3.connect(test_db_path, check_same_thread=False)
        test_db.row_factory = sqlite3.Row
        conv_id = create_conversation_if_needed(test_db, 1, None)
        test_db.close()
        
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
    
    @patch('app.routers.chat.build_answer')
    def test_send_message_creates_conversation(
        self,
        mock_build_answer,
        client,
        test_db_path,
        mock_get_current_user,
        mock_require_active_org
    ):
        """Test création automatique de conversation."""
        # Override des dépendances FastAPI
        def override_get_db():
            conn = sqlite3.connect(test_db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        
        def override_get_current_user():
            return mock_get_current_user
        
        def override_require_active_org():
            return mock_require_active_org
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org()] = override_require_active_org
        
        mock_build_answer.return_value = (
            "Réponse",
            5,
            []
        )
        
        # Compter les conversations avant
        test_db = sqlite3.connect(test_db_path, check_same_thread=False)
        test_db.row_factory = sqlite3.Row
        count_before = test_db.execute(
            "SELECT COUNT(*) FROM conversations"
        ).fetchone()[0]
        test_db.close()
        
        try:
            # Envoyer un message sans conversation_id
            response = client.post(
                "/chat/message",
                json={
                    "content": "Test question"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            
            # Vérifier qu'une nouvelle conversation a été créée
            test_db = sqlite3.connect(test_db_path, check_same_thread=False)
            test_db.row_factory = sqlite3.Row
            count_after = test_db.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]
            test_db.close()
            assert count_after == count_before + 1
        finally:
            # Nettoyer les overrides
            app.dependency_overrides.clear()

class TestChatDomainEndpoint:
    """Tests pour l'endpoint /domains/{domain}/chat/message."""
    
    @patch('app.routers.chat.build_answer')
    def test_send_message_for_domain(
        self,
        mock_build_answer,
        client,
        test_db_path,
        mock_get_current_user,
        mock_require_active_org
    ):
        """Test envoi de message pour un domaine spécifique."""
        # Override des dépendances FastAPI
        def override_get_db():
            conn = sqlite3.connect(test_db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        
        def override_get_current_user():
            return mock_get_current_user
        
        def override_require_active_org():
            return mock_require_active_org
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org()] = override_require_active_org
        
        mock_build_answer.return_value = (
            "Réponse médicale",
            15,
            [{"text": "Source médicale", "score": 0.95}]
        )
        
        try:
            # Envoyer un message pour le domaine médical
            response = client.post(
                "/domains/medical/chat/message",
                json={
                    "content": "Question médicale"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            # Vérifier que build_answer a été appelé avec le bon domaine
            mock_build_answer.assert_called_once()
            call_kwargs = mock_build_answer.call_args[1]
            assert call_kwargs.get("domain") == "medical"
            assert call_kwargs.get("auto_detect_domain") is False
        finally:
            # Nettoyer les overrides
            app.dependency_overrides.clear()

class TestChatValidation:
    """Tests de validation pour les endpoints de chat."""
    
    def test_message_create_schema(self):
        """Test validation du schéma MessageCreate."""
        # Message valide
        valid_msg = MessageCreate(content="Test", conversation_id=1)
        assert valid_msg.content == "Test"
        assert valid_msg.conversation_id == 1
        
        # Message sans conversation_id (devrait être valide)
        valid_msg_no_conv = MessageCreate(content="Test")
        assert valid_msg_no_conv.content == "Test"
        assert valid_msg_no_conv.conversation_id is None
    
    def test_message_response_schema(self):
        """Test validation du schéma MessageResponse."""
        from app.schemas import MessageResponse
        
        response = MessageResponse(
            conversation_id=1,
            message="Réponse",
            usage=10,
            sources=[{"text": "Source", "score": 0.9}]
        )
        assert response.conversation_id == 1
        assert response.message == "Réponse"
        assert response.usage == 10
        assert len(response.sources) == 1

