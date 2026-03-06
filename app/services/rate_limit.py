"""
Simple in-memory rate limiter by client IP.
"""
import logging
import time
from collections import defaultdict
from typing import Tuple

from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    def __init__(self, requests_per_window: int = 20, window_seconds: int = 60):
        self._requests = requests_per_window
        self._window = window_seconds
        self._counts: dict[str, list[float]] = defaultdict(list)

    def _key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self._window
        self._counts[key] = [t for t in self._counts[key] if t > cutoff]

    def allow(self, request: Request) -> Tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, remaining). Does NOT record the request."""
        key = self._key(request)
        self._clean(key)
        n = len(self._counts[key])
        if n >= self._requests:
            return False, 0
        return True, self._requests - n - 1

    def record(self, request: Request) -> None:
        """Record one request (call after allow() returned True)."""
        key = self._key(request)
        self._counts[key].append(time.monotonic())

    def raise_if_exceeded(self, request: Request) -> None:
        allowed, remaining = self.allow(request)
        if not allowed:
            logger.warning("Rate limit exceeded for %s", self._key(request))
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
        self.record(request)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
