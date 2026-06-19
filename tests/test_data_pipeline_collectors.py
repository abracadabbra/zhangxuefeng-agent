"""Collector tests for manual raw snapshot directories."""

import json
from datetime import datetime, timezone

import pytest

from backend.data_pipeline.collectors import ManualSnapshotCollector
from backend.data_pipeline.raw_store.checksums import compute_sha256


def make_manifest_payload(file_hash: str) -> dict:
    return {
        "snapshot_id": "sd_scores_2025_001",
        "source_id": "sd_exam_authority",
        "dataset": "admission_scores",
        "source_url": "https://example.gov.cn/scores.csv",
        "published_year": 2025,
        "collected_at": datetime(2026, 6, 6, tzinfo=timezone.utc).isoformat(),
        "collector": "manual",
        "collector_version": "0.1.0",
        "files": [
            {
                "path": "files/original.csv",
                "sha256": file_hash,
                "content_type": "text/csv",
            }
        ],
        "license_note": "Manual review required before production use.",
    }


def write_snapshot(tmp_path, file_content: str, manifest_hash: str | None = None):
    snapshot_dir = tmp_path / "snapshot"
    data_file = snapshot_dir / "files" / "original.csv"
    data_file.parent.mkdir(parents=True)
    data_file.write_text(file_content, encoding="utf-8")

    file_hash = manifest_hash or compute_sha256(data_file)
    manifest_path = snapshot_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(make_manifest_payload(file_hash)),
        encoding="utf-8",
    )
    return snapshot_dir


def test_manual_snapshot_collector_loads_valid_local_snapshot(tmp_path):
    snapshot_dir = write_snapshot(
        tmp_path,
        "school,score\n山东大学,620\n",
    )

    collected = ManualSnapshotCollector(snapshot_dir).collect()

    assert collected.is_valid
    assert collected.file_issues == ()
    assert collected.root_dir == snapshot_dir
    assert collected.manifest.snapshot_id == "sd_scores_2025_001"
    assert collected.manifest.collector == "manual"


def test_manual_snapshot_collector_reports_checksum_issues(tmp_path):
    snapshot_dir = write_snapshot(
        tmp_path,
        "changed content\n",
        manifest_hash="a" * 64,
    )

    collected = ManualSnapshotCollector(snapshot_dir).collect()

    assert not collected.is_valid
    assert collected.file_issues == ("checksum mismatch: files/original.csv",)


def test_manual_snapshot_collector_requires_manifest(tmp_path):
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        ManualSnapshotCollector(snapshot_dir).collect()
