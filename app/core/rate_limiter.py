import os
import time
from fastapi import HTTPException, Request, Depends
from redis.asyncio import Redis

# Use a connection pool for efficiency
redis_pool = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)

async def get_redis() -> Redis:
    return redis_pool

class RateLimiter:
    def __init__(self, requests: int, window: int):
        """
        :param requests: Max number of requests allowed
        :param window: Time window in seconds
        """
        self.requests = requests
        self.window = window

    async def __call__(self, request: Request, redis: Redis = Depends(get_redis)):
        # Identify client by IP for unauthenticated users, or user_id if we have it in state
        # In a real production setup you'd extract the user ID from the JWT token
        client_ip = request.client.host if request.client else "127.0.0.1"
        key = f"rate_limit:{request.url.path}:{client_ip}"
        
        current_time = time.time()
        window_start = current_time - self.window

        async with redis.pipeline(transaction=True) as pipe:
            # 1. Remove timestamps older than the window
            pipe.zremrangebyscore(key, 0, window_start)
            # 2. Count requests in the current window
            pipe.zcard(key)
            # 3. Add the current request timestamp
            pipe.zadd(key, {str(current_time): current_time})
            # 4. Set TTL on the key to automatically clean it up
            pipe.expire(key, self.window)
            
            # Execute pipeline
            results = await pipe.execute()
            
        request_count = results[1] # result of zcard
        
        if request_count >= self.requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {self.window} seconds."
            )
        
        return True
