"""
Tests unitaires pour les endpoints MLOps.
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from app.main import app
from app.dependencies import get_current_user, require_active_org

@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)

@pytest.fixture
def test_db_path(tmp_path):
    """Chemin de la base de données de test."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    
    # Créer les tables nécessaires
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            is_active INTEGER DEFAULT 1,
            organization_id INTEGER
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            credit_balance INTEGER DEFAULT 1000,
            is_active INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active'
        )
    """)
    
    conn.commit()
    conn.close()
    return str(db_path)

@pytest.fixture
def mock_user():
    """Mock utilisateur."""
    return {
        "id": 1,
        "email": "test@example.com",
        "full_name": "Test User",
        "organization_id": 1,
        "is_active": True
    }

@pytest.fixture
def mock_org():
    """Mock organisation."""
    return {
        "id": 1,
        "name": "Test Org",
        "credit_balance": 1000,
        "is_active": True,
        "status": "active"
    }

class TestMLOpsEndpoints:
    """Tests pour les endpoints MLOps."""
    
    def test_get_metrics_disabled(self, client, test_db_path, mock_user, mock_org):
        """Test récupération des métriques quand MLOps est désactivé."""
        def override_get_db():
            conn = sqlite3.connect(test_db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = False
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/metrics",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is False
                assert "message" in data
        finally:
            app.dependency_overrides.clear()
    
    def test_get_metrics_enabled(self, client, test_db_path, mock_user, mock_org):
        """Test récupération des métriques quand MLOps est activé."""
        def override_get_db():
            conn = sqlite3.connect(test_db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = True
                mock_tracker.experiment_name = "test_experiment"
                mock_tracker.get_latest_metrics.return_value = [
                    {"run_id": "1", "metrics": {"response_time_ms": 100}},
                    {"run_id": "2", "metrics": {"response_time_ms": 200}}
                ]
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/metrics?limit=5",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is True
                assert data["experiment_name"] == "test_experiment"
                assert data["total_runs"] == 2
        finally:
            app.dependency_overrides.clear()
    
    def test_get_stats_disabled(self, client, test_db_path, mock_user, mock_org):
        """Test récupération des stats quand MLOps est désactivé."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = False
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/stats",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is False
        finally:
            app.dependency_overrides.clear()
    
    def test_get_stats_enabled(self, client, test_db_path, mock_user, mock_org):
        """Test récupération des stats quand MLOps est activé."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = True
                mock_tracker.get_latest_metrics.return_value = [
                    {
                        "run_id": "1",
                        "metrics": {
                            "response_time_ms": 100,
                            "token_usage": 50,
                            "num_sources": 3,
                            "avg_source_score": 0.8
                        }
                    },
                    {
                        "run_id": "2",
                        "metrics": {
                            "response_time_ms": 200,
                            "token_usage": 100,
                            "num_sources": 5,
                            "avg_source_score": 0.9
                        }
                    }
                ]
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/stats",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is True
                assert "stats" in data
                assert "response_time_ms" in data["stats"]
                assert data["stats"]["response_time_ms"]["avg"] == 150.0
        finally:
            app.dependency_overrides.clear()
    
    def test_get_stats_no_metrics(self, client, test_db_path, mock_user, mock_org):
        """Test récupération des stats sans métriques."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = True
                mock_tracker.get_latest_metrics.return_value = []
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/stats",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is True
                assert data["total_runs"] == 0
                assert data["stats"] == {}
        finally:
            app.dependency_overrides.clear()
    
    def test_log_feedback_disabled(self, client, test_db_path, mock_user, mock_org):
        """Test log feedback quand MLOps est désactivé."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = False
                mock_get_tracker.return_value = mock_tracker
                
                response = client.post(
                    "/mlops/feedback",
                    json={"rating": 5, "helpful": True},
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is False
        finally:
            app.dependency_overrides.clear()
    
    def test_log_feedback_success(self, client, test_db_path, mock_user, mock_org):
        """Test log feedback avec succès."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = True
                mock_get_tracker.return_value = mock_tracker
                
                response = client.post(
                    "/mlops/feedback",
                    params={
                        "query_id": "test_query",
                        "rating": 5,
                        "helpful": True,
                        "feedback_text": "Great answer!"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                mock_tracker.log_retrieval_experiment.assert_called_once()
        finally:
            app.dependency_overrides.clear()
    
    def test_get_alert_thresholds(self, client, test_db_path, mock_user, mock_org):
        """Test récupération des seuils d'alerte."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_alerts') as mock_get_alerts:
                mock_alerts = MagicMock()
                mock_alerts.enabled = True
                mock_alerts.email_enabled = True
                mock_alerts.webhook_enabled = False
                mock_alerts.thresholds = {
                    "response_time_ms": MagicMock(
                        warning_threshold=1000,
                        critical_threshold=5000,
                        comparison="greater_than"
                    )
                }
                mock_get_alerts.return_value = mock_alerts
                
                response = client.get(
                    "/mlops/alerts/thresholds",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is True
                assert "thresholds" in data
        finally:
            app.dependency_overrides.clear()
    
    def test_test_alert_disabled(self, client, test_db_path, mock_user, mock_org):
        """Test alerte quand MLOps alerts est désactivé."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_alerts') as mock_get_alerts:
                mock_alerts = MagicMock()
                mock_alerts.enabled = False
                mock_get_alerts.return_value = mock_alerts
                
                response = client.post(
                    "/mlops/alerts/test",
                    params={"metric_name": "response_time_ms", "value": 1000.0},
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is False
        finally:
            app.dependency_overrides.clear()
    
    def test_test_alert_enabled(self, client, test_db_path, mock_user, mock_org):
        """Test alerte quand MLOps alerts est activé."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_alerts') as mock_get_alerts:
                mock_alerts = MagicMock()
                mock_alerts.enabled = True
                mock_alerts.check_metrics.return_value = ["warning"]
                mock_get_alerts.return_value = mock_alerts
                
                response = client.post(
                    "/mlops/alerts/test",
                    params={"metric_name": "response_time_ms", "value": 1000.0},
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["metric"] == "response_time_ms"
                assert data["value"] == 1000.0
                assert "alerts_triggered" in data
        finally:
            app.dependency_overrides.clear()
    
    def test_get_errors_disabled(self, client, test_db_path, mock_user, mock_org):
        """Test récupération des erreurs quand MLOps est désactivé."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = False
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/errors",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is False
        finally:
            app.dependency_overrides.clear()
    
    def test_get_errors_enabled(self, client, test_db_path, mock_user, mock_org):
        """Test récupération des erreurs quand MLOps est activé."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = True
                mock_tracker.get_latest_metrics.return_value = [
                    {"run_id": "1", "type": "error", "message": "Test error"},
                    {"run_id": "2", "type": "warning", "message": "Test warning"}
                ]
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/errors?limit=10",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is True
                assert data["total_errors"] == 1
                assert data["total_warnings"] == 1
        finally:
            app.dependency_overrides.clear()
    
    def test_export_metrics_disabled(self, client, test_db_path, mock_user, mock_org):
        """Test export métriques quand MLOps est désactivé."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = False
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/export?format=json",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is False
        finally:
            app.dependency_overrides.clear()
    
    def test_export_metrics_json(self, client, test_db_path, mock_user, mock_org):
        """Test export métriques en JSON."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = True
                mock_tracker.get_latest_metrics.return_value = [
                    {"run_id": "1", "metrics": {"response_time_ms": 100}}
                ]
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/export?format=json&limit=50",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["format"] == "json"
                assert "data" in data
                assert data["total"] == 1
        finally:
            app.dependency_overrides.clear()
    
    def test_export_metrics_csv(self, client, test_db_path, mock_user, mock_org):
        """Test export métriques en CSV."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = True
                mock_tracker.get_latest_metrics.return_value = [
                    {
                        "run_id": "1",
                        "start_time": "2024-01-01",
                        "status": "success",
                        "type": "query",
                        "metrics": {"response_time_ms": 100},
                        "params": {"query": "test"}
                    }
                ]
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/export?format=csv&limit=50",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["format"] == "csv"
                assert "data" in data
                assert "content_type" in data
        finally:
            app.dependency_overrides.clear()
    
    def test_export_metrics_csv_empty(self, client, test_db_path, mock_user, mock_org):
        """Test export métriques CSV sans données."""
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org] = override_require_active_org
        
        try:
            with patch('app.routers.mlops.get_mlops_tracker') as mock_get_tracker:
                mock_tracker = MagicMock()
                mock_tracker.enabled = True
                mock_tracker.get_latest_metrics.return_value = []
                mock_get_tracker.return_value = mock_tracker
                
                response = client.get(
                    "/mlops/export?format=csv",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["format"] == "csv"
                assert data["data"] == ""
        finally:
            app.dependency_overrides.clear()

