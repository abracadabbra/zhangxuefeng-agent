"""
用户画像管理 — Pydantic model + Redis 持久化
"""
import json
import os
from typing import Optional
from pydantic import BaseModel, Field

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Redis 客户端（延迟初始化）
_redis_client = None


def _get_redis():
    """延迟获取 Redis 客户端"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis
            _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        except ImportError:
            raise RuntimeError("redis 包未安装，请执行: pip install redis")
    return _redis_client


class UserProfile(BaseModel):
    """
    用户画像 — 必问字段 + 选问字段
    """
    # 必问字段
    score: Optional[int] = Field(None, description="高考分数")
    province: Optional[str] = Field(None, description="所在省份")
    subject: Optional[str] = Field(None, description="文理/选科")
    family_background: Optional[str] = Field(None, description="家庭条件")

    # 选问字段
    target_city: Optional[str] = Field(None, description="目标城市")
    risk_tolerance: Optional[str] = Field(None, description="风险偏好：保守/稳健/激进")
    career_goal: Optional[str] = Field(None, description="职业方向")

    def is_required_complete(self) -> bool:
        """必问字段是否全部填写"""
        return all([
            self.score is not None,
            self.province is not None,
            self.subject is not None,
            self.family_background is not None,
        ])

    def missing_required_fields(self) -> list[str]:
        """返回缺失的必问字段名列表"""
        missing = []
        if self.score is None:
            missing.append("score")
        if self.province is None:
            missing.append("province")
        if self.subject is None:
            missing.append("subject")
        if self.family_background is None:
            missing.append("family_background")
        return missing

    def to_context_dict(self) -> dict:
        """导出为可注入 system prompt 的上下文字典"""
        ctx = {}
        if self.score is not None:
            ctx["分数"] = self.score
        if self.province is not None:
            ctx["省份"] = self.province
        if self.subject is not None:
            ctx["科类"] = self.subject
        if self.family_background is not None:
            ctx["家庭条件"] = self.family_background
        if self.target_city is not None:
            ctx["目标城市"] = self.target_city
        if self.risk_tolerance is not None:
            ctx["风险偏好"] = self.risk_tolerance
        if self.career_goal is not None:
            ctx["职业方向"] = self.career_goal
        return ctx


def _profile_key(session_id: str) -> str:
    return f"user:{session_id}:profile"


async def load_profile(session_id: str) -> UserProfile:
    """从 Redis 加载画像，不存在则返回空画像"""
    r = _get_redis()
    data = await r.get(_profile_key(session_id))
    if data:
        return UserProfile.model_validate_json(data)
    return UserProfile()


async def save_profile(session_id: str, profile: UserProfile) -> None:
    """保存画像到 Redis，TTL 24 小时"""
    r = _get_redis()
    await r.set(_profile_key(session_id), profile.model_dump_json(), ex=86400)


async def update_profile(session_id: str, field: str, value) -> UserProfile:
    """
    更新画像单个字段并持久化
    返回更新后的画像
    """
    profile = await load_profile(session_id)
    if field in UserProfile.model_fields:
        setattr(profile, field, value)
    await save_profile(session_id, profile)
    return profile
