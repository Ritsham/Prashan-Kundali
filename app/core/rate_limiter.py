import hashlib
import logging
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from app.config import get_settings


redis_pool = Redis.from_url(get_settings().redis_url, decode_responses=True)
logger = logging.getLogger("kundali.rate_limit")
_memory_buckets: dict[str, list[float]] = {}


async def get_redis() -> Redis:
    return redis_pool


class RateLimiter:
    def __init__(self, requests: int, window: int, scope: Optional[str] = None):
        self.requests = requests
        self.window = window
        self.scope = scope

    async def __call__(self, request: Request, redis: Redis = Depends(get_redis)):
        scope = self.scope or request.url.path
        client_ip = request.client.host if request.client else "127.0.0.1"
        identity = request.headers.get("authorization") or client_ip
        identity_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        key = f"rate_limit:{scope}:{identity_hash}"

        current_time = time.time()
        window_start = current_time - self.window

        try:
            async with redis.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                pipe.zadd(key, {str(current_time): current_time})
                pipe.expire(key, self.window)
                results = await pipe.execute()
            request_count = int(results[1])
        except Exception:
            logger.warning("redis_rate_limiter_unavailable scope=%s", scope, exc_info=True)
            bucket = [stamp for stamp in _memory_buckets.get(key, []) if stamp >= window_start]
            request_count = len(bucket)
            bucket.append(current_time)
            _memory_buckets[key] = bucket

        if request_count >= self.requests:
            raise HTTPException(
                status_code=429,
                detail={"message": "Rate limit exceeded", "retry_after_seconds": self.window},
                headers={"Retry-After": str(self.window)},
            )

        return True


public_limiter = RateLimiter(requests=60, window=60, scope="public")
auth_limiter = RateLimiter(requests=30, window=60, scope="auth")
llm_limiter = RateLimiter(requests=10, window=60, scope="llm")
booking_limiter = RateLimiter(requests=8, window=60, scope="booking")
payment_limiter = RateLimiter(requests=12, window=60, scope="payment")
websocket_limiter = RateLimiter(requests=20, window=60, scope="websocket")
