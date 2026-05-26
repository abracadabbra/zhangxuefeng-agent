"""
张雪峰 AI 咨询 Agent — FastAPI 后端

提供对话 API、上下文管理、Agent 路由
"""
import os
import json
import uuid
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

# ============== Config ==============
SKILL_PATH = os.getenv("SKILL_PATH", "/root/zhangxuefeng-agent/SKILL.md")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL", "gpt-4o-mini")

# ============== Pydantic Models ==============
class Message(BaseModel):
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="会话ID，空则创建新会话")
    message: str = Field(..., description="用户消息")
    user_context: Optional[dict] = Field(default=None, description="用户背景信息: 省份/分数/文理科/家庭条件等")

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    model: str
    usage: Optional[dict] = None

class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    message_count: int
    user_context: Optional[dict]

# ============== In-Memory Store ==============
sessions: dict[str, dict] = {}

def load_skill() -> str:
    """加载 SKILL.md 内容作为 system prompt"""
    try:
        with open(SKILL_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

# ============== FastAPI App ==============
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[{datetime.now()}] 张雪峰 Agent 启动 | Model: {MODEL}")
    yield
    print(f"[{datetime.now()}] 张雪峰 Agent 关闭")

app = FastAPI(
    title="张雪峰 AI 咨询 Agent",
    description="高考/考研/职业规划咨询，基于张雪峰认知操作系统",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== Helper ==============
def build_messages(skill_content: str, history: list[dict], user_message: str, user_context: Optional[dict]) -> list[dict]:
    """构建发送给 LLM 的消息列表"""
    system_content = skill_content

    # 注入用户背景信息
    if user_context:
        ctx_parts = []
        分数 = user_context.get("分数")
        if 分数:
            ctx_parts.append(f"- 考生分数：{分数}分")
        省份 = user_context.get("省份")
        if 省份:
            ctx_parts.append(f"- 所在省份：{省份}")
        科类 = user_context.get("科类")
        if 科类:
            ctx_parts.append(f"- 文理科：{科类}")
        家庭条件 = user_context.get("家庭条件")
        if 家庭条件:
            ctx_parts.append(f"- 家庭条件：{家庭条件}")
        预算 = user_context.get("预算")
        if 预算:
            ctx_parts.append(f"- 预算范围：{预算}")

        if ctx_parts:
            system_content += "\n\n## 用户背景信息\n" + "\n".join(ctx_parts)

    messages = [{"role": "system", "content": system_content}]

    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})
    return messages

# ============== API Endpoints ==============
@app.get("/")
async def root():
    return {"status": "ok", "agent": "张雪峰 AI", "model": MODEL, "skill_loaded": bool(load_skill())}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """核心对话接口"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 获取或创建会话
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "history": [],
            "message_count": 0,
            "user_context": req.user_context or {}
        }

    session = sessions[session_id]

    # 更新上下文
    if req.user_context:
        session["user_context"].update(req.user_context)

    # 构建消息
    skill_content = load_skill()
    if not skill_content:
        raise HTTPException(status_code=500, detail="SKILL.md 未找到")

    messages = build_messages(skill_content, session["history"], req.message, session["user_context"])

    # 调用 LLM
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"LLM 调用失败: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM 调用异常: {str(e)}")

    reply = data["choices"][0]["message"]["content"]
    usage = data.get("usage")

    # 更新历史
    session["history"].append({"role": "user", "content": req.message})
    session["history"].append({"role": "assistant", "content": reply})
    session["message_count"] += 2

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        model=data.get("model", MODEL),
        usage=usage
    )

@app.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    s = sessions[session_id]
    return SessionInfo(
        session_id=session_id,
        created_at=s["created_at"],
        message_count=s["message_count"],
        user_context=s["user_context"]
    )

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "deleted", "session_id": session_id}

# ============== Run ==============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
