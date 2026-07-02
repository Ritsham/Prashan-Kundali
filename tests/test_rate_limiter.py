import unittest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request

from app.core.rate_limiter import RateLimiter

class TestRateLimiter(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limiter_allows_requests_below_limit(self):
        # Mock request
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.url = MagicMock()
        request.url.path = "/api/test"

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis.zcard.return_value = 5  # Under limit
        
        limiter = RateLimiter(requests=10, window=60)
        
        with patch("app.core.rate_limiter.get_redis_client", return_value=mock_redis):
            # Should not raise exception
            await limiter(request)
            
            # Verify redis calls
            mock_redis.zremrangebyscore.assert_called_once()
            mock_redis.zcard.assert_called_once()
            mock_redis.zadd.assert_called_once()
            mock_redis.expire.assert_called_once()

    async def test_rate_limiter_blocks_requests_above_limit(self):
        # Mock request
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.url = MagicMock()
        request.url.path = "/api/test"

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis.zcard.return_value = 10  # At/above limit
        
        limiter = RateLimiter(requests=10, window=60)
        
        with patch("app.core.rate_limiter.get_redis_client", return_value=mock_redis):
            with self.assertRaises(HTTPException) as context:
                await limiter(request)
                
            self.assertEqual(context.exception.status_code, 429)
            self.assertEqual(context.exception.detail, "Rate limit exceeded. Please try again later.")
