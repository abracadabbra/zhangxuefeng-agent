"""Tests for the real-data MVP readiness summary."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from backend.data_pipeline.pilots.evidence_inventory import (
    build_evidence_artifact_inventory,
)
from backend.data_pipeline.pilots.readiness_summary import (
    build_mvp_readiness_summary,
    build_mvp_readiness_summary_from_paths,
)
from backend.data_pipeline.pilots.readiness_summary_cli import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"


def load_artifact(name: str) -> dict:
    with (ARTIFACTS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


class MvpReadinessSummaryTest(unittest.TestCase):
    def test_checked_in_artifacts_keep_real_snapshot_blocked(self) -> None:
        summary = build_mvp_readiness_summary_from_paths(
            source_snapshot_planning_review_path=(
                ARTIFACTS_DIR / "sd_source_snapshot_planning_blocked.json"
            ),
            example_chain_smoke_path=(
                ARTIFACTS_DIR / "sd_example_chain_smoke.json"
            ),
            artifacts_dir=ARTIFACTS_DIR,
        )

        self.assertFalse(summary["passed"])
        self.assertFalse(summary["ready_for_real_snapshot"])
        self.assertTrue(summary["synthetic_chain_ready"])
        self.assertTrue(summary["usage_to_approval_chain_ready"])
        self.assertTrue(summary["source_to_quality_chain_ready"])
        self.assertTrue(summary["evidence_inventory_ready"])
        self.assertGreaterEqual(summary["artifact_summary"]["artifact_count"], 43)
        self.assertFalse(summary["ready_for_loader_discussion"])
        self.assertFalse(summary["ready_for_agent_visibility_discussion"])
        self.assertEqual(
            summary["scope"]["usage_to_approval_chain"]["target_review_status"],
            "approved",
        )
        self.assertEqual(
            summary["scope"]["source_to_quality_chain"]["snapshot_id"],
            "synthetic_snapshot_2025_001",
        )
        self.assertIn(
            "source_snapshot_planning_not_ready",
            summary["blockers"],
        )

    def test_summary_collects_required_reviews(self) -> None:
        summary = build_mvp_readiness_summary(
            source_snapshot_planning_review=load_artifact(
                "sd_source_snapshot_planning_blocked.json"
            ),
            example_chain_smoke=load_artifact("sd_example_chain_smoke.json"),
            evidence_inventory=build_evidence_artifact_inventory(ARTIFACTS_DIR),
        )

        self.assertIn(
            "Approve or review the source before preparing a raw snapshot.",
            summary["required_reviews"],
        )
        self.assertIn(
            "Provide a separate approved loader run command.",
            summary["required_reviews"],
        )
        self.assertIn(
            "Provide separate Agent visibility approval.",
            summary["required_reviews"],
        )

    def test_summary_blocks_failed_source_to_quality_chain(self) -> None:
        summary = build_mvp_readiness_summary(
            source_snapshot_planning_review=load_artifact(
                "source_snapshot_planning_approved_example.json",
            ),
            example_chain_smoke={"passed": True, "required_reviews": []},
            source_to_quality_chain_smoke={
                "passed": False,
                "scope": {"source_id": "synthetic_reviewed_source_example"},
                "required_reviews": ["Fix source-to-quality chain."],
            },
            evidence_inventory={"passed": True, "required_reviews": []},
        )

        self.assertFalse(summary["passed"])
        self.assertFalse(summary["source_to_quality_chain_ready"])
        self.assertIn("source_to_quality_chain_not_ready", summary["blockers"])
        self.assertIn("Fix source-to-quality chain.", summary["required_reviews"])

    def test_summary_blocks_failed_usage_to_approval_chain(self) -> None:
        summary = build_mvp_readiness_summary(
            source_snapshot_planning_review=load_artifact(
                "source_snapshot_planning_approved_example.json",
            ),
            example_chain_smoke={"passed": True, "required_reviews": []},
            usage_to_approval_chain_smoke={
                "passed": False,
                "scope": {"source_id": "synthetic_reviewed_source_example"},
                "required_reviews": ["Fix usage-to-approval chain."],
            },
            evidence_inventory={"passed": True, "required_reviews": []},
        )

        self.assertFalse(summary["passed"])
        self.assertFalse(summary["usage_to_approval_chain_ready"])
        self.assertIn("usage_to_approval_chain_not_ready", summary["blockers"])
        self.assertIn("Fix usage-to-approval chain.", summary["required_reviews"])

    def test_summary_ignores_previous_summary_required_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)
            source_review_path = artifacts_dir / "source_review.json"
            chain_smoke_path = artifacts_dir / "chain_smoke.json"
            previous_summary_path = artifacts_dir / "sd_mvp_readiness_summary.json"
            source_review_path.write_text(
                json.dumps({
                    "action": "source_snapshot_planning_review",
                    "passed": False,
                    "ready_for_snapshot_planning": False,
                    "scope": {"province": "山东"},
                    "required_reviews": ["Keep source review."],
                }),
                encoding="utf-8",
            )
            chain_smoke_path.write_text(
                json.dumps({
                    "action": "real_data_example_chain_smoke",
                    "passed": True,
                    "scope": {"source_id": "sd_exam_authority"},
                    "required_reviews": [],
                }),
                encoding="utf-8",
            )
            previous_summary_path.write_text(
                json.dumps({
                    "action": "real_data_mvp_readiness_summary",
                    "required_reviews": ["Drop stale self review."],
                }),
                encoding="utf-8",
            )

            summary = build_mvp_readiness_summary_from_paths(
                source_snapshot_planning_review_path=source_review_path,
                example_chain_smoke_path=chain_smoke_path,
                artifacts_dir=artifacts_dir,
            )

        self.assertIn("Keep source review.", summary["required_reviews"])
        self.assertNotIn("Drop stale self review.", summary["required_reviews"])

    def test_cli_emits_summary_and_blocking_exit_code(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "--artifacts-dir",
                str(ARTIFACTS_DIR),
                "--source-snapshot-planning-review",
                str(ARTIFACTS_DIR / "sd_source_snapshot_planning_blocked.json"),
                "--example-chain-smoke",
                str(ARTIFACTS_DIR / "sd_example_chain_smoke.json"),
            ])

        summary = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(summary["action"], "real_data_mvp_readiness_summary")
        self.assertFalse(summary["ready_for_real_snapshot"])
        self.assertTrue(summary["usage_to_approval_chain_ready"])
        self.assertTrue(summary["source_to_quality_chain_ready"])
        self.assertIn(
            "separate_loader_run_command_required",
            summary["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
