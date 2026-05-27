"""健康检查 + 监控指标路由"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.metrics import metrics
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """健康检查接口"""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        model=settings.MODEL,
    )


@router.get("/metrics")
async def get_metrics():
    """监控指标接口（供 Grafana / Prometheus 抓取）"""
    return metrics.get_summary()
