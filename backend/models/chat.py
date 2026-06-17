"""聊天会话和消息的 ORM 模型"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.time_utils import utc_now


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=utc_now)
    user_context = Column(Text, default="{}")  # JSON string
    query_state = Column(Text, default="{}")  # JSON string

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), nullable=False)
    role = Column(String, nullable=False)  # user / assistant / tool
    content = Column(Text)
    tool_call_id = Column(String)
    created_at = Column(DateTime, default=utc_now)

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (Index("idx_messages_session", "session_id"),)
