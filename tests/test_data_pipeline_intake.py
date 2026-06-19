"""Official sample intake review tests."""

import json

from backend.data_pipeline.intake.cli import main as intake_cli_main
from backend.data_pipeline.intake.review import review_intake_payload


def make_ready_intake() -> dict:
    return {
        "not_a_dry_run_bundle": True,
        "pilot_scope": {
            "source_id": "sd_exam_authority",
            "dataset": "admission_scores",
            "province": "山东",
            "published_year": 2025,
        },
        "source_review": {
            "dataset_page_url": "https://www.sdzk.cn/NewsInfo.aspx?NewsID=7010",
            "attachment_url": "",
            "data_category_confirmed": True,
            "license_or_citation_notes": "Internal review only; no redistribution.",
            "review_status": "reviewed",
            "reviewed_by": "reviewer-a",
            "reviewed_at": "2026-06-07",
        },
        "snapshot_planning_review": {
            "action": "source_snapshot_planning_review",
            "passed": True,
            "ready_for_snapshot_planning": True,
            "scope": {
                "data_category": "admission_scores",
                "province": "山东",
                "year": 2025,
            },
            "blockers": [],
            "required_reviews": [],
            "source_summary": {
                "matching_source_ids": ["sd_exam_authority"],
                "review_statuses": ["approved"],
                "coverage_years": [2025],
                "has_matching_source": True,
                "has_approved_source": True,
                "has_requested_year": True,
            },
        },
        "snapshot_review": {
            "snapshot_id": "sd_pilot_2025_001",
            "source_url": "https://www.sdzk.cn/NewsInfo.aspx?NewsID=7010",
            "local_snapshot_dir": (
                "data/raw/sd_exam_authority/admission_scores/2025/"
                "sd_pilot_2025_001"
            ),
            "original_file_name": "official.xls",
            "original_file_sha256": "a" * 64,
            "collected_at": "2026-06-07T00:00:00Z",
            "published_year_confirmed": True,
            "original_file_preserved": True,
        },
        "quality_config": {
            "current_year": 2026,
            "expected_provinces": ["山东"],
            "expected_years": [2025],
            "require_review_metadata": True,
        },
    }


def test_intake_review_blocks_blank_template():
    report = review_intake_payload({"not_a_dry_run_bundle": True})

    assert report["passed"] is False
    assert report["ready_for_snapshot"] is False
    assert report["issue_counts"]["error"] > 0
    assert "missing_pilot_scope_source_id" in {
        issue["code"] for issue in report["issues"]
    }


def test_intake_review_passes_ready_packet():
    report = review_intake_payload(make_ready_intake())

    assert report["passed"] is True
    assert report["ready_for_snapshot"] is True
    assert report["issue_counts"] == {"error": 0, "warning": 0, "info": 0}
    assert report["required_reviews"] == []
    assert report["scope"] == {
        "source_id": "sd_exam_authority",
        "dataset": "admission_scores",
        "province": "山东",
        "published_year": 2025,
    }
    assert report["snapshot_planning_review"]["ready_for_snapshot_planning"] is True


def test_intake_review_blocks_quality_scope_mismatch():
    intake = make_ready_intake()
    intake["quality_config"]["expected_years"] = [2024]

    report = review_intake_payload(intake)

    assert report["passed"] is False
    assert report["issues"][-1]["code"] == "quality_config_missing_year"


def test_intake_review_blocks_unready_snapshot_planning():
    intake = make_ready_intake()
    intake["snapshot_planning_review"]["ready_for_snapshot_planning"] = False

    report = review_intake_payload(intake)

    assert report["passed"] is False
    assert "snapshot_planning_not_ready" in {
        issue["code"] for issue in report["issues"]
    }
    assert "Resolve source snapshot planning blockers." in report[
        "required_reviews"
    ]


def test_intake_review_blocks_snapshot_planning_source_mismatch():
    intake = make_ready_intake()
    intake["snapshot_planning_review"]["source_summary"]["matching_source_ids"] = [
        "other_source"
    ]

    report = review_intake_payload(intake)

    assert report["passed"] is False
    assert "snapshot_planning_source_id_mismatch" in {
        issue["code"] for issue in report["issues"]
    }


def test_intake_cli_prints_review_report(tmp_path, capsys):
    intake_path = tmp_path / "intake.json"
    review_output = tmp_path / "intake_review.json"
    intake_path.write_text(
        json.dumps(make_ready_intake(), ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = intake_cli_main(
        [str(intake_path), "--review-output", str(review_output)]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(review_output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout_payload == file_payload
    assert file_payload["action"] == "official_sample_intake_review"
