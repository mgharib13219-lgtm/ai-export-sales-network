import time
from collections import defaultdict, deque
from threading import Lock

class SlidingWindowLimiter:
    def __init__(self, limit=20, window_seconds=60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key):
        now = time.monotonic()
        with self._lock:
            q = self._events[key]
            cutoff = now - self.window_seconds
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

pipeline_limiter = SlidingWindowLimiter(limit=10, window_seconds=60)
