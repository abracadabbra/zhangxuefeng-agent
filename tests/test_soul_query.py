"""灵魂追问引擎测试"""
import pytest
from backend.soul_query import SoulQueryEngine, QueryState, MAX_QUERY_ROUNDS
from backend.user_profile import UserProfile


@pytest.fixture
def engine():
    return SoulQueryEngine()


@pytest.fixture
def empty_profile():
    return UserProfile()


@pytest.fixture
def full_profile():
    return UserProfile(
        score=650,
        province="河南",
        subject="理科",
        family_background="工薪阶层",
    )


class TestMaxQueryRounds:
    def test_max_rounds_is_5(self):
        assert MAX_QUERY_ROUNDS == 5


class TestRequiredFields:
    def test_all_4_required_fields_can_be_asked(self, engine, empty_profile):
        """4 个必问字段全部能被问到"""
        state = QueryState()
        asked = []

        for _ in range(4):
            q = engine.get_next_question(empty_profile, state)
            assert q is not None, f"Expected question but got None at round {state.round_count}"
            asked.append(q)

        assert state.round_count == 4
        assert len(state.asked_fields) == 4

    def test_required_fields_order(self, engine, empty_profile):
        """必问字段按顺序提问：score → province → subject → family_background"""
        state = QueryState()
        expected_order = ["score", "province", "subject", "family_background"]

        for field_name in expected_order:
            engine.get_next_question(empty_profile, state)

        assert state.asked_fields == expected_order


class TestOptionalFields:
    def test_optional_field_asked_after_required(self, engine, empty_profile):
        """必问字段问完后，可选问 1 个选问字段"""
        state = QueryState()

        # 问完 4 个必问字段
        for _ in range(4):
            engine.get_next_question(empty_profile, state)

        # 第 5 轮应该问选问字段
        q = engine.get_next_question(empty_profile, state)
        assert q is not None
        assert state.round_count == 5

    def test_optional_field_not_asked_when_round_limit_reached(self, engine, empty_profile):
        """达到 MAX_QUERY_ROUNDS 后不再追问"""
        state = QueryState()

        for _ in range(MAX_QUERY_ROUNDS):
            engine.get_next_question(empty_profile, state)

        q = engine.get_next_question(empty_profile, state)
        assert q is None

    def test_optional_field_asked_when_profile_complete(self, engine, full_profile):
        """必问字段全部填写后，仍可追问选问字段"""
        state = QueryState()
        q = engine.get_next_question(full_profile, state)
        # 必问字段已全，会追问选问字段
        assert q is not None
        assert state.round_count == 1


class TestSkipHandling:
    def test_handle_skip_records_field(self, engine):
        state = QueryState()
        engine.handle_skip(state, "target_city")
        assert "target_city" in state.skipped_fields

    def test_skip_default_values(self, engine):
        assert engine.get_skip_default("target_city") == "不限"
        assert engine.get_skip_default("risk_tolerance") == "稳健"
        assert engine.get_skip_default("career_goal") == "未确定"


class TestQueryComplete:
    def test_complete_when_all_required_filled(self, engine, full_profile):
        assert engine.is_query_complete(full_profile) is True

    def test_incomplete_when_missing_required(self, engine, empty_profile):
        assert engine.is_query_complete(empty_profile) is False
