"""
Tests unitaires pour les services RAG.
"""

import pytest
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.rag import (
    retrieve_chunks,
    retrieve_chunks_with_metadata,
    index_document_content
)

class TestRAGServices:
    """Tests pour les services RAG."""
    
    @patch('app.services.rag.VectorStore')
    @patch('app.services.rag.get_embedding_vector')
    @patch('app.services.rag.settings')
    def test_retrieve_chunks_basic(
        self,
        mock_settings,
        mock_get_embedding,
        mock_vector_store_class
    ):
        """Test récupération basique de chunks."""
        mock_settings.embedding_model = "test-model"
        mock_get_embedding.return_value = [0.1] * 384
        
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store
        mock_vector_store.search.return_value = [
            {"text": "chunk 1", "score": 0.9, "metadata": {"source": "doc1"}},
            {"text": "chunk 2", "score": 0.8, "metadata": {"source": "doc2"}},
        ]
        
        results = list(retrieve_chunks(
            organization_id=1,
            query="test query",
            use_hybrid=False,
            domain="tech"
        ))
        
        assert len(results) == 2
        # retrieve_chunks retourne une séquence de strings, pas de dicts
        assert results[0] == "chunk 1"
        assert results[1] == "chunk 2"
        mock_vector_store.search.assert_called_once()
    
    @patch('app.services.rag.hybrid_search')
    @patch('app.services.rag.get_embedding_vector')
    @patch('app.services.rag.settings')
    def test_retrieve_chunks_hybrid(
        self,
        mock_settings,
        mock_get_embedding,
        mock_hybrid_search
    ):
        """Test récupération avec recherche hybride."""
        mock_settings.embedding_model = "test-model"
        mock_get_embedding.return_value = [0.1] * 384
        
        mock_hybrid_search.return_value = [
            {"text": "chunk 1", "score": 0.9, "metadata": {"source": "doc1"}},
        ]
        
        results = list(retrieve_chunks(
            organization_id=1,
            query="test query",
            use_hybrid=True,
            domain="tech"
        ))
        
        assert len(results) == 1
        mock_hybrid_search.assert_called_once()
    
    @patch('app.services.rag.VectorStore')
    @patch('app.services.rag.get_embedding_vector')
    @patch('app.services.rag.settings')
    def test_retrieve_chunks_with_metadata(
        self,
        mock_settings,
        mock_get_embedding,
        mock_vector_store_class
    ):
        """Test récupération avec métadonnées."""
        mock_settings.embedding_model = "test-model"
        mock_get_embedding.return_value = [0.1] * 384
        
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store
        mock_vector_store.search.return_value = [
            {
                "text": "chunk 1",
                "score": 0.9,
                "metadata": {"source": "doc1", "page": 1}
            },
        ]
        
        results = retrieve_chunks_with_metadata(
            organization_id=1,
            query="test query",
            use_hybrid=False,
            domain="tech"
        )
        
        assert len(results) == 1
        assert results[0]["metadata"]["source"] == "doc1"
        assert results[0]["score"] == 0.9
    
    @patch('app.services.rag.chunk_text_hierarchical')
    @patch('app.services.rag.detect_domain_from_document')
    @patch('app.services.rag.VectorStore')
    @patch('app.services.rag.get_embedding_vector')
    @patch('app.services.rag.get_mlops_tracker')
    @patch('app.services.rag.db_session')
    def test_index_document_content(
        self,
        mock_db_session,
        mock_mlops_tracker,
        mock_get_embedding,
        mock_vector_store_class,
        mock_detect_domain,
        mock_chunk_text
    ):
        """Test indexation de contenu de document."""
        # Setup mocks
        mock_db = Mock()
        mock_db.execute.return_value = Mock()
        mock_db.commit = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db_session.return_value.__exit__.return_value = None
        
        mock_chunk_text.return_value = [
            {"text": "chunk 1", "index": 0, "metadata": {}},
            {"text": "chunk 2", "index": 1, "metadata": {}},
        ]
        
        mock_detect_domain.return_value = "tech"
        mock_get_embedding.return_value = [0.1] * 384
        
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store
        
        mock_mlops_tracker.return_value.enabled = False
        
        # Test
        chunk_count = index_document_content(
            document_id=1,
            organization_id=1,
            text_content="Test document content",
            metadata={"domain": "tech"}
        )
        
        assert chunk_count == 2
        mock_chunk_text.assert_called_once()
        mock_vector_store.delete_chunks_by_document.assert_called_once()
    
    @patch('app.services.rag.chunk_text_hierarchical')
    @patch('app.services.rag.detect_domain_from_document')
    @patch('app.services.rag.VectorStore')
    @patch('app.services.rag.get_embedding_vector')
    @patch('app.services.rag.get_mlops_tracker')
    @patch('app.services.rag.db_session')
    def test_index_document_content_with_metadata_domain(
        self,
        mock_db_session,
        mock_mlops_tracker,
        mock_get_embedding,
        mock_vector_store_class,
        mock_detect_domain,
        mock_chunk_text
    ):
        """Test indexation avec domaine dans métadonnées."""
        mock_db = Mock()
        mock_db.execute.return_value = Mock()
        mock_db.commit = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db_session.return_value.__exit__.return_value = None
        
        mock_chunk_text.return_value = [
            {"text": "chunk 1", "index": 0, "metadata": {}},
        ]
        
        mock_detect_domain.return_value = "medical"
        mock_get_embedding.return_value = [0.1] * 384
        
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store
        
        mock_mlops_tracker.return_value.enabled = False
        
        # Le domaine dans metadata devrait override la détection
        chunk_count = index_document_content(
            document_id=1,
            organization_id=1,
            text_content="Test document",
            metadata={"domain": "legal"}
        )
        
        assert chunk_count == 1
        # Vérifier que delete_chunks_by_document est appelé avec "legal" (depuis metadata)
        mock_vector_store.delete_chunks_by_document.assert_called_once_with(1, domain="legal")

