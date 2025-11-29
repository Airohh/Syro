"""
Tests supplémentaires pour les services de chat - amélioration de la couverture.
"""

import pytest
import sqlite3
from unittest.mock import Mock, patch, MagicMock

from app.services.chat import (
    _get_detected_domains,
    build_answer,
    build_answer_stream
)
from app.config import settings

class TestChatServicesExtended:
    """Tests supplémentaires pour les services de chat."""
    
    def test_get_detected_domains_forced_domain(self):
        """Test détection de domaine avec domaine forcé."""
        with patch('app.services.chat.settings') as mock_settings:
            mock_settings.domain = "general"
            domains, final_domain = _get_detected_domains(
                "Test query",
                auto_detect_domain=True,
                forced_domain="medical"
            )
            assert domains is None
            assert final_domain == "medical"
    
    def test_get_detected_domains_auto_detect(self):
        """Test auto-détection de domaine."""
        with patch('app.services.chat.settings') as mock_settings, \
             patch('app.services.chat.detect_domain') as mock_detect:
            mock_settings.domain = "general"
            mock_detect.return_value = ["medical", "legal"]
            
            domains, final_domain = _get_detected_domains(
                "Test medical query",
                auto_detect_domain=True,
                forced_domain=None
            )
            assert domains == ["medical", "legal"]
            # Le primary_domain est le premier domaine détecté
            assert final_domain == "medical"
            mock_detect.assert_called_once()
    
    def test_get_detected_domains_no_auto_detect(self):
        """Test sans auto-détection."""
        with patch('app.services.chat.settings') as mock_settings:
            mock_settings.domain = "tech"
            domains, final_domain = _get_detected_domains(
                "Test query",
                auto_detect_domain=False,
                forced_domain=None
            )
            assert domains is None
            assert final_domain == "tech"
    
    @patch('app.services.chat.retrieve_chunks_with_metadata')
    @patch('app.services.chat.answer_from_context')
    @patch('app.services.chat.settings')
    @patch('app.services.chat.get_mlops_tracker')
    @patch('app.services.chat.get_adaptive_manager')
    def test_build_answer_with_dict_usage(
        self,
        mock_adaptive_manager,
        mock_mlops_tracker,
        mock_settings,
        mock_answer_from_context,
        mock_retrieve_chunks
    ):
        """Test build_answer avec usage comme dict."""
        mock_settings.domain = "general"
        mock_settings.performance_mode = "standard"
        mock_mlops_tracker.return_value.enabled = False
        mock_adaptive_manager.return_value.record_latency = Mock()
        
        mock_retrieve_chunks.return_value = [
            {"text": "chunk 1", "score": 0.9, "metadata": {"source": "doc1"}},
        ]
        mock_answer_from_context.return_value = (
            "Answer",
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )
        
        answer, usage, sources = build_answer(1, "Test query", include_sources=True)
        
        assert answer == "Answer"
        assert isinstance(usage, dict)
        assert usage["total_tokens"] == 30
        assert len(sources) == 1
    
    @patch('app.services.chat.retrieve_chunks_with_metadata')
    @patch('app.services.chat.answer_from_context_stream')
    @patch('app.services.chat.settings')
    def test_build_answer_stream(
        self,
        mock_settings,
        mock_answer_stream,
        mock_retrieve_chunks
    ):
        """Test build_answer_stream."""
        mock_settings.domain = "general"
        mock_retrieve_chunks.return_value = [
            {"text": "chunk 1", "score": 0.9, "metadata": {"source": "doc1"}},
        ]
        mock_answer_stream.return_value = iter(["Answer ", "chunk ", "1"])
        
        result = list(build_answer_stream(1, "Test query"))
        
        assert len(result) == 3
        assert result == ["Answer ", "chunk ", "1"]
    
    @patch('app.services.chat.retrieve_chunks_with_metadata')
    @patch('app.services.chat.answer_from_context')
    @patch('app.services.chat.settings')
    @patch('app.services.chat.get_mlops_tracker')
    @patch('app.services.chat.get_adaptive_manager')
    def test_build_answer_error_handling(
        self,
        mock_adaptive_manager,
        mock_mlops_tracker,
        mock_settings,
        mock_answer_from_context,
        mock_retrieve_chunks
    ):
        """Test gestion d'erreur dans build_answer."""
        mock_settings.domain = "general"
        mock_settings.performance_mode = "standard"
        mock_mlops_tracker.return_value.enabled = False
        mock_adaptive_manager.return_value.record_latency = Mock()
        
        mock_retrieve_chunks.return_value = []
        mock_answer_from_context.side_effect = Exception("Test error")
        
        # build_answer capture l'exception mais la relance telle quelle (pas de conversion HTTPException ici)
        # L'HTTPException est créée dans le router, pas dans le service
        with pytest.raises(Exception) as exc_info:
            build_answer(1, "Test query", include_sources=True)
        
        assert str(exc_info.value) == "Test error"

