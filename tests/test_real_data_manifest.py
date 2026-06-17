from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.real_data.contracts import CanonicalAdmissionCandidate, run_quality_gate
from backend.real_data.manifest import (
    StagingManifestReadError,
    StagingManifestWriteError,
    iter_manifest_artifact_paths,
    load_staging_manifest,
    write_staging_manifest,
)
from backend.real_data.source_registry import (
    SHANDONG_2025_REGULAR_BATCH_1_PAGE,
    build_snapshot,
    sha256_bytes,
)
from backend.real_data.staging import write_admission_staging_artifact


def _snapshot(snapshot_id: str, payload: bytes = b"manifest pilot xls bytes"):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    return build_snapshot(
        source_page=source,
        attachment=source.attachments[0],
        raw_file_sha256=sha256_bytes(payload),
        captured_at=datetime(2026, 6, 9, 10, 0, tzinfo=UTC),
        operator="codex",
        snapshot_id=snapshot_id,
    )


def _candidate(snapshot, **overrides):
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


def _write_artifact(tmp_path: Path, snapshot_id: str, candidate: CanonicalAdmissionCandidate):
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot(snapshot_id)
    aligned_candidate = candidate.model_copy(
        update={
            "source_batch_id": snapshot.source_batch_id,
            "snapshot_id": snapshot.snapshot_id,
        }
    )
    report = run_quality_gate(
        candidates=[aligned_candidate],
        source_page=source,
        snapshot=snapshot,
        expected_min_records=1,
    )
    return write_admission_staging_artifact(
        candidates=[aligned_candidate],
        source_page=source,
        snapshot=snapshot,
        quality_report=report,
        output_dir=tmp_path,
    )


def test_staging_manifest_writes_and_revalidates_artifact_entries(tmp_path: Path):
    snapshot = _snapshot("sd-2025-manifest-a")
    artifact = _write_artifact(
        tmp_path / "staging",
        snapshot.snapshot_id,
        _candidate(snapshot),
    )
    manifest_path = tmp_path / "manifest.json"

    written = write_staging_manifest(
        manifest_path=manifest_path,
        artifact_paths=[artifact.artifact_path],
    )
    loaded = load_staging_manifest(manifest_path)

    assert written == loaded
    assert loaded.schema_version == "real_data_staging_manifest.v1"
    assert loaded.artifacts[0].artifact_path == artifact.artifact_path
    assert loaded.artifacts[0].province == "山东"
    assert loaded.artifacts[0].year == 2025
    assert loaded.artifacts[0].quality_status == "pass"
    assert loaded.artifacts[0].quality_report_id == "sd-2025-manifest-a-quality"
    assert loaded.artifacts[0].candidate_count == 1
    assert iter_manifest_artifact_paths(manifest_path) == (artifact.artifact_path,)


def test_staging_manifest_rejects_empty_artifact_list(tmp_path: Path):
    with pytest.raises(StagingManifestWriteError, match="at least one artifact"):
        write_staging_manifest(manifest_path=tmp_path / "manifest.json", artifact_paths=[])


def test_staging_manifest_rejects_default_overwrite(tmp_path: Path):
    snapshot = _snapshot("sd-2025-manifest-a")
    artifact = _write_artifact(tmp_path / "staging", snapshot.snapshot_id, _candidate(snapshot))
    manifest_path = tmp_path / "manifest.json"
    write_staging_manifest(manifest_path=manifest_path, artifact_paths=[artifact.artifact_path])

    with pytest.raises(FileExistsError, match="staging manifest already exists"):
        write_staging_manifest(manifest_path=manifest_path, artifact_paths=[artifact.artifact_path])


def test_staging_manifest_rejects_duplicate_snapshot_entries(tmp_path: Path):
    snapshot = _snapshot("sd-2025-manifest-a")
    artifact = _write_artifact(tmp_path / "staging", snapshot.snapshot_id, _candidate(snapshot))

    with pytest.raises(StagingManifestWriteError, match="invalid staging manifest"):
        write_staging_manifest(
            manifest_path=tmp_path / "manifest.json",
            artifact_paths=[artifact.artifact_path, artifact.artifact_path],
        )


def test_staging_manifest_read_rejects_tampered_summary(tmp_path: Path):
    snapshot = _snapshot("sd-2025-manifest-a")
    artifact = _write_artifact(tmp_path / "staging", snapshot.snapshot_id, _candidate(snapshot))
    manifest_path = tmp_path / "manifest.json"
    write_staging_manifest(manifest_path=manifest_path, artifact_paths=[artifact.artifact_path])
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["candidate_count"] = 999
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(StagingManifestReadError, match="invalid staging manifest"):
        load_staging_manifest(manifest_path)


def test_staging_manifest_read_rejects_tampered_quality_report_id(tmp_path: Path):
    snapshot = _snapshot("sd-2025-manifest-a")
    artifact = _write_artifact(tmp_path / "staging", snapshot.snapshot_id, _candidate(snapshot))
    manifest_path = tmp_path / "manifest.json"
    write_staging_manifest(manifest_path=manifest_path, artifact_paths=[artifact.artifact_path])
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["quality_report_id"] = "tampered-quality-report"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(StagingManifestReadError, match="invalid staging manifest"):
        load_staging_manifest(manifest_path)


def test_staging_manifest_read_rejects_tampered_referenced_artifact(tmp_path: Path):
    snapshot = _snapshot("sd-2025-manifest-a")
    artifact = _write_artifact(tmp_path / "staging", snapshot.snapshot_id, _candidate(snapshot))
    manifest_path = tmp_path / "manifest.json"
    write_staging_manifest(manifest_path=manifest_path, artifact_paths=[artifact.artifact_path])
    artifact_payload = json.loads(artifact.artifact_path.read_text(encoding="utf-8"))
    artifact_payload["citations"][0]["snapshot"] = "tampered"
    artifact.artifact_path.write_text(
        json.dumps(artifact_payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(StagingManifestReadError, match="invalid staging manifest"):
        load_staging_manifest(manifest_path)
