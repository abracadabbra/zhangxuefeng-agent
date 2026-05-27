"""
录取分数线相关 Pydantic 模式
"""
from typing import Optional
from pydantic import BaseModel, Field


class AdmissionScoreOut(BaseModel):
    """分数线输出模式"""
    id: int
    school_id: int
    major_id: Optional[int] = None
    province: str
    year: int
    batch: str
    subject_type: str
    min_score: Optional[int] = None
    avg_score: Optional[float] = None
    max_score: Optional[int] = None
    min_rank: Optional[int] = None
    plan_count: Optional[int] = None
    # 关联字段（查询时填充）
    school_name: Optional[str] = None
    major_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AdmissionScoreQuery(BaseModel):
    """分数线查询参数"""
    school_name: Optional[str] = Field(None, description="院校名称（模糊匹配）")
    school_id: Optional[int] = Field(None, description="院校ID")
    major_name: Optional[str] = Field(None, description="专业名称（模糊匹配）")
    major_id: Optional[int] = Field(None, description="专业ID")
    province: Optional[str] = Field(None, description="招生省份")
    year: Optional[int] = Field(None, description="年份")
    year_from: Optional[int] = Field(None, description="起始年份")
    year_to: Optional[int] = Field(None, description="截止年份")
    batch: Optional[str] = Field(None, description="批次")
    subject_type: Optional[str] = Field(None, description="科类")
    min_score_floor: Optional[int] = Field(None, description="最低分下限")
    max_score_ceil: Optional[int] = Field(None, description="最低分上限")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")


class ScoreStats(BaseModel):
    """分数统计信息"""
    school_name: str
    major_name: Optional[str] = None
    province: str
    year: int
    min_score: Optional[int] = None
    avg_score: Optional[float] = None
    max_score: Optional[int] = None
    min_rank: Optional[int] = None
    score_count: int = 0
