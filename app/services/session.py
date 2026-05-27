"""
会话管理服务 — Redis 持久化

功能：
- 会话 CRUD（创建、读取、更新、删除）
- 会话 TTL 自动过期（24 小时）
- 对话历史存储
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import get_settings

# Redis 客户端单例
_redis_client = None


def _get_redis():
    """延迟获取 Redis 客户端"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis
            settings = get_settings()
            _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        except ImportError:
            raise RuntimeError("redis 包未安装，请执行: pip install redis")
    return _redis_client


class Message(BaseModel):
    """单条消息"""
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class SessionData(BaseModel):
    """会话数据"""
    session_id: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    messages: list[Message] = Field(default_factory=list)
    user_context: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


def _session_key(session_id: str) -> str:
    """Redis key 格式"""
    return f"session:{session_id}"


async def create_session(session_id: Optional[str] = None) -> SessionData:
    """创建新会话"""
    sid = session_id or str(uuid.uuid4())
    session = SessionData(session_id=sid)
    await save_session(session)
    return session


async def get_session(session_id: str) -> Optional[SessionData]:
    """获取会话，不存在返回 None"""
    r = _get_redis()
    data = await r.get(_session_key(session_id))
    if data:
        return SessionData.model_validate_json(data)
    return None


async def save_session(session: SessionData) -> None:
    """保存会话到 Redis，TTL 24 小时"""
    session.updated_at = datetime.now().isoformat()
    r = _get_redis()
    await r.set(
        _session_key(session.session_id),
        session.model_dump_json(),
        ex=86400,  # 24 小时
    )


async def delete_session(session_id: str) -> bool:
    """删除会话，返回是否成功"""
    r = _get_redis()
    result = await r.delete(_session_key(session_id))
    return result > 0


async def add_message(
    session_id: str,
    role: str,
    content: str,
) -> Optional[SessionData]:
    """向会话添加消息"""
    session = await get_session(session_id)
    if session is None:
        return None

    session.messages.append(Message(role=role, content=content))
    await save_session(session)
    return session


async def get_history(
    session_id: str,
    limit: int = 20,
) -> list[dict]:
    """获取会话历史（最近 N 条）"""
    session = await get_session(session_id)
    if session is None:
        return []

    messages = session.messages[-limit:] if limit > 0 else session.messages
    return [{"role": m.role, "content": m.content} for m in messages]


async def update_context(
    session_id: str,
    context: dict,
) -> Optional[SessionData]:
    """更新用户上下文"""
    session = await get_session(session_id)
    if session is None:
        return None

    session.user_context.update(context)
    await save_session(session)
    return session


async def list_sessions(
    limit: int = 50,
    offset: int = 0,
) -> list[SessionData]:
    """列出所有会话（仅用于管理）"""
    r = _get_redis()
    keys = []
    async for key in r.scan_iter(match="session:*", count=100):
        keys.append(key)
        if len(keys) >= limit + offset:
            break

    sessions = []
    for key in keys[offset:offset + limit]:
        data = await r.get(key)
        if data:
            sessions.append(SessionData.model_validate_json(data))

    return sessions
