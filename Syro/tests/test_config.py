"""Tests pour la configuration."""

import pytest
from pathlib import Path

from app.config import Settings, settings

class TestSettings:
    """Tests pour la classe Settings."""
    
    def test_settings_defaults(self):
        """Test les valeurs par défaut des settings."""
        assert settings.app_name == "Syro"
        # domain est surchargeable via .env ; on vérifie le type, pas la valeur
        # (la valeur par défaut de classe est "tech" mais l'env peut la forcer).
        assert isinstance(settings.domain, str) and settings.domain
        assert settings.debug is True
    
    def test_settings_paths_exist(self):
        """Test que les chemins sont créés."""
        assert settings.data_dir.exists()
        assert (settings.data_dir / "tmp").exists()
    
    def test_get_fast_mode_config(self):
        """Test la configuration mode fast."""
        config = settings.get_fast_mode_config()
        
        assert config["retrieval_top_k"] == 5
        assert config["rerank_top_k"] == 3
        assert config["enable_reranking"] is False
    
    def test_get_quality_mode_config(self):
        """Test la configuration mode quality."""
        config = settings.get_quality_mode_config()
        
        assert config["retrieval_top_k"] == 15
        assert config["rerank_top_k"] == 5
        assert config["enable_reranking"] is True
    
    def test_security_settings(self):
        """Test les settings de sécurité."""
        assert hasattr(settings, "cors_allow_origins")
        assert hasattr(settings, "max_file_size_mb")
        assert hasattr(settings, "enable_file_validation")
        assert hasattr(settings, "enable_security_headers")
    
    def test_observability_settings(self):
        """Test les settings d'observabilité."""
        assert hasattr(settings, "log_level")
        assert hasattr(settings, "log_json_format")
        assert hasattr(settings, "metrics_enabled")
        assert hasattr(settings, "tracing_enabled")

