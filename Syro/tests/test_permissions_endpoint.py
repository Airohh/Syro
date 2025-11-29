"""
Tests unitaires pour les endpoints de permissions.
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.db import get_db
from app.dependencies import get_current_user, get_current_org

@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)

@pytest.fixture
def test_db_path(tmp_path):
    """Chemin de la base de données de test."""
    db_path = tmp_path / "test_permissions.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # Créer les tables nécessaires
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            organization_id INTEGER,
            role TEXT DEFAULT 'member'
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_access_levels (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            priority INTEGER
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_quality_levels (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            priority INTEGER
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id INTEGER,
            organization_id INTEGER,
            max_access_level_id INTEGER,
            min_quality_level_id INTEGER,
            can_upload_documents INTEGER DEFAULT 1,
            can_delete_documents INTEGER DEFAULT 0,
            can_manage_users INTEGER DEFAULT 0,
            can_view_analytics INTEGER DEFAULT 0,
            can_export_data INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, organization_id)
        )
    """)
    
    # Insérer des données de test
    conn.execute("""
        INSERT INTO users (id, email, organization_id, role)
        VALUES (1, 'admin@example.com', 1, 'owner'),
               (2, 'member@example.com', 1, 'member')
    """)
    
    conn.execute("""
        INSERT INTO organizations (id, name, status)
        VALUES (1, 'Test Org', 'active')
    """)
    
    conn.execute("""
        INSERT INTO document_access_levels (id, name, description, priority)
        VALUES (1, 'public', 'Public access', 1),
               (2, 'internal', 'Internal access', 2)
    """)
    
    conn.execute("""
        INSERT INTO document_quality_levels (id, name, description, priority)
        VALUES (1, 'draft', 'Draft quality', 1),
               (2, 'reviewed', 'Reviewed quality', 2)
    """)
    
    conn.execute("""
        INSERT INTO user_permissions (user_id, organization_id, max_access_level_id, min_quality_level_id)
        VALUES (1, 1, 2, 1),
               (2, 1, 1, 1)
    """)
    
    conn.commit()
    conn.close()
    
    return str(db_path)

@pytest.fixture
def mock_user_owner():
    """Mock utilisateur owner."""
    return {
        "id": 1,
        "email": "admin@example.com",
        "organization_id": 1,
        "role": "owner"
    }

@pytest.fixture
def mock_user_member():
    """Mock utilisateur member."""
    return {
        "id": 2,
        "email": "member@example.com",
        "organization_id": 1,
        "role": "member"
    }

@pytest.fixture
def mock_org():
    """Mock organisation."""
    return {
        "id": 1,
        "name": "Test Org",
        "status": "active"
    }

class TestPermissionsEndpoints:
    """Tests pour les endpoints de permissions."""
    
    def test_list_quality_levels(
        self,
        client,
        test_db_path
    ):
        """Test liste des niveaux de qualité."""
        def override_get_db():
            conn = sqlite3.connect(test_db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            response = client.get("/permissions/quality-levels")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["name"] == "draft"
            assert data[1]["name"] == "reviewed"
        finally:
            app.dependency_overrides.clear()
    
    @patch('app.routers.permissions.get_user_permissions')
    def test_get_my_permissions_success(
        self,
        mock_get_permissions,
        client,
        test_db_path,
        mock_user_owner,
        mock_org
    ):
        """Test récupération des permissions de l'utilisateur."""
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
            return mock_user_owner
        
        def override_get_current_org():
            return mock_org
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_org] = override_get_current_org
        
        mock_get_permissions.return_value = {
            "max_access_level_id": 2,
            "min_quality_level_id": 1,
            "can_upload_documents": True,
            "can_delete_documents": False,
            "can_manage_users": True,
            "can_view_analytics": True,
            "can_export_data": False
        }
        
        try:
            response = client.get(
                "/permissions/me",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == 1
            assert data["organization_id"] == 1
            assert data["can_upload_documents"] is True
            # Vérifier que get_user_permissions a été appelé avec les bons arguments
            # Le 3ème argument est une connexion DB, pas le chemin
            assert mock_get_permissions.called
            call_args = mock_get_permissions.call_args[0]
            assert call_args[0] == 1  # user_id
            assert call_args[1] == 1  # org_id
            assert isinstance(call_args[2], sqlite3.Connection)  # db connection
        finally:
            app.dependency_overrides.clear()
    
    @patch('app.routers.permissions.get_user_permissions')
    def test_get_my_permissions_not_found(
        self,
        mock_get_permissions,
        client,
        test_db_path,
        mock_user_owner,
        mock_org
    ):
        """Test permissions non trouvées."""
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
            return mock_user_owner
        
        def override_get_current_org():
            return mock_org
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_org] = override_get_current_org
        
        mock_get_permissions.return_value = None
        
        try:
            response = client.get(
                "/permissions/me",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 404
            assert "Permissions not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_permissions_as_owner(
        self,
        client,
        test_db_path,
        mock_user_owner,
        mock_org
    ):
        """Test récupération des permissions d'un utilisateur par un owner."""
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
            return mock_user_owner
        
        def override_get_current_org():
            return mock_org
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_org] = override_get_current_org
        
        try:
            response = client.get(
                "/permissions/users/2",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == 2
            assert data["organization_id"] == 1
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_permissions_as_member_forbidden(
        self,
        client,
        test_db_path,
        mock_user_member,
        mock_org
    ):
        """Test accès refusé pour un membre."""
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
            return mock_user_member
        
        def override_get_current_org():
            return mock_org
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_org] = override_get_current_org
        
        try:
            response = client.get(
                "/permissions/users/1",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 403
            assert "Only admins and owners" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

