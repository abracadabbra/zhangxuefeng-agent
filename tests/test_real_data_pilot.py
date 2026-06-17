import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.real_data.parser import build_raw_admission_row
from backend.real_data.pilot import (
    ReviewedRawRowsArtifactReadError,
    load_reviewed_raw_rows_artifact,
    run_reviewed_admission_pilot,
    run_reviewed_admission_pilot_from_artifact,
    write_reviewed_raw_rows_artifact,
)
from backend.real_data.source_registry import (
    HENAN_2025_UNDERGRAD_PARALLEL_PAGE,
    build_manual_snapshot,
    sha256_bytes,
)


def _snapshot():
    return build_manual_snapshot(
        source_page=HENAN_2025_UNDERGRAD_PARALLEL_PAGE,
        raw_file_name="henan-2025-undergrad-physical-reviewed-sample.html",
        raw_file_url=(
            "https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?"
            "yearTip=2025&pc=1&kl=5"
        ),
        raw_file_sha256=sha256_bytes(b"reviewed henan pilot sample"),
        captured_at=datetime(2026, 6, 9, 17, 30, tzinfo=UTC),
        operator="codex",
        snapshot_id="ha-2025-undergrad-physical-reviewed-sample",
    )


def _reviewed_row(snapshot):
    return build_raw_admission_row(
        snapshot=snapshot,
        raw_row_number=10,
        raw_values={
            "院校代号": "10459",
            "院校名称": "郑州大学",
            "专业代号": "0809",
            "专业名称": "计算机类",
            "计划数": "12",
            "投档最低分": "600",
            "投档最低位次": "20000",
        },
    )


def test_reviewed_raw_rows_artifact_writes_and_loads_with_schema_report(tmp_path: Path):
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    snapshot = _snapshot()
    row = _reviewed_row(snapshot)

    artifact = write_reviewed_raw_rows_artifact(
        rows=[row],
        source_page=source,
        snapshot=snapshot,
        output_dir=tmp_path,
    )
    payload = load_reviewed_raw_rows_artifact(artifact.artifact_path)

    assert artifact.row_count == 1
    assert artifact.schema_status == "pass"
    assert payload.schema_version == "real_data_reviewed_rows.v1"
    assert payload.source_page == source
    assert payload.snapshot == snapshot
    assert payload.rows == (row,)
    assert payload.schema_report.status == "pass"
    assert payload.schema_report.matched_fields["min_score"] == "投档最低分"


def test_reviewed_raw_rows_artifact_rejects_tampered_schema_report(tmp_path: Path):
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    snapshot = _snapshot()
    artifact = write_reviewed_raw_rows_artifact(
        rows=[_reviewed_row(snapshot)],
        source_page=source,
        snapshot=snapshot,
        output_dir=tmp_path,
    )
    payload = json.loads(artifact.artifact_path.read_text(encoding="utf-8"))
    payload["schema_report"]["missing_required_fields"] = ["min_score"]
    artifact.artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ReviewedRawRowsArtifactReadError, match="invalid reviewed raw rows"):
        load_reviewed_raw_rows_artifact(artifact.artifact_path)


def test_reviewed_raw_rows_artifact_rejects_row_snapshot_mismatch(tmp_path: Path):
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    snapshot = _snapshot()
    row = _reviewed_row(snapshot).model_copy(update={"snapshot_id": "other-snapshot"})

    with pytest.raises(ValueError, match="raw row snapshot"):
        write_reviewed_raw_rows_artifact(
            rows=[row],
            source_page=source,
            snapshot=snapshot,
            output_dir=tmp_path,
        )


def test_reviewed_raw_rows_artifact_rejects_duplicate_raw_row_numbers(tmp_path: Path):
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    snapshot = _snapshot()
    first = _reviewed_row(snapshot)
    duplicate = _reviewed_row(snapshot).model_copy(
        update={"raw_values": {**first.raw_values, "专业名称": "软件工程"}}
    )

    with pytest.raises(ValueError, match="raw row numbers must be unique"):
        write_reviewed_raw_rows_artifact(
            rows=[first, duplicate],
            source_page=source,
            snapshot=snapshot,
            output_dir=tmp_path,
        )


