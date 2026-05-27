"""FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI

from app.api import chat, feedback, health
from app.core.config import get_settings
from app.core.middleware import setup_middleware
from app.core.monitoring import setup_logging, setup_sentry

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "[%s] %s 启动 | Model: %s",
        datetime.now(),
        settings.APP_NAME,
        settings.MODEL,
    )
    yield
    logger.info("[%s] %s 关闭", datetime.now(), settings.APP_NAME)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="高考/考研/职业规划咨询，基于张雪峰认知操作系统",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    setup_sentry()
    setup_middleware(app)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(feedback.router)

    return app


app = create_app()
