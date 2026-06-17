import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.real_data import cli
from backend.real_data.parser import build_raw_admission_row
from backend.real_data.pilot import write_reviewed_raw_rows_artifact
from backend.real_data.source_registry import (
    HENAN_2025_UNDERGRAD_PARALLEL_PAGE,
    build_manual_snapshot,
    sha256_bytes,
)


def _snapshot(snapshot_id: str = "ha-2025-undergrad-physical-cli-sample"):
    return build_manual_snapshot(
        source_page=HENAN_2025_UNDERGRAD_PARALLEL_PAGE,
        raw_file_name="henan-2025-undergrad-physical-reviewed-sample.html",
        raw_file_url=(
            "https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?"
            "yearTip=2025&pc=1&kl=5"
        ),
        raw_file_sha256=sha256_bytes(b"reviewed henan cli sample"),
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


def _base_args(raw_artifact_path: Path, output_dir: Path) -> list[str]:
    return [
        "bundle-dry-run",
        "--reviewed-rows-artifact",
        str(raw_artifact_path),
        "--output-dir",
        str(output_dir),
        "--province",
        "河南",
        "--year",
        "2025",
        "--batch",
        "本科批",
        "--subject-type",
        "物理类",
        "--expected-school",
        "郑州大学",
    ]


def test_bundle_dry_run_cli_outputs_auditable_summary(tmp_path: Path, capsys):
    snapshot = _snapshot()
    raw_artifact = _write_reviewed_artifact(tmp_path, [_reviewed_row(snapshot)])

    exit_code = cli.main(_base_args(raw_artifact.artifact_path, tmp_path / "bundle"))

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["quality_status"] == "pass"
    assert output["quality_report_id"] == f"{snapshot.snapshot_id}-quality"
    assert output["schema_status"] == "pass"
    assert output["source"] == {
        "province": "河南",
        "source_name": "河南省教育考试院",
        "source_page_id": "ha-2025-undergrad-parallel-page",
        "source_type": "official_exam_authority",
        "source_url": "https://gaokao.haedu.cn/517/518/519/2025/1207/150720.html",
        "year": 2025,
    }
    assert output["snapshot"] == {
        "captured_at": "2026-06-09T17:30:00+00:00",
        "operator": "codex",
        "raw_file_name": "henan-2025-undergrad-physical-reviewed-sample.html",
        "raw_file_sha256": sha256_bytes(b"reviewed henan cli sample"),
        "raw_file_url": (
            "https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?"
            "yearTip=2025&pc=1&kl=5"
        ),
        "snapshot_id": snapshot.snapshot_id,
        "source_batch_id": "河南-2025-manual",
    }
    assert output["record_count_raw"] == 1
    assert output["record_count_parsed"] == 1
    assert output["record_count_passed"] == 1
    assert output["coverage"] == {
        "expected_min_records": 1,
        "expected_schools": ["郑州大学"],
        "missing_schools": [],
        "observed_records": 1,
        "observed_schools": ["郑州大学"],
    }
    assert output["freshness_result"] == "published_in_admission_year"
    assert output["confidence_summary"] == {"high": 1, "low": 0, "medium": 0}
    assert output["issues"] == {
        "cross_source_conflicts": [],
        "duplicate_conflicts": [],
        "field_errors": [],
        "range_errors": [],
        "warnings": [],
    }
    assert output["manifest_artifact_count"] == 1
    assert output["citation_record_count"] == 1
    assert Path(output["staging_artifact_path"]).exists()
    assert Path(output["manifest_path"]).exists()
    assert output["sample_citation"]["source"] == "河南省教育考试院"
    assert output["sample_citation"]["snapshot_url"] == snapshot.raw_file_url
    assert output["sample_citation"]["confidence"] == "high"


def test_bundle_dry_run_cli_runs_documented_fixture(tmp_path: Path, capsys):
    fixture_path = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")

    exit_code = cli.main(_base_args(fixture_path, tmp_path / "bundle"))

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["quality_status"] == "pass"
    assert output["schema_status"] == "pass"
    assert output["record_count_raw"] == 1
    assert output["record_count_parsed"] == 1
    assert output["record_count_passed"] == 1
    assert output["coverage"]["observed_schools"] == ["郑州大学"]
    assert output["confidence_summary"] == {"high": 1, "low": 0, "medium": 0}
    assert output["issues"]["field_errors"] == []
    assert output["manifest_artifact_count"] == 1
    assert output["citation_record_count"] == 1
    assert Path(output["staging_artifact_path"]).exists()
    assert Path(output["manifest_path"]).exists()
    assert output["sample_citation"] == {
        "confidence": "high",
        "snapshot": "ha-2025-undergrad-physical-dry-run-fixture",
        "snapshot_url": (
            "https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?"
            "yearTip=2025&pc=1&kl=5"
        ),
        "source": "河南省教育考试院",
        "source_batch_id": "河南-2025-manual",
        "source_url": "https://gaokao.haedu.cn/517/518/519/2025/1207/150720.html",
        "year": 2025,
    }


def test_bundle_dry_run_cli_reports_blocked_without_downstream_manifest(tmp_path: Path, capsys):
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

    exit_code = cli.main(_base_args(raw_artifact.artifact_path, tmp_path / "bundle"))

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["quality_status"] == "blocked"
    assert output["quality_report_id"] == f"{snapshot.snapshot_id}-quality"
    assert output["schema_status"] == "blocked"
    assert output["source"]["source_name"] == "河南省教育考试院"
    assert output["snapshot"]["snapshot_id"] == snapshot.snapshot_id
    assert output["snapshot"]["raw_file_sha256"] == sha256_bytes(b"reviewed henan cli sample")
    assert output["record_count_passed"] == 0
    assert output["blocked_reasons"] == ["missing_source_schema_field", "no parsed candidates"]
    assert output["confidence_summary"] == {"high": 0, "low": 0, "medium": 0}
    assert output["issues"]["field_errors"] == [
        {
            "code": "missing_source_schema_field",
            "level": "error",
            "message": "source schema is missing required field min_score",
            "raw_row_number": None,
        }
    ]
    assert output["issues"]["warnings"] == [
        {
            "code": "pilot_school_coverage_gap",
            "level": "warning",
            "message": "missing pilot schools: 郑州大学",
            "raw_row_number": None,
        },
        {
            "code": "record_coverage_gap",
            "level": "warning",
            "message": "parsed candidate count is below pilot expectation",
            "raw_row_number": None,
        }
    ]
    assert output["staging_artifact_path"] is None
    assert output["manifest_path"] is None
    assert output["manifest_artifact_count"] == 0
    assert output["citation_record_count"] == 0
    assert list((tmp_path / "bundle").rglob("*.json")) == []


def test_bundle_dry_run_cli_rejects_tampered_reviewed_artifact(tmp_path: Path, capsys):
    snapshot = _snapshot()
    raw_artifact = _write_reviewed_artifact(tmp_path, [_reviewed_row(snapshot)])
    payload = json.loads(raw_artifact.artifact_path.read_text(encoding="utf-8"))
    payload["rows"][0]["snapshot_id"] = "tampered"
    raw_artifact.artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    exit_code = cli.main(_base_args(raw_artifact.artifact_path, tmp_path / "bundle"))

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "real-data dry-run failed" in captured.err
    assert list((tmp_path / "bundle").rglob("*.json")) == []


def test_bundle_dry_run_cli_blocks_reference_manifest_conflict(tmp_path: Path, capsys):
    reference_snapshot = _snapshot("ha-2025-cli-reference")
    reference_raw = _write_reviewed_artifact(
        tmp_path / "reference",
        [_reviewed_row(reference_snapshot, min_score="600")],
        snapshot=reference_snapshot,
    )
    reference_dir = tmp_path / "reference_bundle"
    assert cli.main(_base_args(reference_raw.artifact_path, reference_dir)) == 0
    capsys.readouterr()

    candidate_snapshot = _snapshot("ha-2025-cli-conflict")
    candidate_raw = _write_reviewed_artifact(
        tmp_path / "candidate",
        [_reviewed_row(candidate_snapshot, min_score="601")],
        snapshot=candidate_snapshot,
    )
    args = _base_args(candidate_raw.artifact_path, tmp_path / "candidate_bundle")
    args.extend(["--reference-manifest", str(reference_dir / "staging_manifest.json")])

    exit_code = cli.main(args)
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["quality_status"] == "blocked"
    assert output["record_count_passed"] == 0
    assert output["issues"]["cross_source_conflicts"][0]["code"] == "cross_source_conflict"
    assert "min_score" in output["issues"]["cross_source_conflicts"][0]["message"]
    assert output["staging_artifact_path"] is None
    assert output["manifest_path"] is None
    assert output["citation_record_count"] == 0
    assert list((tmp_path / "candidate_bundle").rglob("*.json")) == []


def test_bundle_dry_run_cli_rejects_missing_required_args():
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["bundle-dry-run"])

    assert exc_info.value.code == 2


