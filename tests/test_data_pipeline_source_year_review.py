"""Source dataset-year review tests."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from backend.data_pipeline.sources.year_review import review_source_years
from backend.data_pipeline.sources.year_review_cli import main as year_review_cli


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_year_payload() -> dict:
    return {
        "action": "source_year_review",
        "source_id": "ha_exam_authority",
        "scope": {
            "province": "河南",
            "data_categories": ["admission_scores", "enrollment_plans"],
        },
        "homepage_url": "https://www.haeea.cn/",
        "source_url": "https://www.haeea.cn/example-official-dataset",
        "candidate_years": [2025],
        "year_evidence": [
            {
                "year": 2025,
                "dataset_page_url": "https://www.haeea.cn/example-official-dataset",
                "attachment_url": "",
                "data_categories": ["admission_scores", "enrollment_plans"],
                "published_year_confirmed": True,
                "source_matches_scope": True,
            },
        ],
        "decision": {
            "allow_source_year_registration": True,
            "register_years": [2025],
        },
        "reviewed_by": "year-reviewer",
        "reviewed_at": "2026-06-08T00:00:00+08:00",
    }


class SourceYearReviewTest(unittest.TestCase):
    def test_source_year_review_allows_explicit_year_registration(self) -> None:
        review = review_source_years(make_year_payload())

        self.assertTrue(review["passed"])
        self.assertTrue(review["ready_for_source_year_registration"])
        self.assertEqual(review["issue_counts"]["error"], 0)
        self.assertEqual(
            review["registry_update_hint"]["add_years_if_missing"],
            [2025],
        )

    def test_source_year_review_blocks_missing_candidate_years(self) -> None:
        payload = make_year_payload()
        payload["candidate_years"] = []
        payload["year_evidence"] = []
        payload["decision"] = {
            "allow_source_year_registration": False,
            "register_years": [],
        }
        payload["reviewed_by"] = ""
        payload["reviewed_at"] = ""

        review = review_source_years(payload)

        self.assertFalse(review["passed"])
        self.assertFalse(review["ready_for_source_year_registration"])
        self.assertEqual(
            [issue["code"] for issue in review["issues"]],
            [
                "missing_candidate_years",
                "missing_year_evidence",
                "source_year_registration_not_allowed",
                "missing_register_years",
                "missing_reviewed_by",
                "missing_reviewed_at",
            ],
        )
        self.assertIn(
            "Review official dataset candidate years.",
            review["required_reviews"],
        )

    def test_source_year_review_blocks_unreviewed_register_year(self) -> None:
        payload = make_year_payload()
        payload["decision"]["register_years"] = [2024]

        review = review_source_years(payload)

        self.assertFalse(review["passed"])
        self.assertEqual(
            review["issues"][0]["code"],
            "register_years_not_in_candidates",
        )

    def test_source_year_review_cli_writes_optional_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            year_path = Path(tmpdir) / "year_review.json"
            output_path = Path(tmpdir) / "review.json"
            year_path.write_text(
                json.dumps(make_year_payload(), ensure_ascii=False),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = year_review_cli([
                    str(year_path),
                    "--review-output",
                    str(output_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(file_payload, stdout_payload)
        self.assertEqual(stdout_payload["action"], "source_year_review")

    def test_source_year_review_template_is_blocked_by_default(self) -> None:
        template_path = (
            PROJECT_ROOT
            / "examples"
            / "real_data"
            / "source_year_review_template.json"
        )
        with template_path.open(encoding="utf-8") as f:
            payload = json.load(f)

        review = review_source_years(payload)

        self.assertFalse(review["passed"])
        self.assertFalse(review["ready_for_source_year_registration"])
        issue_codes = {issue["code"] for issue in review["issues"]}
        self.assertIn("missing_source_id", issue_codes)
        self.assertIn("missing_candidate_years", issue_codes)
        self.assertIn("source_year_registration_not_allowed", issue_codes)


if __name__ == "__main__":
    unittest.main()
