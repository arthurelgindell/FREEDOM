"""
FREEDOM API Dependencies
FastAPI dependency injection for shared resources
"""

import asyncio
from functools import lru_cache
from typing import Optional, Generator
import redis.asyncio as redis
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.orchestration.graphs.council import AICouncil
from .config import get_settings, Settings


# Global instances
_council_instance: Optional[AICouncil] = None
_redis_client: Optional[redis.Redis] = None


@lru_cache()
def get_ai_council() -> AICouncil:
    """Get singleton AI Council instance"""
    global _council_instance
    if _council_instance is None:
        try:
            _council_instance = AICouncil()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI Council initialization failed: {str(e)}"
            )
    return _council_instance


async def get_redis_client(settings: Settings = Depends(get_settings)) -> redis.Redis:
    """Get Redis client connection"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
    return _redis_client


async def verify_council_health(council: AICouncil = Depends(get_ai_council)) -> AICouncil:
    """Verify AI Council is healthy and available"""
    try:
        agent_count = len(council.agents)
        if agent_count == 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No AI agents available"
            )
        return council
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Council health check failed: {str(e)}"
        )


async def validate_api_key(api_key: Optional[str] = None) -> bool:
    """Validate API key for external access (placeholder)"""
    if api_key is None:
        return True  # Allow public access for now
    return True  # TODO: Implement proper API key validation


# Dependency for request rate limiting
class RateLimiter:
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window

    async def __call__(
        self,
        client_ip: str,
        redis_client: redis.Redis = Depends(get_redis_client)
    ) -> bool:
        """Rate limiting check"""
        key = f"rate_limit:{client_ip}"
        current = await redis_client.get(key)

        if current is None:
            await redis_client.setex(key, self.window, 1)
            return True

        if int(current) >= self.requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )

        await redis_client.incr(key)
        return True


# Create rate limiter instance
rate_limiter = RateLimiter(requests=100, window=3600)


# Cleanup on shutdown
async def cleanup_resources():
    """Clean up global resources on app shutdown"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()