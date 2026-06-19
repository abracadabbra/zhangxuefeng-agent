"""Tests for no-write evidence artifact inventory."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from backend.data_pipeline.pilots.evidence_inventory import (
    build_evidence_artifact_inventory,
)
from backend.data_pipeline.pilots.evidence_inventory_cli import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"


class EvidenceArtifactInventoryTest(unittest.TestCase):
    def test_inventory_summarizes_checked_in_artifacts(self) -> None:
        report = build_evidence_artifact_inventory(ARTIFACTS_DIR)

        self.assertTrue(report["passed"])
        self.assertGreaterEqual(report["artifact_count"], 10)
        self.assertEqual(report["issue_counts"]["warning"], 0)
        names = {artifact["name"] for artifact in report["artifacts"]}
        self.assertIn("sd_parser_rows_bundle_smoke.json", names)
        self.assertIn("sd_quality_smoke.json", names)
        self.assertIn("sd_example_chain_smoke.json", names)
        self.assertIn("sd_mvp_readiness_summary.json", names)
        self.assertIn("sd_mvp_action_queue.json", names)
        self.assertIn("source_review_approval_reviewed_example_review.json", names)
        self.assertIn(
            "source_review_approval_reviewed_example_update_plan_blocked.json",
            names,
        )
        self.assertIn("sd_source_snapshot_planning_blocked.json", names)
        self.assertIn("source_snapshot_planning_approved_example.json", names)
        self.assertIn("priority_source_coverage_report.json", names)
        self.assertIn("priority_source_coverage_action_queue.json", names)
        self.assertIn("priority_source_year_review_coverage_report.json", names)
        self.assertIn("ha_source_year_review_blocked.json", names)
        self.assertIn("sd_source_usage_review_blocked.json", names)
        self.assertIn("source_usage_review_reviewed_example.json", names)
        self.assertIn(
            "source_usage_to_approval_chain_smoke_reviewed_example.json",
            names,
        )
        self.assertIn("sd_source_review_human_checklist_blocked.json", names)
        self.assertIn("sd_source_review_handoff_blocked.json", names)
        self.assertIn("sd_source_review_chain_smoke_blocked.json", names)
        self.assertIn("sd_source_review_approval_candidate_review.json", names)
        self.assertIn("source_review_chain_smoke_reviewed_example.json", names)
        self.assertIn(
            "source_review_chain_smoke_reviewed_example_update_plan.json",
            names,
        )
        self.assertIn(
            "source_registry_patch_approval_reviewed_example_review.json",
            names,
        )
        self.assertIn("source_registry_patch_preview_reviewed_example.json", names)
        self.assertIn(
            "source_registry_patch_chain_smoke_reviewed_example.json",
            names,
        )
        self.assertIn("sd_source_registry_update_plan_blocked.json", names)
        self.assertIn("source_to_intake_chain_smoke_approved_example.json", names)
        self.assertIn("source_intake_review_approved_example.json", names)
        self.assertIn("source_parser_rows_bundle_smoke_approved_example.json", names)
        self.assertIn("source_quality_smoke_approved_example.json", names)
        self.assertIn("source_to_quality_chain_smoke_approved_example.json", names)
        self.assertIn("sd_source_registry_patch_approval_blocked.json", names)
        self.assertIn("sd_source_registry_patch_preview_blocked.json", names)
        self.assertIn("sd_source_registry_patch_chain_smoke_blocked.json", names)
        self.assertIn(
            "Provide separate Agent visibility approval.",
            report["required_reviews"],
        )
        self.assertIn(
            "Complete license or citation review.",
            report["required_reviews"],
        )
        self.assertIn(
            "Approve real-data ingestion only after usage review passes.",
            report["required_reviews"],
        )
        self.assertIn(
            "Review official dataset pages and candidate years.",
            report["required_reviews"],
        )
        self.assertIn(
            "Complete usage/citation and source approval reviews.",
            report["required_reviews"],
        )
        self.assertIn(
            "Review official dataset candidate years.",
            report["required_reviews"],
        )
        self.assertIn(
            "Create source year review packets for priority provinces.",
            report["required_reviews"],
        )
        self.assertIn(
            "Complete blocked priority source year reviews.",
            report["required_reviews"],
        )
        self.assertIn(
            "Complete source review handoff manual actions.",
            report["required_reviews"],
        )
        self.assertIn(
            "Resolve source registry update plan blockers.",
            report["required_reviews"],
        )
        self.assertIn(
            "Pass source registry patch approval review.",
            report["required_reviews"],
        )
        self.assertIn(
            "Resolve source registry patch preview blockers.",
            report["required_reviews"],
        )

    def test_inventory_preserves_no_write_non_goals(self) -> None:
        report = build_evidence_artifact_inventory(ARTIFACTS_DIR)

        self.assertIn("Does not fetch remote data.", report["non_goals"])
        self.assertIn("Does not write database rows or seed data.", report["non_goals"])
        self.assertIn("Does not refresh RAG or Agent-visible data.", report["non_goals"])

    def test_inventory_blocks_missing_required_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_path = Path(tmpdir) / "present.json"
            artifact_path.write_text(
                json.dumps({"action": "present", "passed": True}),
                encoding="utf-8",
            )

            report = build_evidence_artifact_inventory(
                tmpdir,
                required_artifacts=("present.json", "missing.json"),
            )

        self.assertFalse(report["passed"])
        self.assertEqual(report["issue_counts"]["error"], 1)
        self.assertEqual(
            report["issues"][0]["code"],
            "missing_required_artifact",
        )

    def test_inventory_can_ignore_required_reviews_from_named_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            included_path = Path(tmpdir) / "included.json"
            excluded_path = Path(tmpdir) / "excluded.json"
            included_path.write_text(
                json.dumps({
                    "action": "included",
                    "required_reviews": ["Keep this review."],
                }),
                encoding="utf-8",
            )
            excluded_path.write_text(
                json.dumps({
                    "action": "excluded",
                    "required_reviews": ["Drop this stale review."],
                }),
                encoding="utf-8",
            )

            report = build_evidence_artifact_inventory(
                tmpdir,
                required_artifacts=("included.json", "excluded.json"),
                exclude_required_reviews_from=("excluded.json",),
            )

        self.assertIn("Keep this review.", report["required_reviews"])
        self.assertNotIn("Drop this stale review.", report["required_reviews"])

    def test_cli_uses_default_required_artifacts(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([str(ARTIFACTS_DIR)])

        report = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn(
            "sd_parser_rows_bundle_smoke.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_quality_smoke.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_example_chain_smoke.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_source_review_human_checklist_blocked.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_snapshot_planning_approved_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "priority_source_coverage_report.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "priority_source_coverage_action_queue.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "priority_source_year_review_coverage_report.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "ha_source_year_review_blocked.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_source_usage_review_blocked.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_usage_review_reviewed_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_usage_to_approval_chain_smoke_reviewed_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_source_review_handoff_blocked.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_source_review_chain_smoke_blocked.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_source_review_approval_candidate_review.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_review_chain_smoke_reviewed_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_review_chain_smoke_reviewed_example_update_plan.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_registry_patch_approval_reviewed_example_review.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_registry_patch_preview_reviewed_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_registry_patch_chain_smoke_reviewed_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_source_registry_update_plan_blocked.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_source_registry_patch_approval_blocked.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_source_registry_patch_preview_blocked.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_source_registry_patch_chain_smoke_blocked.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_to_intake_chain_smoke_approved_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_intake_review_approved_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_parser_rows_bundle_smoke_approved_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_quality_smoke_approved_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_to_quality_chain_smoke_approved_example.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_mvp_readiness_summary.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "sd_mvp_action_queue.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_review_approval_reviewed_example_review.json",
            report["required_artifacts"],
        )
        self.assertIn(
            "source_review_approval_reviewed_example_update_plan_blocked.json",
            report["required_artifacts"],
        )


if __name__ == "__main__":
    unittest.main()
