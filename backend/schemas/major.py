"""
专业相关 Pydantic 模式
"""
from typing import Optional
from pydantic import BaseModel, Field


class MajorOut(BaseModel):
    """专业输出模式"""
    id: int
    name: str
    category: str
    sub_category: Optional[str] = None
    employment_rate: Optional[float] = None
    avg_salary: Optional[float] = None
    description: Optional[str] = None
    job_directions: Optional[str] = None
    is_hot: int = 0

    model_config = {"from_attributes": True}


class MajorQuery(BaseModel):
    """专业查询参数"""
    name: Optional[str] = Field(None, description="专业名称（模糊匹配）")
    category: Optional[str] = Field(None, description="学科门类")
    sub_category: Optional[str] = Field(None, description="专业类")
    is_hot: Optional[int] = Field(None, description="是否热门")
    min_employment_rate: Optional[float] = Field(None, description="最低就业率")
    min_avg_salary: Optional[float] = Field(None, description="最低平均薪资")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
