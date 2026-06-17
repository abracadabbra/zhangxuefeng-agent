from backend.agent.structured_output import (
    MajorRecommendation,
    RecommendationResult,
    SchoolRecommendation,
    get_recommendation_instructions,
    parse_recommendation,
)


def test_school_recommendation_supports_explanation_fields():
    recommendation = SchoolRecommendation(
        school_name="北京邮电大学",
        reason="计算机和通信学科强。",
        admission_probability=0.62,
        match_score=8,
        strategy="稳",
        risk_points=["热门专业分数波动大"],
        alternatives=["南京邮电大学"],
    )

    assert recommendation.strategy == "稳"
    assert recommendation.risk_points == ["热门专业分数波动大"]
    assert recommendation.alternatives == ["南京邮电大学"]


def test_major_recommendation_keeps_backward_compatible_defaults():
    recommendation = MajorRecommendation(
        major_name="计算机科学与技术",
        category="工学",
        reason="就业面广。",
        employment_rate=0.9,
        avg_salary=18000,
    )

    assert recommendation.strategy is None
    assert recommendation.risk_points == []
    assert recommendation.alternatives == []


def test_recommendation_result_has_default_gradient_summary():
    result = RecommendationResult(recommendations=[], summary="建议冲稳保分层填报。")

    assert result.gradient_summary == {"冲": [], "稳": [], "保": []}


def test_parse_recommendation_fallback_preserves_summary_text():
    result = parse_recommendation("无法解析的普通文本")

    assert result.recommendations == []
    assert result.summary == "无法解析的普通文本"
    assert result.gradient_summary == {"冲": [], "稳": [], "保": []}


def test_recommendation_instructions_require_explanation_fields():
    instructions = get_recommendation_instructions()

    assert "每个推荐项都必须说明为什么适合" in instructions
    assert "risk_points" in instructions
    assert "alternatives" in instructions
    assert "gradient_summary" in instructions
    assert "format" in instructions.lower()
