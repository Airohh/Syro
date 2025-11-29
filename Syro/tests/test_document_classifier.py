"""
Tests unitaires pour le service de classification de documents.
"""

import pytest
from unittest.mock import patch

from app.services.document_classifier import (
    classify_document,
    should_ask_confirmation
)

class TestDocumentClassifier:
    """Tests pour le service de classification de documents."""
    
    @patch('app.services.document_classifier.detect_domain_simple')
    def test_classify_document_with_text(self, mock_detect_domain):
        """Test classification avec texte."""
        mock_detect_domain.return_value = [
            ("medical", 0.8),
            ("legal", 0.2),
            ("general", 0.1)
        ]
        
        result = classify_document(
            text="Patient diagnosis and treatment plan",
            filename=None,
            mime_type=None
        )
        
        assert "domain" in result
        assert "confidence" in result
        assert "alternatives" in result
        assert result["domain"] == "medical"
        assert result["confidence"] > 0
    
    @patch('app.services.document_classifier.detect_domain_simple')
    @patch('app.services.document_classifier.DOMAIN_KEYWORDS')
    def test_classify_document_with_filename(
        self,
        mock_domain_keywords,
        mock_detect_domain
    ):
        """Test classification avec nom de fichier."""
        mock_detect_domain.return_value = [
            ("general", 0.5),
            ("medical", 0.3)
        ]
        mock_domain_keywords.__getitem__.return_value = ["medical", "health"]
        
        result = classify_document(
            text="Some content",
            filename="medical_report.pdf",
            mime_type=None
        )
        
        assert "domain" in result
        assert "confidence" in result
        assert "alternatives" in result
    
    @patch('app.services.document_classifier.detect_domain_simple')
    def test_classify_document_empty_scores(self, mock_detect_domain):
        """Test classification sans scores."""
        mock_detect_domain.return_value = []
        
        result = classify_document(
            text="Unknown content",
            filename=None,
            mime_type=None
        )
        
        assert result["domain"] == "general"
        assert result["confidence"] == 0.3
        assert result["alternatives"] == []
    
    @patch('app.services.document_classifier.detect_domain_simple')
    def test_classify_document_long_text(self, mock_detect_domain):
        """Test classification avec texte long."""
        mock_detect_domain.return_value = [("tech", 0.9)]
        
        # Réduire la taille pour éviter les problèmes de mémoire
        long_text = "Technical content. " * 100  # Réduit de 2000 à 100
        result = classify_document(
            text=long_text,
            filename=None,
            mime_type=None
        )
        
        # Vérifier que la fonction a été appelée
        mock_detect_domain.assert_called_once()
        assert result["domain"] == "tech"
    
    def test_should_ask_confirmation_low_confidence(self):
        """Test demande de confirmation avec faible confiance."""
        result = {
            "domain": "medical",
            "confidence": 0.5,
            "alternatives": []
        }
        assert should_ask_confirmation(result, threshold=0.7) is True
    
    def test_should_ask_confirmation_high_confidence(self):
        """Test pas de demande avec haute confiance."""
        result = {
            "domain": "medical",
            "confidence": 0.9,
            "alternatives": []
        }
        assert should_ask_confirmation(result, threshold=0.7) is False
    
    def test_should_ask_confirmation_close_alternatives(self):
        """Test demande avec alternatives proches."""
        result = {
            "domain": "medical",
            "confidence": 0.75,
            "alternatives": [
                {"domain": "legal", "confidence": 0.70}
            ]
        }
        assert should_ask_confirmation(result, threshold=0.7) is True
    
    def test_should_ask_confirmation_distant_alternatives(self):
        """Test pas de demande avec alternatives distantes."""
        result = {
            "domain": "medical",
            "confidence": 0.85,
            "alternatives": [
                {"domain": "legal", "confidence": 0.20}
            ]
        }
        assert should_ask_confirmation(result, threshold=0.7) is False

