"""
Tests unitaires pour le service de statistiques.
"""

import pytest
import sqlite3
from unittest.mock import patch
from datetime import datetime, timedelta

from app.services.stats_service import (
    get_user_stats,
    get_document_stats_by_org,
    get_storage_stats,
    get_usage_stats
)

class TestStatsService:
    """Tests pour le service de statistiques."""
    
    @pytest.fixture
    def test_db(self, tmp_path):
        """Base de données de test."""
        db_path = tmp_path / "test_stats.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER,
                filename TEXT,
                ingestion_status TEXT,
                created_at TIMESTAMP,
                storage_path TEXT,
                source_type TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        
        conn.execute("""
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER,
                created_at TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY,
                conversation_id INTEGER,
                created_at TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE doc_chunks (
                id INTEGER PRIMARY KEY,
                document_id INTEGER,
                organization_id INTEGER
            )
        """)
        
        # Insérer des données de test
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        conn.execute("""
            INSERT INTO documents (id, organization_id, filename, ingestion_status, created_at, storage_path, source_type)
            VALUES 
                (1, 1, 'doc1.pdf', 'complete', ?, '/path/doc1.pdf', 'pdf'),
                (2, 1, 'doc2.txt', 'complete', ?, '/path/doc2.txt', 'text'),
                (3, 1, 'doc3.pdf', 'pending', ?, '/path/doc3.pdf', 'pdf'),
                (4, 1, 'doc4.txt', 'failed', ?, '/path/doc4.txt', 'text')
        """, (month_ago, week_ago, now, now))
        
        conn.execute("""
            INSERT INTO conversations (id, organization_id, created_at)
            VALUES (1, 1, ?), (2, 1, ?)
        """, (week_ago, now))
        
        conn.execute("""
            INSERT INTO messages (id, conversation_id, created_at)
            VALUES (1, 1, ?), (2, 1, ?), (3, 2, ?)
        """, (week_ago, week_ago, now))
        
        conn.execute("""
            INSERT INTO doc_chunks (id, document_id, organization_id)
            VALUES (1, 1, 1), (2, 1, 1), (3, 2, 1)
        """)
        
        conn.commit()
        return conn
    
    def test_get_document_stats_by_org(self, test_db):
        """Test récupération des statistiques de documents."""
        stats = get_document_stats_by_org(1, test_db)
        
        assert stats["total"] == 4
        assert stats["pending"] == 1
        assert stats["failed"] == 1
        assert stats["last_7_days"] == 2
        assert stats["last_30_days"] == 3
    
    @patch('app.config.settings')
    def test_get_storage_stats(self, mock_settings, test_db, tmp_path):
        """Test récupération des statistiques de stockage."""
        # Créer des fichiers de test
        (storage_dir / "file1.txt").write_bytes(b"x" * 1024)  # 1 KB
        (storage_dir / "file2.txt").write_bytes(b"x" * 2048)  # 2 KB
        
        mock_settings.data_dir = tmp_path / "data"
        
        stats = get_storage_stats(1, test_db)
        
        assert "total_bytes" in stats
        assert "total_mb" in stats
        assert "total_gb" in stats
        assert "chunks_indexed" in stats
        assert stats["chunks_indexed"] == 3
        assert stats["total_bytes"] == 3072  # 1 KB + 2 KB
    
    def test_get_usage_stats(self, test_db):
        """Test récupération des statistiques d'utilisation."""
        stats = get_usage_stats(1, test_db)
        
        assert stats["conversations"] == 2
        assert stats["messages"] == 3
        assert stats["recent_conversations_7d"] >= 1
    
    @patch('app.services.stats_service.get_document_stats_by_org')
    @patch('app.services.stats_service.get_storage_stats')
    @patch('app.services.stats_service.get_usage_stats')
    def test_get_user_stats(
        self,
        mock_usage_stats,
        mock_storage_stats,
        mock_doc_stats,
        test_db
    ):
        """Test récupération des statistiques complètes utilisateur."""
        mock_doc_stats.return_value = {
            "total": 10,
            "by_domain": {"tech": 5},
            "last_7_days": 2,
            "last_30_days": 5,
            "pending": 0,
            "failed": 0
        }
        
        mock_storage_stats.return_value = {
            "total_bytes": 1000000,
            "total_mb": 1.0,
            "total_gb": 0.001,
            "chunks_indexed": 100
        }
        
        mock_usage_stats.return_value = {
            "conversations": 20,
            "messages": 100,
            "recent_conversations_7d": 5
        }
        
        stats = get_user_stats(1, 1)
        
        assert "documents" in stats
        assert "storage" in stats
        assert "usage" in stats
        assert stats["documents"]["total"] == 10
        assert stats["storage"]["total_mb"] == 1.0
        assert stats["usage"]["conversations"] == 20

