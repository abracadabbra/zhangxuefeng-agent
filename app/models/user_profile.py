"""用户画像 Pydantic 模型"""

from typing import Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """
    用户画像 — 必问字段 + 选问字段
    """
    # 必问字段
    score: Optional[int] = Field(None, description="高考分数")
    province: Optional[str] = Field(None, description="所在省份")
    subject: Optional[str] = Field(None, description="文理/选科")
    family_background: Optional[str] = Field(None, description="家庭条件")

    # 选问字段
    target_city: Optional[str] = Field(None, description="目标城市")
    risk_tolerance: Optional[str] = Field(None, description="风险偏好：保守/稳健/激进")
    career_goal: Optional[str] = Field(None, description="职业方向")

    def is_required_complete(self) -> bool:
        """必问字段是否全部填写"""
        return all([
            self.score is not None,
            self.province is not None,
            self.subject is not None,
            self.family_background is not None,
        ])

    def missing_required_fields(self) -> list[str]:
        """返回缺失的必问字段名列表"""
        missing = []
        if self.score is None:
            missing.append("score")
        if self.province is None:
            missing.append("province")
        if self.subject is None:
            missing.append("subject")
        if self.family_background is None:
            missing.append("family_background")
        return missing

    def to_context_dict(self) -> dict:
        """导出为可注入 system prompt 的上下文字典"""
        ctx = {}
        if self.score is not None:
            ctx["分数"] = self.score
        if self.province is not None:
            ctx["省份"] = self.province
        if self.subject is not None:
            ctx["科类"] = self.subject
        if self.family_background is not None:
            ctx["家庭条件"] = self.family_background
        if self.target_city is not None:
            ctx["目标城市"] = self.target_city
        if self.risk_tolerance is not None:
            ctx["风险偏好"] = self.risk_tolerance
        if self.career_goal is not None:
            ctx["职业方向"] = self.career_goal
        return ctx
