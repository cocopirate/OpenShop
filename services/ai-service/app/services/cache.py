"""Redis-based result cache for AI completions."""
from __future__ import annotations

import hashlib
import json

import redis.asyncio as aioredis
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

_CACHE_PREFIX = "cache:"


def make_request_hash(system_prompt: str, user_prompt: str) -> str:
    payload = json.dumps({"s": system_prompt, "u": user_prompt}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class ResultCache:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def get(self, request_hash: str) -> str | None:
        key = f"{_CACHE_PREFIX}{request_hash}"
        value = await self._redis.get(key)
        if value is not None:
            log.info("cache.hit", hash=request_hash[:8])
            return value.decode() if isinstance(value, bytes) else value
        return None

    async def set(self, request_hash: str, content: str, ttl: int | None = None) -> None:
        key = f"{_CACHE_PREFIX}{request_hash}"
        ttl = ttl if ttl is not None else settings.CACHE_DEFAULT_TTL
        await self._redis.setex(key, ttl, content)
        log.info("cache.set", hash=request_hash[:8], ttl=ttl)
