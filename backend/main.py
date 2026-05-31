"""
张雪峰 AI 咨询 Agent — FastAPI 后端

提供对话 API、SSE 流式输出、Function Calling 支持、灵魂追问引擎
"""
import os
import json
import logging
import uuid
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# 加载 .env 文件（覆盖已存在的环境变量）
load_dotenv(override=True)

logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.agent.core import AgentCore
from backend.soul_query import SoulQueryEngine, QueryState
from backend.user_profile import UserProfile, load_profile, save_profile, update_profile
from backend.database import init_db
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.cache import cache_flush
from backend.routers import schools_router, majors_router, scores_router, plans_router, subject_rankings_router
from backend.session_store import SessionStore

# ============== Config ==============
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("OPENAI_MODEL") or os.getenv("MODEL", "gpt-4o-mini")
USE_LANGCHAIN = os.getenv("USE_LANGCHAIN", "false").lower() == "true"

# ============== Pydantic Models ==============
class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="会话ID，空则创建新会话")
    message: str = Field(..., description="用户消息")
    user_context: Optional[dict] = Field(default=None, description="用户背景信息")
    stream: bool = Field(default=False, description="是否使用 SSE 流式输出")

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    model: str
    tool_calls: list[dict] = Field(default_factory=list, description="工具调用记录")
    usage: Optional[dict] = None

class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    message_count: int
    user_context: Optional[dict]
    messages: list[dict] = Field(default_factory=list, description="完整消息历史")

# ============== Persistent Store ==============
session_store = SessionStore()

# ============== Agent Instance ==============
agent = None  # AgentCore 或 LangChainAgent

# 灵魂追问引擎实例
soul_engine = SoulQueryEngine()


def get_agent():
    """获取 Agent 实例（根据 USE_LANGCHAIN 切换）"""
    global agent
    if agent is None:
        if USE_LANGCHAIN:
            from backend.agent.langchain_agent import LangChainAgent
            agent = LangChainAgent(session_store=session_store)
            logger.info("Using LangChain Agent")
        else:
            agent = AgentCore(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                model=MODEL,
            )
            logger.info("Using AgentCore")
    return agent


# ============== FastAPI App ==============
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[{datetime.now()}] 张雪峰 Agent 启动 | Model: {MODEL}")

    # 初始化数据库
    init_db()
    print(f"[{datetime.now()}] 数据库初始化完成")

    # 配置 LangSmith
    if USE_LANGCHAIN:
        from backend.agent.langsmith_config import setup_langsmith
        setup_langsmith()

    yield
    print(f"[{datetime.now()}] 张雪峰 Agent 关闭")


