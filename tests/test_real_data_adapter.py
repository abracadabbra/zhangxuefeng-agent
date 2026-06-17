from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.real_data.adapter import (
    AdmissionQuery,
    ApprovalRequiredError,
    query_admission_records_from_approval,
    query_admission_records_from_manifest,
    query_admission_records_from_staging,
)
from backend.real_data.approval import ManualApprovalChecklist, write_manual_approval_artifact
from backend.real_data.contracts import CanonicalAdmissionCandidate, run_quality_gate
from backend.real_data.manifest import write_staging_manifest
from backend.real_data.source_registry import (
    SHANDONG_2025_REGULAR_BATCH_1_PAGE,
    build_snapshot,
    sha256_bytes,
)
from backend.real_data.staging import (
    StagingArtifactReadError,
    write_admission_staging_artifact,
)


def _snapshot(snapshot_id: str | None = None):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    return build_snapshot(
        source_page=source,
        attachment=source.attachments[0],
        raw_file_sha256=sha256_bytes(b"adapter pilot xls bytes"),
        captured_at=datetime(2026, 6, 9, 10, 0, tzinfo=UTC),
        operator="codex",
        snapshot_id=snapshot_id,
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


def _write_artifact(
    tmp_path: Path,
    candidates: list[CanonicalAdmissionCandidate],
    snapshot_id: str | None = None,
):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot(snapshot_id=snapshot_id)
    aligned_candidates = [
        candidate.model_copy(
            update={
                "source_batch_id": snapshot.source_batch_id,
                "snapshot_id": snapshot.snapshot_id,
            }
        )
        for candidate in candidates
    ]
    report = run_quality_gate(
        candidates=aligned_candidates,
        source_page=source,
        snapshot=snapshot,
        expected_min_records=1,
    )
    return write_admission_staging_artifact(
        candidates=aligned_candidates,
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )


def test_adapter_queries_validated_staging_records_with_citations(tmp_path: Path):
    artifact = _write_artifact(
        tmp_path,
        [
            _candidate(school_name="山东大学", major_or_group_name="计算机类", raw_row_number=2),
            _candidate(
                school_name="中国海洋大学",
                major_or_group_name="海洋科学",
                min_score=610,
                raw_row_number=3,
            ),
        ],
    )

    result = query_admission_records_from_staging(
        artifact.artifact_path,
        AdmissionQuery(province="山东", year=2025, school_name="山东大学"),
    )

    assert result.total == 1
    record = result.records[0]
    assert record.school_name == "山东大学"
    assert record.source == "山东省教育招生考试院"
    assert record.source_url == SHANDONG_2025_REGULAR_BATCH_1_PAGE.source_url
    assert record.snapshot_url == SHANDONG_2025_REGULAR_BATCH_1_PAGE.attachments[0].url
    assert record.year == 2025
    assert record.confidence == "high"


def test_adapter_filters_by_major_batch_subject_and_score_range(tmp_path: Path):
    artifact = _write_artifact(
        tmp_path,
        [
            _candidate(school_name="山东大学", major_or_group_name="计算机类", min_score=620),
            _candidate(
                school_name="中国海洋大学",
                major_or_group_name="海洋科学",
                min_score=610,
                raw_row_number=3,
            ),
        ],
    )

    result = query_admission_records_from_staging(
        artifact.artifact_path,
        AdmissionQuery(
            major_keyword="计算机",
            batch="普通类常规批第1次志愿",
            subject_type="普通类",
            min_score_at_least=615,
            min_score_at_most=625,
        ),
    )

    assert result.total == 1
    assert result.records[0].major_or_group_name == "计算机类"


def test_adapter_returns_empty_result_for_non_matching_query(tmp_path: Path):
    artifact = _write_artifact(tmp_path, [_candidate()])

    result = query_admission_records_from_staging(
        artifact.artifact_path,
        AdmissionQuery(province="河南"),
    )

    assert result.total == 0
    assert result.records == ()


def test_adapter_rejects_invalid_score_range():
    with pytest.raises(ValidationError, match="min_score_at_least"):
        AdmissionQuery(min_score_at_least=650, min_score_at_most=600)


def test_adapter_reuses_typed_readback_and_rejects_tampered_artifact(tmp_path: Path):
    artifact = _write_artifact(tmp_path, [_candidate()])
    payload = json.loads(artifact.artifact_path.read_text(encoding="utf-8"))
    payload["citations"][0]["snapshot_url"] = "https://example.invalid/tampered"
    artifact.artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(StagingArtifactReadError, match="invalid staging artifact"):
        query_admission_records_from_staging(artifact.artifact_path, AdmissionQuery())


def test_adapter_queries_multiple_validated_artifacts_from_manifest(tmp_path: Path):
    first = _write_artifact(
        tmp_path / "first",
        [_candidate(school_name="山东大学", major_or_group_name="计算机类")],
        snapshot_id="sd-2025-adapter-first",
    )
    second = _write_artifact(
        tmp_path / "second",
        [
            _candidate(
                school_name="中国海洋大学",
                major_or_group_name="海洋科学",
                min_score=610,
                raw_row_number=3,
            )
        ],
        snapshot_id="sd-2025-adapter-second",
    )
    manifest_path = tmp_path / "manifest.json"
    write_staging_manifest(
        manifest_path=manifest_path,
        artifact_paths=[first.artifact_path, second.artifact_path],
    )

    result = query_admission_records_from_manifest(
        manifest_path,
        AdmissionQuery(province="山东", year=2025, min_score_at_least=600),
    )

    assert result.total == 2
    assert {record.school_name for record in result.records} == {"山东大学", "中国海洋大学"}
    assert {record.source for record in result.records} == {"山东省教育招生考试院"}


def _checklist():
    return ManualApprovalChecklist(
        source_verified=True,
        snapshot_verified=True,
        quality_reviewed=True,
        citation_reviewed=True,
        no_production_writes_verified=True,
    )


def test_adapter_queries_records_from_approved_manifest(tmp_path: Path):
    artifact = _write_artifact(
        tmp_path / "staging",
        [_candidate(school_name="山东大学", major_or_group_name="计算机类")],
        snapshot_id="sd-2025-approved-adapter",
    )
    manifest_path = tmp_path / "manifest.json"
    write_staging_manifest(manifest_path=manifest_path, artifact_paths=[artifact.artifact_path])
    approval_path = tmp_path / "approval.json"
    write_manual_approval_artifact(
        approval_path=approval_path,
        manifest_path=manifest_path,
        reviewer="codex-reviewer",
        reviewed_at=datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
        decision="approved",
        checklist=_checklist(),
    )

    result = query_admission_records_from_approval(
        approval_path,
        AdmissionQuery(province="山东", school_name="山东大学"),
    )

    assert result.total == 1
    assert result.records[0].source == "山东省教育招生考试院"
    assert result.records[0].confidence == "high"


def test_adapter_blocks_rejected_manual_approval(tmp_path: Path):
    artifact = _write_artifact(
        tmp_path / "staging",
        [_candidate(school_name="山东大学", major_or_group_name="计算机类")],
        snapshot_id="sd-2025-rejected-adapter",
    )
    manifest_path = tmp_path / "manifest.json"
    write_staging_manifest(manifest_path=manifest_path, artifact_paths=[artifact.artifact_path])
    approval_path = tmp_path / "approval.json"
    checklist = _checklist().model_copy(update={"citation_reviewed": False})
    write_manual_approval_artifact(
        approval_path=approval_path,
        manifest_path=manifest_path,
        reviewer="codex-reviewer",
        reviewed_at=datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
        decision="rejected",
        checklist=checklist,
    )

    with pytest.raises(ApprovalRequiredError, match="not approved"):
        query_admission_records_from_approval(approval_path, AdmissionQuery())


def test_adapter_approval_query_rejects_tampered_approval(tmp_path: Path):
    artifact = _write_artifact(
        tmp_path / "staging",
        [_candidate(school_name="山东大学", major_or_group_name="计算机类")],
        snapshot_id="sd-2025-tampered-approval-adapter",
    )
    manifest_path = tmp_path / "manifest.json"
    write_staging_manifest(manifest_path=manifest_path, artifact_paths=[artifact.artifact_path])
    approval_path = tmp_path / "approval.json"
    write_manual_approval_artifact(
        approval_path=approval_path,
        manifest_path=manifest_path,
        reviewer="codex-reviewer",
        reviewed_at=datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
        decision="approved",
        checklist=_checklist(),
    )
    payload = json.loads(approval_path.read_text(encoding="utf-8"))
    payload["citation_record_count"] = 999
    approval_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid manual approval"):
        query_admission_records_from_approval(approval_path, AdmissionQuery())
