"""会话持久化存储测试"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.session_store import SessionStore
from backend.soul_query import QueryState


@pytest.fixture
def store(tmp_path, monkeypatch):
    """每个测试用独立的 SQLite 数据库"""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 导入模型以注册到 Base.metadata
    from backend.models import chat  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # 替换 session_store 模块中引用的 SessionLocal
    import backend.session_store as store_module
    monkeypatch.setattr(store_module, "SessionLocal", TestSession)

    return SessionStore()


class TestGetOrCreate:
    def test_creates_new_session(self, store):
        session = store.get_or_create("test-001")
        assert session["message_count"] == 0
        assert session["history"] == []
        assert isinstance(session["query_state"], QueryState)

    def test_returns_existing_session(self, store):
        store.add_message("test-002", "user", "hello")
        store.add_message("test-002", "assistant", "hi")
        session = store.get_or_create("test-002")
        assert session["message_count"] == 2
        assert session["history"][0]["content"] == "hello"

    def test_user_context_preserved(self, store):
        session = store.get_or_create("test-003", user_context={"分数": "650"})
        assert session["user_context"]["分数"] == "650"


class TestAddMessage:
    def test_add_and_retrieve(self, store):
        store.add_message("test-010", "user", "你好")
        store.add_message("test-010", "assistant", "你好！有什么可以帮你的？")
        session = store.get_or_create("test-010")
        assert len(session["history"]) == 2
        assert session["history"][0]["role"] == "user"
        assert session["history"][1]["role"] == "assistant"


class TestUpdateContext:
    def test_update_context(self, store):
        store.get_or_create("test-020")
        store.update_context("test-020", {"分数": "700"})
        session = store.get_or_create("test-020")
        assert session["user_context"]["分数"] == "700"


class TestUpdateQueryState:
    def test_update_query_state(self, store):
        store.get_or_create("test-030")
        qs = QueryState(round_count=2, asked_fields=["score", "province"])
        store.update_query_state("test-030", qs)
        session = store.get_or_create("test-030")
        restored_qs = session["query_state"]
        assert restored_qs.round_count == 2
        assert restored_qs.asked_fields == ["score", "province"]


class TestDelete:
    def test_delete_session(self, store):
        store.add_message("test-040", "user", "msg")
        assert store.exists("test-040") is True
        store.delete("test-040")
        assert store.exists("test-040") is False

    def test_delete_nonexistent_no_error(self, store):
        store.delete("nonexistent")  # should not raise


class TestExists:
    def test_exists_returns_true(self, store):
        store.get_or_create("test-050")
        assert store.exists("test-050") is True

    def test_exists_returns_false(self, store):
        assert store.exists("nonexistent") is False
