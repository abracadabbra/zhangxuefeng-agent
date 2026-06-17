"""
画像相关端点：/profile/*
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.dependencies import session_store, soul_engine
from backend.security import validate_session_id
from backend.user_profile import (
    apply_profile_context,
    apply_profile_field,
    empty_profile,
    load_profile,
    update_profile,
)

router = APIRouter()


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
    question: str | None
    round_count: int
    is_complete: bool


@router.get("/profile/{session_id}", response_model=ProfileResponse)
async def get_profile(session_id: str):
    """获取用户画像"""
    validate_session_id(session_id)
    try:
        profile = await load_profile(session_id)
    except Exception:
        session = session_store.get_or_create(session_id)
        ctx = session.get("user_context", {})
        profile = apply_profile_context(empty_profile(), ctx) if ctx else empty_profile()

    return ProfileResponse(
        session_id=session_id,
        profile=profile.model_dump(),
        is_complete=profile.is_required_complete(),
        missing_fields=profile.missing_required_fields(),
    )


@router.put("/profile/{session_id}", response_model=ProfileResponse)
async def update_profile_endpoint(session_id: str, req: ProfileUpdateRequest):
    """更新用户画像字段"""
    validate_session_id(session_id)
    try:
        profile = await update_profile(session_id, req.field, req.value)
    except Exception:
        profile = empty_profile()
        profile = apply_profile_field(profile, req.field, req.value)

    return ProfileResponse(
        session_id=session_id,
        profile=profile.model_dump(),
        is_complete=profile.is_required_complete(),
        missing_fields=profile.missing_required_fields(),
    )


@router.get("/profile/{session_id}/next-question", response_model=NextQuestionResponse)
async def get_next_question(session_id: str):
    """获取下一个追问问题"""
    validate_session_id(session_id)
    try:
        profile = await load_profile(session_id)
    except Exception:
        session = session_store.get_or_create(session_id)
        ctx = session.get("user_context", {})
        profile = apply_profile_context(empty_profile(), ctx) if ctx else empty_profile()

    session = session_store.get_or_create(session_id)
    query_state = session["query_state"]

    question = soul_engine.get_next_question(profile, query_state)

    return NextQuestionResponse(
        session_id=session_id,
        question=question,
        round_count=query_state.round_count,
        is_complete=soul_engine.is_query_complete(profile),
    )
