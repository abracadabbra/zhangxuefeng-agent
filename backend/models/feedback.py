"""用户反馈 ORM 模型"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime
from backend.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    message_index = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
