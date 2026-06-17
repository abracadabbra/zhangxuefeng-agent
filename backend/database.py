"""
数据库连接和会话管理

使用 SQLAlchemy + SQLite，支持 Alembic 迁移
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 数据库文件路径，默认放在 backend 目录下
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{os.path.join(os.path.dirname(__file__), 'zhangxuefeng.db')}"
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 多线程支持
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类"""

    pass


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表（仅用于开发/测试，生产用 Alembic）"""
    from backend.models import (  # noqa: F401
        admission_score,
        chat,
        enrollment_plan,
        feedback,
        major,
        school,
    )

    Base.metadata.create_all(bind=engine)
