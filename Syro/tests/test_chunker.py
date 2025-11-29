"""
Tests unitaires pour le service de chunking hiérarchique.
"""

import pytest
from unittest.mock import patch

from app.services.chunker import (
    count_tokens,
    chunk_text_hierarchical,
    _split_by_headers,
    _split_large_section,
    _chunk_simple,
)

class TestChunker:
    """Tests pour le service de chunking."""
    
    @patch('app.services.chunker.tiktoken')
    def test_count_tokens_basic(self, mock_tiktoken):
        """Test comptage de tokens basique avec mock."""
        # Mock tiktoken pour éviter les appels réels qui peuvent être coûteux
        mock_encoding = mock_tiktoken.encoding_for_model.return_value
        mock_encoding.encode.return_value = [1, 2, 3, 4, 5]  # Simule 5 tokens
        text = "This is a test text"
        tokens = count_tokens(text)
        assert isinstance(tokens, int)
        assert tokens == 5
    
    def test_count_tokens_empty(self):
        """Test comptage de tokens avec texte vide."""
        tokens = count_tokens("")
        assert tokens == 0
    
    @patch('app.services.chunker.tiktoken')
    def test_count_tokens_with_exception(self, mock_tiktoken):
        """Test comptage de tokens avec exception."""
        mock_tiktoken.encoding_for_model.side_effect = Exception("Error")
        text = "Test text"
        tokens = count_tokens(text)
        # Devrait utiliser l'estimation de fallback
        assert isinstance(tokens, int)
        assert tokens > 0
    
    def test_chunk_text_hierarchical_empty(self):
        """Test chunking avec texte vide."""
        chunks = chunk_text_hierarchical("")
        assert chunks == []
    
    def test_chunk_text_hierarchical_whitespace(self):
        """Test chunking avec texte contenant seulement des espaces."""
        chunks = chunk_text_hierarchical("   \n\n  ")
        assert chunks == []
    
    def test_chunk_text_hierarchical_simple(self):
        """Test chunking simple sans headers."""
        text = "This is a simple text. " * 5
        chunks = chunk_text_hierarchical(text, respect_headers=False, chunk_size=20)
        assert len(chunks) > 0
        assert all("text" in chunk for chunk in chunks)
        assert all("index" in chunk for chunk in chunks)
    
    def test_chunk_text_hierarchical_with_markdown(self):
        """Test chunking avec headers Markdown."""
        text = """# Header 1
Content under header 1.

## Header 2
Content under header 2.
"""
        chunks = chunk_text_hierarchical(text, respect_headers=True)
        assert len(chunks) > 0
        assert all("header" in chunk for chunk in chunks)
        assert all("level" in chunk for chunk in chunks)
    
    def test_chunk_text_hierarchical_with_html(self):
        """Test chunking avec headers HTML."""
        text = """<h1>Header 1</h1>
Content under header 1.
"""
        chunks = chunk_text_hierarchical(text, respect_headers=True)
        assert len(chunks) > 0
    
    def test_chunk_text_hierarchical_single_word(self):
        """Test avec un seul mot."""
        chunks = chunk_text_hierarchical("word", respect_headers=False)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "word"
    
    def test_chunk_text_hierarchical_small_text(self):
        """Test avec texte court."""
        text = "Short text here."
        chunks = chunk_text_hierarchical(text, respect_headers=False)
        assert len(chunks) == 1

class TestChunkerInternal:
    """Tests pour les fonctions internes du chunker."""
    
    def test_split_by_headers_markdown(self):
        """Test _split_by_headers avec Markdown."""
        text = """# Header 1
Content 1

## Header 2
Content 2
"""
        sections = _split_by_headers(text)
        assert len(sections) >= 2
        assert sections[0]["header"] == "Header 1"
        assert sections[0]["level"] == 1
    
    def test_split_by_headers_no_headers(self):
        """Test _split_by_headers sans headers."""
        text = "Just plain text without any headers."
        sections = _split_by_headers(text)
        assert len(sections) == 1
        assert sections[0]["header"] == ""
        assert sections[0]["level"] == 0
    
    def test_split_large_section_basic(self):
        """Test _split_large_section basique."""
        text = "word " * 20
        chunks = _split_large_section(text, chunk_size=5, overlap=2)
        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    def test_split_large_section_small(self):
        """Test _split_large_section avec texte petit."""
        text = "word " * 3
        chunks = _split_large_section(text, chunk_size=10, overlap=2)
        assert len(chunks) == 1
    
    def test_chunk_simple_basic(self):
        """Test _chunk_simple basique."""
        text = "word " * 15
        chunks = _chunk_simple(text, chunk_size=5, overlap=2)
        assert len(chunks) > 0
        assert all("text" in chunk for chunk in chunks)
        assert all("index" in chunk for chunk in chunks)
    
    def test_chunk_simple_empty(self):
        """Test _chunk_simple avec texte vide."""
        chunks = _chunk_simple("", chunk_size=10, overlap=2)
        assert len(chunks) == 0
    
    def test_chunk_simple_structure(self):
        """Test structure des chunks de _chunk_simple."""
        text = "word " * 10
        chunks = _chunk_simple(text, chunk_size=5, overlap=1)
        for chunk in chunks:
            assert "text" in chunk
            assert "index" in chunk
            assert "header" in chunk
            assert "level" in chunk
            assert chunk["header"] == ""
            assert chunk["level"] == 0

