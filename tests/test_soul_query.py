"""
灵魂追问引擎 + 用户画像 单元测试
"""
import pytest
from app.services.soul_query import SoulQueryEngine, QueryState, MAX_QUERY_ROUNDS
from app.models.user_profile import UserProfile


@pytest.fixture
def engine():
    return SoulQueryEngine()


@pytest.fixture
def empty_profile():
    return UserProfile()


@pytest.fixture
def full_profile():
    return UserProfile(
        score=600,
        province="河南",
        subject="理科",
        family_background="工薪阶层",
    )


# ========== 追问顺序正确性 ==========

class TestQueryOrder:
    """测试追问顺序：score -> province -> subject -> family_background"""

    def test_first_question_is_score(self, engine, empty_profile):
        state = QueryState()
        q = engine.get_next_question(empty_profile, state)
        assert q is not None
        assert "分数" in q or "考了多少分" in q

    def test_second_question_is_province(self, engine, empty_profile):
        state = QueryState()
        engine.get_next_question(empty_profile, state)  # score
        q = engine.get_next_question(empty_profile, state)
        assert q is not None
        assert "省" in q

    def test_third_question_is_subject_or_combined(self, engine, empty_profile):
        state = QueryState()
        engine.get_next_question(empty_profile, state)  # score or combined
        engine.get_next_question(empty_profile, state)  # province or combined
        q = engine.get_next_question(empty_profile, state)
        assert q is not None
        # 第三轮可能是 subject 或 family_background（取决于组合追问）
        assert any(kw in q for kw in ["文科", "理科", "文理", "选科", "家里", "家庭", "条件"])

    def test_fourth_question_stops_at_max_rounds(self, engine, empty_profile):
        """追问最多 3 轮，第四轮返回 None"""
        state = QueryState()
        engine.get_next_question(empty_profile, state)  # score (round 1)
        engine.get_next_question(empty_profile, state)  # province (round 2)
        engine.get_next_question(empty_profile, state)  # subject (round 3)
        q = engine.get_next_question(empty_profile, state)  # 应该返回 None
        assert q is None  # 已达到最大轮次


# ========== 已回答字段不再追问 ==========

class TestNoRepeatQuestions:
    """已填写的字段不再追问"""

    def test_score_filled_skips_score(self, engine):
        profile = UserProfile(score=600)
        state = QueryState()
        q = engine.get_next_question(profile, state)
        assert q is not None
        # 第一个问题应该是 province，不是 score
        assert "分数" not in q and "考了多少分" not in q
        assert "省" in q

    def test_all_required_filled_no_question(self, engine, full_profile):
        state = QueryState()
        q = engine.get_next_question(full_profile, state)
        # 必问字段全填了，应该返回 None 或选问字段
        if q is not None:
            assert "分数" not in q
            assert "省" not in q
            assert "文科" not in q and "理科" not in q
            assert "家里" not in q and "家庭" not in q

    def test_is_query_complete_with_all_required(self, engine, full_profile):
        assert engine.is_query_complete(full_profile) is True

    def test_is_query_complete_with_missing(self, engine, empty_profile):
        assert engine.is_query_complete(empty_profile) is False


# ========== 跳过处理逻辑 ==========

class TestSkipHandling:
    """用户跳过问题时的处理"""

    def test_skip_records_field(self, engine):
        state = QueryState()
        engine.handle_skip(state, "target_city")
        assert "target_city" in state.skipped_fields

    def test_skipped_optional_not_asked_again(self, engine):
        """跳过的选问字段不应再被问"""
        profile = UserProfile(
            score=600,
            province="河南",
            subject="理科",
            family_background="工薪阶层",
        )
        state = QueryState()
        engine.handle_skip(state, "target_city")

        q = engine.get_next_question(profile, state)
        if q is not None:
            assert "城市" not in q

    def test_skip_default_values(self, engine):
        assert engine.get_skip_default("target_city") == "不限"
        assert engine.get_skip_default("risk_tolerance") == "稳健"
        assert engine.get_skip_default("career_goal") == "未确定"
        assert engine.get_skip_default("score") is None  # 必问字段无默认值


# ========== 追问轮次限制 ==========

class TestRoundLimit:
    """最多 3 轮追问"""

    def test_max_rounds_stops_questioning(self, engine, empty_profile):
        state = QueryState()
        questions_asked = 0
        while True:
            q = engine.get_next_question(empty_profile, state)
            if q is None:
                break
            questions_asked += 1
        assert questions_asked <= MAX_QUERY_ROUNDS

    def test_round_count_increments(self, engine, empty_profile):
        state = QueryState()
        engine.get_next_question(empty_profile, state)
        assert state.round_count == 1
        engine.get_next_question(empty_profile, state)
        assert state.round_count == 2


# ========== 用户画像模型 ==========

class TestUserProfile:
    """画像模型测试"""

    def test_empty_profile_not_complete(self):
        p = UserProfile()
        assert p.is_required_complete() is False

    def test_full_profile_complete(self, full_profile):
        assert full_profile.is_required_complete() is True

    def test_missing_fields_list(self):
        p = UserProfile(score=500)
        missing = p.missing_required_fields()
        assert "province" in missing
        assert "subject" in missing
        assert "family_background" in missing
        assert "score" not in missing

    def test_to_context_dict(self, full_profile):
        ctx = full_profile.to_context_dict()
        assert ctx["分数"] == 600
        assert ctx["省份"] == "河南"
        assert ctx["科类"] == "理科"
        assert ctx["家庭条件"] == "工薪阶层"
