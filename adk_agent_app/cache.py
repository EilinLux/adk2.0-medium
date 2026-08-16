# adk_agent_app/cache.py
"""Centralized Tool Caching with Redis & Resilient In-Memory Fallback.

Provides a Cache-Aside (Lazy Loading) pattern for expensive tool executions:
1. BigQuery geospatial searches (suggeritore_agent_bq_mcp_soste_tool).
2. Firestore user lookups and food knowledge base queries.
3. Vertex AI RAG corpus retrievals.

Features:
- Dual Backend: Connects to Redis / Google Cloud Memorystore via `redis.asyncio` when `REDIS_HOST`
  is configured, and gracefully degrades to an In-Memory TTL store when Redis is unavailable or unconfigured.
- Intelligent Key Generation: Excludes transient framework objects (`tool_context`, `client`, `self`).
- JSON & Datetime Serialization: Transparently serializes ISO timestamps, Decimals, and Pydantic models.
- Decorator `@cached(ttl=3600, prefix="bigquery:soste")` supporting both async and sync tool functions.
"""

import asyncio
from datetime import date, datetime, time
from decimal import Decimal
import functools
import json
import logging
import os
import time as time_module
from typing import Any, Callable, Dict, Optional, Tuple, Union
from uuid import UUID

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_SOCKET_TIMEOUT = float(os.getenv("REDIS_SOCKET_TIMEOUT", "1.5"))

# Global singleton client reference
_redis_client: Optional[aioredis.Redis] = None


class InMemoryCache:
    """Thread-safe and async-friendly in-memory key-value store with TTL expiration."""

    def __init__(self):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self.hits: int = 0
        self.misses: int = 0

    def get(self, key: str) -> Optional[Any]:
        now = time_module.time()
        item = self._store.get(key)
        if item is None:
            self.misses += 1
            return None
        val, expiry = item
        if now > expiry:
            self._store.pop(key, None)
            self.misses += 1
            return None
        self.hits += 1
        return val

    def set(self, key: str, value: Any, ttl: int) -> None:
        expiry = time_module.time() + max(ttl, 1)
        self._store[key] = (value, expiry)

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0

    @property
    def size(self) -> int:
        now = time_module.time()
        # Clean expired
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            self._store.pop(k, None)
        return len(self._store)


# Global in-memory fallback cache
_local_cache = InMemoryCache()


def _json_serializer(value: Any) -> Any:
    """Serializes datetime, Decimal, UUID, and other non-JSON native types."""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return value.__dict__
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def get_redis_client() -> Optional[aioredis.Redis]:
    """Returns or initializes the async Redis client if REDIS_HOST is configured."""
    global _redis_client
    if not REDIS_HOST:
        return None
    if _redis_client is None:
        try:
            _redis_client = aioredis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                socket_timeout=REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
            )
        except Exception as e:
            logger.warning("Could not initialize Redis client for host '%s': %s", REDIS_HOST, e)
            _redis_client = None
    return _redis_client


async def cache_get(key: str, redis: Optional[aioredis.Redis] = None) -> Optional[Any]:
    """Retrieves a cached value from Redis or falls back to in-memory store."""
    client = redis or get_redis_client()
    if client:
        try:
            raw = await client.get(key)
            if raw is not None:
                return json.loads(raw)
        except Exception as e:
            logger.debug("Redis error on cache_get(%s), falling back to in-memory: %s", key, e)

    return _local_cache.get(key)


async def cache_set(
    key: str,
    value: Any,
    ttl: int,
    redis: Optional[aioredis.Redis] = None,
) -> None:
    """Sets a cached value with TTL in Redis and the local in-memory fallback."""
    # Always set in local memory cache
    _local_cache.set(key, value, ttl)

    client = redis or get_redis_client()
    if client:
        try:
            serialized = json.dumps(value, default=_json_serializer)
            await client.set(key, serialized, ex=max(ttl, 1))
        except Exception as e:
            logger.debug("Redis error on cache_set(%s), stored in memory only: %s", key, e)


def cache_clear() -> None:
    """Flushes local in-memory cache and resets hit/miss counters."""
    _local_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Returns hit, miss, and size statistics for observability."""
    return {
        "memory_cache_size": _local_cache.size,
        "memory_hits": _local_cache.hits,
        "memory_misses": _local_cache.misses,
        "redis_configured": bool(REDIS_HOST),
        "redis_host": REDIS_HOST,
    }


def _build_cache_key(func: Callable[..., Any], prefix: Optional[str], args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
    """Builds a deterministic, normalized cache key ignoring ephemeral arguments."""
    key_prefix = prefix or f"{func.__module__}.{func.__name__}"
    key_parts = [key_prefix]

    def _normalize_val(val: Any) -> str:
        if isinstance(val, (list, set, tuple)):
            return "[" + ",".join(sorted(str(x) for x in val)) + "]"
        if isinstance(val, dict):
            return "{" + ",".join(f"{k}:{_normalize_val(v)}" for k, v in sorted(val.items())) + "}"
        return str(val)

    # Positional args (excluding ephemeral framework objects)
    for arg in args:
        if hasattr(arg, "__class__") and arg.__class__.__name__ in ("ToolContext", "Client", "Session"):
            continue
        key_parts.append(_normalize_val(arg))

    # Keyword args (sorted for determinism, excluding ephemeral framework keys)
    for k, v in sorted(kwargs.items()):
        if k in ("tool_context", "client", "db", "session"):
            continue
        key_parts.append(f"{k}:{_normalize_val(v)}")

    return ":".join(key_parts)


def cached(
    ttl: int = 3600,
    prefix: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to cache tool responses in Redis with automatic in-memory fallback.

    Args:
        ttl: Time-to-live in seconds (default: 3600s / 1 hour).
        prefix: Optional namespace prefix (e.g. 'bigquery:soste'). Defaults to module.function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                cache_key = _build_cache_key(func, prefix, args, kwargs)
                cached_val = await cache_get(cache_key)
                if cached_val is not None:
                    logger.debug("Cache HIT for '%s'", cache_key)
                    return cached_val

                logger.debug("Cache MISS for '%s'", cache_key)
                result = await func(*args, **kwargs)

                # Cache successful results (exclude None or explicit error statuses)
                if result is not None:
                    if isinstance(result, dict) and result.get("status") in ("error", "failed"):
                        return result
                    await cache_set(cache_key, result, ttl=ttl)

                return result

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                cache_key = _build_cache_key(func, prefix, args, kwargs)
                # In sync context, check local in-memory cache directly
                cached_val = _local_cache.get(cache_key)
                if cached_val is not None:
                    logger.debug("Cache HIT (sync) for '%s'", cache_key)
                    return cached_val

                logger.debug("Cache MISS (sync) for '%s'", cache_key)
                result = func(*args, **kwargs)

                if result is not None:
                    if isinstance(result, dict) and result.get("status") in ("error", "failed"):
                        return result
                    _local_cache.set(cache_key, result, ttl=ttl)

                return result

            return sync_wrapper

    return decorator
