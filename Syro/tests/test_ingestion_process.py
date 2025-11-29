"""
Tests unitaires pour le processus d'ingestion de documents.
"""

import pytest
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from app.services.ingestion import process_document, queue_ingestion
from fastapi import BackgroundTasks

class TestIngestionProcess:
    """Tests pour le processus d'ingestion."""
    
    @pytest.fixture
    def test_db(self, tmp_path):
        """Base de données de test."""
        db_path = tmp_path / "test_ingestion.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER,
                filename TEXT,
                source_type TEXT,
                tags TEXT,
                ingestion_status TEXT DEFAULT 'queued',
                chunk_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ingestion_error TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE doc_chunks (
                id INTEGER PRIMARY KEY,
                document_id INTEGER,
                organization_id INTEGER
            )
        """)
        
        # Insérer un document de test
        tags_json = json.dumps(["tag1", "tag2"])
        conn.execute("""
            INSERT INTO documents (id, organization_id, filename, source_type, tags)
            VALUES (1, 1, 'test_snowflake.sql', 'sql', ?)
        """, (tags_json,))
        
        conn.commit()
        return conn
    
    @pytest.fixture
    def test_file(self, tmp_path):
        """Fichier de test."""
        file_path = tmp_path / "test_document.txt"
        file_path.write_text("This is test content for ingestion", encoding="utf-8")
        return str(file_path)
    
    @patch('app.services.ingestion.index_document_content')
    @patch('app.services.ingestion.extract_text_from_bytes')
    @patch('app.services.ingestion.Path')
    @patch('app.services.ingestion.db_session')
    def test_process_document_success(
        self,
        mock_db_session,
        mock_path,
        mock_extract_text,
        mock_index_content,
        test_db,
        test_file
    ):
        """Test traitement réussi d'un document."""
        mock_path_obj = Mock()
        mock_path_obj.read_bytes.return_value = b"test content"
        mock_path_obj.name = "test.txt"
        mock_path.return_value = mock_path_obj
        
        mock_extract_text.return_value = "Extracted text content"
        mock_index_content.return_value = 5
        
        # Mock db_session pour les deux contextes
        mock_db_session.return_value.__enter__.side_effect = [
            test_db,  # Premier contexte (extraction metadata)
            test_db   # Deuxième contexte (update status)
        ]
        mock_db_session.return_value.__exit__.return_value = None
        
        process_document(1, 1, test_file, "text/plain", domain="tech")
        
        mock_extract_text.assert_called_once()
        mock_index_content.assert_called_once()
        
        # Vérifier que le statut a été mis à jour
        row = test_db.execute(
            "SELECT ingestion_status, chunk_count FROM documents WHERE id = 1"
        ).fetchone()
        
        assert row["ingestion_status"] == "complete"
        assert row["chunk_count"] == 5
    
    @patch('app.services.ingestion.extract_text_from_bytes')
    @patch('app.services.ingestion.Path')
    @patch('app.services.ingestion.db_session')
    def test_process_document_empty_text(
        self,
        mock_db_session,
        mock_path,
        mock_extract_text,
        test_db,
        test_file
    ):
        """Test traitement avec texte vide."""
        mock_path_obj = Mock()
        mock_path_obj.read_bytes.return_value = b"test content"
        mock_path_obj.name = "test.txt"
        mock_path.return_value = mock_path_obj
        
        mock_extract_text.return_value = "   "  # Texte vide après strip
        mock_db_session.return_value.__enter__.side_effect = [
            test_db,  # Premier contexte (extraction metadata)
            test_db   # Deuxième contexte (update error)
        ]
        mock_db_session.return_value.__exit__.return_value = None
        
        # L'exception est capturée et gérée dans le code, donc elle ne remonte pas
        # On vérifie plutôt que le statut d'erreur a été mis à jour
        process_document(1, 1, test_file, "text/plain")
        
        # Vérifier que le statut d'erreur a été mis à jour
        row = test_db.execute(
            "SELECT ingestion_status, ingestion_error FROM documents WHERE id = 1"
        ).fetchone()
        
        assert row["ingestion_status"] == "failed"
        assert "Document vide" in row["ingestion_error"]
    
    @patch('app.services.ingestion.index_document_content')
    @patch('app.services.ingestion.extract_text_from_bytes')
    @patch('app.services.ingestion.Path')
    @patch('app.services.ingestion.db_session')
    def test_process_document_with_domain(
        self,
        mock_db_session,
        mock_path,
        mock_extract_text,
        mock_index_content,
        test_db,
        test_file
    ):
        """Test traitement avec domaine forcé."""
        mock_path_obj = Mock()
        mock_path_obj.read_bytes.return_value = b"test content"
        mock_path_obj.name = "test.txt"
        mock_path.return_value = mock_path_obj
        
        mock_extract_text.return_value = "Content"
        mock_index_content.return_value = 3
        
        mock_db_session.return_value.__enter__.side_effect = [test_db, test_db]
        mock_db_session.return_value.__exit__.return_value = None
        
        process_document(1, 1, test_file, "text/plain", domain="medical")
        
        # Vérifier que le domaine est passé dans les métadonnées
        call_args = mock_index_content.call_args
        assert call_args[0][0] == 1  # document_id
        assert call_args[0][1] == 1  # organization_id
        assert call_args[1]["metadata"]["domain"] == "medical"
    
    @patch('app.services.ingestion.index_document_content')
    @patch('app.services.ingestion.extract_text_from_bytes')
    @patch('app.services.ingestion.Path')
    @patch('app.services.ingestion.db_session')
    def test_process_document_metadata_inference(
        self,
        mock_db_session,
        mock_path,
        mock_extract_text,
        mock_index_content,
        test_db,
        test_file
    ):
        """Test inférence de métadonnées depuis le nom de fichier."""
        mock_path_obj = Mock()
        mock_path_obj.read_bytes.return_value = b"test content"
        mock_path_obj.name = "test.txt"
        mock_path.return_value = mock_path_obj
        
        mock_extract_text.return_value = "Content"
        mock_index_content.return_value = 2
        
        mock_db_session.return_value.__enter__.side_effect = [test_db, test_db]
        mock_db_session.return_value.__exit__.return_value = None
        
        process_document(1, 1, test_file, "text/plain")
        
        # Vérifier que le type a été inféré depuis le nom de fichier
        call_args = mock_index_content.call_args
        metadata = call_args[1]["metadata"]
        assert metadata["type"] == "snowflake"  # test_snowflake.sql
    
    def test_queue_ingestion(self):
        """Test ajout d'une tâche d'ingestion à la queue."""
        mock_background_tasks = Mock(spec=BackgroundTasks)
        
        queue_ingestion(
            mock_background_tasks,
            document_id=1,
            organization_id=1,
            storage_path="/path/to/file.txt",
            mime_type="text/plain",
            domain="tech"
        )
        
        mock_background_tasks.add_task.assert_called_once()
        call_args = mock_background_tasks.add_task.call_args
        assert call_args[0][0] == process_document
        assert call_args[0][1] == 1  # document_id
        assert call_args[0][2] == 1  # organization_id

