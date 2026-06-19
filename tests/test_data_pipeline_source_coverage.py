"""Stdlib tests for source registry coverage report."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_pipeline.sources.coverage import (  # noqa: E402
    build_source_coverage_report,
)
from backend.data_pipeline.sources.coverage_cli import (  # noqa: E402
    main as coverage_cli_main,
)


def make_source(
    source_id: str,
    province: str,
    *,
    years: list[int] | None = None,
    review_status: str = "candidate",
) -> dict:
    return {
        "source_id": source_id,
        "name": f"{province} Education Examinations Authority",
        "source_type": "provincial_exam_authority",
        "homepage_url": "https://example.edu.cn/",
        "data_categories": ["admission_scores", "enrollment_plans"],
        "coverage": {
            "provinces": [province],
            "years": years or [],
        },
        "trust_score": 1.0,
        "update_frequency": "annual",
        "collection_method": "manual_download",
        "license_note": "Official source; dataset/citation need review.",
        "review_status": review_status,
    }


class SourceCoverageReportTest(unittest.TestCase):
    def test_report_summarizes_priority_gaps(self) -> None:
        report = build_source_coverage_report(
            {
                "sources": [
                    make_source("sd_exam_authority", "山东", years=[2025]),
                    make_source("gd_exam_authority", "广东"),
                ],
            },
            priority_provinces=["山东", "广东", "河南"],
            priority_data_categories=["admission_scores"],
        )

        self.assertFalse(report["passed"])
        self.assertEqual(report["source_count"], 2)
        self.assertEqual(report["review_status_counts"], {"candidate": 2})
        self.assertEqual(
            report["gap_summary"]["missing_priority_provinces"],
            ["河南"],
        )
        self.assertEqual(
            report["gap_summary"]["priority_provinces_without_years"],
            ["广东"],
        )
        self.assertFalse(report["readiness"]["ready_for_snapshot_planning"])
        self.assertIn(
            "missing_priority_provinces",
            report["readiness"]["snapshot_planning_blockers"],
        )
        self.assertIn(
            "priority_provinces_without_years",
            report["readiness"]["snapshot_planning_blockers"],
        )
        issue_codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("missing_expected_province", issue_codes)
        self.assertIn("priority_province_without_registered_year", issue_codes)

    def test_readiness_needs_approved_sources(self) -> None:
        report = build_source_coverage_report(
            {
                "sources": [
                    make_source("sd_exam_authority", "山东", years=[2025]),
                ],
            },
            priority_provinces=["山东"],
            priority_data_categories=["admission_scores"],
        )

        self.assertTrue(report["passed"])
        self.assertEqual(report["issue_counts"]["error"], 0)
        self.assertEqual(report["gap_summary"]["missing_priority_provinces"], [])
        self.assertFalse(report["readiness"]["ready_for_snapshot_planning"])
        self.assertEqual(
            report["readiness"]["snapshot_planning_blockers"],
            ["priority_provinces_without_approved_source"],
        )

    def test_snapshot_readiness_passes_with_approved_years(self) -> None:
        report = build_source_coverage_report(
            {
                "sources": [
                    make_source(
                        "sd_exam_authority",
                        "山东",
                        years=[2025],
                        review_status="approved",
                    ),
                ],
            },
            priority_provinces=["山东"],
            priority_data_categories=["admission_scores"],
        )

        self.assertTrue(report["readiness"]["ready_for_snapshot_planning"])
        self.assertEqual(report["readiness"]["snapshot_planning_blockers"], [])
        self.assertFalse(report["readiness"]["ready_for_loader_discussion"])
        self.assertFalse(
            report["readiness"]["ready_for_agent_visibility_discussion"]
        )

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "sources.json"
            output_path = tmp_path / "coverage.json"
            registry_path.write_text(
                json.dumps({
                    "sources": [
                        make_source("sd_exam_authority", "山东", years=[2025]),
                    ],
                }, ensure_ascii=False),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = coverage_cli_main([
                    str(registry_path),
                    "--priority-province",
                    "山东",
                    "--priority-data-category",
                    "admission_scores",
                    "--report-output",
                    str(output_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_payload, file_payload)
        self.assertEqual(file_payload["action"], "source_coverage_report")
        self.assertIn("readiness", file_payload)


if __name__ == "__main__":
    unittest.main()
