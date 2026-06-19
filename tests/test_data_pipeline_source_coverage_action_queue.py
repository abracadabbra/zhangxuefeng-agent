"""Priority source coverage action queue tests."""

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

from backend.data_pipeline.sources.coverage_action_queue import (  # noqa: E402
    build_priority_source_coverage_action_queue,
)
from backend.data_pipeline.sources.coverage_action_queue_cli import (  # noqa: E402
    main as coverage_queue_main,
)


ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"


def load_artifact(name: str) -> dict:
    with (ARTIFACTS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


class PrioritySourceCoverageActionQueueTest(unittest.TestCase):
    def test_checked_in_coverage_queue_prioritizes_year_review(self) -> None:
        report = build_priority_source_coverage_action_queue(
            load_artifact("priority_source_coverage_report.json"),
        )

        self.assertFalse(report["passed"])
        self.assertTrue(report["ready_for_human_review"])
        self.assertEqual(report["next_gate"], "review_priority_dataset_years")
        self.assertEqual(
            report["current_state"]["priority_province_without_year_count"],
            7,
        )
        self.assertEqual(
            report["current_state"][
                "priority_province_without_approved_source_count"
            ],
            8,
        )
        action_ids = {item["id"] for item in report["priority_actions"]}
        self.assertIn("review_dataset_year:河南", action_ids)
        self.assertIn("complete_source_approval:山东", action_ids)
        self.assertIn(
            "Review official dataset pages and candidate years.",
            report["required_reviews"],
        )

    def test_coverage_queue_passes_when_no_priority_gaps(self) -> None:
        report = build_priority_source_coverage_action_queue({
            "passed": True,
            "priority_scope": {"provinces": ["山东"]},
            "gap_summary": {
                "missing_priority_provinces": [],
                "priority_provinces_without_years": [],
                "priority_provinces_without_approved_source": [],
            },
            "readiness": {"ready_for_snapshot_planning": True},
        })

        self.assertTrue(report["passed"])
        self.assertFalse(report["ready_for_human_review"])
        self.assertEqual(report["next_gate"], "source_snapshot_planning")
        self.assertEqual(report["priority_actions"], [])

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "coverage_action_queue.json"
            with redirect_stdout(StringIO()):
                exit_code = coverage_queue_main([
                    str(ARTIFACTS_DIR / "priority_source_coverage_report.json"),
                    "--review-output",
                    str(output_path),
                ])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(
            payload["action"],
            "priority_source_coverage_action_queue",
        )


if __name__ == "__main__":
    unittest.main()
