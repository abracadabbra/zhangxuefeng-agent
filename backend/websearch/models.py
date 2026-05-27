"""
WebSearch 数据模型

定义搜索结果、可信度评分、新鲜度标记等数据结构
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FreshnessLevel(str, Enum):
    """新鲜度等级"""
    NORMAL = "normal"      # 正常：1年内数据
    ATTENTION = "attention"  # 注意：1-3年数据
    WARNING = "warning"    # 警告：3年以上数据


class SourceType(str, Enum):
    """数据来源类型"""
    GOVERNMENT = "government"    # 官方/政府网站
    UNIVERSITY = "university"    # 高校官网
    MEDIA = "media"            # 主流媒体
    EDUCATION = "education"      # 教育类网站
    FORUM = "forum"            # 论坛/社区
    OTHER = "other"            # 其他


class SearchResult(BaseModel):
    """单条搜索结果"""
    title: str = Field(..., description="标题")
    url: str = Field(..., description="链接")
    snippet: str = Field(..., description="摘要/内容片段")
    source_type: SourceType = Field(default=SourceType.OTHER, description="来源类型")
    published_date: Optional[datetime] = Field(default=None, description="发布日期")
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0, description="可信度评分 0-1")
    freshness_level: FreshnessLevel = Field(default=FreshnessLevel.NORMAL, description="新鲜度等级")
    freshness_reason: str = Field(default="", description="新鲜度判定原因")


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str = Field(..., description="搜索查询")
    results: list[SearchResult] = Field(default_factory=list, description="搜索结果列表")
    total_results: int = Field(default=0, description="结果总数")
    search_time_ms: float = Field(default=0.0, description="搜索耗时(毫秒)")
    source: str = Field(default="tavily", description="搜索引擎来源")
