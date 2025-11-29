"""
Tests unitaires pour les services de chat (build_answer, etc.).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.chat import (
    build_answer,
    _get_detected_domains,
    create_conversation_if_needed,
    store_message
)
from app.config import settings

class TestGetDetectedDomains:
    """Tests pour la détection de domaine."""
    
    def test_forced_domain(self):
        """Test avec domaine forcé."""
        domains, primary = _get_detected_domains(
            query="Test",
            auto_detect_domain=True,
            forced_domain="medical"
        )
        assert domains is None
        assert primary == "medical"
    
    @patch('app.services.chat.settings')
    @patch('app.services.chat.detect_domain')
    def test_auto_detect_general(self, mock_detect, mock_settings):
        """Test auto-détection quand domaine = general."""
        mock_settings.domain = "general"
        mock_detect.return_value = ["medical", "legal"]
        
        domains, primary = _get_detected_domains(
            query="Test médical",
            auto_detect_domain=None,
            forced_domain=None
        )
        assert domains == ["medical", "legal"]
        assert primary == "medical"
    
    @patch('app.services.chat.settings')
    def test_no_auto_detect_specific_domain(self, mock_settings):
        """Test sans auto-détection pour domaine spécifique."""
        mock_settings.domain = "tech"
        
        domains, primary = _get_detected_domains(
            query="Test",
            auto_detect_domain=None,
            forced_domain=None
        )
        assert domains is None
        assert primary == "tech"

class TestBuildAnswer:
    """Tests pour build_answer."""
    
    @patch('app.services.chat.retrieve_chunks_with_metadata')
    @patch('app.services.chat.answer_from_context')
    @patch('app.services.chat.settings')
    def test_build_answer_with_sources_int_usage(
        self,
        mock_settings,
        mock_answer_from_context,
        mock_retrieve_chunks
    ):
        """Test build_answer avec sources et usage comme int."""
        mock_settings.domain = "tech"
        
        # Mock des chunks récupérés
        mock_retrieve_chunks.return_value = [
            {"text": "Chunk 1", "score": 0.9, "metadata": {}},
            {"text": "Chunk 2", "score": 0.8, "metadata": {}}
        ]
        
        # Mock de la réponse LLM avec usage comme int
        mock_answer_from_context.return_value = ("Réponse", 10)
        
        answer, usage, sources = build_answer(
            organization_id=1,
            query="Test question",
            include_sources=True
        )
        
        assert answer == "Réponse"
        assert usage == 10
        assert isinstance(usage, int)
        assert len(sources) == 2
        assert sources[0]["text"] == "Chunk 1"
        assert sources[0]["score"] == 0.9
    
    @patch('app.services.chat.retrieve_chunks_with_metadata')
    @patch('app.services.chat.answer_from_context')
    @patch('app.services.chat.settings')
    def test_build_answer_with_sources_dict_usage(
        self,
        mock_settings,
        mock_answer_from_context,
        mock_retrieve_chunks
    ):
        """Test build_answer avec sources et usage comme dict."""
        mock_settings.domain = "tech"
        
        # Mock des chunks récupérés
        mock_retrieve_chunks.return_value = [
            {"text": "Chunk 1", "score": 0.9, "metadata": {}},
            {"text": "Chunk 2", "score": 0.8, "metadata": {}}
        ]
        
        # Mock de la réponse LLM avec usage comme dict
        mock_answer_from_context.return_value = (
            "Réponse",
            {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}
        )
        
        answer, usage, sources = build_answer(
            organization_id=1,
            query="Test question",
            include_sources=True
        )
        
        assert answer == "Réponse"
        assert isinstance(usage, dict)
        assert usage["total_tokens"] == 80
        assert len(sources) == 2
    
    @patch('app.services.chat.retrieve_chunks')
    @patch('app.services.chat.answer_from_context')
    @patch('app.services.chat.settings')
    def test_build_answer_without_sources(
        self,
        mock_settings,
        mock_answer_from_context,
        mock_retrieve_chunks
    ):
        """Test build_answer sans sources."""
        mock_settings.domain = "tech"
        
        # Mock des chunks récupérés
        mock_retrieve_chunks.return_value = ["Chunk 1", "Chunk 2"]
        
        # Mock de la réponse LLM
        mock_answer_from_context.return_value = ("Réponse", 10)
        
        answer, usage, sources = build_answer(
            organization_id=1,
            query="Test question",
            include_sources=False
        )
        
        assert answer == "Réponse"
        assert usage == 10
        assert sources == []
    
    @patch('app.services.chat.search_multi_domain')
    @patch('app.services.chat.answer_from_context')
    @patch('app.services.chat.detect_domain')
    @patch('app.services.chat.settings')
    def test_build_answer_multi_domain(
        self,
        mock_settings,
        mock_detect_domain,
        mock_answer_from_context,
        mock_search_multi_domain
    ):
        """Test build_answer avec plusieurs domaines détectés."""
        mock_settings.domain = "general"
        mock_detect_domain.return_value = ["medical", "legal"]
        
        # Mock de la recherche multi-domaines
        mock_search_multi_domain.return_value = [
            {"text": "Chunk médical", "score": 0.9, "metadata": {}},
            {"text": "Chunk légal", "score": 0.85, "metadata": {}}
        ]
        
        # Mock de la réponse LLM
        mock_answer_from_context.return_value = ("Réponse multi-domaines", 15)
        
        answer, usage, sources = build_answer(
            organization_id=1,
            query="Question complexe",
            include_sources=True
        )
        
        assert answer == "Réponse multi-domaines"
        assert usage == 15
        assert len(sources) == 2
        mock_search_multi_domain.assert_called_once()

class TestChatUtilities:
    """Tests pour les utilitaires de chat."""
    
    def test_create_conversation_if_needed_new(self):
        """Test création de conversation."""
        db = Mock()
        db.execute.return_value.lastrowid = 1
        
        conv_id = create_conversation_if_needed(db, 1, None)
        
        assert conv_id == 1
        db.execute.assert_called_once()
    
    def test_create_conversation_if_needed_existing(self):
        """Test utilisation de conversation existante."""
        db = Mock()
        
        conv_id = create_conversation_if_needed(db, 1, 5)
        
        assert conv_id == 5
        db.execute.assert_not_called()
    
    def test_store_message(self):
        """Test stockage de message."""
        db = Mock()
        db.execute.return_value.lastrowid = 10
        
        msg_id = store_message(db, 1, "user", "Test", 1)
        
        assert msg_id == 10
        db.execute.assert_called_once()
        call_args = db.execute.call_args
        assert call_args[0][0] == "INSERT INTO messages (conversation_id, sender_type, sender_id, content) VALUES (?, ?, ?, ?)"
        assert call_args[0][1] == (1, "user", 1, "Test")

