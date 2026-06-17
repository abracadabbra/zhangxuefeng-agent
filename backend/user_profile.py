"""用户画像管理 — Pydantic model + Redis 持久化"""

import os
from typing import Any

from pydantic import BaseModel, Field

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# 中文上下文字段 -> UserProfile 字段名映射
CONTEXT_KEY_MAP = {
    "分数": "score",
    "省份": "province",
    "科类": "subject",
    "家庭条件": "family_background",
    "目标城市": "target_city",
    "风险偏好": "risk_tolerance",
    "职业方向": "career_goal",
    "省份批次": "admission_batch",
    "选科限制": "subject_requirements",
    "位次": "rank",
    "家庭预算": "family_budget",
    "地域偏好": "region_preference",
    "城市层级": "city_tier",
    "职业偏好权重": "career_preference_weight",
}

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
            raise RuntimeError("redis 包未安装，请执行: pip install redis") from None
    return _redis_client


class UserProfile(BaseModel):
    """
    用户画像 — 必问字段 + 选问字段
    """

    # 必问字段
    score: int | None = Field(None, description="高考分数")
    province: str | None = Field(None, description="所在省份")
    subject: str | None = Field(None, description="文理/选科")
    family_background: str | None = Field(None, description="家庭条件")

    # 选问字段
    target_city: str | None = Field(None, description="目标城市")
    risk_tolerance: str | None = Field(None, description="风险偏好：保守/稳健/激进")
    career_goal: str | None = Field(None, description="职业方向")
    admission_batch: str | None = Field(None, description="省份批次")
    subject_requirements: str | None = Field(None, description="选科限制")
    rank: int | None = Field(None, description="省内位次")
    family_budget: str | None = Field(None, description="家庭预算")
    region_preference: str | None = Field(None, description="地域偏好")
    city_tier: str | None = Field(None, description="城市层级偏好")
    career_preference_weight: int | None = Field(None, description="职业偏好权重 1-10")

    def is_required_complete(self) -> bool:
        """必问字段是否全部填写"""
        return all(
            [
                self.score is not None,
                self.province is not None,
                self.subject is not None,
                self.family_background is not None,
            ]
        )

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

    def to_context_dict(self) -> dict[str, int | str]:
        """导出为可注入 system prompt 的上下文字典"""
        ctx: dict[str, int | str] = {}
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
        if self.admission_batch is not None:
            ctx["省份批次"] = self.admission_batch
        if self.subject_requirements is not None:
            ctx["选科限制"] = self.subject_requirements
        if self.rank is not None:
            ctx["位次"] = self.rank
        if self.family_budget is not None:
            ctx["家庭预算"] = self.family_budget
        if self.region_preference is not None:
            ctx["地域偏好"] = self.region_preference
        if self.city_tier is not None:
            ctx["城市层级"] = self.city_tier
        if self.career_preference_weight is not None:
            ctx["职业偏好权重"] = self.career_preference_weight
        return ctx


def _profile_key(session_id: str) -> str:
    return f"user:{session_id}:profile"


def empty_profile() -> UserProfile:
    """Create an empty profile using Pydantic defaults."""
    return UserProfile.model_validate({})


async def load_profile(session_id: str) -> UserProfile:
    """从 Redis 加载画像，不存在则返回空画像"""
    r = _get_redis()
    data = await r.get(_profile_key(session_id))
    if data:
        return UserProfile.model_validate_json(data)
    return empty_profile()


async def save_profile(session_id: str, profile: UserProfile) -> None:
    """保存画像到 Redis，TTL 24 小时"""
    r = _get_redis()
    await r.set(_profile_key(session_id), profile.model_dump_json(), ex=86400)


def apply_profile_field(profile: UserProfile, field: str, value: Any) -> UserProfile:
    """Update one profile field through Pydantic validation."""
    if field not in UserProfile.model_fields:
        return profile

    data = profile.model_dump()
    data[field] = value
    return UserProfile.model_validate(data)


def apply_profile_context(profile: UserProfile, context: dict[str, Any]) -> UserProfile:
    """Merge Chinese or internal context keys into missing profile fields."""
    updated = profile
    for key, value in context.items():
        if value is None:
            continue
        field = CONTEXT_KEY_MAP.get(key, key)
        if field in UserProfile.model_fields and getattr(updated, field, None) is None:
            updated = apply_profile_field(updated, field, value)
    return updated


async def update_profile(session_id: str, field: str, value: Any) -> UserProfile:
    """
    更新画像单个字段并持久化
    返回更新后的画像
    """
    profile = await load_profile(session_id)
    profile = apply_profile_field(profile, field, value)
    await save_profile(session_id, profile)
    return profile