def _approval_args(manifest_path: Path, approval_path: Path) -> list[str]:
    return [
        "approve-manifest",
        "--manifest",
        str(manifest_path),
        "--approval-output",
        str(approval_path),
        "--reviewer",
        "codex-reviewer",
        "--reviewed-at",
        "2026-06-09T18:00:00+00:00",
        "--decision",
        "approved",
        "--source-verified",
        "--snapshot-verified",
        "--quality-reviewed",
        "--citation-reviewed",
        "--no-production-writes-verified",
    ]


def test_approval_cli_writes_and_verifies_manual_approval(tmp_path: Path, capsys):
    fixture_path = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")
    bundle_dir = tmp_path / "bundle"
    assert cli.main(_base_args(fixture_path, bundle_dir)) == 0
    capsys.readouterr()
    manifest_path = bundle_dir / "staging_manifest.json"
    approval_path = tmp_path / "approval.json"

    write_exit = cli.main(_approval_args(manifest_path, approval_path))
    write_output = json.loads(capsys.readouterr().out)

    assert write_exit == 0
    assert approval_path.exists()
    assert write_output["decision"] == "approved"
    assert write_output["citation_record_count"] == 1
    assert write_output["checklist"]["no_production_writes_verified"] is True

    verify_exit = cli.main(["verify-approval", "--approval-artifact", str(approval_path)])
    verify_output = json.loads(capsys.readouterr().out)

    assert verify_exit == 0
    assert verify_output == write_output


