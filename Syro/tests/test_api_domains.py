"""Tests d'intégration pour les routes multi-domaines."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def client():
    """Client de test pour l'API."""
    return TestClient(app)

class TestDomainRoutes:
    """Tests pour les routes multi-domaines."""
    
    def test_list_domains(self, client):
        """Test la liste des domaines disponibles."""
        response = client.get("/domains")
        assert response.status_code == 200
        
        data = response.json()
        assert "available_domains" in data
        assert "current_domain" in data
    
    def test_domain_healthcheck(self, client):
        """Test le healthcheck pour un domaine spécifique."""
        response = client.get("/domains/tech/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["domain"] == "tech"
        assert "app_name" in data
    
    def test_domain_healthcheck_invalid(self, client):
        """Test le healthcheck pour un domaine invalide."""
        response = client.get("/domains/invalid/health")
        assert response.status_code == 404
    
    def test_metrics_endpoint(self, client):
        """Test l'endpoint /metrics."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        # Vérifier que c'est du format Prometheus
        content = response.text
        assert len(content) > 0

