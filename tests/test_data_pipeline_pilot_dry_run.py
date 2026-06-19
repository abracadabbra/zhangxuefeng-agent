"""Pilot dry-run tests for reviewed real-data samples."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from backend.data_pipeline.pilots import (
    PilotDryRunBundle,
    PilotLoadNotReadyError,
    PilotSnapshotDirBundle,
    assert_loader_review_ready,
    assert_load_ready,
    build_load_ready_candidates,
    build_load_ready_candidates_bundle,
    build_load_ready_candidates_snapshot_dir,
    run_manual_pilot,
    run_manual_pilot_bundle,
    run_manual_pilot_payload,
    run_manual_pilot_snapshot_dir,
    run_manual_pilot_snapshot_dir_bundle,
)
from backend.data_pipeline.pilots.cli import main as pilot_cli_main
from backend.data_pipeline.quality.checks import QualityGateConfig
from backend.data_pipeline.raw_store.checksums import compute_sha256
from backend.data_pipeline.raw_store.manifest import ManifestFile, RawSnapshotManifest
from backend.data_pipeline.sources.registry import DataSource, SourceCoverage


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "real_data"


def load_example_bundle(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def make_source() -> DataSource:
    return DataSource(
        source_id="sd_exam_authority",
        name="Shandong Education Admissions Examination Institute",
        source_type="provincial_exam_authority",
        homepage_url="https://www.sdzk.cn/default.aspx",
        data_categories=["admission_scores", "enrollment_plans"],
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


def write_snapshot_dir(tmp_path, manifest: RawSnapshotManifest, content: str):
    snapshot_dir = tmp_path / "snapshot"
    data_file = snapshot_dir / manifest.files[0].path
    data_file.parent.mkdir(parents=True)
    data_file.write_text(content, encoding="utf-8")
    manifest.files[0].sha256 = compute_sha256(data_file)
    (snapshot_dir / "manifest.json").write_text(
        manifest.model_dump_json(),
        encoding="utf-8",
    )
    return snapshot_dir


def test_run_manual_pilot_reports_passed_quality_and_coverage():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "min_rank": 12000,
        }
    ]

    result = run_manual_pilot(
        rows,
        make_manifest(),
        QualityGateConfig(
            current_year=2026,
            expected_provinces=("山东",),
            expected_years=(2025,),
        ),
        source=make_source(),
    )

    assert result.snapshot_id == "sd_pilot_2025_001"
    assert result.source_id == "sd_exam_authority"
    assert result.dataset == "admission_scores"
    assert result.candidate_count == 1
    assert result.passed is True
    assert result.load_ready is True
    assert result.blockers == []
    assert result.source_validation_issues == []
    assert result.issue_counts == {"error": 0, "warning": 0, "info": 0}
    assert result.review_status == "ready_for_loader_review"
    assert result.review_notes == ["dry-run passed with no blockers or warnings"]
    assert result.coverage["by_entity_type"] == {"admission_score": 1}
    assert result.coverage["missing_expected_provinces"] == []
    assert result.coverage["missing_expected_years"] == []


def test_run_manual_pilot_snapshot_dir_blocks_checksum_mismatch(tmp_path):
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "min_rank": 12000,
        }
    ]
    manifest = make_manifest()
    snapshot_dir = write_snapshot_dir(
        tmp_path,
        manifest,
        "school,score\n山东大学,620\n",
    )
    data_file = snapshot_dir / manifest.files[0].path
    data_file.write_text("changed after manifest\n", encoding="utf-8")

    result = run_manual_pilot_snapshot_dir(
        rows,
        snapshot_dir,
        QualityGateConfig(current_year=2026),
        source=make_source(),
    )

    assert result.passed is False
    assert result.load_ready is False
    assert result.snapshot_file_issues == ["checksum mismatch: files/manual-sample.csv"]
    assert result.blockers == ["snapshot_file:checksum mismatch: files/manual-sample.csv"]
    assert result.issue_counts == {"error": 0, "warning": 0, "info": 0}
    assert result.review_status == "blocked"
    assert result.review_notes == [
        "blocked by snapshot_file:checksum mismatch: files/manual-sample.csv"
    ]


def test_run_manual_pilot_snapshot_dir_passes_when_files_match(tmp_path):
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "min_rank": 12000,
        }
    ]
    snapshot_dir = write_snapshot_dir(
        tmp_path,
        make_manifest(),
        "school,score\n山东大学,620\n",
    )

    result = run_manual_pilot_snapshot_dir(
        rows,
        snapshot_dir,
        QualityGateConfig(current_year=2026),
        source=make_source(),
    )

    assert result.passed is True
    assert result.load_ready is True
    assert result.snapshot_file_issues == []
    assert result.blockers == []


def test_snapshot_dir_candidate_builder_requires_matching_files(tmp_path):
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "min_rank": 12000,
        }
    ]
    manifest = make_manifest()
    snapshot_dir = write_snapshot_dir(
        tmp_path,
        manifest,
        "school,score\n山东大学,620\n",
    )

    candidates = build_load_ready_candidates_snapshot_dir(
        rows,
        snapshot_dir,
        QualityGateConfig(current_year=2026),
        source=make_source(),
    )

    assert len(candidates) == 1
    assert candidates[0].source.snapshot_id == "sd_pilot_2025_001"

    (snapshot_dir / manifest.files[0].path).write_text(
        "changed after manifest\n",
        encoding="utf-8",
    )

    with pytest.raises(PilotLoadNotReadyError, match="checksum mismatch"):
        build_load_ready_candidates_snapshot_dir(
            rows,
            snapshot_dir,
            QualityGateConfig(current_year=2026),
            source=make_source(),
        )


def test_run_manual_pilot_reports_quality_failures_without_writing_db():
    rows = [
        {
            "school_name": "山东大学",
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 900,
        }
    ]

    result = run_manual_pilot(rows, make_manifest())

    assert result.passed is False
    assert result.load_ready is False
    assert result.blockers == ["quality_error:value_out_of_range"]
    assert result.issue_counts["error"] == 1
    assert result.review_status == "blocked"
    assert result.quality_report.errors[0].code == "value_out_of_range"


def test_run_manual_pilot_reports_source_manifest_mismatch():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
        }
    ]
    source = make_source()
    manifest = make_manifest()
    manifest.source_id = "unknown_source"

    result = run_manual_pilot(rows, manifest, source=source)

    assert result.passed is False
    assert result.load_ready is False
    blocker = (
        "source_validation:manifest source_id unknown_source "
        "does not match source sd_exam_authority"
    )
    assert result.blockers == [
        blocker
    ]
    assert result.issue_counts == {"error": 0, "warning": 0, "info": 0}
    assert result.source_validation_issues == [
        "manifest source_id unknown_source does not match source sd_exam_authority"
    ]


def test_run_manual_pilot_reports_uncovered_dataset_and_year():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2024,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
        }
    ]
    source = make_source()
    source.data_categories = ["enrollment_plans"]
    manifest = make_manifest()
    manifest.published_year = 2024

    result = run_manual_pilot(rows, manifest, source=source)

    assert result.passed is False
    assert result.load_ready is False
    assert result.source_validation_issues == [
        "manifest dataset admission_scores is not covered by source",
        "manifest year 2024 is not covered by source",
    ]


def test_run_manual_pilot_marks_warnings_for_review():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2024,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "confidence": 0.7,
        }
    ]

    result = run_manual_pilot(
        rows,
        make_manifest(),
        QualityGateConfig(
            current_year=2026,
            freshness_window_years=1,
            min_agent_confidence=0.8,
        ),
    )

    assert result.passed is True
    assert result.load_ready is True
    assert result.issue_counts == {"error": 0, "warning": 2, "info": 0}
    assert result.review_status == "needs_warning_review"
    assert result.review_notes == [
        "warning requires review: low_confidence",
        "warning requires review: stale_data",
    ]


def test_pilot_dry_run_result_exports_stable_audit_dict():
    rows = [
        {
            "school_name": "山东大学",
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 900,
        }
    ]

    result = run_manual_pilot(rows, make_manifest(), source=make_source())
    audit = result.to_audit_dict()

    assert audit["snapshot_id"] == "sd_pilot_2025_001"
    assert audit["source_id"] == "sd_exam_authority"
    assert audit["dataset"] == "admission_scores"
    assert audit["candidate_count"] == 1
    assert audit["passed"] is False
    assert audit["load_ready"] is False
    assert audit["blockers"] == ["quality_error:value_out_of_range"]
    assert audit["source_validation_issues"] == []
    assert audit["issue_counts"] == {"error": 1, "warning": 0, "info": 0}
    assert audit["review_status"] == "blocked"
    assert audit["review_notes"] == ["blocked by quality_error:value_out_of_range"]
    assert audit["coverage"]["by_entity_type"] == {"admission_score": 1}
    assert audit["issues"][0]["code"] == "value_out_of_range"


def test_run_manual_pilot_payload_exports_audit_dict_from_json_like_payloads():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
        }
    ]

    audit = run_manual_pilot_payload(
        rows,
        make_manifest().model_dump(),
        source_payload=make_source().model_dump(),
    )

    assert audit["snapshot_id"] == "sd_pilot_2025_001"
    assert audit["source_id"] == "sd_exam_authority"
    assert audit["passed"] is True
    assert audit["load_ready"] is True
    assert audit["blockers"] == []
    assert audit["issue_counts"] == {"error": 0, "warning": 0, "info": 0}
    assert audit["source_validation_issues"] == []


def test_run_manual_pilot_payload_reports_source_mismatch():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
        }
    ]
    manifest_payload = make_manifest().model_dump()
    manifest_payload["source_id"] = "unknown_source"

    audit = run_manual_pilot_payload(
        rows,
        manifest_payload,
        source_payload=make_source().model_dump(),
    )

    assert audit["passed"] is False
    assert audit["load_ready"] is False
    assert audit["source_validation_issues"] == [
        "manifest source_id unknown_source does not match source sd_exam_authority"
    ]


def test_run_manual_pilot_bundle_uses_quality_config():
    payload = {
        "source": make_source().model_dump(),
        "manifest": make_manifest().model_dump(),
        "quality_config": {
            "current_year": 2026,
            "expected_provinces": ["山东", "河南"],
            "expected_years": [2025],
        },
        "rows": [
            {
                "school_name": "山东大学",
                "major_name": None,
                "province": "山东",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 620,
            }
        ],
    }

    audit = run_manual_pilot_bundle(payload)

    assert audit["passed"] is False
    assert audit["load_ready"] is False
    assert audit["blockers"] == ["coverage_missing:province:河南"]
    assert audit["review_status"] == "blocked"
    assert audit["review_notes"] == ["blocked by coverage_missing:province:河南"]
    assert audit["coverage"]["missing_expected_provinces"] == ["河南"]
    assert audit["coverage"]["missing_expected_years"] == []


def test_example_full_bundles_pass_with_required_review_metadata():
    for bundle_name, entity_type in [
        ("sd_pilot_bundle.json", "admission_score"),
        ("sd_plan_pilot_bundle.json", "enrollment_plan"),
    ]:
        payload = load_example_bundle(bundle_name)

        audit = run_manual_pilot_bundle(payload)
        candidates = build_load_ready_candidates_bundle(payload)

        assert payload["quality_config"]["require_review_metadata"] is True
        assert audit["passed"] is True
        assert audit["load_ready"] is True
        assert audit["blockers"] == []
        assert audit["review_status"] == "ready_for_loader_review"
        assert audit["coverage"]["by_entity_type"] == {entity_type: 1}
        assert candidates[0].source.review.reviewed_by == "example-reviewer"


def test_example_snapshot_dir_bundle_passes_with_required_review_metadata():
    payload = load_example_bundle("sd_snapshot_pilot_rows.json")
    snapshot_dir = EXAMPLES_DIR / "snapshots" / "sd_pilot_2025_001"

    audit = run_manual_pilot_snapshot_dir_bundle(payload, snapshot_dir)

    assert payload["quality_config"]["require_review_metadata"] is True
    assert audit["passed"] is True
    assert audit["load_ready"] is True
    assert audit["blockers"] == []
    assert audit["snapshot_file_issues"] == []
    assert audit["review_status"] == "ready_for_loader_review"


def test_run_manual_pilot_blocks_missing_expected_year():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
        }
    ]

    result = run_manual_pilot(
        rows,
        make_manifest(),
        QualityGateConfig(
            current_year=2026,
            expected_provinces=("山东",),
            expected_years=(2024, 2025),
        ),
        source=make_source(),
    )

    assert result.passed is False
    assert result.load_ready is False
    assert result.blockers == ["coverage_missing:year:2024"]
    assert result.review_status == "blocked"
    assert result.review_notes == ["blocked by coverage_missing:year:2024"]
    assert result.coverage["missing_expected_provinces"] == []
    assert result.coverage["missing_expected_years"] == [2024]


def test_pilot_dry_run_bundle_requires_manifest_and_rows():
    assert PilotDryRunBundle.model_validate(
        {
            "manifest": make_manifest().model_dump(),
            "rows": [],
        }
    ).rows == []

    with pytest.raises(ValidationError):
        PilotDryRunBundle.model_validate({"rows": []})

    with pytest.raises(ValidationError):
        PilotDryRunBundle.model_validate({"manifest": make_manifest().model_dump()})


def test_pilot_snapshot_dir_bundle_requires_rows():
    assert PilotSnapshotDirBundle.model_validate({"rows": []}).rows == []

    with pytest.raises(ValidationError):
        PilotSnapshotDirBundle.model_validate({"source": make_source().model_dump()})


def test_pilot_cli_prints_audit_json_and_returns_status(tmp_path, capsys):
    bundle_path = tmp_path / "pilot_bundle.json"
    bundle = {
        "source": make_source().model_dump(mode="json"),
        "manifest": make_manifest().model_dump(mode="json"),
        "rows": [
            {
                "school_name": "山东大学",
                "major_name": None,
                "province": "山东",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 620,
            }
        ],
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    exit_code = pilot_cli_main([str(bundle_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["passed"] is True
    assert output["load_ready"] is True
    assert output["snapshot_id"] == "sd_pilot_2025_001"


def test_pilot_cli_writes_optional_audit_output(tmp_path, capsys):
    bundle_path = tmp_path / "pilot_bundle.json"
    audit_path = tmp_path / "audit" / "sd_pilot_audit.json"
    bundle = {
        "source": make_source().model_dump(mode="json"),
        "manifest": make_manifest().model_dump(mode="json"),
        "rows": [
            {
                "school_name": "山东大学",
                "major_name": None,
                "province": "山东",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 620,
            }
        ],
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    exit_code = pilot_cli_main(
        [
            "--audit-output",
            str(audit_path),
            str(bundle_path),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(audit_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert file_payload == stdout_payload
    assert file_payload["load_ready"] is True


def test_pilot_cli_writes_optional_approval_output(tmp_path, capsys):
    bundle_path = tmp_path / "pilot_bundle.json"
    approval_path = tmp_path / "approval" / "sd_pilot_approval.json"
    bundle = {
        "source": make_source().model_dump(mode="json"),
        "manifest": make_manifest().model_dump(mode="json"),
        "rows": [
            {
                "school_name": "山东大学",
                "major_name": None,
                "province": "山东",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 620,
            }
        ],
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    exit_code = pilot_cli_main(
        [
            "--approval-output",
            str(approval_path),
            str(bundle_path),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    approval_payload = json.loads(approval_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout_payload["review_status"] == "ready_for_loader_review"
    assert approval_payload["action"] == "canonical_loader_approval"
    assert approval_payload["load_allowed"] is True
    assert approval_payload["candidate_count"] == 1
    assert approval_payload["entity_counts"] == {"admission_score": 1}
    assert approval_payload["parser_name"] == "ManualSampleParser"
    assert approval_payload["parser_version"] == "0.1.0"


def test_pilot_cli_refuses_approval_output_for_warning_review(tmp_path, capsys):
    bundle_path = tmp_path / "pilot_bundle_warning.json"
    approval_path = tmp_path / "approval" / "sd_pilot_approval.json"
    bundle = {
        "source": make_source().model_dump(mode="json"),
        "manifest": make_manifest().model_dump(mode="json"),
        "rows": [
            {
                "school_name": "山东大学",
                "major_name": None,
                "province": "山东",
                "year": 2024,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 620,
                "confidence": 0.7,
            }
        ],
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    exit_code = pilot_cli_main(
        [
            "--approval-output",
            str(approval_path),
            str(bundle_path),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output["status"] == "error"
    assert output["error_type"] == "PilotLoadNotReadyError"
    assert "needs_warning_review" in output["message"]
    assert not approval_path.exists()


def test_pilot_cli_refuses_approval_output_for_missing_coverage(tmp_path, capsys):
    bundle_path = tmp_path / "pilot_bundle_missing_coverage.json"
    approval_path = tmp_path / "approval" / "sd_pilot_approval.json"
    bundle = {
        "source": make_source().model_dump(mode="json"),
        "manifest": make_manifest().model_dump(mode="json"),
        "quality_config": {
            "current_year": 2026,
            "expected_provinces": ["山东", "河南"],
            "expected_years": [2025],
        },
        "rows": [
            {
                "school_name": "山东大学",
                "major_name": None,
                "province": "山东",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 620,
            }
        ],
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    exit_code = pilot_cli_main(
        [
            "--approval-output",
            str(approval_path),
            str(bundle_path),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output["status"] == "error"
    assert output["error_type"] == "PilotLoadNotReadyError"
    assert "coverage_missing:province:河南" in output["message"]
    assert not approval_path.exists()


def test_pilot_cli_snapshot_dir_mode_checks_manifest_files(tmp_path, capsys):
    manifest = make_manifest()
    snapshot_dir = write_snapshot_dir(
        tmp_path,
        manifest,
        "school,score\n山东大学,620\n",
    )
    data_file = snapshot_dir / manifest.files[0].path
    data_file.write_text("changed after manifest\n", encoding="utf-8")
    bundle_path = tmp_path / "pilot_snapshot_bundle.json"
    bundle = {
        "source": make_source().model_dump(mode="json"),
        "quality_config": {"current_year": 2026},
        "rows": [
            {
                "school_name": "山东大学",
                "major_name": None,
                "province": "山东",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 620,
            }
        ],
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    exit_code = pilot_cli_main(
        [
            "--snapshot-dir",
            str(snapshot_dir),
            str(bundle_path),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["load_ready"] is False
    assert output["snapshot_file_issues"] == ["checksum mismatch: files/manual-sample.csv"]
    assert output["blockers"] == ["snapshot_file:checksum mismatch: files/manual-sample.csv"]


def test_pilot_cli_returns_nonzero_for_failed_quality_gate(tmp_path, capsys):
    bundle_path = tmp_path / "pilot_bundle_bad.json"
    bundle = {
        "source": make_source().model_dump(mode="json"),
        "manifest": make_manifest().model_dump(mode="json"),
        "rows": [
            {
                "school_name": "山东大学",
                "province": "山东",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 900,
            }
        ],
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    exit_code = pilot_cli_main([str(bundle_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["passed"] is False
    assert output["load_ready"] is False
    assert output["issue_counts"]["error"] == 1


def test_pilot_cli_returns_input_error_for_invalid_bundle(tmp_path, capsys):
    bundle_path = tmp_path / "pilot_bundle_invalid.json"
    bundle_path.write_text(
        json.dumps({"rows": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = pilot_cli_main([str(bundle_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output["status"] == "error"
    assert output["error_type"] == "ValidationError"
    assert "manifest" in output["message"]


def test_pilot_cli_returns_input_error_for_invalid_json(tmp_path, capsys):
    bundle_path = tmp_path / "pilot_bundle_invalid_json.json"
    bundle_path.write_text("{bad-json", encoding="utf-8")

    exit_code = pilot_cli_main([str(bundle_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output["status"] == "error"
    assert output["error_type"] == "JSONDecodeError"


def test_assert_load_ready_accepts_ready_result_and_audit_dict():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
        }
    ]

    result = run_manual_pilot(rows, make_manifest(), source=make_source())

    assert_load_ready(result)
    assert_load_ready(result.to_audit_dict())
    assert_loader_review_ready(result)
    assert_loader_review_ready(result.to_audit_dict())


def test_assert_loader_review_ready_blocks_warning_review_audit():
    audit = {
        "load_ready": True,
        "blockers": [],
        "review_status": "needs_warning_review",
    }

    with pytest.raises(PilotLoadNotReadyError) as exc_info:
        assert_loader_review_ready(audit)

    assert exc_info.value.blockers == ["review_status:needs_warning_review"]


def test_assert_load_ready_raises_with_blockers_for_failed_audit():
    rows = [
        {
            "school_name": "山东大学",
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 900,
        }
    ]
    audit = run_manual_pilot(rows, make_manifest()).to_audit_dict()

    with pytest.raises(PilotLoadNotReadyError) as exc_info:
        assert_load_ready(audit)

    assert exc_info.value.blockers == ["quality_error:value_out_of_range"]
    assert "quality_error:value_out_of_range" in str(exc_info.value)


def test_build_load_ready_candidates_returns_candidates_after_gate():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
        }
    ]

    candidates = build_load_ready_candidates(
        rows,
        make_manifest(),
        source=make_source(),
    )

    assert len(candidates) == 1
    assert candidates[0].entity_type == "admission_score"
    assert candidates[0].source.snapshot_id == "sd_pilot_2025_001"


def test_build_load_ready_candidates_blocks_failed_gate():
    rows = [
        {
            "school_name": "山东大学",
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 900,
        }
    ]

    with pytest.raises(PilotLoadNotReadyError) as exc_info:
        build_load_ready_candidates(rows, make_manifest())

    assert exc_info.value.blockers == ["quality_error:value_out_of_range"]


def test_build_load_ready_candidates_bundle_returns_candidates_after_gate():
    payload = {
        "source": make_source().model_dump(),
        "manifest": make_manifest().model_dump(),
        "rows": [
            {
                "school_name": "山东大学",
                "major_name": None,
                "province": "山东",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 620,
            }
        ],
    }

    candidates = build_load_ready_candidates_bundle(payload)

    assert len(candidates) == 1
    assert candidates[0].natural_key["school_name"] == "山东大学"


def test_build_load_ready_candidates_bundle_blocks_failed_gate():
    payload = {
        "source": make_source().model_dump(),
        "manifest": make_manifest().model_dump(),
        "rows": [
            {
                "school_name": "山东大学",
                "province": "山东",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 900,
            }
        ],
    }

    with pytest.raises(PilotLoadNotReadyError) as exc_info:
        build_load_ready_candidates_bundle(payload)

    assert exc_info.value.blockers == ["quality_error:value_out_of_range"]
