"""结构化输出模型与解析器"""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------


class SchoolRecommendation(BaseModel):
    """学校推荐"""

    school_name: str = Field(description="学校名称")
    reason: str = Field(description="推荐理由")
    admission_probability: float = Field(description="录取概率 0-1")
    match_score: int = Field(description="匹配度 1-10")
    strategy: Literal["冲", "稳", "保"] | None = Field(
        default=None,
        description="志愿梯度：冲、稳、保",
    )
    risk_points: list[str] = Field(
        default_factory=list,
        description="风险点，如分数波动、选科限制、地域/预算约束",
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description="替代学校或替代专业方案",
    )


class MajorRecommendation(BaseModel):
    """专业推荐"""

    major_name: str = Field(description="专业名称")
    category: str = Field(description="学科门类")
    reason: str = Field(description="推荐理由")
    employment_rate: float = Field(description="就业率")
    avg_salary: float = Field(description="平均薪资")
    strategy: Literal["冲", "稳", "保"] | None = Field(
        default=None,
        description="推荐梯度：冲、稳、保",
    )
    risk_points: list[str] = Field(
        default_factory=list,
        description="风险点，如就业周期、读研要求、行业波动",
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description="替代专业或交叉方向",
    )


class RecommendationResult(BaseModel):
    """推荐结果容器"""

    recommendations: list[SchoolRecommendation | MajorRecommendation] = Field(
        default_factory=list,
        description="推荐列表，包含学校推荐和/或专业推荐",
    )
    summary: str = Field(description="总结建议")
    gradient_summary: dict[Literal["冲", "稳", "保"], list[str]] = Field(
        default_factory=lambda: {"冲": [], "稳": [], "保": []},
        description="按冲稳保分组的推荐名称摘要",
    )


# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------

recommendation_parser = PydanticOutputParser(pydantic_object=RecommendationResult)


RECOMMENDATION_OUTPUT_REQUIREMENTS = "\n".join(
    [
        "推荐结果生成要求：",
        "- 每个推荐项都必须说明为什么适合该考生，reason 不能空泛。",
        "- 每个推荐项都必须给出 strategy，且只能是“冲”“稳”“保”之一。",
        (
            "- 每个推荐项都必须给出 risk_points，列出至少 1 个真实风险；"
            "没有明确风险时也要说明“需核实最新招生章程/分数波动”。"
        ),
        "- 每个推荐项都必须给出 alternatives，列出至少 1 个替代学校、替代专业或相邻方案。",
        (
            "- gradient_summary 必须按“冲”“稳”“保”汇总 recommendations 中的推荐名称，"
            "名称要与 school_name 或 major_name 保持一致。"
        ),
        "- summary 需要总结冲稳保组合策略、关键理由和主要风险。",
    ]
)


def get_format_instructions() -> str:
    """获取结构化输出的格式说明，用于注入 system prompt"""
    return recommendation_parser.get_format_instructions()


def get_recommendation_instructions() -> str:
    """获取结构化推荐输出说明，包含业务要求和 Pydantic 格式约束。"""
    return f"{RECOMMENDATION_OUTPUT_REQUIREMENTS}\n\n{get_format_instructions()}"


def parse_recommendation(text: str) -> RecommendationResult:
    """将 LLM 原始文本解析为 RecommendationResult"""
    try:
        return recommendation_parser.parse(text)
    except Exception:
        logger.warning("结构化解析失败，返回兜底结果", exc_info=True)
        return RecommendationResult(recommendations=[], summary=text)
