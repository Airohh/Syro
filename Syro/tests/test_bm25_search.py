"""Unit tests for BM25 search service."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.bm25_search import BM25Search

class TestBM25Search:
    """Test BM25Search service."""
    
    def test_tokenize(self):
        """Test text tokenization."""
        bm25 = BM25Search()
        tokens = bm25._tokenize("Hello World! This is a test.")
        assert tokens == ["hello", "world", "this", "is", "a", "test"]
    
    def test_tokenize_empty(self):
        """Test tokenization of empty string."""
        bm25 = BM25Search()
        tokens = bm25._tokenize("")
        assert tokens == []
    
    def test_tokenize_special_chars(self):
        """Test tokenization with special characters."""
        bm25 = BM25Search()
        tokens = bm25._tokenize("SQL-query: SELECT * FROM users;")
        assert "sql" in tokens
        assert "query" in tokens
        assert "select" in tokens
    
    @patch('app.services.bm25_search.db_session')
    def test_rebuild_index_empty(self, mock_db_session):
        """Test rebuilding index with no documents."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_conn
        
        bm25 = BM25Search()
        bm25._rebuild_index(organization_id=1)
        
        # Should store None for empty index
        assert 1 in bm25._indexes
        bm25_obj, chunk_data = bm25._indexes[1]
        assert bm25_obj is None
        assert chunk_data == []
    
    @patch('app.services.bm25_search.db_session')
    def test_rebuild_index_with_documents(self, mock_db_session):
        """Test rebuilding index with documents."""
        mock_row1 = MagicMock()
        mock_row1.__getitem__.side_effect = lambda k: {
            "chunk_id": 1,
            "text": "Snowflake is a data warehouse",
            "document_id": 1,
            "source_type": "snowflake",
            "tags": "sql",
        }.get(k)
        
        mock_row2 = MagicMock()
        mock_row2.__getitem__.side_effect = lambda k: {
            "chunk_id": 2,
            "text": "Airflow orchestrates workflows",
            "document_id": 2,
            "source_type": "airflow",
            "tags": "python",
        }.get(k)
        
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [mock_row1, mock_row2]
        mock_db_session.return_value.__enter__.return_value = mock_conn
        
        bm25 = BM25Search()
        bm25._rebuild_index(organization_id=1)
        
        # Should have index
        assert 1 in bm25._indexes
        bm25_obj, chunk_data = bm25._indexes[1]
        assert bm25_obj is not None
        assert len(chunk_data) == 2
    
    @patch('app.services.bm25_search.db_session')
    def test_search_empty_index(self, mock_db_session):
        """Test search with empty index."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_conn
        
        bm25 = BM25Search()
        results = bm25.search(organization_id=1, query="test", top_k=5)
        
        assert results == []
    
    @patch('app.services.bm25_search.db_session')
    def test_search_with_results(self, mock_db_session):
        """Test search returning results."""
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda k: {
            "chunk_id": 1,
            "text": "Snowflake is a data warehouse",
            "document_id": 1,
            "source_type": "snowflake",
            "tags": "sql",
        }.get(k)
        
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [mock_row]
        mock_db_session.return_value.__enter__.return_value = mock_conn
        
        bm25 = BM25Search()
        results = bm25.search(organization_id=1, query="snowflake", top_k=5)
        
        assert len(results) > 0
        assert results[0]["chunk_id"] == 1
        assert "snowflake" in results[0]["text"].lower()
        assert "score" in results[0]
    
    @patch('app.services.bm25_search.db_session')
    def test_search_with_filters(self, mock_db_session):
        """Test search with metadata filters."""
        mock_row1 = MagicMock()
        mock_row1.__getitem__.side_effect = lambda k: {
            "chunk_id": 1,
            "text": "Snowflake is a data warehouse",
            "document_id": 1,
            "source_type": "snowflake",
            "tags": "sql",
        }.get(k)
        
        mock_row2 = MagicMock()
        mock_row2.__getitem__.side_effect = lambda k: {
            "chunk_id": 2,
            "text": "Airflow orchestrates workflows",
            "document_id": 2,
            "source_type": "airflow",
            "tags": "python",
        }.get(k)
        
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [mock_row1, mock_row2]
        mock_db_session.return_value.__enter__.return_value = mock_conn
        
        bm25 = BM25Search()
        results = bm25.search(
            organization_id=1,
            query="data",
            top_k=5,
            filters={"source_type": "snowflake"},
        )
        
        # Should only return snowflake results
        assert all(r["metadata"]["source_type"] == "snowflake" for r in results)
    
    def test_mark_for_rebuild(self):
        """Test marking index for rebuild."""
        bm25 = BM25Search()
        bm25._indexes[1] = (MagicMock(), [])
        
        bm25.mark_for_rebuild(organization_id=1)
        
        assert 1 in bm25._needs_rebuild
        # Index should be removed from cache
        assert 1 not in bm25._indexes
    
    @patch('app.services.bm25_search.db_session')
    def test_search_auto_rebuild(self, mock_db_session):
        """Test that search triggers rebuild if needed."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_conn
        
        bm25 = BM25Search()
        bm25._needs_rebuild.add(1)
        
        # Search should trigger rebuild
        bm25.search(organization_id=1, query="test", top_k=5)
        
        # Should have called rebuild
        assert 1 not in bm25._needs_rebuild

