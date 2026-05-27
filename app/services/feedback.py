"""
反馈服务 — 存储、统计、分析

功能：
- 反馈数据存储（Redis）
- 满意度统计
- 问题分类统计
- 反馈趋势分析
"""
import json
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

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
            raise RuntimeError("redis 包未安装")
    return _redis_client


# ============== 数据模型 ==============

class FeedbackItem(BaseModel):
    """单条反馈"""
    feedback_id: str
    session_id: str
    message_index: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    category: Optional[str] = None  # 问题分类
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class FeedbackStats(BaseModel):
    """反馈统计"""
    total_count: int = 0
    average_rating: float = 0.0
    rating_distribution: dict[int, int] = Field(default_factory=dict)
    category_distribution: dict[str, int] = Field(default_factory=dict)
    recent_trend: list[dict] = Field(default_factory=list)


# ============== 问题分类关键词 ==============

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "志愿填报": ["志愿", "填报", "平行志愿", "提前批", "征集志愿"],
    "院校选择": ["学校", "大学", "院校", "985", "211", "双一流"],
    "专业选择": ["专业", "就业", "前景", "方向"],
    "分数分析": ["分数", "分数线", "位次", "排名"],
    "地域选择": ["城市", "省份", "地区", "北上广"],
    "家庭规划": ["家庭", "经济", "条件", "预算"],
}


def classify_feedback(comment: str) -> str:
    """根据评论内容自动分类"""
    if not comment:
        return "其他"

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in comment:
                return category

    return "其他"


# ============== 存储操作 ==============

def _feedback_key(feedback_id: str) -> str:
    return f"feedback:{feedback_id}"


def _session_feedback_key(session_id: str) -> str:
    return f"feedback:session:{session_id}"


def _stats_key() -> str:
    return "feedback:stats"


async def save_feedback(feedback: FeedbackItem) -> None:
    """保存反馈到 Redis"""
    r = _get_redis()

    # 自动分类
    if feedback.category is None:
        feedback.category = classify_feedback(feedback.comment or "")

    # 保存反馈详情
    await r.set(
        _feedback_key(feedback.feedback_id),
        feedback.model_dump_json(),
        ex=86400 * 30,  # 30 天过期
    )

    # 添加到会话反馈列表
    await r.sadd(_session_feedback_key(feedback.session_id), feedback.feedback_id)

    # 更新统计
    await _update_stats(feedback)


async def get_feedback(feedback_id: str) -> Optional[FeedbackItem]:
    """获取单条反馈"""
    r = _get_redis()
    data = await r.get(_feedback_key(feedback_id))
    if data:
        return FeedbackItem.model_validate_json(data)
    return None


async def get_session_feedbacks(session_id: str) -> list[FeedbackItem]:
    """获取会话的所有反馈"""
    r = _get_redis()
    feedback_ids = await r.smembers(_session_feedback_key(session_id))

    feedbacks = []
    for fid in feedback_ids:
        fb = await get_feedback(fid)
        if fb:
            feedbacks.append(fb)

    return sorted(feedbacks, key=lambda x: x.timestamp, reverse=True)


async def _update_stats(feedback: FeedbackItem) -> None:
    """更新统计数据"""
    r = _get_redis()
    stats_data = await r.get(_stats_key())

    if stats_data:
        stats = json.loads(stats_data)
    else:
        stats = {
            "total_count": 0,
            "rating_sum": 0,
            "rating_distribution": {str(i): 0 for i in range(1, 6)},
            "category_distribution": {},
            "daily_counts": {},
        }

    # 更新统计
    stats["total_count"] += 1
    stats["rating_sum"] += feedback.rating
    stats["rating_distribution"][str(feedback.rating)] = (
        stats["rating_distribution"].get(str(feedback.rating), 0) + 1
    )

    category = feedback.category or "其他"
    stats["category_distribution"][category] = (
        stats["category_distribution"].get(category, 0) + 1
    )

    # 按日统计
    date_key = feedback.timestamp[:10]
    stats["daily_counts"][date_key] = stats["daily_counts"].get(date_key, 0) + 1

    await r.set(_stats_key(), json.dumps(stats, ensure_ascii=False), ex=86400 * 90)


async def get_feedback_stats() -> FeedbackStats:
    """获取反馈统计"""
    r = _get_redis()
    stats_data = await r.get(_stats_key())

    if not stats_data:
        return FeedbackStats()

    stats = json.loads(stats_data)

    total = stats["total_count"]
    avg_rating = stats["rating_sum"] / total if total > 0 else 0.0

    # 最近 7 天趋势
    recent_trend = []
    today = datetime.now()
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        date_key = date.strftime("%Y-%m-%d")
        count = stats.get("daily_counts", {}).get(date_key, 0)
        recent_trend.append({"date": date_key, "count": count})

    return FeedbackStats(
        total_count=total,
        average_rating=round(avg_rating, 2),
        rating_distribution={int(k): v for k, v in stats.get("rating_distribution", {}).items()},
        category_distribution=stats.get("category_distribution", {}),
        recent_trend=recent_trend,
    )
