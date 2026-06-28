"""Unit tests for RAG service."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.rag import (
    index_document_content,
    retrieve_chunks,
    retrieve_chunks_with_metadata,
)

class TestIndexDocumentContent:
    """Test document indexing."""
    
    @patch('app.services.rag.chunk_text_hierarchical')
    @patch('app.services.rag.VectorStore')
    @patch('app.services.rag.db_session')
    @patch('app.services.rag.bm25_search')
    def test_index_document_content(self, mock_bm25, mock_db_session, mock_vector_store_class, mock_chunker):
        """Test indexing document content."""
        # Mock chunker
        mock_chunker.return_value = [
            {"text": "Chunk 1", "index": 0, "header": "Header 1", "level": 1},
            {"text": "Chunk 2", "index": 1, "header": "Header 2", "level": 2},
        ]
        
        # Mock vector store
        mock_vector_store = MagicMock()
        mock_vector_store_class.return_value = mock_vector_store
        
        # Mock database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_conn.execute.return_value = mock_cursor
        mock_db_session.return_value.__enter__.return_value = mock_conn
        
        # Mock BM25
        mock_bm25.mark_for_rebuild = Mock()
        
        chunk_count = index_document_content(
            document_id=1,
            organization_id=1,
            text_content="Test document content",
            metadata={"type": "test"},
        )
        
        assert chunk_count == 2
        # Should delete old chunks
        assert mock_vector_store.delete_chunks_by_document.called
        # Should add new chunks in a single batch call (1 ensure + 1 embed + 1 upsert)
        assert mock_vector_store.add_chunks_batch.call_count == 1
        batch_arg = mock_vector_store.add_chunks_batch.call_args.args[0]
        assert len(batch_arg) == 2
        assert all("chunk_id" in c and "text" in c and "metadata" in c for c in batch_arg)
        # Should mark BM25 for rebuild
        assert mock_bm25.mark_for_rebuild.called

class TestRetrieveChunks:
    """Test chunk retrieval."""
    
    @patch('app.services.rag.hybrid_search')
    def test_retrieve_chunks_hybrid(self, mock_hybrid_search):
        """Test retrieving chunks with hybrid search."""
        mock_hybrid_search.return_value = [
            {"text": "Chunk 1", "score": 0.9},
            {"text": "Chunk 2", "score": 0.8},
        ]
        
        results = retrieve_chunks(
            organization_id=1,
            query="test query",
            top_k=5,
            use_hybrid=True,
        )
        
        assert len(results) == 2
        assert results[0] == "Chunk 1"
        assert results[1] == "Chunk 2"
        assert mock_hybrid_search.called
    
    @patch('app.services.rag.get_embedding_vector')
    @patch('app.services.rag.VectorStore')
    def test_retrieve_chunks_vector_only(self, mock_vector_store_class, mock_embedding):
        """Test retrieving chunks with vector-only search."""
        mock_embedding.return_value = MagicMock()
        
        mock_vector_store = MagicMock()
        mock_vector_store_class.return_value = mock_vector_store
        mock_vector_store.search.return_value = [
            {"text": "Chunk 1", "score": 0.9},
            {"text": "Chunk 2", "score": 0.8},
        ]
        
        results = retrieve_chunks(
            organization_id=1,
            query="test query",
            top_k=5,
            use_hybrid=False,
        )
        
        assert len(results) == 2
        assert results[0] == "Chunk 1"
        assert mock_vector_store.search.called
    
    @patch('app.services.rag.hybrid_search')
    def test_retrieve_chunks_with_filters(self, mock_hybrid_search):
        """Test retrieving chunks with metadata filters."""
        mock_hybrid_search.return_value = [
            {"text": "Chunk 1", "score": 0.9},
        ]
        
        results = retrieve_chunks(
            organization_id=1,
            query="test",
            top_k=5,
            filters={"type": "snowflake"},
        )
        
        # Check that filters were passed
        call_args = mock_hybrid_search.call_args
        assert call_args[1]["filters"] == {"type": "snowflake"}

class TestRetrieveChunksWithMetadata:
    """Test chunk retrieval with metadata."""
    
    @patch('app.services.rag.hybrid_search')
    def test_retrieve_chunks_with_metadata_hybrid(self, mock_hybrid_search):
        """Test retrieving chunks with metadata using hybrid search."""
        mock_hybrid_search.return_value = [
            {
                "text": "Chunk 1",
                "score": 0.9,
                "metadata": {"type": "snowflake"},
            },
            {
                "text": "Chunk 2",
                "score": 0.8,
                "metadata": {"type": "airflow"},
            },
        ]
        
        results = retrieve_chunks_with_metadata(
            organization_id=1,
            query="test",
            top_k=5,
            use_hybrid=True,
        )
        
        assert len(results) == 2
        assert results[0]["text"] == "Chunk 1"
        assert results[0]["metadata"]["type"] == "snowflake"
        assert "score" in results[0]
    
    @patch('app.services.rag.get_embedding_vector')
    @patch('app.services.rag.VectorStore')
    def test_retrieve_chunks_with_metadata_vector_only(self, mock_vector_store_class, mock_embedding):
        """Test retrieving chunks with metadata using vector-only search."""
        mock_embedding.return_value = MagicMock()
        
        mock_vector_store = MagicMock()
        mock_vector_store_class.return_value = mock_vector_store
        mock_vector_store.search.return_value = [
            {
                "text": "Chunk 1",
                "score": 0.9,
                "metadata": {"type": "snowflake"},
            },
        ]
        
        results = retrieve_chunks_with_metadata(
            organization_id=1,
            query="test",
            top_k=5,
            use_hybrid=False,
        )
        
        assert len(results) == 1
        assert results[0]["metadata"]["type"] == "snowflake"
    
    @patch('app.services.rag.hybrid_search')
    def test_retrieve_chunks_with_metadata_filters(self, mock_hybrid_search):
        """Test retrieving chunks with metadata and filters."""
        mock_hybrid_search.return_value = [
            {
                "text": "Chunk 1",
                "score": 0.9,
                "metadata": {"type": "snowflake"},
            },
        ]
        
        results = retrieve_chunks_with_metadata(
            organization_id=1,
            query="test",
            top_k=5,
            filters={"type": "snowflake"},
        )
        
        # Check filters were passed
        call_args = mock_hybrid_search.call_args
        assert call_args[1]["filters"] == {"type": "snowflake"}

