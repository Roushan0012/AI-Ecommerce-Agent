"""Lightweight In-Memory Rate Limiter (Phase 18C).

Provides sliding-window rate limiting without external infrastructure dependencies (e.g. Redis).
Protects abuse-prone authentication and public API endpoints against credential-stuffing and DoS.
"""

import threading
import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request


class InMemoryRateLimiter:
    """Thread-safe sliding-window in-memory rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        self._storage: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, float]:
        """
        Determines whether a request with the given key is permitted within the sliding window.

        Returns:
            Tuple[bool, int, float]:
                - is_allowed: True if request within limit, False otherwise.
                - current_count: Number of requests in current window.
                - retry_after: Seconds remaining until the oldest request expires (0.0 if allowed).
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            timestamps = self._storage[key]
            # Prune timestamps older than window
            valid_timestamps = [t for t in timestamps if t > window_start]

            if len(valid_timestamps) < max_requests:
                valid_timestamps.append(now)
                self._storage[key] = valid_timestamps
                return True, len(valid_timestamps), 0.0

            self._storage[key] = valid_timestamps
            oldest = valid_timestamps[0]
            retry_after = max(1.0, (oldest + window_seconds) - now)
            return False, len(valid_timestamps), retry_after

    def reset(self) -> None:
        """Clears all stored rate limit keys. Useful for test suites."""
        with self._lock:
            self._storage.clear()


def get_client_ip(request: Request) -> str:
    """
    Extracts the client IP address from standard headers or client connection.
    Prioritizes the leftmost X-Forwarded-For IP when behind a reverse proxy.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


# Global singleton instance
rate_limiter = InMemoryRateLimiter()
