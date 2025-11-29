from collections import defaultdict, deque
from typing import Deque, DefaultDict
import time

class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self.calls: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        q = self.calls[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True

chat_rate_limiter = RateLimiter(limit=30, window_seconds=60)
doc_upload_rate_limiter = RateLimiter(limit=10, window_seconds=60)
