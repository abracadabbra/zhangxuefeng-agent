"""Pilot artifact manifest CLI tests."""

import json

from backend.data_pipeline.pilots.artifacts_cli import main as artifacts_cli_main


def write_json(tmp_path, name: str, payload: dict):
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


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


def make_source_audit_with_warning():
    return {
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


def make_dry_run_audit(*, load_ready: bool = True):
    return {
        "snapshot_id": "sd_pilot_2025_001",
        "source_id": "sd_exam_authority",
        "dataset": "admission_scores",
        "candidate_count": 1,
        "passed": load_ready,
        "load_ready": load_ready,
        "blockers": [] if load_ready else ["coverage_missing:province:河南"],
        "coverage": {
            "total": 1,
            "by_entity_type": {"admission_score": 1},
            "by_province": {"山东": 1} if load_ready else {},
            "by_year": {"2025": 1},
            "missing_expected_provinces": [] if load_ready else ["河南"],
            "missing_expected_years": [],
        },
        "issue_counts": {"error": 0, "warning": 0, "info": 0},
        "review_status": (
            "ready_for_loader_review"
            if load_ready
            else "blocked"
        ),
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


def test_artifacts_cli_prints_ready_manifest(tmp_path, capsys):
    source_audit_path = write_json(tmp_path, "source_audit.json", make_source_audit())
    intake_review_path = write_json(tmp_path, "intake_review.json", make_intake_review())
    dry_run_audit_path = write_json(
        tmp_path,
        "dry_run_audit.json",
        make_dry_run_audit(),
    )
    loader_approval_path = write_json(
        tmp_path,
        "loader_approval.json",
        make_loader_approval(),
    )

    exit_code = artifacts_cli_main(
        [
            "--source-audit",
            str(source_audit_path),
            "--intake-review",
            str(intake_review_path),
            "--dry-run-audit",
            str(dry_run_audit_path),
            "--loader-approval",
            str(loader_approval_path),
            "--rows-bundle",
            "examples/real_data/sd_snapshot_pilot_rows.json",
            "--snapshot-dir",
            "examples/real_data/snapshots/sd_pilot_2025_001",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["ready_for_loader_execution"] is True
    assert output["artifact_paths"]["intake_review"] == str(intake_review_path)
    assert output["artifact_paths"]["loader_approval"] == str(loader_approval_path)


def test_artifacts_cli_returns_nonzero_when_not_ready(tmp_path, capsys):
    source_audit_path = write_json(tmp_path, "source_audit.json", make_source_audit())
    intake_review_path = write_json(tmp_path, "intake_review.json", make_intake_review())
    dry_run_audit_path = write_json(
        tmp_path,
        "dry_run_audit.json",
        make_dry_run_audit(load_ready=False),
    )

    exit_code = artifacts_cli_main(
        [
            "--source-audit",
            str(source_audit_path),
            "--intake-review",
            str(intake_review_path),
            "--dry-run-audit",
            str(dry_run_audit_path),
            "--rows-bundle",
            "examples/real_data/sd_snapshot_pilot_rows.json",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["ready_for_loader_execution"] is False
    assert output["required_reviews"] == [
        "Resolve artifact scope issues.",
        "Resolve dry-run blockers before loader approval.",
        "Complete dry-run review before loader approval.",
        "Generate and review loader approval packet.",
    ]


def test_artifacts_cli_returns_nonzero_without_intake_review(tmp_path, capsys):
    source_audit_path = write_json(tmp_path, "source_audit.json", make_source_audit())
    dry_run_audit_path = write_json(
        tmp_path,
        "dry_run_audit.json",
        make_dry_run_audit(),
    )
    loader_approval_path = write_json(
        tmp_path,
        "loader_approval.json",
        make_loader_approval(),
    )

    exit_code = artifacts_cli_main(
        [
            "--source-audit",
            str(source_audit_path),
            "--dry-run-audit",
            str(dry_run_audit_path),
            "--loader-approval",
            str(loader_approval_path),
            "--rows-bundle",
            "examples/real_data/sd_snapshot_pilot_rows.json",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["ready_for_loader_execution"] is False
    assert output["intake_review_issues"] == [
        "missing intake readiness review"
    ]
    assert output["required_reviews"] == [
        "Generate and review intake readiness report."
    ]


def test_artifacts_cli_returns_nonzero_for_source_warning(tmp_path, capsys):
    source_audit_path = write_json(
        tmp_path,
        "source_audit.json",
        make_source_audit_with_warning(),
    )
    intake_review_path = write_json(tmp_path, "intake_review.json", make_intake_review())
    dry_run_audit_path = write_json(
        tmp_path,
        "dry_run_audit.json",
        make_dry_run_audit(),
    )
    loader_approval_path = write_json(
        tmp_path,
        "loader_approval.json",
        make_loader_approval(),
    )

    exit_code = artifacts_cli_main(
        [
            "--source-audit",
            str(source_audit_path),
            "--intake-review",
            str(intake_review_path),
            "--dry-run-audit",
            str(dry_run_audit_path),
            "--loader-approval",
            str(loader_approval_path),
            "--rows-bundle",
            "examples/real_data/sd_snapshot_pilot_rows.json",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["ready_for_loader_execution"] is False
    assert output["required_reviews"] == [
        "Review source registry audit warnings."
    ]


def test_artifacts_cli_returns_nonzero_for_missing_rows_bundle(tmp_path, capsys):
    source_audit_path = write_json(tmp_path, "source_audit.json", make_source_audit())
    intake_review_path = write_json(tmp_path, "intake_review.json", make_intake_review())
    dry_run_audit_path = write_json(
        tmp_path,
        "dry_run_audit.json",
        make_dry_run_audit(),
    )
    loader_approval_path = write_json(
        tmp_path,
        "loader_approval.json",
        make_loader_approval(),
    )
    missing_rows_path = tmp_path / "missing_rows.json"

    exit_code = artifacts_cli_main(
        [
            "--source-audit",
            str(source_audit_path),
            "--intake-review",
            str(intake_review_path),
            "--dry-run-audit",
            str(dry_run_audit_path),
            "--loader-approval",
            str(loader_approval_path),
            "--rows-bundle",
            str(missing_rows_path),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["ready_for_loader_execution"] is False
    assert output["artifact_path_issues"] == [
        f"missing file: rows_bundle:{missing_rows_path}"
    ]
    assert output["required_reviews"] == ["Resolve artifact path issues."]


def test_artifacts_cli_returns_nonzero_for_scope_mismatch(tmp_path, capsys):
    source_audit = make_source_audit()
    source_audit["scope"]["expected_years"] = [2024]
    source_audit_path = write_json(tmp_path, "source_audit.json", source_audit)
    intake_review_path = write_json(tmp_path, "intake_review.json", make_intake_review())
    dry_run_audit_path = write_json(
        tmp_path,
        "dry_run_audit.json",
        make_dry_run_audit(),
    )
    loader_approval_path = write_json(
        tmp_path,
        "loader_approval.json",
        make_loader_approval(),
    )

    exit_code = artifacts_cli_main(
        [
            "--source-audit",
            str(source_audit_path),
            "--intake-review",
            str(intake_review_path),
            "--dry-run-audit",
            str(dry_run_audit_path),
            "--loader-approval",
            str(loader_approval_path),
            "--rows-bundle",
            "examples/real_data/sd_snapshot_pilot_rows.json",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["ready_for_loader_execution"] is False
    assert output["artifact_scope_issues"] == [
        "source audit year is missing from dry-run coverage: 2024"
    ]
    assert output["required_reviews"] == ["Resolve artifact scope issues."]


def test_artifacts_cli_returns_nonzero_for_loader_approval_mismatch(tmp_path, capsys):
    loader_approval = make_loader_approval()
    loader_approval["candidate_count"] = 2
    source_audit_path = write_json(tmp_path, "source_audit.json", make_source_audit())
    intake_review_path = write_json(tmp_path, "intake_review.json", make_intake_review())
    dry_run_audit_path = write_json(
        tmp_path,
        "dry_run_audit.json",
        make_dry_run_audit(),
    )
    loader_approval_path = write_json(
        tmp_path,
        "loader_approval.json",
        loader_approval,
    )

    exit_code = artifacts_cli_main(
        [
            "--source-audit",
            str(source_audit_path),
            "--intake-review",
            str(intake_review_path),
            "--dry-run-audit",
            str(dry_run_audit_path),
            "--loader-approval",
            str(loader_approval_path),
            "--rows-bundle",
            "examples/real_data/sd_snapshot_pilot_rows.json",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["ready_for_loader_execution"] is False
    assert output["loader_approval_issues"] == [
        "loader approval field does not match dry-run audit: "
        "candidate_count=2 != 1"
    ]
    assert output["required_reviews"] == [
        "Resolve loader approval consistency issues."
    ]


def test_artifacts_cli_writes_optional_manifest_output(tmp_path, capsys):
    source_audit_path = write_json(tmp_path, "source_audit.json", make_source_audit())
    intake_review_path = write_json(tmp_path, "intake_review.json", make_intake_review())
    dry_run_audit_path = write_json(
        tmp_path,
        "dry_run_audit.json",
        make_dry_run_audit(),
    )
    loader_approval_path = write_json(
        tmp_path,
        "loader_approval.json",
        make_loader_approval(),
    )
    manifest_path = tmp_path / "artifacts" / "pilot_manifest.json"

    exit_code = artifacts_cli_main(
        [
            "--source-audit",
            str(source_audit_path),
            "--intake-review",
            str(intake_review_path),
            "--dry-run-audit",
            str(dry_run_audit_path),
            "--loader-approval",
            str(loader_approval_path),
            "--rows-bundle",
            "examples/real_data/sd_snapshot_pilot_rows.json",
            "--manifest-output",
            str(manifest_path),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert file_payload == stdout_payload
