"""Tests pour le middleware de métriques."""

import pytest
from unittest.mock import Mock, patch

from app.middleware.metrics import (
    MetricsMiddleware,
    get_metrics_response,
    http_requests_total,
    rag_queries_total,
)

class TestMetricsMiddleware:
    """Tests pour MetricsMiddleware."""
    
    @pytest.mark.asyncio
    async def test_metrics_middleware_normalizes_path(self):
        """Test que le middleware normalise les paths."""
        middleware = MetricsMiddleware(Mock())
        
        # Test de normalisation
        assert middleware._normalize_path("/documents/123") == "/documents/{id}"
