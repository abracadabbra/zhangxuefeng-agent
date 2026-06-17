"""
Redis 缓存层

缓存热门查询结果，TTL 5 分钟，支持缓存失效。
Redis 不可用时自动降级为无缓存模式。
"""

import hashlib
import json
import logging
import os
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 分钟

_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """获取 Redis 连接（惰性初始化，连接失败返回 None）"""
    global _pool
    if _pool is not None:
        return _pool
    try:
        _pool = redis.from_url(REDIS_URL, decode_responses=True)
        await _pool.ping()
        logger.info("Redis 连接成功: %s", REDIS_URL)
        return _pool
    except Exception as e:
        logger.warning("Redis 不可用，缓存降级: %s", e)
        _pool = None
        return None


def _make_key(prefix: str, **params) -> str:
    """生成缓存 key: prefix:md5(params)"""
    raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"cache:{prefix}:{digest}"


async def cache_get(prefix: str, **params) -> Any | None:
    """读取缓存，未命中返回 None"""
    r = await get_redis()
    if r is None:
        return None
    key = _make_key(prefix, **params)
    try:
        data = await r.get(key)
        if data is not None:
            return json.loads(data)
    except Exception as e:
        logger.debug("缓存读取失败: %s", e)
    return None


async def cache_set(prefix: str, value: Any, ttl: int = CACHE_TTL, **params) -> None:
    """写入缓存"""
    r = await get_redis()
    if r is None:
        return
    key = _make_key(prefix, **params)
    try:
        await r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
    except Exception as e:
        logger.debug("缓存写入失败: %s", e)


async def cache_delete(prefix: str, **params) -> None:
    """删除指定缓存条目"""
    r = await get_redis()
    if r is None:
        return
    key = _make_key(prefix, **params)
    try:
        await r.delete(key)
    except Exception as e:
        logger.debug("缓存删除失败: %s", e)


async def cache_invalidate_pattern(pattern: str) -> int:
    """按模式批量失效缓存，返回删除数量"""
    r = await get_redis()
    if r is None:
        return 0
    try:
        deleted = 0
        async for key in r.scan_iter(match=f"cache:{pattern}:*", count=100):
            await r.delete(key)
            deleted += 1
        return deleted
    except Exception as e:
        logger.debug("缓存批量失效失败: %s", e)
        return 0


async def cache_flush() -> None:
    """清除所有应用缓存（仅删除 cache: 前缀的 key）"""
    await cache_invalidate_pattern("*")
