"""用户反馈 ORM 模型"""

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.database import Base
from backend.time_utils import utc_now


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    message_index = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, default=utc_now)
