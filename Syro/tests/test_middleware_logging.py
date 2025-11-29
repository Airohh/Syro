"""Tests pour le middleware de logging."""

import json
import logging
from unittest.mock import Mock, patch

from app.middleware.logging import JSONFormatter, setup_logging, get_logger

class TestJSONFormatter:
    """Tests pour JSONFormatter."""
    
    def test_format_basic_log(self):
        """Test le formatage d'un log basique."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert "timestamp" in data
        assert "logger" in data
    
    def test_format_with_correlation_id(self):
        """Test le formatage avec correlation ID."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "test-correlation-id"
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["correlation_id"] == "test-correlation-id"
    
    def test_format_with_exception(self):
        """Test le formatage avec exception."""
        import sys
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except Exception:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )
            
            result = formatter.format(record)
            data = json.loads(result)
            
            assert data["level"] == "ERROR"
            assert "exception" in data

class TestSetupLogging:
    """Tests pour setup_logging."""
    
    def test_setup_logging_json_format(self):
        """Test la configuration avec format JSON."""
        setup_logging(log_level="INFO", json_format=True)
        
        # Vérifier qu'un handler JSON est configuré
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
    
    def test_setup_logging_standard_format(self):
        """Test la configuration avec format standard."""
        setup_logging(log_level="DEBUG", json_format=False)
        
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

class TestGetLogger:
    """Tests pour get_logger."""
    
    def test_get_logger_returns_logger(self):
        """Test que get_logger retourne un logger."""
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)
    
    def test_get_logger_with_extra(self):
        """Test que le logger peut être utilisé avec extra."""
        logger = get_logger(__name__)
        
        # Ne devrait pas lever d'exception
        logger.info("Test", extra={"user_id": 123, "domain": "tech"})

