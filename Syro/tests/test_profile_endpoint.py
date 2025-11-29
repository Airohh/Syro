"""
Tests unitaires pour les endpoints de profil utilisateur.
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.db import get_db
from app.dependencies import get_current_user, get_current_org
from app.schemas import UserProfileUpdate

@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)

@pytest.fixture
def test_db_path(tmp_path):
    """Chemin de la base de données de test."""
    db_path = tmp_path / "test_profile.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # Créer les tables nécessaires
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            organization_id INTEGER,
            role TEXT DEFAULT 'member',
            status TEXT DEFAULT 'active',
            first_name TEXT,
            last_name TEXT,
            avatar_url TEXT,
            bio TEXT,
            phone TEXT,
            preferences TEXT,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)
    
    # Insérer des données de test
    conn.execute("""
        INSERT INTO users (id, email, password_hash, organization_id, role, status, first_name, last_name)
        VALUES (1, 'test@example.com', 'hashed', 1, 'owner', 'active', 'John', 'Doe')
    """)
    
    conn.execute("""
        INSERT INTO organizations (id, name, status)
        VALUES (1, 'Test Org', 'active')
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
        "organization_id": 1,
        "role": "owner"
    }

@pytest.fixture
def mock_org():
    """Mock organisation."""
    return {
        "id": 1,
        "name": "Test Org",
        "status": "active"
    }

class TestProfileEndpoints:
    """Tests pour les endpoints de profil."""
    
    def test_get_my_profile_success(
        self,
        client,
        test_db_path,
        mock_user
    ):
        """Test récupération du profil utilisateur."""
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
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            response = client.get(
                "/profile/me",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["email"] == "test@example.com"
            assert data["first_name"] == "John"
            assert data["last_name"] == "Doe"
        finally:
            app.dependency_overrides.clear()
    
    def test_get_my_profile_not_found(
        self,
        client,
        test_db_path
    ):
        """Test récupération du profil avec utilisateur inexistant."""
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
            return {"id": 999, "email": "nonexistent@example.com"}
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            response = client.get(
                "/profile/me",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
    
    def test_update_my_profile_success(
        self,
        client,
        test_db_path,
        mock_user
    ):
        """Test mise à jour du profil utilisateur."""
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
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            response = client.put(
                "/profile/me",
                json={
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "bio": "Test bio"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["first_name"] == "Jane"
            assert data["last_name"] == "Smith"
            assert data["bio"] == "Test bio"
        finally:
            app.dependency_overrides.clear()
    
    def test_update_my_profile_no_fields(
        self,
        client,
        test_db_path,
        mock_user
    ):
        """Test mise à jour sans champs."""
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
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            response = client.put(
                "/profile/me",
                json={},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 400
            assert "No fields to update" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    @patch('app.routers.profile.get_user_stats')
    def test_get_profile_stats(
        self,
        mock_get_user_stats,
        client,
        test_db_path,
        mock_user,
        mock_org
    ):
        """Test récupération des statistiques du profil."""
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
        
        def override_get_current_org():
            return mock_org
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_org] = override_get_current_org
        
        mock_get_user_stats.return_value = {
            "documents": {
                "total": 10,
                "by_domain": {"tech": 5, "medical": 5},
                "last_7_days": 3,
                "last_30_days": 8,
                "pending": 0,
                "failed": 0
            },
            "storage": {
                "total_bytes": 1024000,
                "total_mb": 1.0,
                "total_gb": 0.001,
                "chunks_indexed": 100
            },
            "usage": {
                "conversations": 5,
                "messages": 50,
                "recent_conversations_7d": 2
            }
        }
        
        try:
            response = client.get(
                "/profile/stats",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "documents" in data
            assert "storage" in data
            assert "usage" in data
            assert data["documents"]["total"] == 10
            mock_get_user_stats.assert_called_once_with(1, 1)
        finally:
            app.dependency_overrides.clear()
    
    @patch('app.routers.profile.get_documents_by_org')
    @patch('app.routers.profile.filter_documents_by_permissions')
    def test_get_profile_documents(
        self,
        mock_filter,
        mock_get_docs,
        client,
        test_db_path,
        mock_user,
        mock_org
    ):
        """Test récupération des documents du profil."""
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
        
        def override_get_current_org():
            return mock_org
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_org] = override_get_current_org
        
        mock_get_docs.return_value = [
            {"id": 1, "title": "Doc 1"},
            {"id": 2, "title": "Doc 2"}
        ]
        mock_filter.return_value = [
            {"id": 1, "title": "Doc 1"}
        ]
        
        try:
            response = client.get(
                "/profile/documents?limit=10&offset=0",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "documents" in data
            assert "total" in data
            assert data["total"] == 1
            assert len(data["documents"]) == 1
        finally:
            app.dependency_overrides.clear()

