"""Real-data example chain smoke review tests."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_pipeline.pilots.example_chain_smoke import (  # noqa: E402
    build_example_chain_smoke_report,
)
from backend.data_pipeline.pilots.example_chain_smoke_cli import (  # noqa: E402
    main as smoke_main,
)
from backend.data_pipeline.activation.loader_evidence import (  # noqa: E402
    build_loader_run_evidence_review,
)

EXAMPLES_DIR = PROJECT_ROOT / "examples" / "real_data"
ARTIFACTS_DIR = EXAMPLES_DIR / "artifacts"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class RealDataExampleChainSmokeTest(unittest.TestCase):
    def test_example_chain_smoke_passes_checked_in_examples(self):
        report = build_example_chain_smoke_report(
            intake_payload=load_json(
                EXAMPLES_DIR / "sd_official_sample_intake_reviewed_example.json"
            ),
            artifact_manifest=load_json(
                ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"
            ),
            tool_response=load_json(
                EXAMPLES_DIR / "sd_tool_response_with_sources.json"
            ),
            parser_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_parser_rows_bundle_smoke.json"
            ),
            quality_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_quality_smoke.json"
            ),
            expected_activation_review=load_json(
                ARTIFACTS_DIR / "sd_agent_visibility_activation_review.json"
            ),
            expected_source_id="sd_exam_authority",
            expected_snapshot_id="sd_pilot_2025_001",
            expected_dataset="admission_scores",
        )

        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["intake_snapshot_planning_ready"])
        self.assertTrue(report["checks"]["intake_required_reviews_empty"])
        self.assertTrue(
            report["checks"]["intake_source_bound_to_expected_source"]
        )
        self.assertTrue(report["checks"]["answer_policy_citeable"])
        self.assertTrue(report["checks"]["parser_smoke_ready_when_provided"])
        self.assertTrue(
            report["checks"]["parser_smoke_scope_matches_when_provided"]
        )
        self.assertTrue(report["checks"]["quality_smoke_ready_when_provided"])
        self.assertTrue(
            report["checks"]["quality_smoke_scope_matches_when_provided"]
        )
        self.assertTrue(report["checks"]["activation_blocked_without_approval"])
        self.assertTrue(
            report["checks"]["loader_run_evidence_ready_when_provided"]
        )
        self.assertIsNone(report["reviews"]["loader_run_evidence"])
        self.assertIsNone(report["reviews"]["activation_with_approval"])
        self.assertEqual(report["issue_counts"]["error"], 0)
        self.assertEqual(report["required_reviews"], [
            "Provide a separate approved loader run command.",
            "Provide separate Agent visibility approval.",
        ])
        self.assertEqual(
            report,
            load_json(ARTIFACTS_DIR / "sd_example_chain_smoke.json"),
        )

    def test_example_chain_smoke_accepts_separate_activation_approval(self):
        artifact_manifest_path = ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"
        artifact_manifest = load_json(artifact_manifest_path)
        loader_run_record = make_ready_loader_run_record(
            artifact_manifest,
            str(artifact_manifest_path),
        )
        evidence_review = build_loader_run_evidence_review(
            artifact_manifest=artifact_manifest,
            artifact_manifest_path=str(artifact_manifest_path),
            loader_run_record=loader_run_record,
        )
        activation_approval = make_ready_activation_approval(
            evidence_review["loader_run_evidence"],
        )

        report = build_example_chain_smoke_report(
            intake_payload=load_json(
                EXAMPLES_DIR / "sd_official_sample_intake_reviewed_example.json"
            ),
            artifact_manifest=artifact_manifest,
            tool_response=load_json(
                EXAMPLES_DIR / "sd_tool_response_with_sources.json"
            ),
            parser_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_parser_rows_bundle_smoke.json"
            ),
            quality_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_quality_smoke.json"
            ),
            expected_source_id="sd_exam_authority",
            expected_snapshot_id="sd_pilot_2025_001",
            expected_dataset="admission_scores",
            activation_approval=activation_approval,
            loader_run_record=loader_run_record,
            artifact_manifest_path=str(artifact_manifest_path),
        )

        self.assertTrue(report["passed"])
        self.assertTrue(
            report["checks"]["activation_with_approval_ready_when_provided"]
        )
        self.assertTrue(
            report["checks"]["loader_run_evidence_ready_when_provided"]
        )
        self.assertTrue(
            report["reviews"]["activation_with_approval"][
                "ready_for_agent_visibility"
            ]
        )
        self.assertTrue(
            report["reviews"]["loader_run_evidence"][
                "ready_for_activation_evidence"
            ]
        )

    def test_example_chain_smoke_template_activation_artifact_stays_blocked(self):
        artifact_manifest_path = ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"
        report = build_example_chain_smoke_report(
            intake_payload=load_json(
                EXAMPLES_DIR / "sd_official_sample_intake_reviewed_example.json"
            ),
            artifact_manifest=load_json(artifact_manifest_path),
            tool_response=load_json(
                EXAMPLES_DIR / "sd_tool_response_with_sources.json"
            ),
            parser_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_parser_rows_bundle_smoke.json"
            ),
            quality_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_quality_smoke.json"
            ),
            expected_source_id="sd_exam_authority",
            expected_snapshot_id="sd_pilot_2025_001",
            expected_dataset="admission_scores",
            activation_approval=load_json(
                EXAMPLES_DIR / "agent_visibility_approval_template.json"
            ),
            loader_run_record=load_json(
                EXAMPLES_DIR / "canonical_loader_run_record_template.json"
            ),
            artifact_manifest_path=str(artifact_manifest_path),
        )

        self.assertFalse(report["passed"])
        self.assertFalse(
            report["checks"]["activation_with_approval_ready_when_provided"]
        )
        self.assertFalse(
            report["checks"]["loader_run_evidence_ready_when_provided"]
        )
        self.assertFalse(
            report["reviews"]["loader_run_evidence"][
                "ready_for_activation_evidence"
            ]
        )
        self.assertIn(
            "Confirm Agent visibility approval explicitly allows activation.",
            report["required_reviews"],
        )
        self.assertIn(
            "Record loader run ID and completion time.",
            report["required_reviews"],
        )
        self.assertEqual(
            report,
            load_json(
                ARTIFACTS_DIR
                / "sd_example_chain_smoke_templates_blocked.json"
            ),
        )

    def test_example_chain_smoke_blocks_parser_scope_mismatch(self):
        parser_smoke = load_json(
            ARTIFACTS_DIR / "sd_parser_rows_bundle_smoke.json"
        )
        parser_smoke["scope"]["snapshot_id"] = "wrong_snapshot"

        report = build_example_chain_smoke_report(
            intake_payload=load_json(
                EXAMPLES_DIR / "sd_official_sample_intake_reviewed_example.json"
            ),
            artifact_manifest=load_json(
                ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"
            ),
            tool_response=load_json(
                EXAMPLES_DIR / "sd_tool_response_with_sources.json"
            ),
            parser_smoke_review=parser_smoke,
            quality_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_quality_smoke.json"
            ),
            expected_source_id="sd_exam_authority",
            expected_snapshot_id="sd_pilot_2025_001",
            expected_dataset="admission_scores",
        )

        self.assertFalse(report["passed"])
        self.assertFalse(
            report["checks"]["parser_smoke_scope_matches_when_provided"]
        )
        self.assertIn(
            "parser_smoke_scope_matches_when_provided_failed",
            {issue["code"] for issue in report["issues"]},
        )

    def test_example_chain_smoke_blocks_quality_scope_mismatch(self):
        quality_smoke = load_json(ARTIFACTS_DIR / "sd_quality_smoke.json")
        quality_smoke["scope"]["candidate_count"] = 2

        report = build_example_chain_smoke_report(
            intake_payload=load_json(
                EXAMPLES_DIR / "sd_official_sample_intake_reviewed_example.json"
            ),
            artifact_manifest=load_json(
                ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"
            ),
            tool_response=load_json(
                EXAMPLES_DIR / "sd_tool_response_with_sources.json"
            ),
            parser_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_parser_rows_bundle_smoke.json"
            ),
            quality_smoke_review=quality_smoke,
            expected_source_id="sd_exam_authority",
            expected_snapshot_id="sd_pilot_2025_001",
            expected_dataset="admission_scores",
        )

        self.assertFalse(report["passed"])
        self.assertFalse(
            report["checks"]["quality_smoke_scope_matches_when_provided"]
        )
        self.assertIn(
            "quality_smoke_scope_matches_when_provided_failed",
            {issue["code"] for issue in report["issues"]},
        )

    def test_example_chain_smoke_blocks_missing_source_summary(self):
        tool_response = load_json(EXAMPLES_DIR / "sd_tool_response_with_sources.json")
        del tool_response["source_summary"]
        report = build_example_chain_smoke_report(
            intake_payload=load_json(
                EXAMPLES_DIR / "sd_official_sample_intake_reviewed_example.json"
            ),
            artifact_manifest=load_json(
                ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"
            ),
            tool_response=tool_response,
            parser_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_parser_rows_bundle_smoke.json"
            ),
            quality_smoke_review=load_json(
                ARTIFACTS_DIR / "sd_quality_smoke.json"
            ),
            expected_source_id="sd_exam_authority",
            expected_snapshot_id="sd_pilot_2025_001",
            expected_dataset="admission_scores",
        )

        self.assertFalse(report["passed"])
        self.assertIn(
            "answer_policy_passed_failed",
            {issue["code"] for issue in report["issues"]},
        )

    def test_example_chain_smoke_cli_writes_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "example_chain_smoke.json"
            with redirect_stdout(StringIO()):
                exit_code = smoke_main([
                    "--intake",
                    str(EXAMPLES_DIR / "sd_official_sample_intake_reviewed_example.json"),
                    "--artifact-manifest",
                    str(ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"),
                    "--tool-response",
                    str(EXAMPLES_DIR / "sd_tool_response_with_sources.json"),
                    "--parser-smoke-review",
                    str(ARTIFACTS_DIR / "sd_parser_rows_bundle_smoke.json"),
                    "--quality-smoke-review",
                    str(ARTIFACTS_DIR / "sd_quality_smoke.json"),
                    "--expected-activation-review",
                    str(ARTIFACTS_DIR / "sd_agent_visibility_activation_review.json"),
                    "--expect-source-id",
                    "sd_exam_authority",
                    "--expect-snapshot-id",
                    "sd_pilot_2025_001",
                    "--expect-dataset",
                    "admission_scores",
                    "--review-output",
                    str(output_path),
                ])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["action"], "real_data_example_chain_smoke")

    def test_example_chain_smoke_cli_accepts_activation_inputs(self):
        artifact_manifest_path = ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"
        artifact_manifest = load_json(artifact_manifest_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "example_chain_smoke.json"
            loader_run_path = Path(tmpdir) / "loader_run_record.json"
            activation_path = Path(tmpdir) / "agent_visibility_approval.json"
            loader_run_record = make_ready_loader_run_record(
                artifact_manifest,
                str(artifact_manifest_path),
            )
            evidence_review = build_loader_run_evidence_review(
                artifact_manifest=artifact_manifest,
                artifact_manifest_path=str(artifact_manifest_path),
                loader_run_record=loader_run_record,
            )
            write_json(loader_run_path, loader_run_record)
            write_json(
                activation_path,
                make_ready_activation_approval(
                    evidence_review["loader_run_evidence"],
                ),
            )

            with redirect_stdout(StringIO()):
                exit_code = smoke_main([
                    "--intake",
                    str(
                        EXAMPLES_DIR
                        / "sd_official_sample_intake_reviewed_example.json"
                    ),
                    "--artifact-manifest",
                    str(artifact_manifest_path),
                    "--tool-response",
                    str(EXAMPLES_DIR / "sd_tool_response_with_sources.json"),
                    "--parser-smoke-review",
                    str(ARTIFACTS_DIR / "sd_parser_rows_bundle_smoke.json"),
                    "--quality-smoke-review",
                    str(ARTIFACTS_DIR / "sd_quality_smoke.json"),
                    "--expect-source-id",
                    "sd_exam_authority",
                    "--expect-snapshot-id",
                    "sd_pilot_2025_001",
                    "--expect-dataset",
                    "admission_scores",
                    "--activation-approval",
                    str(activation_path),
                    "--loader-run-record",
                    str(loader_run_path),
                    "--review-output",
                    str(output_path),
                ])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(
            payload["checks"]["activation_with_approval_ready_when_provided"]
        )
        self.assertTrue(
            payload["reviews"]["activation_with_approval"][
                "ready_for_agent_visibility"
            ]
        )

    def test_example_chain_smoke_cli_requires_paired_activation_inputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            activation_path = Path(tmpdir) / "agent_visibility_approval.json"
            write_json(
                activation_path,
                load_json(EXAMPLES_DIR / "agent_visibility_approval_template.json"),
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = smoke_main([
                    "--intake",
                    str(
                        EXAMPLES_DIR
                        / "sd_official_sample_intake_reviewed_example.json"
                    ),
                    "--artifact-manifest",
                    str(ARTIFACTS_DIR / "sd_pilot_artifact_manifest.json"),
                    "--tool-response",
                    str(EXAMPLES_DIR / "sd_tool_response_with_sources.json"),
                    "--activation-approval",
                    str(activation_path),
                ])
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["error_type"], "ValueError")


def make_ready_loader_run_record(
    artifact_manifest: dict,
    artifact_manifest_path: str,
) -> dict:
    record = load_json(EXAMPLES_DIR / "canonical_loader_run_record_template.json")
    record.update({
        "run_id": "loader_run_001",
        "completed_at": "2026-06-07T00:00:00Z",
        "artifact_manifest_path": artifact_manifest_path,
        "result_status": "succeeded",
        "source_id": artifact_manifest["source_id"],
        "snapshot_id": artifact_manifest["snapshot_id"],
        "dataset": artifact_manifest["dataset"],
        "loaded_counts": {
            "admission_score": artifact_manifest["candidate_count"],
        },
        "reviewed_by": "reviewer-a",
        "reviewed_at": "2026-06-07",
    })
    return record


def make_ready_activation_approval(loader_run_evidence: dict) -> dict:
    approval = load_json(EXAMPLES_DIR / "agent_visibility_approval_template.json")
    approval.update({
        "allow_agent_visibility": True,
        "loader_run_confirmed": True,
        "reviewed_by": "reviewer-a",
        "reviewed_at": "2026-06-07",
        "loader_run_evidence": loader_run_evidence,
    })
    return approval


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
