"""
院校相关 Pydantic 模式
"""

from pydantic import BaseModel, Field


class SchoolOut(BaseModel):
    """院校输出模式"""

    id: int
    name: str
    province: str
    city: str
    level: str
    school_type: str
    ranking: int | None = None
    is_985: int = 0
    is_211: int = 0
    is_double_first_class: int = 0
    website: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class SchoolQuery(BaseModel):
    """院校查询参数"""

    name: str | None = Field(None, description="院校名称（模糊匹配）")
    province: str | None = Field(None, description="所在省份")
    level: str | None = Field(None, description="层次: 985/211/双一流/普通")
    school_type: str | None = Field(None, description="类型: 综合/理工/医药等")
    is_985: int | None = Field(None, description="是否985")
    is_211: int | None = Field(None, description="是否211")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
