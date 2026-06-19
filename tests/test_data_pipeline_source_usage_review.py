"""Source usage and citation review tests."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from backend.data_pipeline.sources.usage_review import review_source_usage
from backend.data_pipeline.sources.usage_review_cli import main as usage_review_cli


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_usage_payload() -> dict:
    return {
        "action": "source_usage_review",
        "source_id": "sd_exam_authority",
        "scope": {
            "data_category": "admission_scores",
            "province": "山东",
            "years": [2025],
        },
        "source_url": "https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996",
        "attachment_url": (
            "https://www.sdzk.cn/Floadup/file/20250719/"
            "6388855130412530367357143.xls"
        ),
        "usage_terms": {
            "copyright_notice": "未经授权不得复制、转载、建立镜像",
            "redistribution_restriction_detected": True,
            "citation_or_usage_notes": "Requires separate authorization review.",
        },
        "decision": {
            "usage_status": "approved_for_real_data_ingestion",
            "license_reviewed": True,
            "allow_real_data_ingestion": True,
        },
        "reviewed_by": "source-reviewer",
        "reviewed_at": "2026-06-08T00:00:00+08:00",
    }


class SourceUsageReviewTest(unittest.TestCase):
    def test_source_usage_review_allows_explicitly_approved_ingestion(self) -> None:
        review = review_source_usage(make_usage_payload())

        self.assertTrue(review["passed"])
        self.assertTrue(review["ready_for_source_approval_license_review"])
        self.assertEqual(review["issue_counts"]["error"], 0)
        self.assertTrue(review["evidence_summary"]["has_attachment_url"])
        self.assertTrue(review["evidence_summary"]["allow_real_data_ingestion"])

    def test_source_usage_review_blocks_pending_authorization(self) -> None:
        payload = make_usage_payload()
        payload["decision"] = {
            "usage_status": "blocked_pending_authorization",
            "license_reviewed": False,
            "allow_real_data_ingestion": False,
        }
        payload["reviewed_by"] = ""
        payload["reviewed_at"] = ""

        review = review_source_usage(payload)

        self.assertFalse(review["passed"])
        self.assertFalse(review["ready_for_source_approval_license_review"])
        self.assertEqual(
            [issue["code"] for issue in review["issues"]],
            [
                "source_usage_license_not_reviewed",
                "source_usage_ingestion_not_allowed",
                "missing_reviewed_by",
                "missing_reviewed_at",
            ],
        )
        self.assertEqual(
            review["required_reviews"],
            [
                "Complete source license or citation review.",
                "Approve real-data ingestion only after usage review passes.",
                "Provide usage reviewer identity.",
                "Provide usage review date or timestamp.",
            ],
        )

    def test_source_usage_review_blocks_inconsistent_allow_flag(self) -> None:
        payload = make_usage_payload()
        payload["decision"]["usage_status"] = "approved_for_internal_review_only"

        review = review_source_usage(payload)

        self.assertFalse(review["passed"])
        self.assertEqual(
            review["issues"][0]["code"],
            "usage_status_does_not_allow_ingestion",
        )

    def test_source_usage_review_cli_writes_optional_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            usage_path = Path(tmpdir) / "usage.json"
            output_path = Path(tmpdir) / "review.json"
            usage_path.write_text(
                json.dumps(make_usage_payload(), ensure_ascii=False),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = usage_review_cli([
                    str(usage_path),
                    "--review-output",
                    str(output_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(file_payload, stdout_payload)
        self.assertEqual(stdout_payload["action"], "source_usage_review")

    def test_source_usage_review_cli_returns_nonzero_for_blocked_payload(
        self,
    ) -> None:
        payload = make_usage_payload()
        payload["decision"]["license_reviewed"] = False
        with tempfile.TemporaryDirectory() as tmpdir:
            usage_path = Path(tmpdir) / "usage.json"
            usage_path.write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = usage_review_cli([str(usage_path)])

        stdout_payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(stdout_payload["passed"])

    def test_source_usage_review_template_is_blocked_by_default(self) -> None:
        template_path = (
            PROJECT_ROOT
            / "examples"
            / "real_data"
            / "source_usage_review_template.json"
        )
        with template_path.open(encoding="utf-8") as f:
            payload = json.load(f)

        review = review_source_usage(payload)

        self.assertFalse(review["passed"])
        self.assertFalse(review["ready_for_source_approval_license_review"])
        self.assertEqual(
            payload["decision"]["usage_status"],
            "blocked_pending_authorization",
        )
        self.assertIn(
            "missing_source_id",
            {issue["code"] for issue in review["issues"]},
        )
        self.assertIn(
            "source_usage_ingestion_not_allowed",
            {issue["code"] for issue in review["issues"]},
        )


if __name__ == "__main__":
    unittest.main()
