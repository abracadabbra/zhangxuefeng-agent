"""Pilot artifact manifest tests."""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.data_pipeline.pilots import build_pilot_artifact_manifest


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "real_data"
ARTIFACTS_DIR = EXAMPLES_DIR / "artifacts"


def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def make_source_audit():
    return {
        "scope": {
            "data_category": "admission_scores",
            "expected_provinces": ["山东"],
            "expected_years": [2025],
            "require_reviewed": True,
        },
        "passed": True,
        "issues": [],
    }


def make_intake_review():
    return {
        "action": "official_sample_intake_review",
        "passed": True,
        "ready_for_snapshot": True,
        "scope": {
            "source_id": "sd_exam_authority",
            "dataset": "admission_scores",
            "province": "山东",
            "published_year": 2025,
        },
        "issue_counts": {"error": 0, "warning": 0, "info": 0},
        "issues": [],
    }


def make_dry_run_audit():
    return {
        "snapshot_id": "sd_pilot_2025_001",
        "source_id": "sd_exam_authority",
        "dataset": "admission_scores",
        "candidate_count": 1,
        "passed": True,
        "load_ready": True,
        "blockers": [],
        "coverage": {
            "total": 1,
            "by_entity_type": {"admission_score": 1},
            "by_province": {"山东": 1},
            "by_year": {"2025": 1},
            "missing_expected_provinces": [],
            "missing_expected_years": [],
        },
        "issue_counts": {"error": 0, "warning": 0, "info": 0},
        "review_status": "ready_for_loader_review",
        "review_notes": ["dry-run passed with no blockers or warnings"],
    }


def make_loader_approval():
    return {
        "action": "canonical_loader_approval",
        "load_allowed": True,
        "parser_name": "ManualSampleParser",
        "parser_version": "0.1.0",
        "candidate_count": 1,
        "entity_counts": {"admission_score": 1},
        "source_id": "sd_exam_authority",
        "snapshot_id": "sd_pilot_2025_001",
        "dataset": "admission_scores",
    }


def test_build_pilot_artifact_manifest_marks_ready_bundle():
    manifest = build_pilot_artifact_manifest(
        source_audit=make_source_audit(),
        intake_review=make_intake_review(),
        dry_run_audit=make_dry_run_audit(),
        loader_approval=make_loader_approval(),
        source_audit_path="artifacts/real_data/sd_source_audit.json",
        intake_review_path="artifacts/real_data/sd_intake_review.json",
        dry_run_audit_path="artifacts/real_data/sd_dry_run_audit.json",
        loader_approval_path="artifacts/real_data/sd_loader_approval.json",
        rows_bundle_path="examples/real_data/sd_snapshot_pilot_rows.json",
        snapshot_dir="examples/real_data/snapshots/sd_pilot_2025_001",
        generated_at=datetime(2026, 6, 7, tzinfo=timezone.utc),
    ).to_review_dict()

    assert manifest["action"] == "real_data_pilot_artifact_manifest"
    assert manifest["generated_at"] == "2026-06-07T00:00:00Z"
    assert manifest["source_id"] == "sd_exam_authority"
    assert manifest["snapshot_id"] == "sd_pilot_2025_001"
    assert manifest["dataset"] == "admission_scores"
    assert manifest["candidate_count"] == 1
    assert manifest["ready_for_loader_execution"] is True
    assert manifest["artifact_paths"]["source_audit"].endswith("sd_source_audit.json")
    assert manifest["artifact_paths"]["intake_review"].endswith("sd_intake_review.json")
    assert manifest["intake_review_issues"] == []
    assert manifest["review_summary"]["source_issue_counts"] == {
        "error": 0,
        "warning": 0,
        "info": 0,
    }
    assert manifest["review_summary"]["source_audit_scope"] == {
        "data_category": "admission_scores",
        "expected_provinces": ["山东"],
        "expected_years": [2025],
        "require_reviewed": True,
    }
    assert manifest["review_summary"]["intake_review_passed"] is True
    assert manifest["review_summary"]["intake_ready_for_snapshot"] is True
    assert manifest["loader_handoff"] == {
        "recommended_entrypoint": "load_candidates_after_artifact_manifest",
        "artifact_manifest_ready": True,
        "requires_separate_loader_run_command": True,
        "does_not_authorize": [
            "crawler execution",
            "seed data modification",
            "RAG or Agent refresh",
            "production database writes without a separate run command",
        ],
    }
    assert manifest["required_reviews"] == [
        "Provide a separate approved loader run command."
    ]
    assert "Does not approve crawler execution." in manifest["non_goals"]


