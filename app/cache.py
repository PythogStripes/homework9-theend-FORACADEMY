import json

import redis.asyncio as aioredis

from app.config import settings

PROJECTS_KEY = "projects:all"
TTL = 60  # секунды

_redis: aioredis.Redis | None = None


def init_redis() -> None:
    global _redis
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None


async def get_projects_cache() -> list[dict] | None:
    if _redis is None:
        return None
    try:
        raw = await _redis.get(PROJECTS_KEY)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def set_projects_cache(data: list[dict]) -> None:
    if _redis is None:
        return
    try:
        await _redis.set(PROJECTS_KEY, json.dumps(data), ex=TTL)
    except Exception:
        pass


async def invalidate_projects_cache() -> None:
    if _redis is None:
        return
    try:
        await _redis.delete(PROJECTS_KEY)
    except Exception:
        pass