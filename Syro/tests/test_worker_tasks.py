"""Tests pour les tâches Celery du worker."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from worker.tasks import process_document_upload

class TestProcessDocumentUpload:
    """Tests pour process_document_upload."""
    
    @patch('worker.tasks.db_session')
    @patch('worker.tasks.extract_text_from_bytes')
    @patch('worker.tasks.index_document_content')
    def test_process_document_success(
        self,
        mock_index,
        mock_extract,
        mock_db_session
    ):
        """Test le traitement réussi d'un document."""
        # Setup mocks
        mock_extract.return_value = "Test document content"
        mock_index.return_value = 5  # 5 chunks
        
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = {
            "filename": "test.pdf",
            "source_type": "pdf",
            "tags": '["tag1", "tag2"]'
        }
        mock_db_session.return_value.__enter__.return_value = mock_conn
        mock_db_session.return_value.__exit__.return_value = None

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"Test document content")
            temp_path = f.name

        try:
            # Mock pour self (Celery task)
            mock_self = Mock()
            mock_self.request.retries = 0
            mock_self.max_retries = 3

            # Appeler la fonction brute (__wrapped__.__func__) avec un self mocké :
            # la task est bind=True ; __wrapped__/run sont des méthodes bound au
            # vrai task, donc l'appel via Celery injecterait ce task comme self et
            # décalerait mock_self sur document_id (TypeError multiple values).
            result = process_document_upload.__wrapped__.__func__(
                mock_self,
                document_id=1,
                organization_id=1,
                storage_path=temp_path,
                mime_type="text/plain",
                domain="tech"
            )

            assert result["status"] == "complete"
            assert result["document_id"] == 1
            assert result["chunk_count"] == 5

            # Vérifier que index_document_content a été appelé
            mock_index.assert_called_once()
        finally:
            # Nettoyer
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('worker.tasks.db_session')
    @patch('worker.tasks.extract_text_from_bytes')
    def test_process_document_empty_content(
        self,
        mock_extract,
        mock_db_session
    ):
        """Test le traitement d'un document vide."""
        mock_extract.return_value = ""  # Contenu vide
        
        mock_conn = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_conn
        mock_db_session.return_value.__exit__.return_value = None
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"")
            temp_path = f.name
        
        try:
            mock_self = Mock()
            mock_self.request.retries = 0
            mock_self.max_retries = 3
            mock_self.retry = Mock(side_effect=Exception("Should retry"))
            
            with pytest.raises(Exception):
                process_document_upload.__wrapped__.__func__(
                    mock_self,
                    document_id=1,
                    organization_id=1,
                    storage_path=temp_path,
                    mime_type="text/plain"
                )
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('worker.tasks.db_session')
    def test_process_document_file_not_found(self, mock_db_session):
        """Test le traitement d'un fichier inexistant."""
        mock_conn = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_conn
        mock_db_session.return_value.__exit__.return_value = None
        
        mock_self = Mock()
        mock_self.request.retries = 0
        mock_self.max_retries = 3
        mock_self.retry = Mock(side_effect=Exception("Should retry"))
        
        with pytest.raises(Exception):
            process_document_upload.__wrapped__.__func__(
                mock_self,
                document_id=1,
                organization_id=1,
                storage_path="/nonexistent/file.txt",
                mime_type="text/plain"
            )

