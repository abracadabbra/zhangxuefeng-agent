"""Source year review coverage report tests."""

from __future__ import annotations

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

from backend.data_pipeline.sources.year_review_coverage import (  # noqa: E402
    build_source_year_review_coverage_report,
)
from backend.data_pipeline.sources.year_review_coverage_cli import (  # noqa: E402
    main as coverage_main,
)


ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"


def load_artifact(name: str) -> dict:
    with (ARTIFACTS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


class SourceYearReviewCoverageTest(unittest.TestCase):
    def test_checked_in_year_review_coverage_keeps_priority_years_blocked(
        self,
    ) -> None:
        report = build_source_year_review_coverage_report(
            load_artifact("priority_source_coverage_report.json"),
            [load_artifact("ha_source_year_review_blocked.json")],
        )

        self.assertFalse(report["passed"])
        self.assertFalse(report["ready_for_priority_source_year_registration"])
        self.assertEqual(report["next_gate"], "collect_priority_source_year_reviews")
        self.assertEqual(report["current_state"]["required_province_count"], 7)
        self.assertEqual(report["current_state"]["review_artifact_count"], 1)
        self.assertEqual(report["current_state"]["missing_review_count"], 6)
        self.assertIn("河南", report["blocked_reviews"])
        self.assertIn("广东", report["missing_reviews"])

    def test_year_review_coverage_passes_when_all_required_reviews_are_ready(
        self,
    ) -> None:
        review = {
            "action": "source_year_review",
            "ready_for_source_year_registration": True,
            "scope": {"province": "河南"},
        }
        report = build_source_year_review_coverage_report({
            "passed": True,
            "priority_scope": {"data_categories": ["admission_scores"]},
            "gap_summary": {"priority_provinces_without_years": ["河南"]},
        }, [review])

        self.assertTrue(report["passed"])
        self.assertTrue(report["ready_for_priority_source_year_registration"])
        self.assertEqual(report["next_gate"], "source_registry_year_update_plan")

    def test_cli_writes_report_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "year_review_coverage.json"
            with redirect_stdout(StringIO()):
                exit_code = coverage_main([
                    str(ARTIFACTS_DIR / "priority_source_coverage_report.json"),
                    "--artifacts-dir",
                    str(ARTIFACTS_DIR),
                    "--report-output",
                    str(output_path),
                ])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(
            payload["action"],
            "source_year_review_coverage_report",
        )


if __name__ == "__main__":
    unittest.main()
