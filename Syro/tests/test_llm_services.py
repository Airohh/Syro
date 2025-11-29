"""
Tests unitaires pour les services LLM.
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np

from app.services.llm import (
    get_embedding_vector,
    answer_from_context,
    answer_from_context_stream,
    LLMProvider
)

class TestLLMServices:
    """Tests pour les services LLM."""
    
    @patch('app.services.llm.provider')
    def test_get_embedding_vector(
        self,
        mock_provider
    ):
        """Test récupération de vecteur d'embedding."""
        mock_provider.embed.return_value = np.array([0.1] * 384, dtype=np.float32)
        
        result = get_embedding_vector("test query")
        
        assert len(result) == 384
        assert isinstance(result, np.ndarray)
        mock_provider.embed.assert_called_once_with("test query")
    
    @patch('app.services.llm.provider')
    def test_answer_from_context(
        self,
        mock_provider
    ):
        """Test génération de réponse depuis contexte."""
        mock_provider.chat.return_value = ("This is a test answer", 50)
        
        answer, usage = answer_from_context(
            question="What is this?",
            context_chunks=["Context chunk 1", "Context chunk 2"],
            domain="tech"
        )
        
        assert answer == "This is a test answer"
        assert usage == 50
        mock_provider.chat.assert_called_once()
    
    @patch('app.services.llm.provider')
    def test_answer_from_context_stream(
        self,
        mock_provider
    ):
        """Test génération de réponse en streaming."""
        mock_provider.chat_stream.return_value = iter(["Chunk", " 1"])
        
        chunks = list(answer_from_context_stream(
            question="Test",
            context_chunks=["Context"],
            domain="tech"
        ))
        
        assert len(chunks) == 2
        assert chunks[0] == "Chunk"
        assert chunks[1] == " 1"
        mock_provider.chat_stream.assert_called_once()
    
    @patch('app.services.llm.settings')
    def test_llm_provider_init_ollama(
        self,
        mock_settings
    ):
        """Test initialisation du provider Ollama."""
        mock_settings.llm_provider = "ollama"
        mock_settings.ollama_base_url = "http://localhost:11434/v1"
        mock_settings.ollama_use_gpu = False
        mock_settings.openai_api_key = None
        
        provider = LLMProvider()
        
        assert provider._provider == "ollama"
    
    @patch('app.services.llm.settings')
    def test_llm_provider_init_openai(
        self,
        mock_settings
    ):
        """Test initialisation du provider OpenAI."""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        
        provider = LLMProvider()
        
        assert provider._provider == "openai"

