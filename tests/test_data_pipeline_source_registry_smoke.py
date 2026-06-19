"""Source registry smoke review tests."""

import json

from backend.data_pipeline.sources.smoke import build_source_registry_smoke_review
from backend.data_pipeline.sources.smoke_cli import main as smoke_cli_main


def make_source(source_id: str = "sd_exam_authority") -> dict:
    return {
        "source_id": source_id,
        "name": "Shandong Education Admissions Examination Institute",
        "source_type": "provincial_exam_authority",
        "homepage_url": "https://www.sdzk.cn/default.aspx",
        "data_categories": ["admission_scores"],
        "coverage": {
            "provinces": ["山东"],
            "years": [],
        },
        "trust_score": 1.0,
        "update_frequency": "annual",
        "collection_method": "manual_download",
        "license_note": "Official source; dataset/citation need snapshot review.",
        "review_status": "candidate",
    }


def write_json(tmp_path, payload: dict):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_source_registry_smoke_review_passes_valid_registry():
    review = build_source_registry_smoke_review({
        "sources": [make_source()],
    })

    assert review["passed"] is True
    assert review["issue_counts"] == {"error": 0, "warning": 0, "info": 0}
    assert review["coverage_summary"]["source_ids"] == ["sd_exam_authority"]
    assert review["coverage_summary"]["provinces"] == ["山东"]


def test_source_registry_smoke_review_blocks_duplicate_source_ids():
    review = build_source_registry_smoke_review({
        "sources": [
            make_source(),
            make_source(),
        ],
    })

    assert review["passed"] is False
    assert "duplicate_source_id" in {issue["code"] for issue in review["issues"]}


def test_source_registry_smoke_review_blocks_missing_required_field():
    source = make_source()
    del source["homepage_url"]

    review = build_source_registry_smoke_review({
        "sources": [source],
    })

    assert review["passed"] is False
    assert "missing_source_homepage_url" in {
        issue["code"] for issue in review["issues"]
    }


def test_source_registry_smoke_review_blocks_missing_expected_province():
    review = build_source_registry_smoke_review(
        {"sources": [make_source()]},
        expected_provinces=["广东"],
    )

    assert review["passed"] is False
    assert "missing_expected_province" in {
        issue["code"] for issue in review["issues"]
    }


def test_source_registry_smoke_cli_writes_review(tmp_path, capsys):
    registry_path = write_json(tmp_path, {"sources": [make_source()]})
    output_path = tmp_path / "source_registry_smoke_review.json"

    exit_code = smoke_cli_main([
        str(registry_path),
        "--expect-source-id",
        "sd_exam_authority",
        "--expect-province",
        "山东",
        "--expect-data-category",
        "admission_scores",
        "--review-output",
        str(output_path),
    ])
    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout_payload == file_payload
    assert file_payload["action"] == "source_registry_smoke_review"
