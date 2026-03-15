import uuid
import json
import redis.asyncio as aioredis
import os
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def get_redis():
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        yield r
    finally:
        await r.aclose()

async def create_portal_session(redis: aioredis.Redis, data: dict, ttl: int = 600) -> str:
    session_id = str(uuid.uuid4())
    await redis.setex(f"portal:session:{session_id}", ttl, json.dumps(data))
    return session_id

async def consume_session(redis: aioredis.Redis, session_id: str) -> dict | None:
    key = f"portal:session:{session_id}"
    pipe = redis.pipeline()
    await pipe.get(key)
    await pipe.delete(key)
    results = await pipe.execute()
    raw = results[0]
    if raw is None:
        return None
    return json.loads(raw)

async def check_anti_spam(redis: aioredis.Redis, client_mac: str, window_seconds: int = 3600) -> bool:
    """Returns True if allowed (not spamming), False if blocked"""
    key = f"portal:antispam:{client_mac.replace(':', '')}"
    result = await redis.get(key)
    return result is None

async def record_anti_spam(redis: aioredis.Redis, client_mac: str, window_seconds: int = 3600):
    key = f"portal:antispam:{client_mac.replace(':', '')}"
    await redis.setex(key, window_seconds, "1")