def test_approval_cli_rejects_approved_manifest_without_full_checklist(
    tmp_path: Path,
    capsys,
):
    fixture_path = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")
    bundle_dir = tmp_path / "bundle"
    assert cli.main(_base_args(fixture_path, bundle_dir)) == 0
    capsys.readouterr()
    manifest_path = bundle_dir / "staging_manifest.json"
    approval_path = tmp_path / "approval.json"
    args = _approval_args(manifest_path, approval_path)
    args.remove("--citation-reviewed")

    exit_code = cli.main(args)
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "real-data approval failed" in captured.err
    assert not approval_path.exists()


def test_approval_cli_rejects_approved_warning_manifest_without_notes(
    tmp_path: Path,
    capsys,
):
    fixture_path = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")
    bundle_dir = tmp_path / "warning_bundle"
    bundle_args = _base_args(fixture_path, bundle_dir)
    bundle_args.extend(["--expected-school", "河南大学"])
    assert cli.main(bundle_args) == 0
    bundle_output = json.loads(capsys.readouterr().out)
    assert bundle_output["quality_status"] == "warning"
    assert bundle_output["issues"]["warnings"][0]["code"] == "pilot_school_coverage_gap"
    manifest_path = bundle_dir / "staging_manifest.json"
    approval_path = tmp_path / "approval.json"

    exit_code = cli.main(_approval_args(manifest_path, approval_path))
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "real-data approval failed" in captured.err
    assert not approval_path.exists()

    args_with_notes = _approval_args(manifest_path, approval_path)
    args_with_notes.extend(
        ["--notes", "warning reviewed: pilot coverage gap accepted for dry-run sample"]
    )
    write_exit = cli.main(args_with_notes)
    write_output = json.loads(capsys.readouterr().out)

    assert write_exit == 0
    assert approval_path.exists()
    assert write_output["decision"] == "approved"
    assert write_output["notes"].startswith("warning reviewed")


