"""Agent visibility activation review tests."""

import json
from pathlib import Path

from backend.data_pipeline.activation.cli import main as activation_cli_main
from backend.data_pipeline.activation.review import (
    review_agent_visibility_activation,
)


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "real_data"
ARTIFACTS_DIR = EXAMPLES_DIR / "artifacts"


def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def make_artifact_manifest() -> dict:
    return {
        "action": "real_data_pilot_artifact_manifest",
        "source_id": "sd_exam_authority",
        "snapshot_id": "sd_pilot_2025_001",
        "dataset": "admission_scores",
        "candidate_count": 1,
        "ready_for_loader_execution": True,
        "loader_handoff": {
            "requires_separate_loader_run_command": True,
        },
    }


def make_answer_policy_review(answer_mode: str = "citeable") -> dict:
    return {
        "action": "answer_source_policy_review",
        "passed": answer_mode != "unsupported",
        "answer_source_policy": {
            "answer_mode": answer_mode,
        },
    }


def make_activation_approval() -> dict:
    return {
        "action": "agent_visibility_approval",
        "allow_agent_visibility": True,
        "loader_run_confirmed": True,
        "reviewed_by": "reviewer-a",
        "reviewed_at": "2026-06-07",
        "loader_run_evidence": {
            "run_id": "loader-run-20260607-001",
            "completed_at": "2026-06-07T10:00:00+08:00",
            "artifact_manifest_path": "artifacts/real_data/sd_pilot_artifact_manifest.json",
            "result_status": "succeeded",
            "loaded_counts": {
                "admission_score": 1,
            },
        },
        "scope": {
            "source_id": "sd_exam_authority",
            "snapshot_id": "sd_pilot_2025_001",
            "dataset": "admission_scores",
        },
    }


def make_loader_run_evidence_review(approval: dict | None = None) -> dict:
    approval = approval or make_activation_approval()
    return {
        "action": "loader_run_evidence_review",
        "passed": True,
        "ready_for_activation_evidence": True,
        "scope": {
            "source_id": "sd_exam_authority",
            "snapshot_id": "sd_pilot_2025_001",
            "dataset": "admission_scores",
            "candidate_count": 1,
        },
        "loader_run_evidence": dict(approval["loader_run_evidence"]),
    }


def write_json(tmp_path, name: str, payload: dict):
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_activation_review_requires_separate_approval():
    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review(),
    )

    assert review["ready_for_agent_visibility"] is False
    assert review["issue_counts"]["error"] == 1
    assert review["issues"][0]["code"] == "missing_agent_visibility_approval"
    assert review["required_reviews"] == [
        "Provide separate Agent visibility approval."
    ]


def test_activation_review_lists_required_reviews_for_incomplete_approval():
    approval = make_activation_approval()
    approval["allow_agent_visibility"] = False
    approval["loader_run_confirmed"] = False
    approval["reviewed_by"] = ""
    approval["reviewed_at"] = ""

    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review(),
        activation_approval=approval,
    )

    assert review["ready_for_agent_visibility"] is False
    assert review["required_reviews"] == [
        "Confirm Agent visibility approval explicitly allows activation.",
        "Confirm the approved canonical loader run.",
        "Record Agent visibility reviewer and review time.",
    ]


def test_activation_review_passes_with_confirmed_loader_and_policy():
    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review(),
        activation_approval=make_activation_approval(),
        loader_run_evidence_review=make_loader_run_evidence_review(),
    )

    assert review["passed"] is True
    assert review["ready_for_agent_visibility"] is True
    assert review["issue_counts"] == {"error": 0, "warning": 0, "info": 0}
    assert review["scope"] == {
        "source_id": "sd_exam_authority",
        "snapshot_id": "sd_pilot_2025_001",
        "dataset": "admission_scores",
        "candidate_count": 1,
    }


def test_activation_review_blocks_unsupported_answer_policy():
    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review("unsupported"),
        activation_approval=make_activation_approval(),
        loader_run_evidence_review=make_loader_run_evidence_review(),
    )

    assert review["ready_for_agent_visibility"] is False
    assert "answer_source_policy_not_passed" in {
        issue["code"] for issue in review["issues"]
    }
    assert "answer_source_policy_unsupported" in {
        issue["code"] for issue in review["issues"]
    }