def test_static_shandong_artifact_manifest_matches_builder_output():
    manifest = build_pilot_artifact_manifest(
        source_audit=load_json(ARTIFACTS_DIR / "sd_source_audit.json"),
        intake_review=load_json(ARTIFACTS_DIR / "sd_intake_review.json"),
        dry_run_audit=load_json(ARTIFACTS_DIR / "sd_snapshot_pilot_audit.json"),
        loader_approval=load_json(
            ARTIFACTS_DIR / "sd_snapshot_pilot_approval.json"
        ),
        source_audit_path="examples/real_data/artifacts/sd_source_audit.json",
        intake_review_path="examples/real_data/artifacts/sd_intake_review.json",
        dry_run_audit_path=(
            "examples/real_data/artifacts/sd_snapshot_pilot_audit.json"
        ),
        loader_approval_path=(
            "examples/real_data/artifacts/sd_snapshot_pilot_approval.json"
        ),
        rows_bundle_path="examples/real_data/sd_snapshot_pilot_rows.json",
        snapshot_dir="examples/real_data/snapshots/sd_pilot_2025_001",
        generated_at=datetime(2026, 6, 7, tzinfo=timezone.utc),
    ).to_review_dict()

    static_manifest = load_json(
        ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"
    )

    assert manifest == static_manifest
    assert manifest["artifact_path_issues"] == []
    assert manifest["intake_review_issues"] == []
    assert manifest["artifact_scope_issues"] == []
    assert manifest["loader_approval_issues"] == []
    assert manifest["loader_handoff"][
        "requires_separate_loader_run_command"
    ] is True


def test_build_pilot_artifact_manifest_requires_intake_review():
    manifest = build_pilot_artifact_manifest(
        source_audit=make_source_audit(),
        dry_run_audit=make_dry_run_audit(),
        loader_approval=make_loader_approval(),
        source_audit_path="artifacts/real_data/sd_source_audit.json",
        dry_run_audit_path="artifacts/real_data/sd_dry_run_audit.json",
        loader_approval_path="artifacts/real_data/sd_loader_approval.json",
        rows_bundle_path="examples/real_data/sd_snapshot_pilot_rows.json",
    ).to_review_dict()

    assert manifest["ready_for_loader_execution"] is False
    assert manifest["intake_review_issues"] == [
        "missing intake readiness review"
    ]
    assert manifest["required_reviews"] == [
        "Generate and review intake readiness report."
    ]


def test_build_pilot_artifact_manifest_blocks_failed_intake_review():
    intake_review = make_intake_review()
    intake_review["passed"] = False
    intake_review["ready_for_snapshot"] = False
    intake_review["issues"] = [
        {
            "severity": "error",
            "code": "source_review_not_ready",
            "message": "source_review.review_status must be reviewed",
            "field": "source_review.review_status",
        }
    ]

    manifest = build_pilot_artifact_manifest(
        source_audit=make_source_audit(),
        intake_review=intake_review,
        dry_run_audit=make_dry_run_audit(),
        loader_approval=make_loader_approval(),
        source_audit_path="artifacts/real_data/sd_source_audit.json",
        intake_review_path="artifacts/real_data/sd_intake_review.json",
        dry_run_audit_path="artifacts/real_data/sd_dry_run_audit.json",
        loader_approval_path="artifacts/real_data/sd_loader_approval.json",
        rows_bundle_path="examples/real_data/sd_snapshot_pilot_rows.json",
    ).to_review_dict()

    assert manifest["ready_for_loader_execution"] is False
    assert manifest["intake_review_issues"] == [
        "intake review did not pass",
        "intake review is not ready for snapshot",
        "intake review has error issues",
    ]
    assert manifest["required_reviews"] == [
        "Resolve intake readiness review issues."
    ]


def test_build_pilot_artifact_manifest_requires_missing_reviews():
    source_audit = {
        "scope": {
            "data_category": "admission_scores",
            "expected_provinces": ["山东"],
            "expected_years": [2025],
            "require_reviewed": True,
        },
        "passed": True,
        "issues": [
            {
                "severity": "warning",
                "code": "source_not_reviewed",
                "message": "source is not reviewed or approved: sd_exam_authority",
                "source_id": "sd_exam_authority",
            }
        ],
    }
    dry_run_audit = make_dry_run_audit()
    dry_run_audit["load_ready"] = False
    dry_run_audit["review_status"] = "blocked"
    dry_run_audit["blockers"] = ["coverage_missing:province:河南"]

    manifest = build_pilot_artifact_manifest(
        source_audit=source_audit,
        intake_review=make_intake_review(),
        dry_run_audit=dry_run_audit,
        source_audit_path="artifacts/real_data/sd_source_audit.json",
        intake_review_path="artifacts/real_data/sd_intake_review.json",
        dry_run_audit_path="artifacts/real_data/sd_dry_run_audit.json",
        rows_bundle_path="examples/real_data/sd_snapshot_pilot_rows.json",
    ).to_review_dict()

    assert manifest["ready_for_loader_execution"] is False
    assert manifest["review_summary"]["source_issue_counts"]["warning"] == 1
    assert manifest["review_summary"]["dry_run_blockers"] == [
        "coverage_missing:province:河南"
    ]
    assert manifest["required_reviews"] == [
        "Review source registry audit warnings.",
        "Resolve dry-run blockers before loader approval.",
        "Complete dry-run review before loader approval.",
        "Generate and review loader approval packet.",
    ]