app = FastAPI(
    title="张雪峰 AI 咨询 Agent",
    description="高考/考研/职业规划咨询，基于张雪峰认知操作系统",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=os.getenv("CORS_ORIGINS", "*") != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册数据查询路由
app.include_router(schools_router)
app.include_router(majors_router)
app.include_router(scores_router)
app.include_router(plans_router)
app.include_router(subject_rankings_router)


# ============== Helper ==============

# 中文字段名 → UserProfile 字段名映射
_CONTEXT_KEY_MAP = {
    "分数": "score",
    "省份": "province",
    "科类": "subject",
    "家庭条件": "family_background",
    "目标城市": "target_city",
    "风险偏好": "risk_tolerance",
    "职业方向": "career_goal",
}


def _extract_profile_from_message(message: str, profile: UserProfile) -> bool:
    """
    从用户消息中提取画像信息（简单关键词匹配）
    返回 True 表示画像有更新
    """
    import re
    updated = False

    # 提取分数（纯数字或 xx 分）
    score_match = re.search(r'(\d{2,3})\s*分', message)
    if score_match and profile.score is None:
        score = int(score_match.group(1))
        if 100 <= score <= 750:
            profile.score = score
            updated = True

    provinces = [
        "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林",
        "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
        "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西",
        "甘肃", "青海", "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆",
    ]
    for p in provinces:
        if p in message and profile.province is None:
            profile.province = p
            updated = True
            break

    # 提取文理科
    if profile.subject is None:
        if "文科" in message or "文" == message.strip():
            profile.subject = "文科"
            updated = True
        elif "理科" in message or "理" == message.strip():
            profile.subject = "理科"
            updated = True

    # 提取家庭条件
    if profile.family_background is None:
        if "工薪" in message or "打工" in message or "普通家庭" in message:
            profile.family_background = "工薪阶层"
            updated = True
        elif "做生意" in message or "经商" in message or "企业" in message:
            profile.family_background = "经商家庭"
            updated = True
        elif "体制内" in message or "公务员" in message or "事业单位" in message:
            profile.family_background = "体制内家庭"
            updated = True

    return updated


# ============== API Endpoints ==============
@app.get("/")
async def root():
    return {
        "status": "ok",
        "agent": "张雪峰 AI",
        "model": MODEL,
        "features": ["function_calling", "sse_streaming", "soul_query", "data_query"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/db/status")
async def db_status():
    """数据库状态检查"""
    from backend.database import SessionLocal
    from backend.models import School, Major, AdmissionScore, EnrollmentPlan
    from contextlib import closing
    with closing(SessionLocal()) as db:
        try:
            return {
                "status": "connected",
                "tables": {
                    "schools": db.query(School).count(),
                    "majors": db.query(Major).count(),
                    "admission_scores": db.query(AdmissionScore).count(),
                    "enrollment_plans": db.query(EnrollmentPlan).count(),
                },
            }
        except Exception as e:
            return {"status": "error", "detail": str(e)}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """核心对话接口 — 支持非流式和 SSE 流式输出"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 获取或创建会话（持久化）
    session_id = req.session_id or str(uuid.uuid4())
    session = session_store.get_or_create(session_id, user_context=req.user_context)
    query_state: QueryState = session["query_state"]

    if req.user_context:
        session["user_context"].update(req.user_context)
        session_store.update_context(session_id, session["user_context"])

    # 加载用户画像（Redis 持久化）
    try:
        profile = await load_profile(session_id)
    except Exception:
        profile = UserProfile()

    if session["user_context"]:
        for key, val in session["user_context"].items():
            if val is None:
                continue
            field = _CONTEXT_KEY_MAP.get(key)
            if field and field in UserProfile.model_fields and getattr(profile, field, None) is None:
                setattr(profile, field, val)

    # 从用户消息中尝试提取画像信息
    profile_updated = _extract_profile_from_message(req.message, profile)
    if profile_updated:
        try:
            await save_profile(session_id, profile)
        except Exception:
            pass

    # 如果画像有数据但 Redis 中为空（前端通过 user_context 传入），持久化
    if profile.is_required_complete():
        try:
            await save_profile(session_id, profile)
        except Exception:
            pass

    # 灵魂追问：检查画像完整性
    if not soul_engine.is_query_complete(profile):
        question = soul_engine.get_next_question(profile, query_state)
        if question:
            session_store.add_message(session_id, "user", req.message)
            session_store.add_message(session_id, "assistant", question)
            session_store.update_query_state(session_id, query_state)
            return ChatResponse(
                session_id=session_id,
                reply=question,
                model="soul-query-engine",
                usage=None,
            )

    # 画像完整，正常调用 LLM
    session["user_context"] = profile.to_context_dict()
    session_store.update_context(session_id, session["user_context"])

    # 检查 API Key
    if not OPENAI_API_KEY and not USE_LANGCHAIN:
        error_reply = "抱歉，AI 服务暂时不可用（API Key 未配置）。请联系管理员配置 OPENAI_API_KEY 环境变量。"
        session_store.add_message(session_id, "user", req.message)
        session_store.add_message(session_id, "assistant", error_reply)
        return ChatResponse(
            session_id=session_id,
            reply=error_reply,
            model=MODEL,
            tool_calls=[],
            usage=None,
        )

    agent_instance = get_agent()

    # LangChain Agent 模式
    if USE_LANGCHAIN:
        if req.stream:
            return EventSourceResponse(
                _stream_response_langchain(agent_instance, session_id, req.message, session["user_context"]),
                media_type="text/event-stream",
            )

        result = await agent_instance.chat(
            message=req.message,
            session_id=session_id,
            user_context=session["user_context"],
        )
        return ChatResponse(
            session_id=session_id,
            reply=result["reply"],
            model="langchain-agent",
            tool_calls=result.get("tool_calls", []),
            usage=None,
        )

    # 传统 AgentCore 模式
    # 构建历史消息
    messages = list(session["history"])
    messages.append({"role": "user", "content": req.message})

    # 流式输出
    if req.stream:
        return EventSourceResponse(
            _stream_response(agent_instance, messages, session_id, req.message, session["user_context"]),
            media_type="text/event-stream",
        )

    # 非流式输出
    try:
        result = await agent_instance.chat(messages, user_context=session["user_context"])
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        error_reply = f"抱歉，AI 服务暂时出现问题，请稍后重试。错误：{type(e).__name__}"
        session_store.add_message(session_id, "user", req.message)
        session_store.add_message(session_id, "assistant", error_reply)
        return ChatResponse(
            session_id=session_id,
            reply=error_reply,
            model=MODEL,
            tool_calls=[],
            usage=None,
        )

    # 持久化历史
    session_store.add_message(session_id, "user", req.message)
    session_store.add_message(session_id, "assistant", result["reply"])

    return ChatResponse(
        session_id=session_id,
        reply=result["reply"],
        model=MODEL,
        tool_calls=result["tool_calls"],
        usage=result["usage"],
    )


async def _stream_response(
    agent_instance: AgentCore,
    messages: list[dict],
    session_id: str,
    user_message: str,
    user_context: dict,
):
    """SSE 流式响应生成器"""
    full_reply = ""
    tool_calls_log = []

    try:
        async for event in agent_instance.chat_stream(messages, user_context=user_context):
            if event["type"] == "text":
                full_reply += event["content"]
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "text", "content": event["content"]}, ensure_ascii=False),
                }
            elif event["type"] == "tool_call":
                tool_calls_log.append({"name": event["name"], "arguments": event["arguments"]})
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "tool_call", "name": event["name"], "arguments": event["arguments"]}, ensure_ascii=False),
                }
            elif event["type"] == "tool_result":
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "tool_result", "name": event["name"], "result": event["result"]}, ensure_ascii=False),
                }
            elif event["type"] == "done":
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "done", "usage": event["usage"]}, ensure_ascii=False),
                }
    except Exception as e:
        logger.error(f"LLM 流式调用失败: {type(e).__name__}: {e}", exc_info=True)
        yield {
            "event": "message",
            "data": json.dumps({"type": "text", "content": f"\n\nAI 服务暂时不可用：{type(e).__name__}: {str(e)[:200]}"}, ensure_ascii=False),
        }
        yield {
            "event": "message",
            "data": json.dumps({"type": "done", "usage": None}, ensure_ascii=False),
        }

    # 持久化历史
    session_store.add_message(session_id, "user", user_message)
    session_store.add_message(session_id, "assistant", full_reply)


async def _stream_response_langchain(
    agent_instance,
    session_id: str,
    user_message: str,
    user_context: dict,
):
    """LangChain Agent 的 SSE 流式响应生成器"""
    try:
        async for event in agent_instance.chat_stream(
            message=user_message,
            session_id=session_id,
            user_context=user_context,
        ):
            if event["type"] == "text":
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "text", "content": event["content"]}, ensure_ascii=False),
                }
            elif event["type"] == "tool_call":
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "tool_call", "name": event["name"], "arguments": event["arguments"]}, ensure_ascii=False),
                }
            elif event["type"] == "tool_result":
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "tool_result", "name": event["name"], "result": event["result"]}, ensure_ascii=False),
                }
            elif event["type"] == "done":
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "done", "usage": None}, ensure_ascii=False),
                }
    except Exception as e:
        logger.error(f"LangChain 流式调用失败: {type(e).__name__}: {e}", exc_info=True)
        yield {
            "event": "message",
            "data": json.dumps({"type": "text", "content": f"\n\nAI 服务暂时不可用：{type(e).__name__}: {str(e)[:200]}"}, ensure_ascii=False),
        }
        yield {
            "event": "message",
            "data": json.dumps({"type": "done", "usage": None}, ensure_ascii=False),
        }


# ============== 画像管理 API ==============

class ProfileUpdateRequest(BaseModel):
    field: str = Field(..., description="字段名")
    value: str = Field(..., description="字段值")

class ProfileResponse(BaseModel):
    session_id: str
    profile: dict
    is_complete: bool
    missing_fields: list[str]

class NextQuestionResponse(BaseModel):
    session_id: str
    question: Optional[str]
    round_count: int
    is_complete: bool


@app.get("/profile/{session_id}", response_model=ProfileResponse)
async def get_profile(session_id: str):
    """获取用户画像"""
    try:
        profile = await load_profile(session_id)
    except Exception:
        session = session_store.get_or_create(session_id)
        ctx = session.get("user_context", {})
        profile = UserProfile(**ctx) if ctx else UserProfile()

    return ProfileResponse(
        session_id=session_id,
        profile=profile.model_dump(),
        is_complete=profile.is_required_complete(),
        missing_fields=profile.missing_required_fields(),
    )


@app.put("/profile/{session_id}", response_model=ProfileResponse)
async def update_profile_endpoint(session_id: str, req: ProfileUpdateRequest):
    """更新用户画像字段"""
    try:
        profile = await update_profile(session_id, req.field, req.value)
    except Exception:
        profile = UserProfile()
        if req.field in UserProfile.model_fields:
            setattr(profile, req.field, req.value)

    return ProfileResponse(
        session_id=session_id,
        profile=profile.model_dump(),
        is_complete=profile.is_required_complete(),
        missing_fields=profile.missing_required_fields(),
    )


@app.get("/profile/{session_id}/next-question", response_model=NextQuestionResponse)
async def get_next_question(session_id: str):
    """获取下一个追问问题"""
    try:
        profile = await load_profile(session_id)
    except Exception:
        session = session_store.get_or_create(session_id)
        ctx = session.get("user_context", {})
        profile = UserProfile(**ctx) if ctx else UserProfile()

    session = session_store.get_or_create(session_id)
    query_state: QueryState = session["query_state"]

    question = soul_engine.get_next_question(profile, query_state)

    return NextQuestionResponse(
        session_id=session_id,
        question=question,
        round_count=query_state.round_count,
        is_complete=soul_engine.is_query_complete(profile),
    )


@app.get("/sessions")
async def list_sessions(limit: int = 20):
    """列出最近的会话"""
    return session_store.list_recent(limit=limit)


@app.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    s = session_store.get_or_create(session_id)
    return SessionInfo(
        session_id=session_id,
        created_at=s["created_at"],
        message_count=s["message_count"],
        user_context=s["user_context"],
        messages=s["history"],
    )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    session_store.delete(session_id)
    return {"status": "deleted", "session_id": session_id}


# ============== 推荐 API ==============

class RecommendRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="会话ID")
    message: str = Field(..., description="推荐请求，如'推荐计算机专业'")
    user_context: Optional[dict] = Field(default=None, description="用户背景信息")


@app.post("/recommend")
async def recommend(req: RecommendRequest):
    """结构化推荐接口 — 返回学校/专业推荐结果"""
    if not USE_LANGCHAIN:
        raise HTTPException(status_code=501, detail="推荐接口需要启用 LangChain (USE_LANGCHAIN=true)")

    session_id = req.session_id or str(uuid.uuid4())
    agent_instance = get_agent()

    # 检查是否支持结构化输出
    if not hasattr(agent_instance, "chat_structured"):
        raise HTTPException(status_code=501, detail="Agent 不支持结构化输出")

    try:
        result = await agent_instance.chat_structured(
            message=req.message,
            session_id=session_id,
            user_context=req.user_context,
        )
        return {
            "session_id": session_id,
            "recommendations": result.recommendations,
            "summary": result.summary,
        }
    except Exception as e:
        logger.error(f"推荐失败: {e}")
        raise HTTPException(status_code=500, detail=f"推荐失败: {type(e).__name__}")


@app.get("/session/{session_id}/export")
async def export_session(session_id: str):
    """导出对话记录为 Markdown"""
    if not session_store.exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    s = session_store.get_or_create(session_id)

    lines = [
        f"# 张雪峰 AI 咨询记录",
        f"",
        f"**会话 ID**: `{session_id}`",
        f"**时间**: {s['created_at']}",
        f"",
        f"---",
        f"",
    ]

    role_map = {"user": "用户", "assistant": "张雪峰 AI"}
    for msg in s["history"]:
        role = role_map.get(msg["role"], msg["role"])
        content = msg.get("content", "")
        if content:
            lines.append(f"**{role}**: {content}")
            lines.append("")

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=chat-{session_id[:8]}.md"},
    )


# ============== 反馈 API ==============

class FeedbackRequest(BaseModel):
    session_id: str
    message_index: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


@app.post("/api/v1/feedback")
async def submit_feedback(req: FeedbackRequest):
    """提交用户反馈"""
    from backend.models.feedback import Feedback
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        fb = Feedback(
            session_id=req.session_id,
            message_index=req.message_index,
            rating=req.rating,
            comment=req.comment,
        )
        db.add(fb)
        db.commit()
        return {"status": "ok", "id": fb.id}
    finally:
        db.close()


@app.get("/api/v1/feedback/stats")
async def feedback_stats():
    """反馈统计"""
    from backend.models.feedback import Feedback
    from backend.database import SessionLocal
    from sqlalchemy import func
    db = SessionLocal()
    try:
        total = db.query(func.count(Feedback.id)).scalar()
        avg_rating = db.query(func.avg(Feedback.rating)).scalar()
        distribution = (
            db.query(Feedback.rating, func.count(Feedback.id))
            .group_by(Feedback.rating)
            .all()
        )
        return {
            "total": total,
            "avg_rating": round(float(avg_rating), 2) if avg_rating else 0,
            "distribution": {str(r): c for r, c in distribution},
        }
    finally:
        db.close()


@app.get("/tools")
async def list_tools():
    """返回所有已注册工具的定义"""
    from backend.tools.definitions import TOOLS
    return {"tools": TOOLS}


# ============== Run ==============
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
