"""Redis sliding-window rate limiter for SMS sending."""
import time
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.config import settings


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after: int  # seconds to wait; 0 if allowed
    limit: int
    remaining: int
    window: int  # window in seconds


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window: int,  # seconds
) -> RateLimitResult:
    """
    Sliding window rate limiter using Redis sorted set.
    Returns RateLimitResult indicating whether the request is allowed.
    """
    now = time.time()
    window_start = now - window
    pipe = redis.pipeline()
    # Remove entries outside the window
    pipe.zremrangebyscore(key, 0, window_start)
    # Count entries currently in the window
    pipe.zcard(key)
    # Add current request with score=timestamp
    pipe.zadd(key, {str(now): now})
    # Set expiry so the key auto-cleans
    pipe.expire(key, window + 1)
    results = await pipe.execute()
    count_before = results[1]  # count before adding current request

    if count_before >= limit:
        # Get the oldest entry to calculate retry_after
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            oldest_time = oldest[0][1]
            retry_after = max(1, int(window - (now - oldest_time)) + 1)
        else:
            retry_after = window
        # Remove the entry we just added since request is rejected
        await redis.zremrangebyscore(key, now, now)
        return RateLimitResult(
            allowed=False,
            retry_after=retry_after,
            limit=limit,
            remaining=0,
            window=window,
        )

    return RateLimitResult(
        allowed=True,
        retry_after=0,
        limit=limit,
        remaining=max(0, limit - count_before - 1),
        window=window,
    )


async def check_phone_rate_limit(redis: Redis, phone: str) -> RateLimitResult:
    """Check per-phone rate limits (configurable per-minute and per-day)."""
    result = await check_rate_limit(
        redis,
        f"sms:rl:phone:min:{phone}",
        limit=settings.SMS_RATE_LIMIT_PHONE_PER_MINUTE,
        window=60,
    )
    if not result.allowed:
        return result
    result = await check_rate_limit(
        redis,
        f"sms:rl:phone:day:{phone}",
        limit=settings.SMS_RATE_LIMIT_PHONE_PER_DAY,
        window=86400,
    )
    return result


async def check_ip_rate_limit(redis: Redis, ip: str) -> RateLimitResult:
    """Check per-IP rate limits (configurable per-minute and per-day)."""
    result = await check_rate_limit(
        redis,
        f"sms:rl:ip:min:{ip}",
        limit=settings.SMS_RATE_LIMIT_IP_PER_MINUTE,
        window=60,
    )
    if not result.allowed:
        return result
    result = await check_rate_limit(
        redis,
        f"sms:rl:ip:day:{ip}",
        limit=settings.SMS_RATE_LIMIT_IP_PER_DAY,
        window=86400,
    )
    return result
