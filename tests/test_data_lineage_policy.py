"""Answer source policy tests."""

import json
from pathlib import Path

from backend.data_pipeline.lineage.policy_cli import main as policy_cli_main
from backend.data_pipeline.lineage.policy import build_answer_source_policy


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "real_data"
ARTIFACTS_DIR = EXAMPLES_DIR / "artifacts"


def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def test_build_answer_source_policy_marks_citeable_summary():
    policy = build_answer_source_policy(
        {
            "source_count": 1,
            "citation_ready": True,
            "needs_caution": False,
        }
    )

    assert policy == {
        "answer_mode": "citeable",
        "citation_ready": True,
        "requires_citation": True,
        "requires_caution": False,
        "allowed_default_answer": True,
        "reasons": [],
    }


def test_build_answer_source_policy_marks_citeable_with_caution():
    policy = build_answer_source_policy(
        {
            "source_count": 1,
            "citation_ready": True,
            "needs_caution": True,
        }
    )

    assert policy == {
        "answer_mode": "citeable_with_caution",
        "citation_ready": True,
        "requires_citation": True,
        "requires_caution": True,
        "allowed_default_answer": False,
        "reasons": ["source_caution_required"],
    }


def test_build_answer_source_policy_marks_incomplete_metadata_unsupported():
    policy = build_answer_source_policy(
        {
            "source_count": 1,
            "citation_ready": True,
            "needs_caution": False,
            "source_metadata_complete": False,
        }
    )

    assert policy == {
        "answer_mode": "unsupported",
        "citation_ready": False,
        "requires_citation": False,
        "requires_caution": True,
        "allowed_default_answer": False,
        "reasons": [
            "source_metadata_incomplete",
            "not_citation_ready",
            "source_caution_required",
        ],
    }


def test_build_answer_source_policy_marks_partial_coverage_unsupported():
    policy = build_answer_source_policy(
        {
            "item_count": 2,
            "items_with_sources": 1,
            "source_count": 1,
            "citation_ready": False,
            "needs_caution": True,
        }
    )

    assert policy == {
        "answer_mode": "unsupported",
        "citation_ready": False,
        "requires_citation": False,
        "requires_caution": True,
        "allowed_default_answer": False,
        "reasons": [
            "partial_source_coverage",
            "source_caution_required",
        ],
    }


def test_build_answer_source_policy_marks_missing_summary_unsupported():
    assert build_answer_source_policy(None) == {
        "answer_mode": "unsupported",
        "citation_ready": False,
        "requires_citation": False,
        "requires_caution": True,
        "allowed_default_answer": False,
        "reasons": ["missing_source_summary"],
    }


def test_build_answer_source_policy_marks_legacy_untraced_reason():
    policy = build_answer_source_policy(
        {
            "item_count": 1,
            "items_with_sources": 0,
            "source_count": 0,
            "citation_ready": False,
            "needs_caution": True,
            "source_status": "legacy_untraced",
        }
    )

    assert policy["answer_mode"] == "unsupported"
    assert policy["reasons"] == [
        "legacy_untraced_tool",
        "no_sources",
        "partial_source_coverage",
        "source_caution_required",
    ]


def test_answer_policy_cli_reviews_tool_response(tmp_path, capsys):
    tool_response_path = tmp_path / "tool_response.json"
    policy_output = tmp_path / "answer_policy.json"
    tool_response_path.write_text(
        json.dumps(
            {
                "status": "success",
                "source_summary": {
                    "source_count": 1,
                    "citation_ready": True,
                    "needs_caution": False,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = policy_cli_main(
        [str(tool_response_path), "--policy-output", str(policy_output)]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(policy_output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout_payload == file_payload
    assert file_payload["action"] == "answer_source_policy_review"
    assert file_payload["passed"] is True
    assert file_payload["answer_source_policy"]["answer_mode"] == "citeable"


def test_answer_policy_cli_blocks_unsupported_summary_only(tmp_path, capsys):
    summary_path = tmp_path / "source_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "item_count": 1,
                "items_with_sources": 0,
                "source_count": 0,
                "citation_ready": False,
                "needs_caution": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = policy_cli_main([str(summary_path), "--summary-only"])
    stdout_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert stdout_payload["passed"] is False
    assert stdout_payload["answer_source_policy"]["answer_mode"] == "unsupported"
    assert stdout_payload["answer_source_policy"]["reasons"] == [
        "no_sources",
        "partial_source_coverage",
        "source_caution_required",
    ]


def test_answer_policy_cli_rejects_missing_source_summary(tmp_path, capsys):
    response_path = tmp_path / "tool_response.json"
    response_path.write_text(
        json.dumps({"status": "success"}, ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = policy_cli_main([str(response_path)])
    stdout_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert stdout_payload["status"] == "error"
    assert stdout_payload["error_type"] == "ValueError"


def test_static_shandong_answer_policy_artifact_matches_cli(tmp_path, capsys):
    source_summary_path = tmp_path / "source_summary.json"
    source_summary_path.write_text(
        json.dumps(
            load_json(ARTIFACTS_DIR / "sd_answer_source_policy.json")[
                "source_summary"
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = policy_cli_main([str(source_summary_path), "--summary-only"])
    stdout_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert stdout_payload == load_json(
        ARTIFACTS_DIR / "sd_answer_source_policy.json"
    )
