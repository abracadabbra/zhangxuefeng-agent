import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.real_data.adapter import AdmissionQuery, query_admission_records_from_manifest
from backend.real_data.bundle import run_reviewed_admission_pilot_bundle_from_artifact
from backend.real_data.manifest import load_staging_manifest
from backend.real_data.parser import build_raw_admission_row
from backend.real_data.pilot import (
    ReviewedRawRowsArtifactReadError,
    write_reviewed_raw_rows_artifact,
)
from backend.real_data.source_registry import (
    HENAN_2025_UNDERGRAD_PARALLEL_PAGE,
    build_manual_snapshot,
    sha256_bytes,
)


def _snapshot(snapshot_id: str = "ha-2025-undergrad-physical-bundle-sample"):
    return build_manual_snapshot(
        source_page=HENAN_2025_UNDERGRAD_PARALLEL_PAGE,
        raw_file_name="henan-2025-undergrad-physical-reviewed-sample.html",
        raw_file_url=(
            "https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?"
            "yearTip=2025&pc=1&kl=5"
        ),
        raw_file_sha256=sha256_bytes(b"reviewed henan bundle sample"),
        captured_at=datetime(2026, 6, 9, 17, 30, tzinfo=UTC),
        operator="codex",
        snapshot_id=snapshot_id,
    )


def _reviewed_row(snapshot, min_score: str = "600"):
    return build_raw_admission_row(
        snapshot=snapshot,
        raw_row_number=10,
        raw_values={
            "院校代号": "10459",
            "院校名称": "郑州大学",
            "专业代号": "0809",
            "专业名称": "计算机类",
            "计划数": "12",
            "投档最低分": min_score,
            "投档最低位次": "20000",
        },
    )


def _write_reviewed_artifact(tmp_path: Path, rows, snapshot=None):
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    snapshot = snapshot or _snapshot()
    return write_reviewed_raw_rows_artifact(
        rows=rows,
        source_page=source,
        snapshot=snapshot,
        output_dir=tmp_path / "raw",
    )


def test_bundle_runs_reviewed_artifact_to_staging_manifest_and_query(tmp_path: Path):
    snapshot = _snapshot()
    raw_artifact = _write_reviewed_artifact(tmp_path, [_reviewed_row(snapshot)])

    result = run_reviewed_admission_pilot_bundle_from_artifact(
        reviewed_rows_artifact_path=raw_artifact.artifact_path,
        province="河南",
        year=2025,
        batch="本科批",
        subject_type="物理类",
        output_dir=tmp_path / "bundle",
        expected_schools=("郑州大学",),
    )

    assert result.pilot_result.quality_report.status == "pass"
    assert result.pilot_result.artifact is not None
    assert result.manifest_path == tmp_path / "bundle" / "staging_manifest.json"
    assert result.manifest is not None
    assert result.manifest.artifacts[0].snapshot_id == snapshot.snapshot_id
    assert load_staging_manifest(result.manifest_path) == result.manifest

    query_result = query_admission_records_from_manifest(
        result.manifest_path,
        AdmissionQuery(province="河南", school_name="郑州大学", major_keyword="计算机"),
    )
    assert query_result.total == 1
    record = query_result.records[0]
    assert record.min_score == 600
    assert record.source == "河南省教育考试院"
    assert record.snapshot_url == snapshot.raw_file_url
    assert record.confidence == "high"


def test_bundle_blocks_cross_source_conflict_against_reference_manifest(tmp_path: Path):
    reference_snapshot = _snapshot("ha-2025-reference")
    reference_raw = _write_reviewed_artifact(
        tmp_path / "reference",
        [_reviewed_row(reference_snapshot, min_score="600")],
        snapshot=reference_snapshot,
    )
    reference_result = run_reviewed_admission_pilot_bundle_from_artifact(
        reviewed_rows_artifact_path=reference_raw.artifact_path,
        province="河南",
        year=2025,
        batch="本科批",
        subject_type="物理类",
        output_dir=tmp_path / "reference_bundle",
        expected_schools=("郑州大学",),
    )
    assert reference_result.manifest_path is not None

    candidate_snapshot = _snapshot("ha-2025-conflicting-candidate")
    candidate_raw = _write_reviewed_artifact(
        tmp_path / "candidate",
        [_reviewed_row(candidate_snapshot, min_score="601")],
        snapshot=candidate_snapshot,
    )

    result = run_reviewed_admission_pilot_bundle_from_artifact(
        reviewed_rows_artifact_path=candidate_raw.artifact_path,
        province="河南",
        year=2025,
        batch="本科批",
        subject_type="物理类",
        output_dir=tmp_path / "candidate_bundle",
        reference_manifest_path=reference_result.manifest_path,
        expected_schools=("郑州大学",),
    )

    assert result.pilot_result.quality_report.status == "blocked"
    assert result.pilot_result.quality_report.record_count_passed == 0
    assert result.pilot_result.quality_report.cross_source_conflicts[0].code == (
        "cross_source_conflict"
    )
    assert "min_score" in result.pilot_result.quality_report.cross_source_conflicts[0].message
    assert result.pilot_result.artifact is None
    assert result.manifest_path is None
    assert result.manifest is None
    assert list((tmp_path / "candidate_bundle").rglob("*.json")) == []


def test_bundle_blocks_before_manifest_when_schema_is_missing_score(tmp_path: Path):
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
    raw_artifact = _write_reviewed_artifact(tmp_path, [row])

    result = run_reviewed_admission_pilot_bundle_from_artifact(
        reviewed_rows_artifact_path=raw_artifact.artifact_path,
        province="河南",
        year=2025,
        batch="本科批",
        subject_type="物理类",
        output_dir=tmp_path / "bundle",
    )

    assert result.pilot_result.schema_report.status == "blocked"
    assert result.pilot_result.quality_report.status == "blocked"
    assert result.pilot_result.artifact is None
    assert result.manifest_path is None
    assert result.manifest is None
    assert list((tmp_path / "bundle").rglob("*.json")) == []


def test_bundle_rejects_tampered_reviewed_artifact_before_downstream_writes(tmp_path: Path):
    snapshot = _snapshot()
    raw_artifact = _write_reviewed_artifact(tmp_path, [_reviewed_row(snapshot)])
    payload = json.loads(raw_artifact.artifact_path.read_text(encoding="utf-8"))
    payload["rows"][0]["snapshot_id"] = "tampered"
    raw_artifact.artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ReviewedRawRowsArtifactReadError, match="invalid reviewed raw rows"):
        run_reviewed_admission_pilot_bundle_from_artifact(
            reviewed_rows_artifact_path=raw_artifact.artifact_path,
            province="河南",
            year=2025,
            batch="本科批",
            subject_type="物理类",
            output_dir=tmp_path / "bundle",
        )

    assert list((tmp_path / "bundle").rglob("*.json")) == []
