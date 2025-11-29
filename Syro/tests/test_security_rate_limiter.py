"""Tests pour le rate limiter avec Redis."""

import pytest
from unittest.mock import Mock, patch

from app.security.rate_limiter import RedisRateLimiter

class TestRedisRateLimiter:
    """Tests pour RedisRateLimiter."""
    
    def test_rate_limiter_memory_fallback(self):
        """Test que le rate limiter fonctionne en mémoire si Redis n'est pas disponible."""
        limiter = RedisRateLimiter(limit=3, window_seconds=60, redis_url=None)
        
        # Premières 3 requêtes devraient passer
        assert limiter.allow("test_key")[0] is True
        assert limiter.allow("test_key")[0] is True
        assert limiter.allow("test_key")[0] is True
        
        # 4ème requête devrait être bloquée
        allowed, remaining = limiter.allow("test_key")
        assert allowed is False
        assert remaining == 0
    
    def test_rate_limiter_different_keys(self):
        """Test que chaque clé a son propre compteur."""
        limiter = RedisRateLimiter(limit=2, window_seconds=60)
        
        # Clé 1
        assert limiter.allow("key1")[0] is True
        assert limiter.allow("key1")[0] is True
        assert limiter.allow("key1")[0] is False
        
        # Clé 2 (indépendante)
        assert limiter.allow("key2")[0] is True
        assert limiter.allow("key2")[0] is True
        assert limiter.allow("key2")[0] is False
    
    def test_rate_limiter_remaining_count(self):
        """Test que le compteur restant est correct."""
        limiter = RedisRateLimiter(limit=5, window_seconds=60)
        
        allowed, remaining = limiter.allow("test")
        assert allowed is True
        assert remaining == 4
        
        allowed, remaining = limiter.allow("test")
        assert allowed is True
        assert remaining == 3
    
    @patch('app.security.rate_limiter.redis')
    def test_rate_limiter_redis_available(self, mock_redis):
        """Test que le rate limiter utilise Redis si disponible."""
        # Mock Redis client
        mock_client = Mock()
        mock_pipeline = Mock()
        mock_client.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [None, 0, None, None]  # zremrangebyscore, zcard, zadd, expire
        
        with patch('app.security.rate_limiter.redis.from_url', return_value=mock_client):
            limiter = RedisRateLimiter(limit=5, window_seconds=60, redis_url="redis://localhost:6379/0")
            
            allowed, remaining = limiter.allow("test_key")
            
            # Vérifier que Redis a été appelé
            assert mock_client.pipeline.called
            assert mock_pipeline.execute.called

