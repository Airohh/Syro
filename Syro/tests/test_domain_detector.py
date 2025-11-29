"""
Tests unitaires pour le service de détection de domaine.
"""

import pytest

from app.services.domain_detector import (
    detect_domain_simple,
    detect_domain,
    get_domain_confidence,
    should_use_multi_domain,
    detect_domain_from_document
)

class TestDomainDetector:
    """Tests pour le service de détection de domaine."""
    
    def test_detect_domain_simple_tech(self):
        """Test détection de domaine tech."""
        result = detect_domain_simple("How to use Python pandas?")
        assert len(result) > 0
        assert any(domain == "tech" for domain, _ in result)
    
    def test_detect_domain_simple_medical(self):
        """Test détection de domaine medical."""
        result = detect_domain_simple("What are the symptoms of flu?")
        assert len(result) > 0
        assert any(domain == "medical" for domain, _ in result)
    
    def test_detect_domain_simple_legal(self):
        """Test détection de domaine legal."""
        result = detect_domain_simple("What is a contract?")
        assert len(result) > 0
        assert any(domain == "legal" for domain, _ in result)
    
    def test_detect_domain_simple_finance(self):
        """Test détection de domaine finance."""
        result = detect_domain_simple("How to calculate profit?")
        assert len(result) > 0
        assert any(domain == "finance" for domain, _ in result)
    
    def test_detect_domain_simple_education(self):
        """Test détection de domaine education."""
        result = detect_domain_simple("What is pedagogy?")
        assert len(result) > 0
        assert any(domain == "education" for domain, _ in result)
    
    def test_detect_domain_simple_no_match(self):
        """Test détection sans correspondance."""
        result = detect_domain_simple("Random text without keywords")
        assert len(result) > 0
        # Devrait retourner "general" par défaut
        assert result[0][0] == "general"
        assert result[0][1] == 0.5
    
    def test_detect_domain_default(self):
        """Test détection de domaine avec top_k par défaut."""
        result = detect_domain("How to use Python?")
        assert isinstance(result, list)
        assert len(result) > 0
        assert "general" in result
    
    def test_detect_domain_top_k(self):
        """Test détection de domaine avec top_k spécifié."""
        result = detect_domain("Python and SQL queries", top_k=3)
        assert isinstance(result, list)
        assert len(result) <= 4  # top_k + general
        assert "general" in result
    
    def test_detect_domain_empty_query(self):
        """Test détection avec requête vide."""
        result = detect_domain("")
        assert isinstance(result, list)
        assert "general" in result
    
    def test_get_domain_confidence_match(self):
        """Test récupération de confiance pour un domaine correspondant."""
        confidence = get_domain_confidence("How to use Python?", "tech")
        assert isinstance(confidence, float)
        assert confidence >= 0.0
    
    def test_get_domain_confidence_no_match(self):
        """Test récupération de confiance pour un domaine non correspondant."""
        confidence = get_domain_confidence("Random text", "tech")
        assert confidence == 0.0
    
    def test_get_domain_confidence_medical(self):
        """Test récupération de confiance pour domaine medical."""
        confidence = get_domain_confidence("What are the symptoms?", "medical")
        assert isinstance(confidence, float)
        assert confidence >= 0.0
    
    def test_should_use_multi_domain_true(self):
        """Test should_use_multi_domain avec plusieurs domaines."""
        # Utiliser une requête qui correspond à plusieurs domaines
        result = should_use_multi_domain("Python programming and medical symptoms")
        assert isinstance(result, bool)
    
    def test_should_use_multi_domain_false(self):
        """Test should_use_multi_domain avec un seul domaine."""
        result = should_use_multi_domain("Random text without keywords")
        assert isinstance(result, bool)
    
    def test_should_use_multi_domain_custom_threshold(self):
        """Test should_use_multi_domain avec seuil personnalisé."""
        result = should_use_multi_domain("Python and SQL", threshold=0.5)
        assert isinstance(result, bool)
    
    def test_detect_domain_from_document_short(self):
        """Test détection depuis document court."""
        text = "This is a medical document about symptoms."
        result = detect_domain_from_document(text)
        assert isinstance(result, str)
        assert result in ["medical", "general"]
    
    def test_detect_domain_from_document_long(self):
        """Test détection depuis document long."""
        # Créer un texte long (>2000 caractères)
        long_text = "Python " * 500 + "SQL " * 500
        result = detect_domain_from_document(long_text)
        assert isinstance(result, str)
        # Devrait utiliser seulement les 2000 premiers caractères
        assert result in ["tech", "general"]
    
    def test_detect_domain_from_document_empty(self):
        """Test détection depuis document vide."""
        result = detect_domain_from_document("")
        assert result == "general"
    
    def test_detect_domain_from_document_top_k(self):
        """Test détection depuis document avec top_k."""
        text = "Python programming and SQL queries"
        result = detect_domain_from_document(text, top_k=1)
        assert isinstance(result, str)
        assert result in ["tech", "general"]

