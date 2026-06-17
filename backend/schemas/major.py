"""
专业相关 Pydantic 模式
"""

from pydantic import BaseModel, Field


class MajorOut(BaseModel):
    """专业输出模式"""

    id: int
    name: str
    category: str
    sub_category: str | None = None
    employment_rate: float | None = None
    avg_salary: float | None = None
    description: str | None = None
    job_directions: str | None = None
    is_hot: int = 0

    model_config = {"from_attributes": True}


class MajorQuery(BaseModel):
    """专业查询参数"""

    name: str | None = Field(None, description="专业名称（模糊匹配）")
    category: str | None = Field(None, description="学科门类")
    sub_category: str | None = Field(None, description="专业类")
    is_hot: int | None = Field(None, description="是否热门")
    min_employment_rate: float | None = Field(None, description="最低就业率")
    min_avg_salary: float | None = Field(None, description="最低平均薪资")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
