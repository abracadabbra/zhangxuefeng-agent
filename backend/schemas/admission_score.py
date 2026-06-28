"""
录取分数线相关 Pydantic 模式
"""
from pydantic import BaseModel, Field


class AdmissionScoreOut(BaseModel):
    """分数线输出模式"""

    id: int
    school_id: int
    major_id: int | None = None
    major_label: str | None = None
    province: str
    year: int
    batch: str
    subject_type: str | None = None
    min_score: int | None = None
    avg_score: float | None = None
    max_score: int | None = None
    min_rank: int | None = None
    plan_count: int | None = None
    # 关联字段（查询时填充）
    school_name: str | None = None
    major_name: str | None = None

    model_config = {"from_attributes": True}


class AdmissionScoreQuery(BaseModel):
    """分数线查询参数"""

    school_name: str | None = Field(None, description="院校名称（模糊匹配）")
    school_id: int | None = Field(None, description="院校ID")
    major_name: str | None = Field(None, description="投档单位名称（模糊匹配 major_label）")
    major_id: int | None = Field(None, description="标准专业ID")
    province: str | None = Field(None, description="招生省份")
    year: int | None = Field(None, description="年份")
    year_from: int | None = Field(None, description="起始年份")
    year_to: int | None = Field(None, description="截止年份")
    batch: str | None = Field(None, description="批次")
    subject_type: str | None = Field(None, description="科类")
    min_score_floor: int | None = Field(None, description="最低分下限")
    max_score_ceil: int | None = Field(None, description="最低分上限")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")


class ScoreStats(BaseModel):
    """分数统计信息"""

    school_name: str
    major_name: str | None = None
    province: str
    year: int
    min_score: int | None = None
    avg_score: float | None = None
    max_score: int | None = None
    min_rank: int | None = None
    score_count: int = 0