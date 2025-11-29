"""Rate limiting avec Redis pour distribution."""

import time
from typing import Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..config import settings

class RedisRateLimiter:
    """Rate limiter distribué avec Redis."""
    
    def __init__(
        self,
        limit: int,
        window_seconds: int,
        redis_url: Optional[str] = None
    ):
        self.limit = limit
        self.window = window_seconds
        self.redis_url = redis_url or settings.celery_broker_url
        
        if REDIS_AVAILABLE and self.redis_url:
            try:
                # Extraire l'URL Redis depuis celery_broker_url
                if self.redis_url.startswith("redis://"):
                    self.redis_client = redis.from_url(self.redis_url)
                else:
                    self.redis_client = None
            except Exception:
                self.redis_client = None
        else:
            self.redis_client = None
    
    def allow(self, key: str) -> tuple[bool, int]:
        """
        Vérifier si une requête est autorisée.
        
        Args:
            key: Clé unique pour le rate limiting (ex: "user:123" ou "ip:1.2.3.4")
        
        Returns:
            tuple: (allowed, remaining)
        """
        if self.redis_client:
            return self._allow_redis(key)
        else:
            return self._allow_memory(key)
    
    def _allow_redis(self, key: str) -> tuple[bool, int]:
        """Rate limiting avec Redis (distribué)."""
        try:
            redis_key = f"rate_limit:{key}"
            now = time.time()
            window_start = now - self.window
            
            # Utiliser un pipeline pour atomicité
            pipe = self.redis_client.pipeline()
            
            # Supprimer les entrées expirées
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Compter les requêtes dans la fenêtre
            pipe.zcard(redis_key)
            
            # Ajouter la requête actuelle
            pipe.zadd(redis_key, {str(now): now})
            
            # Définir l'expiration
            pipe.expire(redis_key, self.window)
            
            results = pipe.execute()
            count = results[1]
            
            if count < self.limit:
                return True, self.limit - count - 1
            else:
                return False, 0
                
        except Exception:
            # Fallback sur mémoire si Redis échoue
            return self._allow_memory(key)
    
    def _allow_memory(self, key: str) -> tuple[bool, int]:
        """Rate limiting en mémoire (fallback)."""
        from collections import defaultdict, deque
        from typing import Deque, DefaultDict
        
        if not hasattr(self, "_memory_store"):
            self._memory_store: DefaultDict[str, Deque[float]] = defaultdict(deque)
        
        now = time.time()
        q = self._memory_store[key]
        
        # Supprimer les entrées expirées
        while q and now - q[0] > self.window:
            q.popleft()
        
        if len(q) < self.limit:
            q.append(now)
            return True, self.limit - len(q)
        else:
            return False, 0

# Rate limiters globaux
chat_rate_limiter = RedisRateLimiter(limit=30, window_seconds=60)
doc_upload_rate_limiter = RedisRateLimiter(limit=10, window_seconds=60)
auth_rate_limiter = RedisRateLimiter(limit=5, window_seconds=60)  # Limite stricte pour login

