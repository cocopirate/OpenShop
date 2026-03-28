"""Async Redis client – lifecycle helpers shared by the entire service."""
from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_pool: ConnectionPool | None = None
_client: Redis | None = None


async def init_redis() -> None:
    global _pool, _client
    _pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_POOL_MAX_SIZE,
        decode_responses=True,
    )
    _client = Redis(connection_pool=_pool)


async def close_redis() -> None:
    global _pool, _client
    if _client is not None:
        await _client.aclose()
        _client = None
    if _pool is not None:
        await _pool.aclose()
        _pool = None


def get_redis() -> Redis:
    if _client is None:
        raise RuntimeError(
            "Redis client is not initialised. Call init_redis() first."
        )
    return _client
