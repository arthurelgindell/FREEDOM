"""
Caching layer for routing decisions and model responses.
Implements both in-memory LRU cache and Redis cache for distributed systems.
"""

import hashlib
import json
import time
from functools import lru_cache
from typing import Optional, Dict, Any, Protocol
from dataclasses import dataclass, asdict

# Try to import redis, but make it optional
try:
    import redis.asyncio as redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    RedisError = Exception
    REDIS_AVAILABLE = False

from .types import ModelType, TaskType


@dataclass
class CachedDecision:
    """Cached routing decision with metadata"""
    decision_data: Dict[str, Any]
    timestamp: float
    hit_count: int = 0


class CacheInterface(Protocol):
    """Protocol for cache implementations"""

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        ...

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        ...

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        ...

    async def clear(self) -> bool:
        """Clear all cache entries"""
        ...


class InMemoryCache:
    """In-memory LRU cache for single-instance deployments"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CachedDecision] = {}
        self._access_order = []

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if key in self.cache:
            cached = self.cache[key]
            # Check if expired
            if time.time() - cached.timestamp > self.default_ttl:
                del self.cache[key]
                return None

            # Update hit count and access order
            cached.hit_count += 1
            self._update_access_order(key)
            return json.dumps(cached.decision_data)
        return None

    async def set(self, key: str, value: str, ttl: int = None) -> bool:
        """Set value in cache"""
        try:
            # Enforce size limit
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()

            self.cache[key] = CachedDecision(
                decision_data=json.loads(value),
                timestamp=time.time()
            )
            self._update_access_order(key)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self.cache:
            del self.cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False

    async def clear(self) -> bool:
        """Clear all cache entries"""
        self.cache.clear()
        self._access_order.clear()
        return True

    def _update_access_order(self, key: str):
        """Update LRU access order"""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def _evict_lru(self):
        """Evict least recently used item"""
        if self._access_order:
            lru_key = self._access_order[0]
            del self.cache[lru_key]
            self._access_order.pop(0)


class RedisCache:
    """Redis cache for distributed deployments"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0",
                 key_prefix: str = "router:", default_ttl: int = 3600):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.client = None

    async def connect(self):
        """Establish Redis connection"""
        if not REDIS_AVAILABLE:
            # Redis not installed, silently fail
            return

        if not self.client and redis:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            try:
                await self.client.ping()
            except RedisError:
                # Fall back to in-memory if Redis unavailable
                self.client = None
                raise

    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self.client = None

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.client:
            return None

        try:
            full_key = f"{self.key_prefix}{key}"
            value = await self.client.get(full_key)

            # Increment hit count
            if value:
                await self.client.hincrby(f"{full_key}:meta", "hits", 1)

            return value
        except RedisError:
            return None

    async def set(self, key: str, value: str, ttl: int = None) -> bool:
        """Set value in cache with TTL"""
        if not self.client:
            return False

        try:
            full_key = f"{self.key_prefix}{key}"
            ttl = ttl or self.default_ttl

            # Set value with expiration
            await self.client.setex(full_key, ttl, value)

            # Store metadata
            await self.client.hset(f"{full_key}:meta", mapping={
                "created": time.time(),
                "hits": 0
            })
            await self.client.expire(f"{full_key}:meta", ttl)

            return True
        except RedisError:
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.client:
            return False

        try:
            full_key = f"{self.key_prefix}{key}"
            result = await self.client.delete(full_key, f"{full_key}:meta")
            return result > 0
        except RedisError:
            return False

    async def clear(self) -> bool:
        """Clear all cache entries with prefix"""
        if not self.client:
            return False

        try:
            cursor = 0
            while True:
                cursor, keys = await self.client.scan(
                    cursor, match=f"{self.key_prefix}*", count=100
                )
                if keys:
                    await self.client.delete(*keys)
                if cursor == 0:
                    break
            return True
        except RedisError:
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.client:
            return {}

        try:
            info = await self.client.info("stats")
            keys_count = await self.client.dbsize()

            return {
                "total_keys": keys_count,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": info.get("keyspace_hits", 0) /
                          max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            }
        except RedisError:
            return {}


class RoutingCache:
    """High-level routing decision cache"""

    def __init__(self, cache_backend: CacheInterface):
        self.cache = cache_backend

    @staticmethod
    def create_task_hash(objective: str, task_type: TaskType,
                        complexity: int, context: Dict[str, Any] = None) -> str:
        """Create deterministic hash for task parameters"""
        # Include key parameters in hash
        hash_input = {
            "objective": objective[:200],  # Truncate long objectives
            "task_type": task_type.value,
            "complexity": complexity
        }

        # Add relevant context
        if context:
            for key in ["force_model", "local_failures", "budget_remaining"]:
                if key in context:
                    hash_input[key] = context[key]

        # Create hash
        content = json.dumps(hash_input, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def get_cached_decision(self, task_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached routing decision"""
        cached = await self.cache.get(f"decision:{task_hash}")
        if cached:
            return json.loads(cached)
        return None

    async def cache_decision(self, task_hash: str, decision: Dict[str, Any],
                           ttl: int = 3600) -> bool:
        """Cache routing decision"""
        return await self.cache.set(
            f"decision:{task_hash}",
            json.dumps(decision),
            ttl
        )

    async def get_model_response(self, model_type: ModelType, prompt_hash: str) -> Optional[str]:
        """Get cached model response"""
        cached = await self.cache.get(f"response:{model_type.value}:{prompt_hash}")
        return cached

    async def cache_model_response(self, model_type: ModelType, prompt_hash: str,
                                  response: str, ttl: int = 1800) -> bool:
        """Cache model response (shorter TTL for responses)"""
        return await self.cache.set(
            f"response:{model_type.value}:{prompt_hash}",
            response,
            ttl
        )

    async def invalidate_model_cache(self, model_type: ModelType) -> bool:
        """Invalidate all cached responses for a model"""
        # This would need pattern matching in Redis
        # For now, return True
        return True


class HybridCache:
    """Hybrid cache using both in-memory and Redis"""

    def __init__(self, redis_url: str = None, memory_size: int = 100):
        self.memory_cache = InMemoryCache(max_size=memory_size)
        self.redis_cache = None

        if redis_url:
            self.redis_cache = RedisCache(redis_url)

    async def connect(self):
        """Connect to Redis if configured"""
        if self.redis_cache:
            try:
                await self.redis_cache.connect()
            except RedisError:
                print("Redis unavailable, using in-memory cache only")
                self.redis_cache = None

    async def get(self, key: str) -> Optional[str]:
        """Try memory first, then Redis"""
        # Check memory cache
        result = await self.memory_cache.get(key)
        if result:
            return result

        # Check Redis if available
        if self.redis_cache:
            result = await self.redis_cache.get(key)
            if result:
                # Populate memory cache
                await self.memory_cache.set(key, result)
            return result

        return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set in both caches"""
        memory_result = await self.memory_cache.set(key, value, ttl)

        if self.redis_cache:
            redis_result = await self.redis_cache.set(key, value, ttl)
            return memory_result and redis_result

        return memory_result

    async def delete(self, key: str) -> bool:
        """Delete from both caches"""
        memory_result = await self.memory_cache.delete(key)

        if self.redis_cache:
            redis_result = await self.redis_cache.delete(key)
            return memory_result or redis_result

        return memory_result

    async def clear(self) -> bool:
        """Clear both caches"""
        memory_result = await self.memory_cache.clear()

        if self.redis_cache:
            redis_result = await self.redis_cache.clear()
            return memory_result and redis_result

        return memory_result