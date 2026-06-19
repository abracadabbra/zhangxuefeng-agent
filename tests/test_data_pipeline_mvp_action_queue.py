"""Tests for the real-data MVP action queue."""

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

from backend.data_pipeline.pilots.action_queue import (  # noqa: E402
    build_mvp_action_queue,
)
from backend.data_pipeline.pilots.action_queue_cli import (  # noqa: E402
    main as action_queue_main,
)


ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"


def load_artifact(name: str) -> dict:
    with (ARTIFACTS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


class MvpActionQueueTest(unittest.TestCase):
    def test_checked_in_artifacts_prioritize_source_review_actions(self) -> None:
        report = build_mvp_action_queue(
            readiness_summary=load_artifact("sd_mvp_readiness_summary.json"),
            source_review_handoff=load_artifact(
                "sd_source_review_handoff_blocked.json",
            ),
        )

        self.assertFalse(report["passed"])
        self.assertTrue(report["ready_for_human_review"])
        self.assertEqual(report["next_gate"], "source_usage_and_citation_review")
        action_ids = [item["id"] for item in report["priority_actions"]]
        self.assertEqual(action_ids[:3], [
            "review_usage_and_citation",
            "record_reviewer",
            "prepare_separate_source_approval",
        ])
        self.assertIn("resolve_source_snapshot_planning", action_ids)
        self.assertIn("provide_loader_run_command", action_ids)
        self.assertIn("provide_agent_visibility_approval", action_ids)
        self.assertEqual(report["current_state"]["ready_for_real_snapshot"], False)
        self.assertEqual(
            report["current_state"]["usage_to_approval_chain_ready"],
            True,
        )
        self.assertEqual(report["current_state"]["source_to_quality_chain_ready"], True)
        self.assertEqual(
            report["source_review_context"]["candidate_url"],
            "https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996",
        )
        self.assertIn(
            "review_usage_and_citation",
            report["source_review_context"]["pending_action_ids"],
        )
        self.assertIn(
            "verify_official_page",
            report["source_review_context"]["verified_action_ids"],
        )
        self.assertIn(
            "Complete source review handoff manual actions.",
            report["required_reviews"],
        )

    def test_action_queue_defers_loader_until_source_ready(self) -> None:
        handoff = load_artifact("sd_source_review_handoff_blocked.json")
        handoff["next_manual_actions"] = [
            item
            for item in handoff["next_manual_actions"]
            if item["status"] in {"verified", "confirmed"}
        ]

        report = build_mvp_action_queue(
            readiness_summary=load_artifact("sd_mvp_readiness_summary.json"),
            source_review_handoff=handoff,
        )

        self.assertEqual(report["next_gate"], "source_snapshot_planning")
        self.assertEqual(
            report["priority_actions"][0]["id"],
            "resolve_source_snapshot_planning",
        )
        self.assertEqual(report["priority_actions"][0]["status"], "blocked")
        self.assertEqual(
            report["priority_actions"][1]["id"],
            "provide_loader_run_command",
        )
        self.assertEqual(report["priority_actions"][1]["status"], "deferred")

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "action_queue.json"
            with redirect_stdout(StringIO()):
                exit_code = action_queue_main([
                    "--readiness-summary",
                    str(ARTIFACTS_DIR / "sd_mvp_readiness_summary.json"),
                    "--source-review-handoff",
                    str(ARTIFACTS_DIR / "sd_source_review_handoff_blocked.json"),
                    "--review-output",
                    str(output_path),
                ])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["action"], "real_data_mvp_action_queue")
        self.assertEqual(payload["next_gate"], "source_usage_and_citation_review")


if __name__ == "__main__":
    unittest.main()
