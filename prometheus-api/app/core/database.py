from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from fastapi import HTTPException, status
from supabase import Client, create_client

from .config import get_settings

try:
    import redis
except ImportError:  # pragma: no cover - optional at runtime
    redis = None


@lru_cache()
def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase is not configured",
        )
    return create_client(settings.supabase_url, settings.supabase_key)


@dataclass
class IdempotencyEntry:
    status_code: int
    body: str
    headers: dict[str, str]
    expires_at: float


class IdempotencyStore:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self.ttl_seconds = ttl_seconds
        self._memory: dict[str, IdempotencyEntry] = {}
        self._lock = threading.Lock()
        self._redis = self._build_redis_client()

    def _build_redis_client(self):
        if redis is None:
            return None

        settings = get_settings()
        if not settings.redis_url:
            return None

        try:
            client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception:
            return None

    def get(self, key: str) -> IdempotencyEntry | None:
        now = time.time()
        if self._redis is not None:
            try:
                raw = self._redis.get(key)
                if not raw:
                    return None
                data = json.loads(raw)
                return IdempotencyEntry(
                    status_code=int(data["status_code"]),
                    body=str(data["body"]),
                    headers=dict(data.get("headers") or {}),
                    expires_at=now + max(int(self._redis.ttl(key) or 0), 0),
                )
            except Exception:
                return None

        with self._lock:
            entry = self._memory.get(key)
            if not entry:
                return None
            if entry.expires_at <= now:
                self._memory.pop(key, None)
                return None
            return entry

    def set(self, key: str, status_code: int, body: str, headers: dict[str, str]) -> None:
        safe_headers = {
            "content-type": headers.get("content-type", "application/json"),
        }

        if self._redis is not None:
            try:
                payload = json.dumps(
                    {
                        "status_code": status_code,
                        "body": body,
                        "headers": safe_headers,
                    }
                )
                self._redis.setex(key, self.ttl_seconds, payload)
                return
            except Exception:
                return

        now = time.time()
        entry = IdempotencyEntry(
            status_code=status_code,
            body=body,
            headers=safe_headers,
            expires_at=now + self.ttl_seconds,
        )
        with self._lock:
            self._memory[key] = entry
            self._cleanup_locked(now)

    def _cleanup_locked(self, now: float) -> None:
        expired = [key for key, value in self._memory.items() if value.expires_at <= now]
        for key in expired:
            self._memory.pop(key, None)


# Dependency for FastAPI
def get_db():
    """FastAPI dependency for database access."""
    client = get_supabase_client()
    try:
        yield client
    finally:
        pass  # Supabase client doesn't need explicit cleanup


@lru_cache()
def get_idempotency_store() -> IdempotencyStore:
    settings = get_settings()
    ttl_seconds = 600
    if settings.cache_backend == "memory":
        ttl_seconds = 600
    return IdempotencyStore(ttl_seconds=ttl_seconds)
