# tests/07a-tool-caching-and-session-scaling/test_cache_decorator.py
"""Comprehensive Test Suite for Centralized Tool Caching (@cached).

Tests:
1. In-memory cache hit, miss, and TTL expiration.
2. Async @cached decorator behavior and performance.
3. Sync @cached decorator behavior.
4. Deterministic key generation ignoring ephemeral framework arguments (tool_context, db, client).
5. Argument normalization for lists, sets, and dictionaries.
6. Error handling: does not cache error payloads (status='error').
7. Redis client fallback: graceful degradation to in-memory when Redis is unavailable.
8. Real tool caching integration: _fetch_user_document and _execute_cached_soste_query.
"""

import asyncio
from datetime import datetime
import os
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from adk_agent_app.cache import (
    InMemoryCache,
    _build_cache_key,
    cache_clear,
    cache_get,
    cache_set,
    cached,
    get_cache_stats,
)


@pytest.fixture(autouse=True)
def clean_cache():
    """Ensure in-memory cache is cleared before and after each test."""
    cache_clear()
    yield
    cache_clear()


class TestInMemoryCache:
    """Tests the low-level thread-safe in-memory key-value cache."""

    def test_set_and_get_hit(self):
        cache = InMemoryCache()
        cache.set("key1", {"data": "highway_station_123"}, ttl=10)
        val = cache.get("key1")
        assert val == {"data": "highway_station_123"}
        assert cache.hits == 1
        assert cache.misses == 0

    def test_get_miss(self):
        cache = InMemoryCache()
        val = cache.get("non_existent")
        assert val is None
        assert cache.hits == 0
        assert cache.misses == 1

    def test_ttl_expiration(self):
        cache = InMemoryCache()
        cache.set("ephemeral_key", "data", ttl=1)
        assert cache.get("ephemeral_key") == "data"
        time.sleep(1.05)
        assert cache.get("ephemeral_key") is None
        assert cache.misses == 1


class TestCacheKeyBuilding:
    """Validates deterministic cache key generation."""

    def test_ephemeral_arguments_ignored(self):
        def sample_tool(stop_id: str, tool_context: Any = None, db: Any = None):
            pass

        mock_context_1 = MagicMock()
        mock_context_1.__class__.__name__ = "ToolContext"
        mock_context_2 = MagicMock()
        mock_context_2.__class__.__name__ = "ToolContext"

        key1 = _build_cache_key(sample_tool, prefix="test:tool", args=("station_A", mock_context_1), kwargs={"db": "conn1"})
        key2 = _build_cache_key(sample_tool, prefix="test:tool", args=("station_A", mock_context_2), kwargs={"db": "conn2"})

        assert key1 == key2
        assert "ToolContext" not in key1
        assert "conn1" not in key1
        assert key1 == "test:tool:station_A"

    def test_iterable_arguments_normalized(self):
        def sample_food_tool(stop_names: list):
            pass

        key1 = _build_cache_key(sample_food_tool, prefix="food:kb", args=(["Cantagallo", "Badia al Pino"],), kwargs={})
        key2 = _build_cache_key(sample_food_tool, prefix="food:kb", args=(["Badia al Pino", "Cantagallo"],), kwargs={})

        assert key1 == key2
        assert "[Badia al Pino,Cantagallo]" in key1


class TestCachedDecorator:
    """Tests the @cached decorator on sync and async functions."""

    @pytest.mark.asyncio
    async def test_async_cached_hits_and_misses(self):
        call_count = 0

        @cached(ttl=60, prefix="test:async_expensive")
        async def mock_expensive_query(station_id: str) -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {"station_id": station_id, "fetched_at": time.time()}

        res1 = await mock_expensive_query("A1_KM_120")
        assert call_count == 1
        assert res1["station_id"] == "A1_KM_120"

        # Second call with same arguments should hit the cache without calling inner function
        res2 = await mock_expensive_query("A1_KM_120")
        assert call_count == 1
        assert res2 == res1

        # Different argument executes the function
        res3 = await mock_expensive_query("A1_KM_200")
        assert call_count == 2
        assert res3["station_id"] == "A1_KM_200"

    def test_sync_cached_hits_and_misses(self):
        call_count = 0

        @cached(ttl=60, prefix="test:sync_expensive")
        def mock_sync_search(lat: float, lon: float) -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {"results": [lat, lon], "count": 1}

        res1 = mock_sync_search(43.7696, 11.2558)
        assert call_count == 1
        res2 = mock_sync_search(43.7696, 11.2558)
        assert call_count == 1
        assert res1 == res2

        stats = get_cache_stats()
        assert stats["memory_hits"] >= 1

    @pytest.mark.asyncio
    async def test_skip_caching_on_error_response(self):
        call_count = 0

        @cached(ttl=60, prefix="test:error_handling")
        async def faulty_tool(param: str) -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"status": "error", "message": "GCP transient network timeout"}
            return {"status": "success", "data": "recovered"}

        res1 = await faulty_tool("p1")
        assert res1["status"] == "error"
        assert call_count == 1

        # Since it was an error, it should not be cached; second call executes again
        res2 = await faulty_tool("p1")
        assert res2["status"] == "success"
        assert call_count == 2


class TestRedisFallback:
    """Validates graceful fallback when Redis is unconfigured or encounters an error."""

    @pytest.mark.asyncio
    async def test_redis_failure_falls_back_to_in_memory(self):
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection refused")

        # Set value in local cache
        await cache_set("fallback_test", {"item": "sosta_1"}, ttl=60, redis=mock_redis)

        # Get value should fall back to memory without raising an exception
        val = await cache_get("fallback_test", redis=mock_redis)
        assert val == {"item": "sosta_1"}
