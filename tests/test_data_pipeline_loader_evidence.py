"""Loader run evidence review tests."""

import json
from pathlib import Path

from backend.data_pipeline.activation.loader_evidence import (
    build_loader_run_evidence_review,
)
from backend.data_pipeline.activation.loader_evidence_cli import (
    main as loader_evidence_cli_main,
)


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "real_data"
ARTIFACTS_DIR = EXAMPLES_DIR / "artifacts"
ARTIFACT_MANIFEST_PATH = (
    ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"
)


def load_json(path: Path) -> dict:
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


def make_loader_run_record() -> dict:
    return {
        "action": "canonical_loader_run_record",
        "run_id": "loader-run-20260608-001",
        "completed_at": "2026-06-08T10:00:00+08:00",
        "artifact_manifest_path": str(ARTIFACT_MANIFEST_PATH),
        "loader_entrypoint": "load_candidates_after_artifact_manifest",
        "result_status": "succeeded",
        "source_id": "sd_exam_authority",
        "snapshot_id": "sd_pilot_2025_001",
        "dataset": "admission_scores",
        "loaded_counts": {
            "admission_score": 1,
        },
    }


def write_json(tmp_path, name: str, payload: dict):
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_loader_run_evidence_review_passes_for_matching_record():
    review = build_loader_run_evidence_review(
        artifact_manifest=make_artifact_manifest(),
        artifact_manifest_path=str(ARTIFACT_MANIFEST_PATH),
        loader_run_record=make_loader_run_record(),
    )

    assert review["passed"] is True
    assert review["ready_for_activation_evidence"] is True
    assert review["issue_counts"] == {"error": 0, "warning": 0, "info": 0}
    assert review["loader_run_evidence"] == {
        "run_id": "loader-run-20260608-001",
        "completed_at": "2026-06-08T10:00:00+08:00",
        "artifact_manifest_path": str(ARTIFACT_MANIFEST_PATH),
        "result_status": "succeeded",
        "loaded_counts": {
            "admission_score": 1,
        },
    }


def test_loader_run_evidence_review_blocks_failed_run():
    record = make_loader_run_record()
    record["result_status"] = "failed"

    review = build_loader_run_evidence_review(
        artifact_manifest=make_artifact_manifest(),
        artifact_manifest_path=str(ARTIFACT_MANIFEST_PATH),
        loader_run_record=record,
    )

    assert review["ready_for_activation_evidence"] is False
    assert "loader_run_not_succeeded" in {
        issue["code"] for issue in review["issues"]
    }


def test_loader_run_evidence_review_blocks_scope_mismatch():
    record = make_loader_run_record()
    record["dataset"] = "enrollment_plans"

    review = build_loader_run_evidence_review(
        artifact_manifest=make_artifact_manifest(),
        artifact_manifest_path=str(ARTIFACT_MANIFEST_PATH),
        loader_run_record=record,
    )

    assert review["ready_for_activation_evidence"] is False
    assert "loader_run_record_dataset_mismatch" in {
        issue["code"] for issue in review["issues"]
    }
    assert (
        "Resolve loader run record source, snapshot, or dataset mismatch."
        in review["required_reviews"]
    )


def test_loader_run_evidence_review_blocks_loaded_count_mismatch():
    record = make_loader_run_record()
    record["loaded_counts"] = {
        "admission_score": 2,
    }

    review = build_loader_run_evidence_review(
        artifact_manifest=make_artifact_manifest(),
        artifact_manifest_path=str(ARTIFACT_MANIFEST_PATH),
        loader_run_record=record,
    )

    assert review["ready_for_activation_evidence"] is False
    assert "loader_run_candidate_count_mismatch" in {
        issue["code"] for issue in review["issues"]
    }
    assert "Resolve loader run loaded count mismatch." in review["required_reviews"]


def test_loader_run_evidence_cli_writes_review(tmp_path, capsys):
    manifest_path = write_json(
        tmp_path,
        "artifact_manifest.json",
        make_artifact_manifest(),
    )
    record = make_loader_run_record()
    record["artifact_manifest_path"] = str(manifest_path)
    record_path = write_json(tmp_path, "loader_run_record.json", record)
    output_path = tmp_path / "loader_run_evidence_review.json"

    exit_code = loader_evidence_cli_main(
        [
            "--artifact-manifest",
            str(manifest_path),
            "--loader-run-record",
            str(record_path),
            "--review-output",
            str(output_path),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout_payload == file_payload
    assert file_payload["action"] == "loader_run_evidence_review"
    assert file_payload["ready_for_activation_evidence"] is True


def test_loader_run_evidence_cli_blocks_template_record(capsys):
    exit_code = loader_evidence_cli_main(
        [
            "--artifact-manifest",
            str(ARTIFACT_MANIFEST_PATH),
            "--loader-run-record",
            str(EXAMPLES_DIR / "canonical_loader_run_record_template.json"),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert stdout_payload["ready_for_activation_evidence"] is False
    assert stdout_payload["issue_counts"]["error"] > 0
    assert stdout_payload["required_reviews"] == [
        "Record loader run ID and completion time.",
        "Record loader run artifact manifest path.",
        "Resolve loader run record manifest path mismatch.",
        "Confirm the canonical loader run succeeded.",
        "Record valid loader run loaded counts.",
    ]
    assert stdout_payload == load_json(
        ARTIFACTS_DIR / "sd_loader_run_evidence_templates_blocked.json"
    )