def test_activation_review_warns_for_caution_policy_but_allows_visibility():
    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review("citeable_with_caution"),
        activation_approval=make_activation_approval(),
        loader_run_evidence_review=make_loader_run_evidence_review(),
    )

    assert review["ready_for_agent_visibility"] is True
    assert review["issue_counts"] == {"error": 0, "warning": 1, "info": 0}
    assert review["issues"][0]["code"] == "answer_source_policy_requires_caution"
    assert review["required_reviews"][0] == (
        "Configure Agent answers to cite sources and lower certainty."
    )


def test_activation_review_blocks_scope_mismatch():
    approval = make_activation_approval()
    approval["scope"]["dataset"] = "enrollment_plans"

    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review(),
        activation_approval=approval,
        loader_run_evidence_review=make_loader_run_evidence_review(approval),
    )

    assert review["ready_for_agent_visibility"] is False
    assert "agent_visibility_scope_dataset_mismatch" in {
        issue["code"] for issue in review["issues"]
    }


def test_activation_review_requires_loader_run_evidence_when_confirmed():
    approval = make_activation_approval()
    approval.pop("loader_run_evidence")

    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review(),
        activation_approval=approval,
        loader_run_evidence_review=make_loader_run_evidence_review(),
    )

    assert review["ready_for_agent_visibility"] is False
    assert "missing_loader_run_evidence" in {
        issue["code"] for issue in review["issues"]
    }


def test_activation_review_blocks_loader_run_count_mismatch():
    approval = make_activation_approval()
    approval["loader_run_evidence"]["loaded_counts"] = {
        "admission_score": 2,
    }

    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review(),
        activation_approval=approval,
        loader_run_evidence_review=make_loader_run_evidence_review(approval),
    )

    assert review["ready_for_agent_visibility"] is False
    assert "loader_run_candidate_count_mismatch" in {
        issue["code"] for issue in review["issues"]
    }


def test_activation_review_requires_loader_run_evidence_review():
    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review(),
        activation_approval=make_activation_approval(),
    )

    assert review["ready_for_agent_visibility"] is False
    assert "missing_loader_run_evidence_review" in {
        issue["code"] for issue in review["issues"]
    }


def test_activation_review_blocks_loader_run_evidence_review_mismatch():
    approval = make_activation_approval()
    evidence_review = make_loader_run_evidence_review(approval)
    evidence_review["loader_run_evidence"]["run_id"] = "different-run"

    review = review_agent_visibility_activation(
        artifact_manifest=make_artifact_manifest(),
        answer_policy_review=make_answer_policy_review(),
        activation_approval=approval,
        loader_run_evidence_review=evidence_review,
    )

    assert review["ready_for_agent_visibility"] is False
    assert "loader_run_evidence_review_mismatch" in {
        issue["code"] for issue in review["issues"]
    }


def test_activation_cli_writes_review_report(tmp_path, capsys):
    artifact_path = write_json(
        tmp_path,
        "artifact_manifest.json",
        make_artifact_manifest(),
    )
    answer_policy_path = write_json(
        tmp_path,
        "answer_policy.json",
        make_answer_policy_review(),
    )
    approval_path = write_json(
        tmp_path,
        "activation_approval.json",
        make_activation_approval(),
    )
    evidence_review_path = write_json(
        tmp_path,
        "loader_run_evidence_review.json",
        make_loader_run_evidence_review(),
    )
    output_path = tmp_path / "activation_review.json"

    exit_code = activation_cli_main(
        [
            "--artifact-manifest",
            str(artifact_path),
            "--answer-policy-review",
            str(answer_policy_path),
            "--activation-approval",
            str(approval_path),
            "--loader-run-evidence-review",
            str(evidence_review_path),
            "--review-output",
            str(output_path),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout_payload == file_payload
    assert file_payload["action"] == "agent_visibility_activation_review"
    assert file_payload["ready_for_agent_visibility"] is True


def test_activation_cli_returns_nonzero_when_not_ready(tmp_path, capsys):
    artifact_path = write_json(
        tmp_path,
        "artifact_manifest.json",
        make_artifact_manifest(),
    )

    exit_code = activation_cli_main(["--artifact-manifest", str(artifact_path)])
    stdout_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert stdout_payload["ready_for_agent_visibility"] is False


def test_static_shandong_activation_review_matches_cli(capsys):
    exit_code = activation_cli_main(
        [
            "--artifact-manifest",
            str(ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"),
            "--answer-policy-review",
            str(ARTIFACTS_DIR / "sd_answer_source_policy.json"),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert stdout_payload == load_json(
        ARTIFACTS_DIR / "sd_agent_visibility_activation_review.json"
    )
