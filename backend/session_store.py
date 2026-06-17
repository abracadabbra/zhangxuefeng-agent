"""聊天会话持久化存储 — SQLite + SQLAlchemy"""

import json
import logging
from typing import Any, cast

from backend.database import SessionLocal
from backend.models.chat import ChatMessage, ChatSession
from backend.soul_query import QueryState
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)
RECOMMENDATION_REPORT_ROLE = "recommendation_report"
RECOMMENDATION_FAVORITES_ROLE = "recommendation_favorites"
INTERNAL_MESSAGE_ROLES = (RECOMMENDATION_REPORT_ROLE, RECOMMENDATION_FAVORITES_ROLE)


def _unique_string_list(items: list[str]) -> list[str]:
    """去重并保序，避免会话元数据无限膨胀。"""
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


class SessionStore:
    """替代内存 sessions dict，持久化到 SQLite"""

    def get_or_create(self, session_id: str, user_context: dict | None = None) -> dict:
        """获取已有会话或创建新会话，返回与原 sessions[session_id] 相同结构的 dict"""
        db = SessionLocal()
        try:
            session = cast(
                Any,
                db.query(ChatSession).filter(ChatSession.session_id == session_id).first(),
            )
            if session is None:
                now = utc_now()
                ctx = json.dumps(user_context or {}, ensure_ascii=False)
                session = ChatSession(
                    session_id=session_id,
                    created_at=now,
                    user_context=ctx,
                    query_state=json.dumps(
                        {"round_count": 0, "asked_fields": [], "skipped_fields": []}
                    ),
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                logger.info(f"Created new session: {session_id}")

            # 反序列化历史消息
            history = []
            recommendation_report: dict[str, Any] = {}
            messages = cast(
                list[Any],
                (
                    db.query(ChatMessage)
                    .filter(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.id)
                    .all()
                ),
            )
            for msg in messages:
                if msg.role == RECOMMENDATION_REPORT_ROLE:
                    try:
                        recommendation_report = json.loads(msg.content or "{}")
                    except json.JSONDecodeError:
                        logger.warning("Invalid recommendation report payload: %s", session_id)
                    continue
                if msg.role == RECOMMENDATION_FAVORITES_ROLE:
                    continue
                entry = {"role": msg.role, "content": msg.content}
                if msg.tool_call_id:
                    entry["tool_call_id"] = msg.tool_call_id
                history.append(entry)

            # 反序列化 query_state
            qs_data = json.loads(session.query_state) if session.query_state else {}
            query_state = QueryState(
                round_count=qs_data.get("round_count", 0),
                asked_fields=qs_data.get("asked_fields", []),
                skipped_fields=qs_data.get("skipped_fields", []),
            )

            # 反序列化 user_context
            ctx_data = json.loads(session.user_context) if session.user_context else {}
            if user_context:
                ctx_data.update(user_context)

            return {
                "created_at": session.created_at.isoformat()
                if session.created_at
                else utc_now().isoformat(),
                "history": history,
                "message_count": len(history),
                "user_context": ctx_data,
                "query_state": query_state,
                "recommendations": recommendation_report.get("recommendations", []),
                "summary": recommendation_report.get("summary", ""),
                "gradient_summary": recommendation_report.get("gradient_summary", {}),
            }
        finally:
            db.close()

    def add_message(
        self, session_id: str, role: str, content: str, tool_call_id: str | None = None
    ) -> None:
        """追加一条消息到会话（自动创建 session 如果不存在）"""
        db = SessionLocal()
        try:
            # 确保 session 存在
            session = cast(
                Any,
                db.query(ChatSession).filter(ChatSession.session_id == session_id).first(),
            )
            if session is None:
                session = ChatSession(session_id=session_id, created_at=utc_now())
                db.add(session)
                db.flush()

            msg = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                tool_call_id=tool_call_id,
            )
            db.add(msg)
            db.commit()
        finally:
            db.close()

    def update_context(self, session_id: str, context: dict) -> None:
        """更新会话的 user_context"""
        db = SessionLocal()
        try:
            session = cast(
                Any,
                db.query(ChatSession).filter(ChatSession.session_id == session_id).first(),
            )
            if session:
                session.user_context = json.dumps(context, ensure_ascii=False)
                db.commit()
        finally:
            db.close()

    def update_query_state(self, session_id: str, query_state: QueryState) -> None:
        """更新会话的 query_state"""
        db = SessionLocal()
        try:
            session = cast(
                Any,
                db.query(ChatSession).filter(ChatSession.session_id == session_id).first(),
            )
            if session:
                session.query_state = json.dumps(
                    {
                        "round_count": query_state.round_count,
                        "asked_fields": query_state.asked_fields,
                        "skipped_fields": query_state.skipped_fields,
                    },
                    ensure_ascii=False,
                )
                db.commit()
        finally:
            db.close()

    def save_recommendation_report(
        self,
        session_id: str,
        recommendations: list[dict[str, Any]],
        summary: str,
        gradient_summary: dict[str, Any] | None = None,
    ) -> None:
        """保存最近一次结构化推荐结果，供会话导出使用。"""
        payload = json.dumps(
            {
                "recommendations": recommendations,
                "summary": summary,
                "gradient_summary": gradient_summary or {},
            },
            ensure_ascii=False,
        )
        db = SessionLocal()
        try:
            session = cast(
                Any,
                db.query(ChatSession).filter(ChatSession.session_id == session_id).first(),
            )
            if session is None:
                session = ChatSession(session_id=session_id, created_at=utc_now())
                db.add(session)
                db.flush()

            existing = cast(
                Any,
                (
                    db.query(ChatMessage)
                    .filter(
                        ChatMessage.session_id == session_id,
                        ChatMessage.role == RECOMMENDATION_REPORT_ROLE,
                    )
                    .first()
                ),
            )
            if existing:
                existing.content = payload
            else:
                db.add(
                    ChatMessage(
                        session_id=session_id,
                        role=RECOMMENDATION_REPORT_ROLE,
                        content=payload,
                    )
                )
            db.commit()
        finally:
            db.close()

    def get_recommendation_favorites(self, session_id: str) -> list[str]:
        """读取会话收藏的推荐 key 列表。"""
        db = SessionLocal()
        try:
            existing = cast(
                Any,
                (
                    db.query(ChatMessage)
                    .filter(
                        ChatMessage.session_id == session_id,
                        ChatMessage.role == RECOMMENDATION_FAVORITES_ROLE,
                    )
                    .first()
                ),
            )
            if not existing:
                return []
            try:
                payload = json.loads(existing.content or "{}")
            except json.JSONDecodeError:
                logger.warning("Invalid recommendation favorites payload: %s", session_id)
                return []
            favorite_keys = payload.get("favorite_keys", [])
            if not isinstance(favorite_keys, list):
                return []
            return _unique_string_list([item for item in favorite_keys if isinstance(item, str)])
        finally:
            db.close()

    def save_recommendation_favorites(self, session_id: str, favorite_keys: list[str]) -> None:
        """覆盖保存会话收藏的推荐 key 列表。"""
        payload = json.dumps(
            {"favorite_keys": _unique_string_list(favorite_keys)},
            ensure_ascii=False,
        )
        db = SessionLocal()
        try:
            session = cast(
                Any,
                db.query(ChatSession).filter(ChatSession.session_id == session_id).first(),
            )
            if session is None:
                session = ChatSession(session_id=session_id, created_at=utc_now())
                db.add(session)
                db.flush()

            existing = cast(
                Any,
                (
                    db.query(ChatMessage)
                    .filter(
                        ChatMessage.session_id == session_id,
                        ChatMessage.role == RECOMMENDATION_FAVORITES_ROLE,
                    )
                    .first()
                ),
            )
            if existing:
                existing.content = payload
            else:
                db.add(
                    ChatMessage(
                        session_id=session_id,
                        role=RECOMMENDATION_FAVORITES_ROLE,
                        content=payload,
                    )
                )
            db.commit()
        finally:
            db.close()

    def delete(self, session_id: str) -> None:
        """删除会话及其所有消息"""
        db = SessionLocal()
        try:
            session = cast(
                Any,
                db.query(ChatSession).filter(ChatSession.session_id == session_id).first(),
            )
            if session:
                db.delete(session)
                db.commit()
                logger.info(f"Deleted session: {session_id}")
        finally:
            db.close()

    def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        db = SessionLocal()
        try:
            return (
                db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
                is not None
            )
        finally:
            db.close()

    def list_recent(self, limit: int = 20) -> list[dict]:
        """列出最近的会话（按创建时间倒序）"""
        db = SessionLocal()
        try:
            sessions = cast(
                list[Any],
                (db.query(ChatSession).order_by(ChatSession.created_at.desc()).limit(limit).all()),
            )
            result = []
            for s in sessions:
                msg_count = (
                    db.query(ChatMessage)
                    .filter(
                        ChatMessage.session_id == s.session_id,
                        ChatMessage.role.not_in(INTERNAL_MESSAGE_ROLES),
                    )
                    .count()
                )
                result.append(
                    {
                        "session_id": s.session_id,
                        "created_at": s.created_at.isoformat() if s.created_at else "",
                        "message_count": msg_count,
                        "user_context": json.loads(s.user_context) if s.user_context else {},
                    }
                )
            return result
        finally:
            db.close()
