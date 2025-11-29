"""
Tests unitaires pour les endpoints de documents.
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import tempfile

from app.main import app
from app.db import get_db
from app.dependencies import get_current_user, require_active_org
from app.schemas import DocumentTextUpload

@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)

@pytest.fixture
def test_db_path(tmp_path):
    """Chemin de la base de données de test."""
    db_path = tmp_path / "test_documents.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # Créer un document de test
            conn.execute("""
                INSERT OR REPLACE INTO documents (id, organization_id, filename, storage_path, ingestion_status, chunk_count, ingestion_error)
                VALUES (1, 1, 'test.pdf', '/path/to/test.pdf', 'complete', 10, NULL)
            """)
            conn.commit()
            
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        
        def override_get_current_user():
            return mock_user
        
        def override_require_active_org():
            return mock_org
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org(0)] = override_require_active_org
        
        try:
            response = client.get(
                "/documents/1/status",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == 1
            assert data["status"] == "complete"
            assert data["chunk_count"] == 10
        finally:
            app.dependency_overrides.clear()
    
    def test_get_document_status_not_found(
        self,
        client,
        test_db_path,
        mock_user,
        mock_org
    ):
        """Test récupération du statut d'un document inexistant."""
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
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org(0)] = override_require_active_org
        
        try:
            response = client.get(
                "/documents/999/status",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 404
            assert "non trouvé" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()
    
    @patch('app.routers.documents.enqueue_document_ingestion')
    @patch('app.routers.documents.create_document_entry')
    @patch('app.routers.documents.checksum_bytes')
    @patch('app.routers.documents.parse_tags')
    @patch('app.routers.documents.detect_source_type')
    @patch('app.routers.documents.classify_document')
    @patch('app.routers.documents.extract_text_from_bytes')
    @patch('app.routers.documents.validate_filename')
    @patch('app.routers.documents.validate_file_content')
    @patch('app.routers.documents.settings')
    def test_upload_file_with_classification(
        self,
        mock_settings,
        mock_validate_file,
        mock_validate_filename,
        mock_extract_text,
        mock_classify,
        mock_detect_source,
        mock_parse_tags,
        mock_checksum,
        mock_create_doc,
        mock_enqueue,
        client,
        test_db_path,
        mock_user,
        mock_org,
        temp_data_dir
    ):
        """Test upload avec classification automatique."""
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
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org(0)] = override_require_active_org
        
        mock_settings.enable_file_validation = True
        mock_settings.max_file_size_mb = 10
        mock_settings.data_dir = temp_data_dir
        mock_validate_filename.return_value = "test.pdf"
        mock_validate_file.return_value = ("application/pdf", None)
        mock_extract_text.return_value = "Medical document content"
        mock_classify.return_value = {
            "domain": "medical",
            "confidence": 0.85,
            "alternatives": []
        }
        mock_parse_tags.return_value = []
        mock_checksum.return_value = "abc123"
        mock_detect_source.return_value = "pdf"
        mock_create_doc.return_value = (1, 1)
        mock_enqueue.return_value = "task-123"
        
        try:
            test_file_content = b"PDF content test"
            files = {"file": ("test.pdf", test_file_content, "application/pdf")}
            data = {"tags": "medical,test"}
            
            response = client.post(
                "/documents/upload-with-classification",
                files=files,
                data=data,
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == 1
            assert data["classification"]["domain"] == "medical"
            mock_classify.assert_called_once()
        finally:
            app.dependency_overrides.clear()
    
    @patch('app.routers.documents.enqueue_document_ingestion')
    @patch('app.routers.documents.create_document_entry')
    @patch('app.routers.documents.checksum_bytes')
    @patch('app.routers.documents.parse_tags')
    @patch('app.routers.documents.detect_source_type')
    @patch('app.routers.documents.validate_filename')
    @patch('app.routers.documents.validate_file_content')
    @patch('app.routers.documents.settings')
    def test_upload_file_with_classification_domain_provided(
        self,
        mock_settings,
        mock_validate_file,
        mock_validate_filename,
        mock_detect_source,
        mock_parse_tags,
        mock_checksum,
        mock_create_doc,
        mock_enqueue,
        client,
        test_db_path,
        mock_user,
        mock_org,
        temp_data_dir
    ):
        """Test upload avec domaine fourni (pas de classification)."""
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
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[require_active_org(0)] = override_require_active_org
        
        mock_settings.enable_file_validation = True
        mock_settings.max_file_size_mb = 10
        mock_settings.data_dir = temp_data_dir
        mock_validate_filename.return_value = "test.pdf"
        mock_validate_file.return_value = ("application/pdf", None)
        mock_parse_tags.return_value = []
        mock_checksum.return_value = "abc123"
        mock_detect_source.return_value = "pdf"
        mock_create_doc.return_value = (1, 1)
        mock_enqueue.return_value = "task-123"
        
        try:
            test_file_content = b"PDF content test"
            files = {"file": ("test.pdf", test_file_content, "application/pdf")}
            data = {"domain": "legal"}
            
            response = client.post(
                "/documents/upload-with-classification",
                files=files,
                data=data,
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == 1
            assert data["classification"]["domain"] == "legal"
            # extract_text_from_bytes ne devrait pas être appelé si le domaine est fourni
        finally:
            app.dependency_overrides.clear()

