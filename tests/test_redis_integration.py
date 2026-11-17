"""Real Redis integration coverage for shared rate limits and conversation sessions."""
import asyncio
import os
import uuid

import pytest
from redis.asyncio import Redis

from app import main


@pytest.mark.skipif(not os.getenv("TEST_REDIS_URL"), reason="TEST_REDIS_URL is not configured")
def test_real_redis_rate_limit_and_session_roundtrip():
    async def exercise():
        client = Redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
        original_client = main.redis_client
        main.redis_client = client
        suffix = uuid.uuid4().hex
        ip = f"198.51.100.{int(suffix[:2], 16) % 254 + 1}"
        response_id = f"resp_{suffix}"
        rate_key = f"cv-agent:rate:{__import__('hashlib').sha256(ip.encode()).hexdigest()}"
        session_key = main.session_key(response_id)
        try:
            assert await main.rate_limited(ip) is False
            await main.remember(response_id, [{"role": "user", "content": "hola"}], "respuesta")
            stored = await main.load_history(response_id)
            assert stored == [
                {"role": "user", "content": "hola"},
                {"role": "assistant", "content": "respuesta"},
            ]
            assert await client.ttl(session_key) > 0
        finally:
            main.redis_client = original_client
            await client.delete(rate_key, session_key)
            await client.aclose()

    asyncio.run(exercise())
