"""Quality gate tests for real-data candidates."""

from backend.data_pipeline.quality import (
    CandidateReviewMetadata,
    CandidateSource,
    CanonicalCandidate,
    QualityGateConfig,
    run_quality_gate,
)


def admission_candidate(**overrides) -> CanonicalCandidate:
    payload = {
        "entity_type": "admission_score",
        "natural_key": {
            "school_name": "Example University",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
        },
        "values": {
            "min_score": 620,
            "avg_score": None,
            "max_score": None,
            "min_rank": 12000,
            "plan_count": None,
        },
        "source": CandidateSource(
            snapshot_id="sd_scores_2025_001",
            source_record_ref="page=12,row=8",
            confidence=0.95,
        ),
    }
    payload.update(overrides)
    return CanonicalCandidate.model_validate(payload)


def enrollment_candidate(**overrides) -> CanonicalCandidate:
    payload = {
        "entity_type": "enrollment_plan",
        "natural_key": {
            "school_name": "Example University",
            "major_name": "Computer Science and Technology",
            "province": "山东",
            "year": 2025,
        },
        "values": {
            "plan_count": 20,
            "subject_requirement": "物理+化学",
            "batch": "本科批",
            "duration": 4,
            "tuition": 6000,
        },
        "source": CandidateSource(
            snapshot_id="sd_plans_2025_001",
            source_record_ref="sheet=plans,row=42",
            confidence=0.95,
        ),
    }
    payload.update(overrides)
    return CanonicalCandidate.model_validate(payload)


def reviewed_source() -> CandidateSource:
    return CandidateSource(
        snapshot_id="sd_scores_2025_001",
        source_record_ref="page=12,row=8",
        confidence=0.95,
        review=CandidateReviewMetadata(
            extracted_by="extractor-a",
            reviewed_by="reviewer-a",
            reviewed_at="2026-06-07",
            notes="Matched official row.",
        ),
    )


def test_quality_gate_passes_valid_candidates_and_reports_coverage():
    report = run_quality_gate(
        [admission_candidate(), enrollment_candidate()],
        QualityGateConfig(expected_provinces=("山东",), expected_years=(2025,)),
    )

    assert report.passed is True
    assert report.errors == []
    assert report.coverage["total"] == 2
    assert report.coverage["by_entity_type"] == {
        "admission_score": 1,
        "enrollment_plan": 1,
    }
    assert report.coverage["missing_expected_provinces"] == []
    assert report.coverage["missing_expected_years"] == []


def test_quality_gate_blocks_missing_required_fields():
    candidate = admission_candidate(
        natural_key={
            "school_name": "Example University",
            "province": "山东",
            "year": 2025,
            "batch": "",
            "subject_type": "综合",
        }
    )

    report = run_quality_gate([candidate])

    assert report.passed is False
    assert [issue.code for issue in report.errors] == ["missing_required_field"]
    assert report.errors[0].field == "batch"


def test_quality_gate_blocks_out_of_range_values():
    candidate = admission_candidate(values={"min_score": 900, "min_rank": 0})

    report = run_quality_gate([candidate])

    assert report.passed is False
    assert [issue.field for issue in report.errors] == ["min_score", "min_rank"]


def test_quality_gate_blocks_conflicting_duplicates():
    first = admission_candidate()
    second = admission_candidate(values={"min_score": 630})

    report = run_quality_gate([first, second])

    assert report.passed is False
    assert report.errors[0].code == "conflicting_duplicate"
    assert report.errors[0].candidate_index == 1


def test_quality_gate_warns_for_stale_and_low_confidence_data():
    candidate = admission_candidate(
        natural_key={
            "school_name": "Example University",
            "major_name": None,
            "province": "山东",
            "year": 2022,
            "batch": "本科批",
            "subject_type": "综合",
        },
        source=CandidateSource(
            snapshot_id="sd_scores_2022_001",
            source_record_ref="page=3,row=1",
            confidence=0.7,
        ),
    )

    report = run_quality_gate([candidate], QualityGateConfig(current_year=2026))

    assert report.passed is True
    assert [issue.code for issue in report.warnings] == ["stale_data", "low_confidence"]


def test_quality_gate_reports_missing_expected_coverage():
    report = run_quality_gate(
        [admission_candidate()],
        QualityGateConfig(expected_provinces=("山东", "河南"), expected_years=(2024, 2025)),
    )

    assert report.coverage["missing_expected_provinces"] == ["河南"]
    assert report.coverage["missing_expected_years"] == [2024]


def test_quality_gate_model_validates_config_payloads():
    config = QualityGateConfig.model_validate(
        {
            "current_year": 2026,
            "expected_provinces": ["山东"],
            "expected_years": [2025],
            "require_review_metadata": True,
        }
    )

    assert config.expected_provinces == ("山东",)
    assert config.expected_years == (2025,)
    assert config.require_review_metadata is True


def test_quality_gate_defaults_to_allow_missing_review_metadata():
    report = run_quality_gate([admission_candidate()])

    assert report.passed is True
    assert [issue.code for issue in report.errors] == []


def test_quality_gate_blocks_missing_review_metadata_when_required():
    report = run_quality_gate(
        [admission_candidate()],
        QualityGateConfig(require_review_metadata=True),
    )

    assert report.passed is False
    assert [issue.field for issue in report.errors] == [
        "source.review.reviewed_by",
        "source.review.reviewed_at",
    ]
    assert {issue.code for issue in report.errors} == {"missing_review_metadata"}


def test_quality_gate_accepts_review_metadata_when_required():
    report = run_quality_gate(
        [admission_candidate(source=reviewed_source())],
        QualityGateConfig(require_review_metadata=True),
    )

    assert report.passed is True
    assert report.errors == []
