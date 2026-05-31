"""结构化输出模型与解析器"""
from __future__ import annotations

import logging
from typing import Union

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

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


class MajorRecommendation(BaseModel):
    """专业推荐"""

    major_name: str = Field(description="专业名称")
    category: str = Field(description="学科门类")
    reason: str = Field(description="推荐理由")
    employment_rate: float = Field(description="就业率")
    avg_salary: float = Field(description="平均薪资")


class RecommendationResult(BaseModel):
    """推荐结果容器"""

    recommendations: list[Union[SchoolRecommendation, MajorRecommendation]] = Field(
        default_factory=list,
        description="推荐列表，包含学校推荐和/或专业推荐",
    )
    summary: str = Field(description="总结建议")


# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------

recommendation_parser = PydanticOutputParser(pydantic_object=RecommendationResult)


def get_format_instructions() -> str:
    """获取结构化输出的格式说明，用于注入 system prompt"""
    return recommendation_parser.get_format_instructions()


def parse_recommendation(text: str) -> RecommendationResult:
    """将 LLM 原始文本解析为 RecommendationResult"""
    try:
        return recommendation_parser.parse(text)
    except Exception:
        logger.warning("结构化解析失败，返回兜底结果", exc_info=True)
        return RecommendationResult(recommendations=[], summary=text)
