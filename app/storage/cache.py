import os
import json
import redis
from typing import Optional, Any

# Get Redis URL from environment or fallback to localhost
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"Warning: Failed to connect to Redis. {e}")
    redis_client = None

def get_cache(key: str) -> Optional[Any]:
    if not redis_client:
        return None
    try:
        val = redis_client.get(key)
        if val:
            return json.loads(val)
        return None
    except Exception as e:
        print(f"Redis get error: {e}")
        return None

def set_cache(key: str, value: Any, expiration_seconds: int = 3600) -> None:
    if not redis_client:
        return
    try:
        redis_client.setex(key, expiration_seconds, json.dumps(value))
    except Exception as e:
        print(f"Redis set error: {e}")
