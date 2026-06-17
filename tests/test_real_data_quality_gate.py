from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.real_data.contracts import (
    CanonicalAdmissionCandidate,
    build_citation_metadata,
    run_quality_gate,
)
from backend.real_data.source_registry import (
    SHANDONG_2025_REGULAR_BATCH_1_PAGE,
    SourcePage,
    build_snapshot,
    sha256_bytes,
)


def _snapshot():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    return build_snapshot(
        source_page=source,
        attachment=source.attachments[0],
        raw_file_sha256=sha256_bytes(b"pilot xls bytes"),
        captured_at=datetime(2026, 6, 9, 10, 0, tzinfo=UTC),
        operator="codex",
    )


def _candidate(**overrides):
    snapshot = _snapshot()
    data = {
        "province": "山东",
        "year": 2025,
        "school_name": "山东大学",
        "major_or_group_name": "计算机类",
        "batch": "普通类常规批第1次志愿",
        "subject_type": "普通类",
        "min_score": 620,
        "min_rank": 12000,
        "plan_count": 12,
        "source_batch_id": snapshot.source_batch_id,
        "snapshot_id": snapshot.snapshot_id,
        "raw_row_number": 2,
        "confidence": "high",
    }
    data.update(overrides)
    return CanonicalAdmissionCandidate.model_validate(data)


def test_candidate_requires_traceable_lineage_fields():
    with pytest.raises(ValidationError) as exc_info:
        CanonicalAdmissionCandidate.model_validate(
            {
                "province": "山东",
                "year": 2025,
                "school_name": "山东大学",
                "major_or_group_name": "计算机类",
                "batch": "普通类常规批第1次志愿",
                "subject_type": "普通类",
                "min_score": 620,
                "confidence": "high",
            }
        )

    error_text = str(exc_info.value)
    assert "source_batch_id" in error_text
    assert "snapshot_id" in error_text
    assert "raw_row_number" in error_text


def test_quality_gate_passes_clean_official_candidate():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )

    report = run_quality_gate(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        expected_schools=("山东大学",),
        expected_min_records=1,
    )

    assert report.status == "pass"
    assert report.record_count_passed == 1
    assert report.duplicate_conflicts == ()
    assert report.coverage_metrics.missing_schools == ()
    assert report.confidence_summary == {"high": 1, "medium": 0, "low": 0}


def test_quality_gate_blocks_duplicate_candidate_keys():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    first = _candidate(source_batch_id=snapshot.source_batch_id, snapshot_id=snapshot.snapshot_id)
    duplicate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
        raw_row_number=3,
    )

    report = run_quality_gate(candidates=[first, duplicate], source_page=source, snapshot=snapshot)

    assert report.status == "blocked"
    assert report.record_count_passed == 0
    assert report.duplicate_conflicts[0].code == "duplicate_canonical_key"


def test_quality_gate_blocks_cross_source_conflicts():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
        min_score=620,
        min_rank=12000,
        plan_count=12,
    )
    reference = candidate.model_copy(
        update={
            "source_batch_id": "sd-2025-reference",
            "snapshot_id": "sd-2025-reference-snapshot",
            "min_score": 618,
            "min_rank": 12300,
            "plan_count": 10,
        }
    )

    report = run_quality_gate(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        reference_candidates=(reference,),
    )

    assert report.status == "blocked"
    assert report.record_count_passed == 0
    assert report.cross_source_conflicts[0].code == "cross_source_conflict"
    assert report.cross_source_conflicts[0].raw_row_number == candidate.raw_row_number
    assert "sd-2025-reference/sd-2025-reference-snapshot" in (
        report.cross_source_conflicts[0].message
    )
    assert "min_score, min_rank, plan_count" in report.cross_source_conflicts[0].message


def test_quality_gate_blocks_snapshot_source_page_mismatch():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot().model_copy(update={"source_page_id": "different-source-page"})
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )

    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)

    assert report.status == "blocked"
    assert report.record_count_passed == 0
    assert report.field_errors[0].code == "snapshot_source_page_mismatch"


def test_quality_gate_blocks_disallowed_source_type():
    source = SourcePage.model_validate(
        {
            "source_page_id": "authorized-sample-page",
            "source_name": "授权样本来源",
            "source_type": "authorized_partner",
            "province": "山东",
            "year": 2025,
            "document_title": "授权样本投档数据",
            "source_url": "https://authorized.example.edu/admission.html",
            "authority_note": "授权合作方提供，仅用于测试本轮允许来源范围。",
        }
    )
    snapshot = _snapshot().model_copy(
        update={
            "source_page_id": source.source_page_id,
            "source_batch_id": "山东-2025-authorized",
        }
    )
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )

    report = run_quality_gate(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        allowed_source_types=("official_exam_authority",),
    )

    assert report.status == "blocked"
    assert report.record_count_passed == 0
    assert report.field_errors[0].code == "source_type_not_allowed"


def test_quality_gate_blocks_snapshot_captured_before_publish_date():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot().model_copy(update={"captured_at": datetime(2025, 7, 18, tzinfo=UTC)})
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )

    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)

    assert report.status == "blocked"
    assert report.record_count_passed == 0
    assert report.field_errors[0].code == "snapshot_captured_before_publish"


def test_quality_gate_blocks_low_confidence_candidates():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
        confidence="low",
    )

    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)

    assert report.status == "blocked"
    assert report.blocked_reasons == ("low confidence row 2",)


def test_quality_gate_allows_explicit_raw_and_parsed_counts():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()

    report = run_quality_gate(
        candidates=[],
        source_page=source,
        snapshot=snapshot,
        record_count_raw=3,
        record_count_parsed=0,
    )

    assert report.status == "blocked"
    assert report.record_count_raw == 3
    assert report.record_count_parsed == 0
    assert report.record_count_passed == 0


def test_quality_gate_warns_on_missing_pilot_school():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
        confidence="medium",
    )

    report = run_quality_gate(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        expected_schools=("山东大学", "中国海洋大学"),
    )

    assert report.status == "warning"
    assert report.record_count_passed == 1
    assert report.coverage_metrics.missing_schools == ("中国海洋大学",)
    assert report.confidence_summary["medium"] == 1
    assert tuple(issue.code for issue in report.warning_issues) == (
        "medium_confidence_row",
        "pilot_school_coverage_gap",
    )
    assert report.warning_issues[0].raw_row_number == candidate.raw_row_number


def test_agent_citation_metadata_keeps_source_year_snapshot_confidence():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )

    citation = build_citation_metadata(candidate, source, snapshot)

    assert citation.source == "山东省教育招生考试院"
    assert citation.source_url == "https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996"
    assert citation.snapshot_url == source.attachments[0].url
    assert citation.year == 2025
    assert citation.snapshot == snapshot.snapshot_id
    assert citation.confidence == "high"
    assert citation.source_batch_id == snapshot.source_batch_id
