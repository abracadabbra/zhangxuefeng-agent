"""
学科排名相关 Pydantic 模式
"""

from pydantic import BaseModel, Field


class SubjectRankingOut(BaseModel):
    """学科排名输出模式"""

    id: int
    school_id: int
    major_category: str
    ranking_source: str
    ranking_year: int
    ranking_position: int | None = None
    grade: str | None = None
    # 关联字段
    school_name: str | None = None

    model_config = {"from_attributes": True}


class SubjectRankingQuery(BaseModel):
    """学科排名查询参数"""

    school_name: str | None = Field(None, description="院校名称（模糊匹配）")
    school_id: int | None = Field(None, description="院校ID")
    major_category: str | None = Field(None, description="学科门类")
    ranking_source: str | None = Field(None, description="排名来源")
    ranking_year: int | None = Field(None, description="评估年份")
    grade: str | None = Field(None, description="评估等级")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
