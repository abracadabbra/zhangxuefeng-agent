"""聊天会话持久化存储 — SQLite + SQLAlchemy"""
import json
import logging
from datetime import datetime

from backend.database import SessionLocal
from backend.models.chat import ChatSession, ChatMessage
from backend.soul_query import QueryState

logger = logging.getLogger(__name__)


class SessionStore:
    """替代内存 sessions dict，持久化到 SQLite"""

    def get_or_create(self, session_id: str, user_context: dict | None = None) -> dict:
        """获取已有会话或创建新会话，返回与原 sessions[session_id] 相同结构的 dict"""
        db = SessionLocal()
        try:
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if session is None:
                now = datetime.utcnow()
                ctx = json.dumps(user_context or {}, ensure_ascii=False)
                session = ChatSession(
                    session_id=session_id,
                    created_at=now,
                    user_context=ctx,
                    query_state=json.dumps({"round_count": 0, "asked_fields": [], "skipped_fields": []}),
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                logger.info(f"Created new session: {session_id}")

            # 反序列化历史消息
            history = []
            messages = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.id)
                .all()
            )
            for msg in messages:
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
                "created_at": session.created_at.isoformat() if session.created_at else datetime.utcnow().isoformat(),
                "history": history,
                "message_count": len(history),
                "user_context": ctx_data,
                "query_state": query_state,
            }
        finally:
            db.close()

    def add_message(self, session_id: str, role: str, content: str, tool_call_id: str | None = None) -> None:
        """追加一条消息到会话（自动创建 session 如果不存在）"""
        db = SessionLocal()
        try:
            # 确保 session 存在
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if session is None:
                session = ChatSession(session_id=session_id, created_at=datetime.utcnow())
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
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if session:
                session.user_context = json.dumps(context, ensure_ascii=False)
                db.commit()
        finally:
            db.close()

    def update_query_state(self, session_id: str, query_state: QueryState) -> None:
        """更新会话的 query_state"""
        db = SessionLocal()
        try:
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if session:
                session.query_state = json.dumps({
                    "round_count": query_state.round_count,
                    "asked_fields": query_state.asked_fields,
                    "skipped_fields": query_state.skipped_fields,
                }, ensure_ascii=False)
                db.commit()
        finally:
            db.close()

    def delete(self, session_id: str) -> None:
        """删除会话及其所有消息"""
        db = SessionLocal()
        try:
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
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
            return db.query(ChatSession).filter(ChatSession.session_id == session_id).first() is not None
        finally:
            db.close()

    def list_recent(self, limit: int = 20) -> list[dict]:
        """列出最近的会话（按创建时间倒序）"""
        db = SessionLocal()
        try:
            sessions = (
                db.query(ChatSession)
                .order_by(ChatSession.created_at.desc())
                .limit(limit)
                .all()
            )
            result = []
            for s in sessions:
                msg_count = db.query(ChatMessage).filter(ChatMessage.session_id == s.session_id).count()
                result.append({
                    "session_id": s.session_id,
                    "created_at": s.created_at.isoformat() if s.created_at else "",
                    "message_count": msg_count,
                    "user_context": json.loads(s.user_context) if s.user_context else {},
                })
            return result
        finally:
            db.close()
