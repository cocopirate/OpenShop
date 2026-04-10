"""Redis-based rate limiter for RPM and TPM per caller_service."""
from __future__ import annotations

import time

import redis.asyncio as aioredis
import structlog

from app.config import settings

log = structlog.get_logger(__name__)


class RateLimiter:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def check_and_increment(
        self,
        caller_service: str,
        token_count: int = 0,
    ) -> tuple[bool, int]:
        """Check rate limits and increment counters.

        Returns (allowed, retry_after_seconds).
        """
        now = int(time.time())
        minute_bucket = now // 60

        rpm_key = f"rl:rpm:{caller_service}:{minute_bucket}"
        tpm_key = f"rl:tpm:{caller_service}:{minute_bucket}"

        pipe = self._redis.pipeline()
        pipe.incr(rpm_key)
        pipe.expire(rpm_key, 120)
        pipe.incrby(tpm_key, max(token_count, 1))
        pipe.expire(tpm_key, 120)
        results = await pipe.execute()

        current_rpm: int = results[0]
        current_tpm: int = results[2]

        retry_after = 60 - (now % 60)

        if current_rpm > settings.RATE_LIMIT_RPM:
            log.warning("rate_limit.rpm_exceeded", service=caller_service, rpm=current_rpm)
            return False, retry_after

        if token_count > 0 and current_tpm > settings.RATE_LIMIT_TPM:
            log.warning("rate_limit.tpm_exceeded", service=caller_service, tpm=current_tpm)
            return False, retry_after

        return True, 0
