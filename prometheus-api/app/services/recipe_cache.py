from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, Optional, Protocol

try:
    import redis
except Exception:  # pragma: no cover - optional dependency resolution
    redis = None

from ..core.config import get_settings
from ..schemas.recipes import Recipe

logger = logging.getLogger(__name__)


class RecipeCacheProtocol(Protocol):
    def set_many(
        self,
        device_id: str,
        inventory_fingerprint: str,
        recipes: list[Recipe],
        ttl_minutes: int,
    ) -> None: ...

    def get_batch(
        self,
        device_id: str,
        inventory_fingerprint: str,
        limit: int | None = None,
    ) -> Optional[list[Recipe]]: ...

    def get(self, device_id: str, recipe_id: str) -> Optional[Recipe]: ...

    def invalidate_device(self, device_id: str) -> None: ...


class RecipeCache:
    """In-memory recipe cache keyed by device and inventory fingerprint."""

    def __init__(self, max_devices: int = 100) -> None:
        self._lock = Lock()
        self._max_devices = max(1, int(max_devices))
        self._recipe_store: Dict[str, Dict[str, tuple[datetime, Recipe]]] = {}
        self._batch_store: Dict[str, Dict[str, tuple[datetime, list[str]]]] = {}
        self._device_last_updated: Dict[str, datetime] = {}

    def set_many(
        self,
        device_id: str,
        inventory_fingerprint: str,
        recipes: list[Recipe],
        ttl_minutes: int,
    ) -> None:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=ttl_minutes)
        with self._lock:
            recipe_bucket = self._recipe_store.setdefault(device_id, {})
            batch_bucket = self._batch_store.setdefault(device_id, {})
            self._device_last_updated[device_id] = now

            recipe_ids: list[str] = []
            for recipe in recipes:
                recipe_bucket[recipe.id] = (expiry, recipe)
                recipe_ids.append(recipe.id)

            batch_bucket[inventory_fingerprint] = (expiry, recipe_ids)
            self._prune_locked()

    def get_batch(
        self,
        device_id: str,
        inventory_fingerprint: str,
        limit: int | None = None,
    ) -> Optional[list[Recipe]]:
        now = datetime.now(timezone.utc)
        with self._lock:
            batch_bucket = self._batch_store.get(device_id)
            recipe_bucket = self._recipe_store.get(device_id)
            if not batch_bucket or not recipe_bucket:
                logger.info(
                    "recipe_cache.batch device_id=%s fingerprint=%s status=miss reason=device_not_found",
                    device_id,
                    inventory_fingerprint,
                )
                return None

            batch_payload = batch_bucket.get(inventory_fingerprint)
            if not batch_payload:
                logger.info(
                    "recipe_cache.batch device_id=%s fingerprint=%s status=miss reason=fingerprint_not_found",
                    device_id,
                    inventory_fingerprint,
                )
                return None

            batch_expiry, recipe_ids = batch_payload
            if batch_expiry < now:
                del batch_bucket[inventory_fingerprint]
                if not batch_bucket and device_id in self._batch_store:
                    del self._batch_store[device_id]
                    if device_id not in self._recipe_store:
                        self._device_last_updated.pop(device_id, None)
                logger.info(
                    "recipe_cache.batch device_id=%s fingerprint=%s status=miss reason=batch_expired",
                    device_id,
                    inventory_fingerprint,
                )
                return None

            recipes: list[Recipe] = []
            for recipe_id in recipe_ids:
                recipe_payload = recipe_bucket.get(recipe_id)
                if not recipe_payload:
                    logger.info(
                        "recipe_cache.batch device_id=%s fingerprint=%s status=miss reason=recipe_missing recipe_id=%s",
                        device_id,
                        inventory_fingerprint,
                        recipe_id,
                    )
                    return None
                recipe_expiry, recipe = recipe_payload
                if recipe_expiry < now:
                    del recipe_bucket[recipe_id]
                    logger.info(
                        "recipe_cache.batch device_id=%s fingerprint=%s status=miss reason=recipe_expired recipe_id=%s",
                        device_id,
                        inventory_fingerprint,
                        recipe_id,
                    )
                    return None
                recipes.append(recipe)

            if limit is not None:
                recipes = recipes[:limit]
            logger.info(
                "recipe_cache.batch device_id=%s fingerprint=%s status=hit count=%s",
                device_id,
                inventory_fingerprint,
                len(recipes),
            )
            return recipes

    def get(self, device_id: str, recipe_id: str) -> Optional[Recipe]:
        now = datetime.now(timezone.utc)
        with self._lock:
            bucket = self._recipe_store.get(device_id)
            if not bucket:
                logger.info(
                    "recipe_cache.recipe device_id=%s recipe_id=%s status=miss reason=device_not_found",
                    device_id,
                    recipe_id,
                )
                return None

            payload = bucket.get(recipe_id)
            if not payload:
                logger.info(
                    "recipe_cache.recipe device_id=%s recipe_id=%s status=miss reason=recipe_not_found",
                    device_id,
                    recipe_id,
                )
                return None

            expiry, recipe = payload
            if expiry < now:
                del bucket[recipe_id]
                if not bucket and device_id in self._recipe_store:
                    del self._recipe_store[device_id]
                    if device_id not in self._batch_store:
                        self._device_last_updated.pop(device_id, None)
                logger.info(
                    "recipe_cache.recipe device_id=%s recipe_id=%s status=miss reason=recipe_expired",
                    device_id,
                    recipe_id,
                )
                return None

            logger.info(
                "recipe_cache.recipe device_id=%s recipe_id=%s status=hit",
                device_id,
                recipe_id,
            )
            return recipe

    def invalidate_device(self, device_id: str) -> None:
        with self._lock:
            self._recipe_store.pop(device_id, None)
            self._batch_store.pop(device_id, None)
            self._device_last_updated.pop(device_id, None)

    def _prune_locked(self) -> None:
        now = datetime.now(timezone.utc)

        for device_id in list(self._recipe_store.keys()):
            recipe_bucket = self._recipe_store[device_id]
            for recipe_id in list(recipe_bucket.keys()):
                if recipe_bucket[recipe_id][0] < now:
                    del recipe_bucket[recipe_id]
            if not recipe_bucket:
                del self._recipe_store[device_id]
                if device_id not in self._batch_store:
                    self._device_last_updated.pop(device_id, None)

        for device_id in list(self._batch_store.keys()):
            batch_bucket = self._batch_store[device_id]
            for fingerprint in list(batch_bucket.keys()):
                if batch_bucket[fingerprint][0] < now:
                    del batch_bucket[fingerprint]
            if not batch_bucket:
                del self._batch_store[device_id]
                if device_id not in self._recipe_store:
                    self._device_last_updated.pop(device_id, None)

        while len(self._device_last_updated) > self._max_devices:
            oldest_device = min(self._device_last_updated, key=self._device_last_updated.get)
            self._recipe_store.pop(oldest_device, None)
            self._batch_store.pop(oldest_device, None)
            self._device_last_updated.pop(oldest_device, None)