def test_query_approved_cli_returns_citation_records(tmp_path: Path, capsys):
    fixture_path = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")
    bundle_dir = tmp_path / "bundle"
    assert cli.main(_base_args(fixture_path, bundle_dir)) == 0
    capsys.readouterr()
    approval_path = tmp_path / "approval.json"
    assert cli.main(_approval_args(bundle_dir / "staging_manifest.json", approval_path)) == 0
    capsys.readouterr()

    exit_code = cli.main(
        [
            "query-approved",
            "--approval-artifact",
            str(approval_path),
            "--province",
            "河南",
            "--year",
            "2025",
            "--school-name",
            "郑州大学",
            "--major-keyword",
            "计算机",
            "--min-score-at-least",
            "600",
            "--min-score-at-most",
            "600",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["total"] == 1
    assert output["records"][0]["school_name"] == "郑州大学"
    assert output["records"][0]["major_or_group_name"] == "计算机类"
    assert output["records"][0]["min_score"] == 600
    assert output["records"][0]["source"] == "河南省教育考试院"
    assert output["records"][0]["source_url"] == (
        "https://gaokao.haedu.cn/517/518/519/2025/1207/150720.html"
    )
    assert output["records"][0]["snapshot_url"] == (
        "https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?"
        "yearTip=2025&pc=1&kl=5"
    )
    assert output["records"][0]["confidence"] == "high"


def test_query_approved_cli_blocks_rejected_approval(tmp_path: Path, capsys):
    fixture_path = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")
    bundle_dir = tmp_path / "bundle"
    assert cli.main(_base_args(fixture_path, bundle_dir)) == 0
    capsys.readouterr()
    approval_path = tmp_path / "approval.json"
    rejected_args = _approval_args(bundle_dir / "staging_manifest.json", approval_path)
    rejected_args[rejected_args.index("approved")] = "rejected"
    rejected_args.remove("--citation-reviewed")
    assert cli.main(rejected_args) == 0
    capsys.readouterr()

    exit_code = cli.main(["query-approved", "--approval-artifact", str(approval_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "real-data approved query failed" in captured.err


def test_audit_approved_cli_outputs_chain_evidence(tmp_path: Path, capsys):
    fixture_path = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")
    bundle_dir = tmp_path / "bundle"
    assert cli.main(_base_args(fixture_path, bundle_dir)) == 0
    capsys.readouterr()
    approval_path = tmp_path / "approval.json"
    assert cli.main(_approval_args(bundle_dir / "staging_manifest.json", approval_path)) == 0
    capsys.readouterr()

    exit_code = cli.main(["audit-approved", "--approval-artifact", str(approval_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["approval_artifact_path"] == str(approval_path)
    assert output["approval"]["decision"] == "approved"
    assert output["manifest_path"] == str(bundle_dir / "staging_manifest.json")
    assert output["manifest_artifact_count"] == 1
    assert output["citation_record_count"] == 1
    assert output["artifact_summaries"][0]["quality_status"] == "pass"
    assert (
        output["artifact_summaries"][0]["quality_report_id"]
        == "ha-2025-undergrad-physical-dry-run-fixture-quality"
    )
    assert output["artifact_summaries"][0]["record_count_raw"] == 1
    assert output["artifact_summaries"][0]["record_count_parsed"] == 1
    assert output["artifact_summaries"][0]["record_count_passed"] == 1
    assert output["artifact_summaries"][0]["coverage"]["observed_schools"] == ["郑州大学"]
    assert output["artifact_summaries"][0]["confidence_summary"] == {
        "high": 1,
        "low": 0,
        "medium": 0,
    }
    assert output["artifact_summaries"][0]["warning_issues"] == []
    assert output["artifact_summaries"][0]["source"] == "河南省教育考试院"
    assert output["artifact_summaries"][0]["source_url"] == (
        "https://gaokao.haedu.cn/517/518/519/2025/1207/150720.html"
    )
    assert output["artifact_summaries"][0]["snapshot_url"] == (
        "https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?"
        "yearTip=2025&pc=1&kl=5"
    )
    assert output["artifact_summaries"][0]["raw_file_sha256"] == (
        "6e17df3513033fc17aa8289e7e026a9eaaa3835cd4f8739ccf77772b0fe93c1d"
    )
    assert output["artifact_summaries"][0]["captured_at"] == "2026-06-09T17:30:00+00:00"
    assert output["artifact_summaries"][0]["operator"] == "codex-fixture"
    assert output["sample_citation_record"]["source"] == "河南省教育考试院"
    assert output["sample_citation_record"]["confidence"] == "high"


def test_audit_approved_cli_outputs_warning_notes_and_issues(tmp_path: Path, capsys):
    fixture_path = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")
    bundle_dir = tmp_path / "warning_bundle"
    bundle_args = _base_args(fixture_path, bundle_dir)
    bundle_args.extend(["--expected-school", "河南大学"])
    assert cli.main(bundle_args) == 0
    bundle_output = json.loads(capsys.readouterr().out)
    assert bundle_output["quality_status"] == "warning"
    approval_path = tmp_path / "approval.json"
    approval_args = _approval_args(bundle_dir / "staging_manifest.json", approval_path)
    approval_args.extend(
        ["--notes", "warning reviewed: pilot coverage gap accepted for dry-run sample"]
    )
    assert cli.main(approval_args) == 0
    capsys.readouterr()

    exit_code = cli.main(["audit-approved", "--approval-artifact", str(approval_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["approval"]["decision"] == "approved"
    assert output["approval"]["notes"].startswith("warning reviewed")
    assert output["artifact_summaries"][0]["quality_status"] == "warning"
    assert (
        output["artifact_summaries"][0]["quality_report_id"]
        == "ha-2025-undergrad-physical-dry-run-fixture-quality"
    )
    assert output["artifact_summaries"][0]["warning_issues"][0]["code"] == (
        "pilot_school_coverage_gap"
    )


def test_audit_approved_cli_blocks_rejected_approval(tmp_path: Path, capsys):
    fixture_path = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")
    bundle_dir = tmp_path / "bundle"
    assert cli.main(_base_args(fixture_path, bundle_dir)) == 0
    capsys.readouterr()
    approval_path = tmp_path / "approval.json"
    rejected_args = _approval_args(bundle_dir / "staging_manifest.json", approval_path)
    rejected_args[rejected_args.index("approved")] = "rejected"
    rejected_args.remove("--citation-reviewed")
    assert cli.main(rejected_args) == 0
    capsys.readouterr()

    exit_code = cli.main(["audit-approved", "--approval-artifact", str(approval_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "real-data approved audit failed" in captured.err
