"""
API 路由包
"""
from backend.routers.schools import router as schools_router
from backend.routers.majors import router as majors_router
from backend.routers.scores import router as scores_router
from backend.routers.plans import router as plans_router
from backend.routers.subject_rankings import router as subject_rankings_router

__all__ = ["schools_router", "majors_router", "scores_router", "plans_router", "subject_rankings_router"]