class RedisRecipeCache:
    """Redis-backed recipe cache. Falls back to memory when unavailable."""

    def __init__(self, redis_url: str, prefix: str = "prometheus:recipe-cache") -> None:
        if redis is None:
            raise RuntimeError("redis package is not installed")

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._prefix = prefix
        self._client.ping()

    def _recipe_key(self, device_id: str, recipe_id: str) -> str:
        return f"{self._prefix}:recipe:{device_id}:{recipe_id}"

    def _batch_key(self, device_id: str, inventory_fingerprint: str) -> str:
        return f"{self._prefix}:batch:{device_id}:{inventory_fingerprint}"

    def set_many(
        self,
        device_id: str,
        inventory_fingerprint: str,
        recipes: list[Recipe],
        ttl_minutes: int,
    ) -> None:
        ttl_seconds = max(60, int(ttl_minutes * 60))
        recipe_ids = [recipe.id for recipe in recipes]

        try:
            pipe = self._client.pipeline(transaction=False)
            for recipe in recipes:
                pipe.setex(self._recipe_key(device_id, recipe.id), ttl_seconds, recipe.model_dump_json())
            pipe.setex(self._batch_key(device_id, inventory_fingerprint), ttl_seconds, json.dumps(recipe_ids))
            pipe.execute()
        except Exception:
            logger.exception("redis cache set_many failed device_id=%s", device_id)

    def get_batch(
        self,
        device_id: str,
        inventory_fingerprint: str,
        limit: int | None = None,
    ) -> Optional[list[Recipe]]:
        try:
            payload = self._client.get(self._batch_key(device_id, inventory_fingerprint))
            if not payload:
                return None

            recipe_ids = json.loads(payload)
            if not isinstance(recipe_ids, list):
                return None

            if limit is not None:
                recipe_ids = recipe_ids[:limit]
            if not recipe_ids:
                return []

            keys = [self._recipe_key(device_id, recipe_id) for recipe_id in recipe_ids]
            recipe_payloads = self._client.mget(keys)
            if not recipe_payloads or any(item is None for item in recipe_payloads):
                return None

            recipes: list[Recipe] = []
            for item in recipe_payloads:
                recipes.append(Recipe.model_validate_json(item))
            return recipes
        except Exception:
            logger.exception("redis cache get_batch failed device_id=%s", device_id)
            return None

    def get(self, device_id: str, recipe_id: str) -> Optional[Recipe]:
        try:
            payload = self._client.get(self._recipe_key(device_id, recipe_id))
            if not payload:
                return None
            return Recipe.model_validate_json(payload)
        except Exception:
            logger.exception("redis cache get failed device_id=%s recipe_id=%s", device_id, recipe_id)
            return None

    def invalidate_device(self, device_id: str) -> None:
        try:
            keys = list(self._client.scan_iter(match=f"{self._prefix}:recipe:{device_id}:*", count=200))
            keys.extend(self._client.scan_iter(match=f"{self._prefix}:batch:{device_id}:*", count=200))
            if keys:
                self._client.delete(*keys)
        except Exception:
            logger.exception("redis cache invalidate failed device_id=%s", device_id)


def _build_recipe_cache() -> RecipeCacheProtocol:
    settings = get_settings()
    backend = ((settings.cache_backend or "").strip().casefold()) or "auto"
    if backend not in {"auto", "memory", "redis"}:
        logger.warning("unknown CACHE_BACKEND=%s. fallback to auto", backend)
        backend = "auto"

    if backend in {"auto", "redis"} and settings.redis_url:
        try:
            logger.info("recipe cache backend=redis")
            return RedisRecipeCache(settings.redis_url)
        except Exception:
            logger.exception("redis cache unavailable. fallback to memory")
            if backend == "redis":
                logger.warning("CACHE_BACKEND=redis but redis is unavailable. using memory cache")

    logger.info("recipe cache backend=memory")
    return RecipeCache()


_recipe_cache: RecipeCacheProtocol = _build_recipe_cache()


def get_recipe_cache() -> RecipeCacheProtocol:
    return _recipe_cache
