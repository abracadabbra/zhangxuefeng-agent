"""
招生计划相关 Pydantic 模式
"""

from pydantic import BaseModel, Field


class EnrollmentPlanOut(BaseModel):
    """招生计划输出模式"""

    id: int
    school_id: int
    major_id: int
    province: str
    year: int
    plan_count: int | None = None
    subject_requirement: str | None = None
    batch: str | None = None
    duration: int | None = None
    tuition: int | None = None
    # 关联字段
    school_name: str | None = None
    major_name: str | None = None

    model_config = {"from_attributes": True}


class EnrollmentPlanQuery(BaseModel):
    """招生计划查询参数"""

    school_name: str | None = Field(None, description="院校名称")
    school_id: int | None = Field(None, description="院校ID")
    major_name: str | None = Field(None, description="专业名称")
    major_id: int | None = Field(None, description="专业ID")
    province: str | None = Field(None, description="招生省份")
    year: int | None = Field(None, description="年份")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
