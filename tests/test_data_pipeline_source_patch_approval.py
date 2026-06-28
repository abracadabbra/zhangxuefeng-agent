"""Stdlib tests for source registry patch approval packets."""

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

from backend.data_pipeline.sources.patch_approval import (  # noqa: E402
    review_source_registry_patch_approval,
)
from backend.data_pipeline.sources.patch_approval_cli import (  # noqa: E402
    main as patch_approval_cli_main,
)
from backend.data_pipeline.sources.review_approval import (  # noqa: E402
    review_source_approval,
)
from backend.data_pipeline.sources.update_plan import (  # noqa: E402
    build_source_registry_update_plan,
)


def make_registry() -> dict:
    return {
        "sources": [
            {
                "source_id": "sd_exam_authority",
                "data_categories": ["admission_scores"],
                "coverage": {
                    "provinces": ["山东"],
                    "years": [],
                },
                "review_status": "candidate",
            }
        ]
    }


def make_update_plan() -> dict:
    approval_review = review_source_approval({
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
        "reviewed_by": "source-reviewer",
        "reviewed_at": "2026-06-08",
    })
    return build_source_registry_update_plan(make_registry(), approval_review)


def make_patch_approval() -> dict:
    return {
        "action": "source_registry_patch_approval",
        "allow_source_registry_patch": True,
        "source_id": "sd_exam_authority",
        "planned_updates_confirmed": True,
        "reviewed_by": "registry-reviewer",
        "reviewed_at": "2026-06-08",
        "review_notes": "Synthetic test approval.",
    }


class SourceRegistryPatchApprovalTest(unittest.TestCase):
    def test_patch_approval_passes_complete_packet(self) -> None:
        review = review_source_registry_patch_approval(
            make_update_plan(),
            make_patch_approval(),
        )

        self.assertTrue(review["passed"])
        self.assertTrue(review["ready_for_registry_patch_execution"])
        self.assertEqual(review["issue_counts"], {"error": 0, "warning": 0, "info": 0})
        self.assertEqual(review["required_reviews"], [])
        self.assertEqual(review["source_id"], "sd_exam_authority")
        self.assertEqual(
            review["planned_updates_summary"]["coverage_years"]["add"],
            [2025],
        )

    def test_patch_approval_template_is_blocked_by_default(self) -> None:
        approval = make_patch_approval()
        approval["allow_source_registry_patch"] = False
        approval["planned_updates_confirmed"] = False
        approval["reviewed_by"] = ""
        approval["reviewed_at"] = ""

        review = review_source_registry_patch_approval(
            make_update_plan(),
            approval,
        )

        self.assertFalse(review["ready_for_registry_patch_execution"])
        self.assertEqual(review["required_reviews"], [
            "Set allow_source_registry_patch=true only after human review.",
            "Confirm the planned registry updates.",
            "Provide registry patch reviewer.",
            "Provide registry patch review date or timestamp.",
        ])

    def test_patch_approval_blocks_source_id_mismatch(self) -> None:
        approval = make_patch_approval()
        approval["source_id"] = "other_source"

        review = review_source_registry_patch_approval(
            make_update_plan(),
            approval,
        )

        self.assertFalse(review["passed"])
        self.assertIn("source_id_mismatch", {
            issue["code"] for issue in review["issues"]
        })
        self.assertIn(
            "Match approval source_id to the registry update plan.",
            review["required_reviews"],
        )

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            update_plan_path = tmp_path / "source_registry_update_plan.json"
            approval_path = tmp_path / "source_registry_patch_approval.json"
            output_path = tmp_path / "source_registry_patch_review.json"
            update_plan_path.write_text(
                json.dumps(make_update_plan(), ensure_ascii=False),
                encoding="utf-8",
            )
            approval_path.write_text(
                json.dumps(make_patch_approval(), ensure_ascii=False),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = patch_approval_cli_main([
                    str(update_plan_path),
                    str(approval_path),
                    "--review-output",
                    str(output_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_payload, file_payload)
        self.assertEqual(
            file_payload["action"],
            "source_registry_patch_approval_review",
        )


if __name__ == "__main__":
    unittest.main()
