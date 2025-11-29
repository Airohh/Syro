"""Unit tests for vector_store service."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from app.services.vector_store import VectorStore

class TestVectorStore:
    """Test VectorStore service."""
    
    @patch('app.services.vector_store.QdrantClient')
    def test_init_creates_collection_if_not_exists(self, mock_qdrant_class):
        """Test that collection is created if it doesn't exist."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        VectorStore()
        
        # Should call get_collections
        assert mock_client.get_collections.called
        # Should create collection
        assert mock_client.create_collection.called
    
    @patch('app.services.vector_store.QdrantClient')
    def test_init_does_not_create_existing_collection(self, mock_qdrant_class):
        """Test that collection is not created if it already exists."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        
        # Mock existing collection
        existing_collection = MagicMock()
        existing_collection.name = "syro_chunks"
        mock_client.get_collections.return_value = MagicMock(
            collections=[existing_collection]
        )
        
        VectorStore()
        
        # Should not create collection
        assert not mock_client.create_collection.called
    
    @patch('app.services.vector_store.QdrantClient')
    @patch('app.services.vector_store.get_embedding_vector')
    def test_add_chunk_without_embedding(self, mock_embedding, mock_qdrant_class):
        """Test adding chunk without providing embedding."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        mock_embedding.return_value = np.random.rand(1536).astype(np.float32)
        
        store = VectorStore()
        store.add_chunk(
            chunk_id="1_1_1",
            organization_id=1,
            document_id=1,
            text="Test text",
        )
        
        # Should generate embedding
        assert mock_embedding.called
        # Should upsert to Qdrant
        assert mock_client.upsert.called
    
    @patch('app.services.vector_store.QdrantClient')
    def test_add_chunk_with_embedding(self, mock_qdrant_class):
        """Test adding chunk with provided embedding."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        embedding = np.random.rand(1536).astype(np.float32)
        store = VectorStore()
        store.add_chunk(
            chunk_id="1_1_1",
            organization_id=1,
            document_id=1,
            text="Test text",
            embedding=embedding,
        )
        
        # Should upsert to Qdrant
        assert mock_client.upsert.called
        call_args = mock_client.upsert.call_args
        assert call_args[1]['collection_name'] == "syro_chunks"
        points = call_args[1]['points']
        assert len(points) == 1
        assert points[0].vector == embedding.tolist()
    
    @patch('app.services.vector_store.QdrantClient')
    def test_add_chunk_id_conversion(self, mock_qdrant_class):
        """Test chunk_id to integer conversion."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        store = VectorStore()
        store.add_chunk(
            chunk_id="1_1_123",
            organization_id=1,
            document_id=1,
            text="Test",
            embedding=np.random.rand(1536).astype(np.float32),
        )
        
        # Check that point ID is integer
        call_args = mock_client.upsert.call_args
        points = call_args[1]['points']
        assert isinstance(points[0].id, int)
        assert points[0].id == 123  # Should extract last part
    
    @patch('app.services.vector_store.QdrantClient')
    def test_delete_chunks_by_document(self, mock_qdrant_class):
        """Test deleting chunks by document ID."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        # Mock scroll result with points
        mock_point = MagicMock()
        mock_point.id = 1
        mock_client.scroll.return_value = ([mock_point], None)
        
        store = VectorStore()
        store.delete_chunks_by_document(document_id=1)
        
        # Should scroll to find points
        assert mock_client.scroll.called
        # Should delete found points
        assert mock_client.delete.called
    
    @patch('app.services.vector_store.QdrantClient')
    def test_delete_chunks_empty_result(self, mock_qdrant_class):
        """Test deleting chunks when no chunks found."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        # Mock empty scroll result
        mock_client.scroll.return_value = ([], None)
        
        store = VectorStore()
        store.delete_chunks_by_document(document_id=1)
        
        # Should not call delete if no points found
        assert not mock_client.delete.called
    
    @patch('app.services.vector_store.QdrantClient')
    def test_search(self, mock_qdrant_class):
        """Test vector search."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        # Mock search results
        mock_result = MagicMock()
        mock_result.id = 1
        mock_result.score = 0.9
        mock_result.payload = {
            "text": "Test text",
            "chunk_id": "1_1_1",
            "document_id": 1,
            "type": "test",
        }
        mock_client.search.return_value = [mock_result]
        
        store = VectorStore()
        query_vector = np.random.rand(1536).astype(np.float32)
        results = store.search(
            query_vector=query_vector,
            organization_id=1,
            top_k=10,
        )
        
        assert len(results) == 1
        assert results[0]["text"] == "Test text"
        assert results[0]["score"] == 0.9
        assert results[0]["chunk_id"] == 1
    
    @patch('app.services.vector_store.QdrantClient')
    def test_search_with_filters(self, mock_qdrant_class):
        """Test vector search with metadata filters."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])
        mock_client.search.return_value = []
        
        store = VectorStore()
        query_vector = np.random.rand(1536).astype(np.float32)
        store.search(
            query_vector=query_vector,
            organization_id=1,
            top_k=10,
            filters={"type": "snowflake"},
        )
        
        # Check that filter was applied
        call_args = mock_client.search.call_args
        query_filter = call_args[1]['query_filter']
        assert query_filter is not None
    
    @patch('app.services.vector_store.QdrantClient')
    def test_get_collection_status(self, mock_qdrant_class):
        """Test getting collection status."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        mock_collection = MagicMock()
        mock_collection.config.params.vectors.size = 1536
        mock_collection.points_count = 100
        mock_collection.status = "green"
        mock_client.get_collection.return_value = mock_collection
        
        store = VectorStore()
        status = store.get_collection_status()
        
        assert status["vector_size"] == 1536
        assert status["points_count"] == 100
        assert status["status"] == "green"

