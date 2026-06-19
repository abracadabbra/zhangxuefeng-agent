"""Approval packet tests for canonical loader handoff."""

from datetime import datetime, timezone

import pytest

from backend.data_pipeline.loaders import build_loader_approval_packet
from backend.data_pipeline.pilots import PilotLoadNotReadyError, run_manual_pilot
from backend.data_pipeline.parsers import ManualSampleParser
from backend.data_pipeline.raw_store.manifest import ManifestFile, RawSnapshotManifest
from backend.data_pipeline.sources.registry import DataSource, SourceCoverage


def make_source() -> DataSource:
    return DataSource(
        source_id="sd_exam_authority",
        name="Shandong Education Admissions Examination Institute",
        source_type="provincial_exam_authority",
        homepage_url="https://www.sdzk.cn/default.aspx",
        data_categories=["admission_scores"],
        coverage=SourceCoverage(provinces=["山东"], years=[2025]),
        trust_score=1.0,
        update_frequency="annual",
        collection_method="manual_download",
        license_note="Official public source; review citation requirements.",
    )


def make_manifest() -> RawSnapshotManifest:
    return RawSnapshotManifest(
        snapshot_id="sd_pilot_2025_001",
        source_id="sd_exam_authority",
        dataset="admission_scores",
        source_url="https://example.gov.cn/manual-sample.csv",
        published_year=2025,
        collected_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        collector="manual",
        collector_version="0.1.0",
        files=[
            ManifestFile(
                path="files/manual-sample.csv",
                sha256="a" * 64,
                content_type="text/csv",
            )
        ],
        license_note="Test fixture only.",
    )


def make_rows(year: int = 2025, confidence: float = 0.95) -> list[dict]:
    return [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": year,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "confidence": confidence,
        }
    ]


def test_build_loader_approval_packet_summarizes_ready_audit():
    rows = make_rows()
    manifest = make_manifest()
    candidates = ManualSampleParser().parse(rows, manifest)
    audit = run_manual_pilot(rows, manifest, source=make_source()).to_audit_dict()

    packet = build_loader_approval_packet(
        audit=audit,
        candidates=candidates,
        parser_name="ManualSampleParser",
        parser_version="0.1.0",
    ).to_review_dict()

    assert packet["action"] == "canonical_loader_approval"
    assert packet["load_allowed"] is True
    assert packet["candidate_count"] == 1
    assert packet["entity_counts"] == {"admission_score": 1}
    assert packet["source_id"] == "sd_exam_authority"
    assert packet["snapshot_id"] == "sd_pilot_2025_001"
    assert packet["dataset"] == "admission_scores"
    assert packet["audit_summary"]["review_status"] == "ready_for_loader_review"
    assert packet["rollback_actions"][0] == (
        "Delete lineage records for snapshot_id=sd_pilot_2025_001."
    )
    assert "Does not approve crawler execution." in packet["non_goals"]


def test_build_loader_approval_packet_blocks_warning_review_audit():
    rows = make_rows(year=2024, confidence=0.7)
    manifest = make_manifest()
    candidates = ManualSampleParser().parse(rows, manifest)
    audit = run_manual_pilot(rows, manifest).to_audit_dict()

    assert audit["review_status"] == "needs_warning_review"
    with pytest.raises(PilotLoadNotReadyError, match="needs_warning_review"):
        build_loader_approval_packet(
            audit=audit,
            candidates=candidates,
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
        )
