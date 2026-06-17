"""
API 路由包
"""

from backend.routers.majors import router as majors_router
from backend.routers.plans import router as plans_router
from backend.routers.schools import router as schools_router
from backend.routers.scores import router as scores_router
from backend.routers.subject_rankings import router as subject_rankings_router

__all__ = [
    "majors_router",
    "plans_router",
    "schools_router",
    "scores_router",
    "subject_rankings_router",
]
