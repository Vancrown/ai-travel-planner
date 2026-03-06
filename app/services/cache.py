"""
In-memory cache with TTL for itinerary responses.
Key = hash of request body to avoid duplicate LLM calls.
"""
import hashlib
import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._store: dict[str, tuple[float, Any]] = {}

    def _key(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def get(self, payload: dict[str, Any]) -> Optional[dict]:
        k = self._key(payload)
        if k not in self._store:
            return None
        expires_at, value = self._store[k]
        if time.monotonic() > expires_at:
            del self._store[k]
            return None
        logger.debug("Cache hit for itinerary request")
        return value

    def set(self, payload: dict[str, Any], value: dict) -> None:
        k = self._key(payload)
        if len(self._store) >= self._max_size:
            self._evict_expired()
            if len(self._store) >= self._max_size:
                oldest = min(self._store.keys(), key=lambda x: self._store[x][0])
                del self._store[oldest]
        self._store[k] = (time.monotonic() + self._ttl, value)

    def _evict_expired(self) -> None:
        now = time.monotonic()
        for k in list(self._store.keys()):
            if self._store[k][0] <= now:
                del self._store[k]
