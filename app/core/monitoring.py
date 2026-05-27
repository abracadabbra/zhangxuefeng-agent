"""监控模块 — Sentry 错误追踪 + 结构化日志"""

import logging
import sys

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """配置结构化日志（JSON 格式）"""
    settings = get_settings()
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # JSON 格式日志
    formatter = logging.Formatter(
        fmt='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)


def setup_sentry() -> None:
    """初始化 Sentry 错误追踪"""
    settings = get_settings()

    if not settings.SENTRY_DSN:
        logger.info("SENTRY_DSN 未配置，跳过 Sentry 初始化")
        return

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment="production" if not settings.DEBUG else "development",
        release=settings.APP_VERSION,
        integrations=[sentry_logging],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
    logger.info("Sentry 已初始化 | env=%s", "production" if not settings.DEBUG else "development")
