"""Stdlib tests for source registry update planning."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_pipeline.sources.review_approval import (  # noqa: E402
    review_source_approval,
)
from backend.data_pipeline.sources.update_plan import (  # noqa: E402
    build_source_registry_update_plan,
)
from backend.data_pipeline.sources.update_plan_cli import (  # noqa: E402
    main as update_plan_main,
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


def make_approval_review(source_id: str = "sd_exam_authority") -> dict:
    approval = {
        "action": "source_review_approval",
        "allow_source_review_approval": True,
        "source_id": source_id,
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
                "source_id": source_id,
                "data_category": "admission_scores",
                "province": "山东",
                "years": [2025],
            },
        },
        "reviewed_by": "reviewer-a",
        "reviewed_at": "2026-06-08",
    }
    return review_source_approval(approval)


class SourceRegistryUpdatePlanTest(unittest.TestCase):
    def test_update_plan_describes_registry_patch(self) -> None:
        plan = build_source_registry_update_plan(
            make_registry(),
            make_approval_review(),
        )

        self.assertTrue(plan["ready_for_registry_patch"])
        self.assertEqual(plan["issue_counts"], {"error": 0, "warning": 0, "info": 0})
        self.assertEqual(
            plan["planned_updates"]["review_status"],
            {"current": "candidate", "target": "approved", "will_update": True},
        )
        self.assertEqual(plan["planned_updates"]["coverage_years"]["add"], [2025])

    def test_update_plan_blocks_unready_approval_review(self) -> None:
        approval_review = make_approval_review()
        approval_review["ready_for_registry_update"] = False

        plan = build_source_registry_update_plan(make_registry(), approval_review)

        self.assertFalse(plan["ready_for_registry_patch"])
        self.assertIn("approval_review_not_ready", {
            issue["code"] for issue in plan["issues"]
        })

    def test_update_plan_blocks_missing_source(self) -> None:
        plan = build_source_registry_update_plan(
            make_registry(),
            make_approval_review("missing_source"),
        )

        self.assertFalse(plan["passed"])
        self.assertIn("source_not_found", {
            issue["code"] for issue in plan["issues"]
        })

    def test_checked_in_synthetic_approval_plan_stays_blocked(self) -> None:
        with (
            ARTIFACTS_DIR
            / "source_review_approval_reviewed_example_update_plan_blocked.json"
        ).open(encoding="utf-8") as f:
            plan = json.load(f)

        self.assertFalse(plan["ready_for_registry_patch"])
        self.assertEqual(plan["source_id"], "synthetic_reviewed_source_example")
        self.assertEqual(plan["planned_updates"], {})
        self.assertEqual(plan["issues"][0]["code"], "source_not_found")

    def test_cli_writes_plan_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "sources.json"
            approval_review_path = tmp_path / "source_approval_review.json"
            plan_path = tmp_path / "source_registry_update_plan.json"
            registry_path.write_text(
                json.dumps(make_registry(), ensure_ascii=False),
                encoding="utf-8",
            )
            approval_review_path.write_text(
                json.dumps(make_approval_review(), ensure_ascii=False),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = update_plan_main([
                    str(registry_path),
                    str(approval_review_path),
                    "--plan-output",
                    str(plan_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(plan_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_payload, file_payload)
        self.assertEqual(file_payload["action"], "source_registry_update_plan")


if __name__ == "__main__":
    unittest.main()
