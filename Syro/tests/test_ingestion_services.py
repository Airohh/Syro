"""
Tests unitaires pour les services d'ingestion.
"""

import pytest
import sqlite3
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.ingestion import (
    parse_tags,
    _serialize_tags,
    compute_next_version,
    create_document_entry,
    checksum_bytes
)

class TestIngestionServices:
    """Tests pour les services d'ingestion."""
    
    def test_parse_tags_with_tags(self):
        """Test parsing de tags avec tags."""
        result = parse_tags("tag1,tag2,tag3")
        assert result == ["tag1", "tag2", "tag3"]
    
    def test_parse_tags_with_spaces(self):
        """Test parsing de tags avec espaces."""
        result = parse_tags("tag1, tag2 , tag3")
        assert result == ["tag1", "tag2", "tag3"]
    
    def test_parse_tags_empty(self):
        """Test parsing de tags vide."""
        result = parse_tags("")
        assert result is None
    
    def test_parse_tags_none(self):
        """Test parsing de tags None."""
        result = parse_tags(None)
        assert result is None
    
    def test_serialize_tags_with_tags(self):
        """Test sérialisation de tags."""
        result = _serialize_tags(["tag1", "tag2", "tag3"])
        assert result == '["tag1", "tag2", "tag3"]'
    
    def test_serialize_tags_empty(self):
        """Test sérialisation de tags vide."""
        result = _serialize_tags([])
        assert result is None
    
    def test_serialize_tags_none(self):
        """Test sérialisation de tags None."""
        result = _serialize_tags(None)
        assert result is None
    
    def test_serialize_tags_deduplicates(self):
        """Test sérialisation déduplique les tags."""
        result = _serialize_tags(["tag1", "tag2", "tag1"])
        assert result == '["tag1", "tag2"]'
    
    def test_compute_next_version_first(self, tmp_path):
        """Test calcul de version pour premier document."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER,
                filename TEXT,
                version INTEGER
            )
        """)
        
        conn.commit()
        
        version = compute_next_version(conn, 1, "test.txt")
        assert version == 1
        
        conn.close()
    
    def test_compute_next_version_increments(self, tmp_path):
        """Test calcul de version incrémente."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER,
                filename TEXT,
                version INTEGER
            )
        """)
        
        conn.execute("""
            INSERT INTO documents (organization_id, filename, version)
            VALUES (1, 'test.txt', 1)
        """)
        
        conn.commit()
        
        version = compute_next_version(conn, 1, "test.txt")
        assert version == 2
        
        conn.close()
    
    def test_create_document_entry(self, tmp_path):
        """Test création d'entrée de document."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER,
                filename TEXT,
                storage_path TEXT,
                mime_type TEXT,
                checksum TEXT,
                tags TEXT,
                version INTEGER,
                source_type TEXT,
                ingestion_status TEXT,
                created_by_user_id INTEGER,
                access_level_id INTEGER,
                quality_level_id INTEGER,
                updated_at TIMESTAMP
            )
        """)
        
        conn.commit()
        
        doc_id, version = create_document_entry(
            conn,
            organization_id=1,
            filename="test.txt",
            storage_path="/path/to/test.txt",
            mime_type="text/plain",
            checksum="abc123",
            tags=["tag1", "tag2"],
            source_type="text",
            created_by_user_id=1,
            access_level_id=1,
            quality_level_id=1
        )
        
        assert doc_id is not None
        assert version == 1
        
        # Vérifier que le document a été créé
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?",
            (doc_id,)
        ).fetchone()
        
        assert row is not None
        assert row["filename"] == "test.txt"
        assert row["organization_id"] == 1
        
        conn.close()
    
    def test_checksum_bytes(self):
        """Test calcul de checksum."""
        content = b"test content"
        checksum = checksum_bytes(content)
        
        assert isinstance(checksum, str)
        assert len(checksum) > 0
    
    def test_checksum_bytes_consistent(self):
        """Test que le checksum est consistant."""
        content = b"test content"
        checksum1 = checksum_bytes(content)
        checksum2 = checksum_bytes(content)
        
        assert checksum1 == checksum2
    
    def test_checksum_bytes_different(self):
        """Test que des contenus différents donnent des checksums différents."""
        content1 = b"test content 1"
        content2 = b"test content 2"
        
        checksum1 = checksum_bytes(content1)
        checksum2 = checksum_bytes(content2)
        
        assert checksum1 != checksum2

