"""
Tests unitaires pour le service de reranking.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.reranker import Reranker, reranker

class TestReranker:
    """Tests pour le service de reranking."""
    
    def test_rerank_empty_passages(self):
        """Test rerank avec passages vides."""
        result = reranker.rerank("test query", [])
        assert result == []
    
    def test_rerank_disabled(self):
        """Test rerank quand reranking est désactivé."""
        test_reranker = Reranker()
        test_reranker._enabled = False
        
        passages = [
            {"text": "Test passage 1", "score": 0.8},
            {"text": "Test passage 2", "score": 0.6}
        ]
        
        result = test_reranker.rerank("test query", passages)
        assert len(result) == 2
        assert result == passages
    
    def test_rerank_disabled_with_top_k(self):
        """Test rerank désactivé avec top_k."""
        test_reranker = Reranker()
        test_reranker._enabled = False
        
        passages = [
            {"text": "Test passage 1", "score": 0.8},
            {"text": "Test passage 2", "score": 0.6},
            {"text": "Test passage 3", "score": 0.4}
        ]
        
        result = test_reranker.rerank("test query", passages, top_k=2)
        assert len(result) == 2
    
    def test_rerank_model_not_available(self):
        """Test rerank quand le modèle n'est pas disponible."""
        test_reranker = Reranker()
        test_reranker._enabled = True
        test_reranker._load_model = Mock(return_value=None)
        
        passages = [
            {"text": "Test passage 1", "score": 0.8},
            {"text": "Test passage 2", "score": 0.6}
        ]
        
        result = test_reranker.rerank("test query", passages)
        assert len(result) == 2
        assert result == passages
    
    def test_rerank_with_model_single_passage(self):
        """Test rerank avec modèle et un seul passage."""
        test_reranker = Reranker()
        test_reranker._enabled = True
        
        mock_model = MagicMock()
        mock_model.compute_score.return_value = 0.9
        test_reranker._load_model = Mock(return_value=mock_model)
        
        with patch('app.services.reranker.settings') as mock_settings:
            mock_settings.rerank_weight = 0.5
            
            passages = [
                {"text": "Test passage 1", "score": 0.8}
            ]
            
            result = test_reranker.rerank("test query", passages)
            assert len(result) == 1
            assert "rerank_score" in result[0]
            assert "final_score" in result[0]
    
    def test_rerank_with_model_multiple_passages(self):
        """Test rerank avec modèle et plusieurs passages."""
        test_reranker = Reranker()
        test_reranker._enabled = True
        
        mock_model = MagicMock()
        mock_model.compute_score.return_value = [0.9, 0.7, 0.5]
        test_reranker._load_model = Mock(return_value=mock_model)
        
        with patch('app.services.reranker.settings') as mock_settings:
            mock_settings.rerank_weight = 0.5
            
            passages = [
                {"text": "Test passage 1", "score": 0.8},
                {"text": "Test passage 2", "score": 0.6},
                {"text": "Test passage 3", "score": 0.4}
            ]
            
            result = test_reranker.rerank("test query", passages)
            assert len(result) == 3
            assert all("rerank_score" in p for p in result)
            assert all("final_score" in p for p in result)
    
    def test_rerank_with_model_numpy_array(self):
        """Test rerank avec modèle retournant numpy array."""
        test_reranker = Reranker()
        test_reranker._enabled = True
        
        import numpy as np
        mock_model = MagicMock()
        mock_model.compute_score.return_value = np.array([0.9, 0.7])
        test_reranker._load_model = Mock(return_value=mock_model)
        
        with patch('app.services.reranker.settings') as mock_settings:
            mock_settings.rerank_weight = 0.5
            
            passages = [
                {"text": "Test passage 1", "score": 0.8},
                {"text": "Test passage 2", "score": 0.6}
            ]
            
            result = test_reranker.rerank("test query", passages)
            assert len(result) == 2
    
    def test_rerank_with_top_k(self):
        """Test rerank avec top_k."""
        test_reranker = Reranker()
        test_reranker._enabled = True
        
        mock_model = MagicMock()
        mock_model.compute_score.return_value = [0.9, 0.7, 0.5, 0.3]
        test_reranker._load_model = Mock(return_value=mock_model)
        
        with patch('app.services.reranker.settings') as mock_settings:
            mock_settings.rerank_weight = 0.5
            
            passages = [
                {"text": "Test passage 1", "score": 0.8},
                {"text": "Test passage 2", "score": 0.6},
                {"text": "Test passage 3", "score": 0.4},
                {"text": "Test passage 4", "score": 0.2}
            ]
            
            result = test_reranker.rerank("test query", passages, top_k=2)
            assert len(result) == 2
    
    def test_rerank_exception_handling(self):
        """Test gestion d'exception lors du rerank."""
        test_reranker = Reranker()
        test_reranker._enabled = True
        
        mock_model = MagicMock()
        mock_model.compute_score.side_effect = Exception("Model error")
        test_reranker._load_model = Mock(return_value=mock_model)
        
        passages = [
            {"text": "Test passage 1", "score": 0.8},
            {"text": "Test passage 2", "score": 0.6}
        ]
        
        result = test_reranker.rerank("test query", passages)
        # Devrait retourner les passages originaux en cas d'erreur
        assert len(result) == 2
    
    def test_check_cuda_no_torch(self):
        """Test vérification CUDA sans torch."""
        test_reranker = Reranker()
        with patch('builtins.__import__', side_effect=ImportError):
            result = test_reranker._check_cuda()
            assert result is False
    
    def test_load_model_disabled(self):
        """Test chargement modèle quand désactivé."""
        test_reranker = Reranker()
        test_reranker._enabled = False
        result = test_reranker._load_model()
        assert result is None
    
    def test_load_model_already_loaded(self):
        """Test chargement modèle déjà chargé."""
        test_reranker = Reranker()
        mock_model = MagicMock()
        test_reranker._model = mock_model
        result = test_reranker._load_model()
        assert result == mock_model
    
    def test_load_model_import_error(self):
        """Test chargement modèle avec erreur d'import."""
        test_reranker = Reranker()
        test_reranker._enabled = True
        
        # Simuler une erreur d'import en patchant l'import dans la fonction
        with patch('builtins.__import__', side_effect=ImportError("No module named 'FlagEmbedding'")):
            result = test_reranker._load_model()
            assert result is None
    
    def test_rerank_normalization(self):
        """Test normalisation des scores."""
        test_reranker = Reranker()
        test_reranker._enabled = True
        
        mock_model = MagicMock()
        # Scores non normalisés
        mock_model.compute_score.return_value = [10.0, 5.0, 2.0]
        test_reranker._load_model = Mock(return_value=mock_model)
        
        with patch('app.services.reranker.settings') as mock_settings:
            mock_settings.rerank_weight = 0.5
            
            passages = [
                {"text": "Test passage 1", "score": 0.8},
                {"text": "Test passage 2", "score": 0.6},
                {"text": "Test passage 3", "score": 0.4}
            ]
            
            result = test_reranker.rerank("test query", passages)
            assert len(result) == 3
            # Les rerank_scores devraient être normalisés entre 0 et 1
            assert all(0 <= p["rerank_score"] <= 1 for p in result)
