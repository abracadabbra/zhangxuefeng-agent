"""Data pipeline contract tests."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.data_pipeline.raw_store.checksums import compute_sha256, verify_manifest_files
from backend.data_pipeline.raw_store.manifest import ManifestFile, RawSnapshotManifest
from backend.data_pipeline.sources.registry import DataSource, SourceCoverage, SourceRegistry


def make_source(source_id: str = "sd_exam_authority") -> DataSource:
    return DataSource(
        source_id=source_id,
        name="Shandong Education Admissions Examination Institute",
        source_type="provincial_exam_authority",
        homepage_url="https://example.gov.cn",
        data_categories=["admission_scores", "enrollment_plans"],
        coverage=SourceCoverage(provinces=["山东"], years=[2024, 2025]),
        trust_score=1.0,
        update_frequency="annual",
        collection_method="manual_download",
        license_note="Official public data; citation requirements need review.",
        review_status="candidate",
    )


def make_manifest(file_hash: str) -> RawSnapshotManifest:
    return RawSnapshotManifest(
        snapshot_id="sd_scores_2025_001",
        source_id="sd_exam_authority",
        dataset="admission_scores",
        source_url="https://example.gov.cn/scores.pdf",
        published_year=2025,
        collected_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        collector="manual",
        collector_version="0.1.0",
        files=[
            ManifestFile(
                path="files/original.csv",
                sha256=file_hash,
                content_type="text/csv",
            )
        ],
        license_note="Manual review required before production use.",
    )


def test_source_registry_supports_lookup_and_category_filtering():
    source = make_source()
    registry = SourceRegistry(sources=[source])

    assert registry.require("sd_exam_authority").name.startswith("Shandong")
    assert registry.by_category("admission_scores") == [source]
    assert registry.by_category("schools") == []


def test_bundled_source_registry_loads_candidate_sources():
    registry_path = Path("backend/data_pipeline/sources/sources.json")

    registry = SourceRegistry.from_json_file(registry_path)

    assert registry.require("moe_school_list").trust_score == 1.0
    assert registry.require("sd_exam_authority").collection_method == "manual_download"
    assert registry.by_category("admission_scores")


def test_source_registry_audits_planned_pilot_scope():
    registry = SourceRegistry(sources=[make_source()])

    audit = registry.audit_scope(
        data_category="admission_scores",
        expected_provinces=("山东",),
        expected_years=(2025,),
    )

    assert audit.passed is True
    assert audit.issues == []
    assert audit.to_dict() == {
        "scope": {
            "data_category": "admission_scores",
            "expected_provinces": ["山东"],
            "expected_years": [2025],
            "require_reviewed": False,
        },
        "passed": True,
        "issues": [],
    }


def test_source_registry_audit_reports_missing_province_source():
    registry = SourceRegistry(sources=[make_source()])

    audit = registry.audit_scope(
        data_category="admission_scores",
        expected_provinces=("河南",),
        expected_years=(2025,),
    )

    assert audit.passed is False
    assert audit.errors[0].code == "missing_province_source"
    assert "河南" in audit.errors[0].message


def test_bundled_source_registry_audit_surfaces_review_warnings():
    registry_path = Path("backend/data_pipeline/sources/sources.json")
    registry = SourceRegistry.from_json_file(registry_path)

    audit = registry.audit_scope(
        data_category="admission_scores",
        expected_provinces=("山东",),
        expected_years=(2025,),
        require_reviewed=True,
    )

    assert audit.passed is True
    assert [issue.code for issue in audit.warnings] == [
        "source_not_reviewed",
    ]
    assert {issue.source_id for issue in audit.warnings} == {"sd_exam_authority"}


def test_source_registry_rejects_duplicate_source_ids():
    with pytest.raises(ValidationError, match="duplicate source_id"):
        SourceRegistry(sources=[make_source(), make_source()])


def test_source_rejects_out_of_range_trust_score():
    with pytest.raises(ValidationError):
        DataSource(
            source_id="bad_trust_source",
            name="Bad Trust Source",
            source_type="other",
            homepage_url="https://example.com",
            data_categories=["admission_scores"],
            trust_score=1.2,
            update_frequency="annual",
            collection_method="manual_download",
            license_note="review",
        )


def test_manifest_rejects_unsafe_relative_paths():
    file_hash = "a" * 64

    with pytest.raises(ValidationError, match="relative"):
        ManifestFile(path="../outside.csv", sha256=file_hash, content_type="text/csv")


def test_checksum_helpers_verify_manifest_files(tmp_path):
    snapshot_dir = tmp_path / "snapshot"
    data_file = snapshot_dir / "files" / "original.csv"
    data_file.parent.mkdir(parents=True)
    data_file.write_text("school,score\nExample University,620\n", encoding="utf-8")

    file_hash = compute_sha256(data_file)
    manifest = make_manifest(file_hash)

    assert verify_manifest_files(snapshot_dir, manifest) == []


def test_checksum_helpers_report_missing_and_mismatched_files(tmp_path):
    snapshot_dir = tmp_path / "snapshot"
    data_file = snapshot_dir / "files" / "original.csv"
    data_file.parent.mkdir(parents=True)
    data_file.write_text("changed content\n", encoding="utf-8")

    manifest = make_manifest("a" * 64)

    assert verify_manifest_files(snapshot_dir, manifest) == [
        "checksum mismatch: files/original.csv"
    ]

    data_file.unlink()
    assert verify_manifest_files(snapshot_dir, manifest) == ["missing file: files/original.csv"]
