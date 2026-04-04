"""Redis connection pool management."""
from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_client: Optional[aioredis.Redis] = None
_pool: Optional[aioredis.ConnectionPool] = None


async def init_redis() -> None:
    global _client, _pool
    _pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_POOL_MAX_SIZE,
        decode_responses=False,
    )
    _client = aioredis.Redis(connection_pool=_pool)


async def close_redis() -> None:
    global _client, _pool
    if _client is not None:
        await _client.aclose()
        _client = None
    if _pool is not None:
        await _pool.aclose()
        _pool = None


def get_redis() -> aioredis.Redis:
    if _client is None:
        raise RuntimeError("Redis not initialised. Call init_redis() first.")
    return _client
