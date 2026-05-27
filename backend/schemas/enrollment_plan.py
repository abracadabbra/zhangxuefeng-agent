"""
招生计划相关 Pydantic 模式
"""
from typing import Optional
from pydantic import BaseModel, Field


class EnrollmentPlanOut(BaseModel):
    """招生计划输出模式"""
    id: int
    school_id: int
    major_id: int
    province: str
    year: int
    plan_count: Optional[int] = None
    subject_requirement: Optional[str] = None
    batch: Optional[str] = None
    duration: Optional[int] = None
    tuition: Optional[int] = None
    # 关联字段
    school_name: Optional[str] = None
    major_name: Optional[str] = None

    model_config = {"from_attributes": True}


class EnrollmentPlanQuery(BaseModel):
    """招生计划查询参数"""
    school_name: Optional[str] = Field(None, description="院校名称")
    school_id: Optional[int] = Field(None, description="院校ID")
    major_name: Optional[str] = Field(None, description="专业名称")
    major_id: Optional[int] = Field(None, description="专业ID")
    province: Optional[str] = Field(None, description="招生省份")
    year: Optional[int] = Field(None, description="年份")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