def test_reviewed_admission_pilot_runs_to_staging_and_citation(tmp_path: Path):
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    snapshot = _snapshot()
    row = _reviewed_row(snapshot)

    result = run_reviewed_admission_pilot(
        rows=[row],
        source_page=source,
        snapshot=snapshot,
        province="河南",
        year=2025,
        batch="本科批",
        subject_type="物理类",
        output_dir=tmp_path,
        expected_schools=("郑州大学",),
    )

    assert result.schema_report.status == "pass"
    assert result.parse_result.issues == ()
    assert result.quality_report.status == "pass"
    assert result.quality_report.record_count_raw == 1
    assert result.quality_report.record_count_parsed == 1
    assert result.quality_report.record_count_passed == 1
    assert result.artifact is not None
    assert result.artifact.artifact_path.exists()
    assert len(result.citation_records) == 1
    record = result.citation_records[0]
    assert record.school_name == "郑州大学"
    assert record.major_or_group_name == "计算机类"
    assert record.min_score == 600
    assert record.source == "河南省教育考试院"
    assert record.source_url == source.source_url
    assert record.snapshot_url == snapshot.raw_file_url
    assert record.snapshot == snapshot.snapshot_id


def test_reviewed_admission_pilot_runs_from_reviewed_rows_artifact(tmp_path: Path):
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    snapshot = _snapshot()
    raw_artifact = write_reviewed_raw_rows_artifact(
        rows=[_reviewed_row(snapshot)],
        source_page=source,
        snapshot=snapshot,
        output_dir=tmp_path / "raw",
    )

    result = run_reviewed_admission_pilot_from_artifact(
        reviewed_rows_artifact_path=raw_artifact.artifact_path,
        province="河南",
        year=2025,
        batch="本科批",
        subject_type="物理类",
        output_dir=tmp_path / "staging",
        expected_schools=("郑州大学",),
    )

    assert result.quality_report.status == "pass"
    assert result.artifact is not None
    assert result.artifact.artifact_path.exists()
    assert result.citation_records[0].source == "河南省教育考试院"


def test_reviewed_admission_pilot_from_artifact_rejects_tampered_raw_artifact(
    tmp_path: Path,
):
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    snapshot = _snapshot()
    raw_artifact = write_reviewed_raw_rows_artifact(
        rows=[_reviewed_row(snapshot)],
        source_page=source,
        snapshot=snapshot,
        output_dir=tmp_path / "raw",
    )
    payload = json.loads(raw_artifact.artifact_path.read_text(encoding="utf-8"))
    payload["rows"][0]["snapshot_id"] = "tampered"
    raw_artifact.artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ReviewedRawRowsArtifactReadError, match="invalid reviewed raw rows"):
        run_reviewed_admission_pilot_from_artifact(
            reviewed_rows_artifact_path=raw_artifact.artifact_path,
            province="河南",
            year=2025,
            batch="本科批",
            subject_type="物理类",
            output_dir=tmp_path / "staging",
        )

    assert list((tmp_path / "staging").rglob("*.json")) == []


def test_reviewed_admission_pilot_blocks_before_staging_when_schema_is_missing_score(
    tmp_path: Path,
):
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    snapshot = _snapshot()
    row = build_raw_admission_row(
        snapshot=snapshot,
        raw_row_number=11,
        raw_values={
            "院校名称": "郑州大学",
            "专业名称": "计算机类",
            "最低位次": "20000",
        },
    )

    result = run_reviewed_admission_pilot(
        rows=[row],
        source_page=source,
        snapshot=snapshot,
        province="河南",
        year=2025,
        batch="本科批",
        subject_type="物理类",
        output_dir=tmp_path,
    )

    assert result.schema_report.status == "blocked"
    assert result.schema_report.missing_required_fields == ("min_score",)
    assert result.quality_report.status == "blocked"
    assert result.quality_report.record_count_raw == 1
    assert result.quality_report.record_count_parsed == 0
    assert result.quality_report.record_count_passed == 0
    assert result.quality_report.field_errors[0].code == "missing_source_schema_field"
    assert result.artifact is None
    assert result.citation_records == ()
    assert list(tmp_path.rglob("*.json")) == []
