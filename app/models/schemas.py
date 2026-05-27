"""Pydantic 数据模型"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============== 请求模型 ==============

class ChatRequest(BaseModel):
    """对话请求"""
    session_id: Optional[str] = Field(None, description="会话ID，空则创建新会话")
    message: str = Field(..., description="用户消息")
    user_context: Optional[dict] = Field(default=None, description="用户背景信息")


class PlanRequest(BaseModel):
    """流程式方案生成请求"""
    exam_type: str = Field(..., description="考试类型: 高考/考研")
    score: int = Field(..., description="分数")
    province: str = Field(..., description="省份")
    subject: str = Field(..., description="文理科/选科")
    family_background: str = Field("普通家庭", description="家庭条件")
    target_city: Optional[str] = Field(None, description="目标城市")
    interests: list[str] = Field(default_factory=list, description="兴趣方向")
    needs_realtime_data: bool = Field(True, description="是否需要实时数据")


# ============== 响应模型 ==============

class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    reply: str
    model: str
    usage: Optional[dict] = None


class PlanResponse(BaseModel):
    """方案生成响应"""
    plan: str
    data_sources: list[str] = Field(default_factory=list)
    freshness_warnings: list[str] = Field(default_factory=list)


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    created_at: str
    message_count: int
    user_context: Optional[dict]


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: str
    model: str
