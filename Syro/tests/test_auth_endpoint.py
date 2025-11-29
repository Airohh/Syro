"""
Tests unitaires pour les endpoints d'authentification.
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from app.main import app
from app.security import verify_password, create_access_token

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
    
    # Créer les tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            is_active INTEGER DEFAULT 1,
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
    
    # Insérer une organisation de test
    conn.execute("""
        INSERT INTO organizations (id, name, status)
        VALUES (1, 'Test Org', 'active')
    """)
    
    # Insérer un utilisateur de test
    from app.security import hash_password
    password_hash = hash_password("test_password")
    conn.execute("""
        INSERT INTO users (id, email, password_hash, full_name, is_active, organization_id, role)
        VALUES (1, 'test@example.com', ?, 'Test User', 1, 1, 'owner')
    """, (password_hash,))
    
    conn.commit()
    conn.close()
    
    return str(db_path)

@pytest.fixture
def test_db(test_db_path):
    """Connexion à la base de données de test."""
    conn = sqlite3.connect(test_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()

class TestLoginEndpoint:
    """Tests pour l'endpoint /auth/login."""
    
    def test_login_success(self, client, test_db_path):
        """Test login réussi."""
        from app.db import get_db
        
        # Override de la dépendance get_db - créer une nouvelle connexion à chaque fois
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
            response = client.post(
                "/auth/login",
                data={
                    "username": "test@example.com",
                    "password": "test_password"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
        finally:
            app.dependency_overrides.clear()
    
    def test_login_invalid_credentials(self, client, test_db_path):
        """Test login avec identifiants invalides."""
        from app.db import get_db
        
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
            response = client.post(
                "/auth/login",
                data={
                    "username": "test@example.com",
                    "password": "wrong_password"
                }
            )
            
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()
    
    @patch('app.routers.auth.auth_rate_limiter')
    def test_login_user_not_found(self, mock_rate_limiter, client, test_db_path):
        """Test login avec utilisateur inexistant."""
        from app.db import get_db
        
        # Permettre le rate limiter pour ce test
        mock_rate_limiter.allow.return_value = (True, 10)
        
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
            response = client.post(
                "/auth/login",
                data={
                    "username": "nonexistent@example.com",
                    "password": "test_password"
                }
            )
            
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()
    
    @patch('app.routers.auth.auth_rate_limiter')
    def test_login_rate_limit(self, mock_rate_limiter, client, test_db_path):
        """Test rate limiting sur le login."""
        from app.db import get_db
        
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
        mock_rate_limiter.allow.return_value = (False, 0)
        
        try:
            response = client.post(
                "/auth/login",
                data={
                    "username": "test@example.com",
                    "password": "test_password"
                }
            )
            
            assert response.status_code == 429
        finally:
            app.dependency_overrides.clear()

class TestSecurity:
    """Tests pour les fonctions de sécurité."""
    
    def test_hash_password(self):
        """Test hashage de mot de passe."""
        from app.security import hash_password
        
        password = "test_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Les hashs doivent être différents (salt aléatoire)
        assert hash1 != hash2
        # Mais doivent être de la même longueur
        assert len(hash1) == len(hash2)
    
    def test_verify_password(self):
        """Test vérification de mot de passe."""
        from app.security import hash_password, verify_password
        
        password = "test_password"
        password_hash = hash_password(password)
        
        # Vérification correcte
        assert verify_password(password, password_hash) is True
        
        # Vérification incorrecte
        assert verify_password("wrong_password", password_hash) is False
    
    def test_create_access_token(self):
        """Test création de token JWT."""
        token = create_access_token({"sub": "test@example.com", "id": 1})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

