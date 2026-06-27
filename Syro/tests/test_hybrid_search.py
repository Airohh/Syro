"""
Tests unitaires pour le service de recherche hybride.
"""

import numpy as np
import pytest
from unittest.mock import patch, Mock

from app.services.hybrid_search import hybrid_search

class TestHybridSearch:
    """Tests pour le service de recherche hybride."""
    
    @patch('app.services.hybrid_search.reranker')
    @patch('app.services.hybrid_search.bm25_search')
    @patch('app.services.hybrid_search.VectorStore')
    @patch('app.services.hybrid_search.get_embedding_vector')
    @patch('app.services.hybrid_search.settings')
    def test_hybrid_search_basic(
        self,
        mock_settings,
        mock_get_embedding,
        mock_vector_store_class,
        mock_bm25_search,
        mock_reranker
    ):
        """Test recherche hybride basique."""
        mock_settings.rerank_top_k = 5
        mock_settings.retrieval_top_k = 5
        mock_settings.hybrid_search_alpha = 0.5
        mock_settings.rrf_k = 60
        
        mock_get_embedding.return_value = np.array([0.1] * 384)
        
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store
        mock_vector_store.search.return_value = [
            {"text": "vector result 1", "score": 0.9, "metadata": {}, "chunk_id": "1_1_1"},
            {"text": "vector result 2", "score": 0.8, "metadata": {}, "chunk_id": "1_1_2"},
        ]
        
        mock_bm25_search.search.return_value = [
            {"text": "bm25 result 1", "score": 0.7, "metadata": {}, "chunk_id": "1_1_3"},
        ]
        
        # Mock reranker pour retourner les résultats triés
        mock_reranker.rerank.return_value = [
            {"text": "vector result 1", "score": 0.9, "metadata": {}, "chunk_id": "1_1_1"},
            {"text": "vector result 2", "score": 0.8, "metadata": {}, "chunk_id": "1_1_2"},
            {"text": "bm25 result 1", "score": 0.7, "metadata": {}, "chunk_id": "1_1_3"},
        ]
        
        results = hybrid_search(
            organization_id=1,
            query="test query",
            top_k=5,
            domain="tech"
        )
        
        assert len(results) > 0
        mock_vector_store.search.assert_called_once()
        mock_bm25_search.search.assert_called_once()
    
    @patch('app.services.hybrid_search.bm25_search')
    @patch('app.services.hybrid_search.VectorStore')
    @patch('app.services.hybrid_search.get_embedding_vector')
    @patch('app.services.hybrid_search.settings')
    def test_hybrid_search_with_filters(
        self,
        mock_settings,
        mock_get_embedding,
        mock_vector_store_class,
        mock_bm25_search
    ):
        """Test recherche hybride avec filtres."""
        mock_settings.rerank_top_k = 5
        mock_settings.retrieval_top_k = 5
        mock_settings.hybrid_search_alpha = 0.5
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_get_embedding.return_value = np.array([0.1] * 384)
        
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store
        mock_vector_store.search.return_value = []
        
        mock_bm25_search.search.return_value = []
        
        results = hybrid_search(
            organization_id=1,
            query="test query",
            top_k=5,
            filters={"domain": "medical"},
            domain="medical"
        )
        
        assert isinstance(results, list)
        # Vérifier que les filtres sont passés
        mock_vector_store.search.assert_called_once()
    
    @patch('app.services.hybrid_search.bm25_search')
    @patch('app.services.hybrid_search.VectorStore')
    @patch('app.services.hybrid_search.get_embedding_vector')
    @patch('app.services.hybrid_search.settings')
    def test_hybrid_search_empty_results(
        self,
        mock_settings,
        mock_get_embedding,
        mock_vector_store_class,
        mock_bm25_search
    ):
        """Test recherche hybride sans résultats."""
        mock_settings.rerank_top_k = 5
        mock_settings.retrieval_top_k = 5
        mock_settings.hybrid_search_alpha = 0.5
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_get_embedding.return_value = np.array([0.1] * 384)
        
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store
        mock_vector_store.search.return_value = []
        
        mock_bm25_search.search.return_value = []
        
        results = hybrid_search(
            organization_id=1,
            query="test query",
            top_k=5,
            domain="tech"
        )

        assert results == []

    @patch('app.services.hybrid_search.bm25_search')
    @patch('app.services.hybrid_search.VectorStore')
    @patch('app.services.hybrid_search.get_embedding_vector')
    @patch('app.services.hybrid_search.settings')
    def test_hybrid_search_embedding_failure_falls_back_to_bm25(
        self,
        mock_settings,
        mock_get_embedding,
        mock_vector_store_class,
        mock_bm25_search
    ):
        """Test dégradation BM25-only quand l'embedding échoue (LLM provider down)."""
        mock_settings.rerank_top_k = 5
        mock_settings.retrieval_top_k = 5
        mock_settings.hybrid_search_alpha = 0.5
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_get_embedding.side_effect = RuntimeError("LLM provider not configured")

        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        mock_bm25_search.search.return_value = [
            {"text": "bm25 result 1", "score": 0.7, "metadata": {}, "chunk_id": "1_1_3"},
        ]

        results = hybrid_search(
            organization_id=1,
            query="test query",
            top_k=5,
            domain="tech"
        )

        # Pas de 500 : la recherche lexicale prend le relais
        assert len(results) == 1
        assert results[0]["text"] == "bm25 result 1"
        mock_vector_store.search.assert_not_called()
        mock_bm25_search.search.assert_called_once()

    @patch('app.services.hybrid_search.bm25_search')
    @patch('app.services.hybrid_search.VectorStore')
    @patch('app.services.hybrid_search.get_embedding_vector')
    @patch('app.services.hybrid_search.settings')
    def test_rrf_ranks_chunk_present_in_both_lists_first(
        self,
        mock_settings,
        mock_get_embedding,
        mock_vector_store_class,
        mock_bm25_search
    ):
        """RRF : un chunk présent dans les deux listes domine (somme des rangs)."""
        mock_settings.rerank_top_k = 5
        mock_settings.retrieval_top_k = 5
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_get_embedding.return_value = np.array([0.1] * 384)

        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store
        # B au rang 1 côté vecteur
        mock_vector_store.search.return_value = [
            {"text": "A", "score": 0.9, "metadata": {}, "chunk_id": "A"},
            {"text": "B", "score": 0.8, "metadata": {}, "chunk_id": "B"},
        ]
        # B au rang 0 côté BM25 -> présent dans les deux listes
        mock_bm25_search.search.return_value = [
            {"text": "B", "score": 0.7, "metadata": {}, "chunk_id": "B"},
            {"text": "C", "score": 0.6, "metadata": {}, "chunk_id": "C"},
        ]

        results = hybrid_search(
            organization_id=1,
            query="test query",
            top_k=5,
            domain="tech",
        )

        # B fusionné (rangs v1 + b0) > A (v0) > C (b1). 3 chunks distincts.
        assert [r["chunk_id"] for r in results] == ["B", "A", "C"]
        # Score brut conservé pour observabilité (non utilisé au tri).
        b = next(r for r in results if r["chunk_id"] == "B")
        assert b["vector_score"] == 0.8 and b["bm25_score"] == 0.7
