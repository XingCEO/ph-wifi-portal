from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

_SESSION_PREFIX = "portal_session:"
_ANTI_SPAM_PREFIX = "anti_spam:"
_ACTIVE_USERS_PREFIX = "active_users:"


class RedisService:
    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    async def create_portal_session(self, data: dict[str, Any], ttl: int) -> str:
        session_id = str(uuid.uuid4())
        key = f"{_SESSION_PREFIX}{session_id}"
        await self._redis.setex(key, ttl, json.dumps(data))
        logger.info("portal_session_created", session_id=session_id, ttl=ttl, client_mac=data.get("client_mac"))
        return session_id

    async def get_portal_session(self, session_id: str) -> dict[str, Any] | None:
        key = f"{_SESSION_PREFIX}{session_id}"
        raw = await self._redis.get(key)
        if raw is None:
            return None
        result: dict[str, Any] = json.loads(raw)
        return result

    async def consume_session(self, session_id: str) -> dict[str, Any] | None:
        key = f"{_SESSION_PREFIX}{session_id}"
        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.get(key)
            await pipe.delete(key)
            results = await pipe.execute()
        raw = results[0]
        if raw is None:
            logger.warning("portal_session_not_found", session_id=session_id)
            return None
        data: dict[str, Any] = json.loads(raw)
        logger.info("portal_session_consumed", session_id=session_id, client_mac=data.get("client_mac"))
        return data

    async def check_anti_spam(self, client_mac: str, window_seconds: int) -> bool:
        key = f"{_ANTI_SPAM_PREFIX}{client_mac}"
        exists = await self._redis.exists(key)
        is_allowed = exists == 0
        if not is_allowed:
            logger.warning("anti_spam_blocked", client_mac=client_mac, window_seconds=window_seconds)
        return is_allowed

    async def record_anti_spam(self, client_mac: str, window_seconds: int) -> None:
        key = f"{_ANTI_SPAM_PREFIX}{client_mac}"
        await self._redis.set(key, "1", ex=window_seconds, nx=True)
        logger.info("anti_spam_recorded", client_mac=client_mac, window_seconds=window_seconds)

    async def increment_active_users(self, hotspot_id: int, ttl: int = 3600) -> None:
        key = f"{_ACTIVE_USERS_PREFIX}{hotspot_id}"
        await self._redis.incr(key)
        await self._redis.expire(key, ttl)

    async def decrement_active_users(self, hotspot_id: int) -> None:
        key = f"{_ACTIVE_USERS_PREFIX}{hotspot_id}"
        current = await self._redis.get(key)
        if current and int(current) > 0:
            await self._redis.decr(key)

    async def get_active_users_count(self, hotspot_id: int) -> int:
        key = f"{_ACTIVE_USERS_PREFIX}{hotspot_id}"
        value = await self._redis.get(key)
        if value is None:
            return 0
        return int(value)


_redis_instance: Redis | None = None  # type: ignore[type-arg]


def set_redis_instance(redis: Redis) -> None:  # type: ignore[type-arg]
    global _redis_instance
    _redis_instance = redis


def get_redis() -> Redis:  # type: ignore[type-arg]
    if _redis_instance is None:
        raise RuntimeError("Redis not initialized")
    return _redis_instance


def get_redis_service(redis: Redis | None = None) -> RedisService:  # type: ignore[type-arg]
    r = redis or get_redis()
    return RedisService(r)
