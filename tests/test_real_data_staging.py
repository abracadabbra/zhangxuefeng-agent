from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.real_data.contracts import CanonicalAdmissionCandidate, run_quality_gate
from backend.real_data.source_registry import (
    SHANDONG_2025_REGULAR_BATCH_1_PAGE,
    build_snapshot,
    sha256_bytes,
)
from backend.real_data.staging import (
    StagingArtifactReadError,
    StagingWriteBlockedError,
    load_admission_staging_artifact,
    project_admission_citation_records,
    write_admission_staging_artifact,
)


def _snapshot():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    return build_snapshot(
        source_page=source,
        attachment=source.attachments[0],
        raw_file_sha256=sha256_bytes(b"pilot staging xls bytes"),
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


def test_staging_artifact_writes_candidates_report_and_citations(tmp_path: Path):
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

    artifact = write_admission_staging_artifact(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )

    payload = json.loads(artifact.artifact_path.read_text(encoding="utf-8"))
    assert artifact.candidate_count == 1
    assert artifact.quality_status == "pass"
    assert payload["schema_version"] == "real_data_staging.v1"
    assert payload["snapshot"]["snapshot_id"] == snapshot.snapshot_id
    assert payload["quality_report"]["snapshot_id"] == snapshot.snapshot_id
    assert payload["candidates"][0]["source_batch_id"] == snapshot.source_batch_id
    assert payload["candidates"][0]["raw_row_number"] == 2
    assert payload["citations"][0]["source"] == "山东省教育招生考试院"
    assert payload["citations"][0]["source_url"] == source.source_url
    assert payload["citations"][0]["snapshot_url"] == snapshot.raw_file_url
    assert payload["citations"][0]["snapshot"] == snapshot.snapshot_id


def test_staging_artifact_loads_back_with_typed_contract(tmp_path: Path):
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
    artifact = write_admission_staging_artifact(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )

    payload = load_admission_staging_artifact(artifact.artifact_path)

    assert payload.schema_version == "real_data_staging.v1"
    assert payload.source_page == source
    assert payload.snapshot == snapshot
    assert payload.quality_report == report
    assert payload.candidates == (candidate,)
    assert payload.citations[0].source_batch_id == snapshot.source_batch_id


def test_staging_artifact_projects_agent_citation_records(tmp_path: Path):
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
    artifact = write_admission_staging_artifact(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )
    payload = load_admission_staging_artifact(artifact.artifact_path)

    records = project_admission_citation_records(payload)

    assert len(records) == 1
    record = records[0]
    assert record.school_name == "山东大学"
    assert record.major_or_group_name == "计算机类"
    assert record.min_score == 620
    assert record.min_rank == 12000
    assert record.plan_count == 12
    assert record.raw_row_number == 2
    assert record.source == "山东省教育招生考试院"
    assert record.source_type == "official_source_snapshot"
    assert record.source_url == "https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996"
    assert record.snapshot_url == snapshot.raw_file_url
    assert record.year == 2025
    assert record.snapshot == snapshot.snapshot_id
    assert record.confidence == "high"
    assert record.source_batch_id == snapshot.source_batch_id


def test_staging_artifact_allows_warning_reports(tmp_path: Path):
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

    artifact = write_admission_staging_artifact(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )

    payload = json.loads(artifact.artifact_path.read_text(encoding="utf-8"))
    assert report.status == "warning"
    assert payload["quality_report"]["status"] == "warning"
    assert payload["quality_report"]["coverage_metrics"]["missing_schools"] == ["中国海洋大学"]


def test_staging_artifact_rejects_default_overwrite(tmp_path: Path):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )
    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)

    first = write_admission_staging_artifact(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )

    with pytest.raises(FileExistsError, match="staging artifact already exists"):
        write_admission_staging_artifact(
            candidates=[candidate],
            source_page=source,
            snapshot=snapshot,
            quality_report=report,
            output_dir=tmp_path,
        )

    assert first.artifact_path.exists()


def test_staging_artifact_rejects_blocked_reports(tmp_path: Path):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
        confidence="low",
    )
    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)

    with pytest.raises(StagingWriteBlockedError, match="blocked quality report"):
        write_admission_staging_artifact(
            candidates=[candidate],
            source_page=source,
            snapshot=snapshot,
            quality_report=report,
            output_dir=tmp_path,
        )

    assert list(tmp_path.rglob("*.json")) == []


def test_staging_artifact_reader_rejects_blocked_payload(tmp_path: Path):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )
    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)
    artifact = write_admission_staging_artifact(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )
    payload = json.loads(artifact.artifact_path.read_text(encoding="utf-8"))
    payload["quality_report"]["status"] = "blocked"
    payload["quality_report"]["blocked_reasons"] = ["manual tamper"]
    artifact.artifact_path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(StagingArtifactReadError, match="invalid staging artifact"):
        load_admission_staging_artifact(artifact.artifact_path)


def test_staging_artifact_reader_rejects_tampered_citation(tmp_path: Path):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )
    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)
    artifact = write_admission_staging_artifact(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )
    payload = json.loads(artifact.artifact_path.read_text(encoding="utf-8"))
    payload["citations"][0]["snapshot"] = "tampered-snapshot"
    artifact.artifact_path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(StagingArtifactReadError, match="invalid staging artifact"):
        load_admission_staging_artifact(artifact.artifact_path)


def test_staging_artifact_reader_rejects_tampered_snapshot_url(tmp_path: Path):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )
    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)
    artifact = write_admission_staging_artifact(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )
    payload = json.loads(artifact.artifact_path.read_text(encoding="utf-8"))
    payload["citations"][0]["snapshot_url"] = source.source_url
    artifact.artifact_path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(StagingArtifactReadError, match="invalid staging artifact"):
        load_admission_staging_artifact(artifact.artifact_path)


def test_staging_artifact_rejects_snapshot_mismatch(tmp_path: Path):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )
    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)
    mismatched_candidate = candidate.model_copy(update={"snapshot_id": "other-snapshot"})

    with pytest.raises(StagingWriteBlockedError, match="candidate snapshot"):
        write_admission_staging_artifact(
            candidates=[mismatched_candidate],
            source_page=source,
            snapshot=snapshot,
            quality_report=report,
            output_dir=tmp_path,
        )


def test_staging_artifact_does_not_touch_seed_directory(tmp_path: Path):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    candidate = _candidate(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
    )
    report = run_quality_gate(candidates=[candidate], source_page=source, snapshot=snapshot)
    seed_dir = Path("backend/seeds").resolve()

    artifact = write_admission_staging_artifact(
        candidates=[candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )

    assert seed_dir not in artifact.artifact_path.resolve().parents
