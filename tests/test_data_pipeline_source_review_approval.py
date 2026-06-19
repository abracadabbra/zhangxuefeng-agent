"""Stdlib tests for source review approval packets."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "examples" / "real_data"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_pipeline.sources.review_approval import (  # noqa: E402
    review_source_approval,
)
from backend.data_pipeline.sources.review_approval_cli import (  # noqa: E402
    main as approval_cli_main,
)


def make_approval() -> dict:
    return {
        "action": "source_review_approval",
        "allow_source_review_approval": True,
        "source_id": "sd_exam_authority",
        "target_review_status": "approved",
        "scope": {
            "data_category": "admission_scores",
            "province": "山东",
            "years": [2025],
        },
        "evidence": {
            "dataset_page_url": "https://www.sdzk.cn/example.html",
            "attachment_url": "",
            "license_or_citation_notes": "Official source reviewed.",
            "data_category_confirmed": True,
            "published_year_confirmed": True,
            "license_reviewed": True,
        },
        "usage_review": {
            "action": "source_usage_review",
            "ready_for_source_approval_license_review": True,
            "scope": {
                "source_id": "sd_exam_authority",
                "data_category": "admission_scores",
                "province": "山东",
                "years": [2025],
            },
        },
        "reviewed_by": "reviewer-a",
        "reviewed_at": "2026-06-08",
        "review_notes": "Synthetic test approval.",
    }


class SourceReviewApprovalTest(unittest.TestCase):
    def test_template_style_payload_is_blocked_by_default(self) -> None:
        payload = make_approval()
        payload["allow_source_review_approval"] = False
        payload["reviewed_by"] = ""

        review = review_source_approval(payload)

        self.assertFalse(review["ready_for_registry_update"])
        issue_codes = {issue["code"] for issue in review["issues"]}
        self.assertIn("source_review_approval_not_allowed", issue_codes)
        self.assertIn("missing_reviewed_by", issue_codes)

    def test_approval_review_passes_complete_packet(self) -> None:
        review = review_source_approval(make_approval())

        self.assertTrue(review["passed"])
        self.assertTrue(review["ready_for_registry_update"])
        self.assertEqual(review["issue_counts"], {"error": 0, "warning": 0, "info": 0})
        self.assertEqual(review["required_reviews"], [])
        self.assertEqual(review["registry_update_hint"], {
            "can_update_registry": True,
            "source_id": "sd_exam_authority",
            "target_review_status": "approved",
            "add_data_category_if_missing": "admission_scores",
            "add_province_if_missing": "山东",
            "add_years_if_missing": [2025],
        })
        self.assertEqual(review["evidence_summary"], {
            "has_dataset_page_url": True,
            "has_attachment_url": False,
            "has_source_url": True,
            "has_license_or_citation_notes": True,
            "data_category_confirmed": True,
            "published_year_confirmed": True,
            "license_reviewed": True,
            "has_usage_review": True,
            "usage_review_ready": True,
            "has_reviewer": True,
            "has_reviewed_at": True,
        })

    def test_approval_review_requires_evidence_url(self) -> None:
        payload = make_approval()
        payload["evidence"]["dataset_page_url"] = ""

        review = review_source_approval(payload)

        self.assertFalse(review["passed"])
        self.assertIn("missing_source_evidence_url", {
            issue["code"] for issue in review["issues"]
        })
        self.assertIn(
            "Provide an official dataset page URL or attachment URL.",
            review["required_reviews"],
        )

    def test_candidate_draft_summary_shows_partial_evidence(self) -> None:
        payload = make_approval()
        payload["allow_source_review_approval"] = False
        payload["evidence"]["data_category_confirmed"] = False
        payload["evidence"]["published_year_confirmed"] = False
        payload["evidence"]["license_reviewed"] = False
        payload["reviewed_by"] = ""
        payload["reviewed_at"] = ""

        review = review_source_approval(payload)

        self.assertFalse(review["ready_for_registry_update"])
        self.assertEqual(review["evidence_summary"], {
            "has_dataset_page_url": True,
            "has_attachment_url": False,
            "has_source_url": True,
            "has_license_or_citation_notes": True,
            "data_category_confirmed": False,
            "published_year_confirmed": False,
            "license_reviewed": False,
            "has_usage_review": True,
            "usage_review_ready": True,
            "has_reviewer": False,
            "has_reviewed_at": False,
        })
        self.assertEqual(review["required_reviews"], [
            "Set allow_source_review_approval=true only after human review.",
            "Confirm the official dataset category.",
            "Confirm the official dataset published year.",
            "Complete license or citation review.",
            "Provide reviewer identity.",
            "Provide review date or timestamp.",
        ])

    def test_approval_review_requires_ready_usage_review(self) -> None:
        payload = make_approval()
        payload["usage_review"]["ready_for_source_approval_license_review"] = False

        review = review_source_approval(payload)

        self.assertFalse(review["ready_for_registry_update"])
        self.assertIn("source_usage_review_not_ready", {
            issue["code"] for issue in review["issues"]
        })
        self.assertIn(
            "Complete source usage review before source approval.",
            review["required_reviews"],
        )

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            approval_path = tmp_path / "source_review_approval.json"
            output_path = tmp_path / "source_review_approval_review.json"
            approval_path.write_text(
                json.dumps(make_approval(), ensure_ascii=False),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = approval_cli_main([
                    str(approval_path),
                    "--review-output",
                    str(output_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_payload, file_payload)
        self.assertEqual(file_payload["action"], "source_review_approval_review")

    def test_checked_in_reviewed_example_passes_packet_review(self) -> None:
        with (
            EXAMPLES_DIR / "source_review_approval_reviewed_example.json"
        ).open(encoding="utf-8") as f:
            payload = json.load(f)

        review = review_source_approval(payload)

        self.assertTrue(review["ready_for_registry_update"])
        self.assertEqual(
            review["scope"]["source_id"],
            "synthetic_reviewed_source_example",
        )
        self.assertEqual(review["required_reviews"], [])
        self.assertEqual(review["issue_counts"]["error"], 0)


if __name__ == "__main__":
    unittest.main()