def test_build_pilot_artifact_manifest_blocks_source_warnings_when_otherwise_ready():
    source_audit = {
        "scope": {
            "data_category": "admission_scores",
            "expected_provinces": ["山东"],
            "expected_years": [2025],
            "require_reviewed": True,
        },
        "passed": True,
        "issues": [
            {
                "severity": "warning",
                "code": "source_years_not_registered",
                "message": "source has no registered coverage years: sd_exam_authority",
                "source_id": "sd_exam_authority",
            }
        ],
    }

    manifest = build_pilot_artifact_manifest(
        source_audit=source_audit,
        intake_review=make_intake_review(),
        dry_run_audit=make_dry_run_audit(),
        loader_approval=make_loader_approval(),
        source_audit_path="artifacts/real_data/sd_source_audit.json",
        intake_review_path="artifacts/real_data/sd_intake_review.json",
        dry_run_audit_path="artifacts/real_data/sd_dry_run_audit.json",
        loader_approval_path="artifacts/real_data/sd_loader_approval.json",
        rows_bundle_path="examples/real_data/sd_snapshot_pilot_rows.json",
    ).to_review_dict()

    assert manifest["ready_for_loader_execution"] is False
    assert manifest["required_reviews"] == [
        "Review source registry audit warnings."
    ]


def test_build_pilot_artifact_manifest_blocks_artifact_path_issues():
    manifest = build_pilot_artifact_manifest(
        source_audit=make_source_audit(),
        intake_review=make_intake_review(),
        dry_run_audit=make_dry_run_audit(),
        loader_approval=make_loader_approval(),
        source_audit_path="artifacts/real_data/sd_source_audit.json",
        intake_review_path="artifacts/real_data/sd_intake_review.json",
        dry_run_audit_path="artifacts/real_data/sd_dry_run_audit.json",
        loader_approval_path="artifacts/real_data/sd_loader_approval.json",
        rows_bundle_path="missing_rows.json",
        artifact_path_issues=["missing file: rows_bundle:missing_rows.json"],
    ).to_review_dict()

    assert manifest["ready_for_loader_execution"] is False
    assert manifest["artifact_path_issues"] == [
        "missing file: rows_bundle:missing_rows.json"
    ]
    assert manifest["required_reviews"] == [
        "Resolve artifact path issues."
    ]


def test_build_pilot_artifact_manifest_blocks_scope_mismatch():
    source_audit = make_source_audit()
    dry_run_audit = make_dry_run_audit()
    dry_run_audit["coverage"]["by_province"] = {"河南": 1}

    manifest = build_pilot_artifact_manifest(
        source_audit=source_audit,
        intake_review=make_intake_review(),
        dry_run_audit=dry_run_audit,
        loader_approval=make_loader_approval(),
        source_audit_path="artifacts/real_data/sd_source_audit.json",
        intake_review_path="artifacts/real_data/sd_intake_review.json",
        dry_run_audit_path="artifacts/real_data/sd_dry_run_audit.json",
        loader_approval_path="artifacts/real_data/sd_loader_approval.json",
        rows_bundle_path="examples/real_data/sd_snapshot_pilot_rows.json",
    ).to_review_dict()

    assert manifest["ready_for_loader_execution"] is False
    assert manifest["artifact_scope_issues"] == [
        "source audit province is missing from dry-run coverage: 山东"
    ]
    assert manifest["required_reviews"] == [
        "Resolve artifact scope issues."
    ]


def test_build_pilot_artifact_manifest_blocks_loader_approval_mismatch():
    loader_approval = make_loader_approval()
    loader_approval["snapshot_id"] = "other_snapshot"

    manifest = build_pilot_artifact_manifest(
        source_audit=make_source_audit(),
        intake_review=make_intake_review(),
        dry_run_audit=make_dry_run_audit(),
        loader_approval=loader_approval,
        source_audit_path="artifacts/real_data/sd_source_audit.json",
        intake_review_path="artifacts/real_data/sd_intake_review.json",
        dry_run_audit_path="artifacts/real_data/sd_dry_run_audit.json",
        loader_approval_path="artifacts/real_data/sd_loader_approval.json",
        rows_bundle_path="examples/real_data/sd_snapshot_pilot_rows.json",
    ).to_review_dict()

    assert manifest["ready_for_loader_execution"] is False
    assert manifest["loader_approval_issues"] == [
        "loader approval field does not match dry-run audit: "
        "snapshot_id=other_snapshot != sd_pilot_2025_001"
    ]
    assert manifest["required_reviews"] == [
        "Resolve loader approval consistency issues."
    ]
