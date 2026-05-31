"""
张雪峰 AI 咨询 Agent -- FastAPI 后端

提供对话 API、SSE 流式输出、Function Calling 支持、灵魂追问引擎
"""
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database import init_db
from backend.logging_config import request_filter, setup_logging
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.routers import (
    majors_router,
    plans_router,
    schools_router,
    scores_router,
    subject_rankings_router,
)
from backend.routes.chat import router as chat_router
from backend.routes.profile import router as profile_router
from backend.routes.session import router as session_router
from backend.routes.system import router as system_router
from backend.docs import setup_docs
from backend.security import SecurityMiddleware

settings = get_settings()
setup_logging(level=settings.log_level, fmt=settings.log_format)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("张雪峰 Agent 启动 | model=%s", settings.effective_model)

    init_db()
    logger.info("数据库初始化完成")

    if settings.use_langchain:
        from backend.agent.langsmith_config import setup_langsmith

        setup_langsmith()

    yield
    logger.info("张雪峰 Agent 关闭")


app = FastAPI(
    title="张雪峰 AI 咨询 Agent",
    description="高考/考研/职业规划咨询，基于张雪峰认知操作系统",
    version="0.2.0",
    lifespan=lifespan,
)

# ============== API 文档 ==============
setup_docs(app)


# ============== Middleware ==============
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """注入 request_id / user_id 到日志上下文。"""
    request_filter.request_id = request.headers.get("X-Request-ID", "-")
    request_filter.user_id = request.headers.get("X-User-ID", "-")
    response = await call_next(request)
    return response


app.add_middleware(SecurityMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_origins != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== Routers ==============
app.include_router(system_router)
app.include_router(chat_router)
app.include_router(session_router)
app.include_router(profile_router)

# 数据查询路由（原有 routers/ 目录）
app.include_router(schools_router)
app.include_router(majors_router)
app.include_router(scores_router)
app.include_router(plans_router)
app.include_router(subject_rankings_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.port)
