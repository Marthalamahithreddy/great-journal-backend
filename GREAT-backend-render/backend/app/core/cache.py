# ═══════════════════════════════════════════════════════════════════════════
# app/core/cache.py
# Optional Redis caching via redis-py async.
# If REDIS_URL is empty, all cache ops are no-ops — app works without Redis.
#
# Strategy:
#   - Cache stats (60 s TTL)       — frequently read, cheap to recompute
#   - Cache article lists (30 s)   — listing queries are expensive with text search
#   - Do NOT cache individual article detail — too many unique keys
#   - Invalidate on any write (submission, admin publish)
# ═══════════════════════════════════════════════════════════════════════════

import json
import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = None


async def get_redis():
    """Lazy-initialize Redis client. Returns None if Redis not configured."""
    global _redis
    if _redis is not None:
        return _redis
    if not settings.REDIS_URL:
        return None
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis.ping()
        logger.info("Redis connected")
        return _redis
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}) — running without cache")
        return None


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    if not r:
        return None
    try:
        val = await r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        await r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        await r.delete(key)
    except Exception:
        pass


async def cache_invalidate_pattern(pattern: str) -> None:
    """Delete all keys matching a glob pattern."""
    r = await get_redis()
    if not r:
        return
    try:
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass
