"""Stdlib tests for source registry patch chain smoke."""

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
from backend.data_pipeline.sources.patch_chain_smoke import (  # noqa: E402
    build_source_registry_patch_chain_smoke,
)
from backend.data_pipeline.sources.patch_chain_smoke_cli import (  # noqa: E402
    main as patch_chain_smoke_cli_main,
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


def make_patch_approval_review() -> dict:
    patch_approval = {
        "action": "source_registry_patch_approval",
        "allow_source_registry_patch": True,
        "source_id": "sd_exam_authority",
        "planned_updates_confirmed": True,
        "reviewed_by": "registry-reviewer",
        "reviewed_at": "2026-06-08",
    }
    return review_source_registry_patch_approval(
        make_update_plan(),
        patch_approval,
    )


class SourceRegistryPatchChainSmokeTest(unittest.TestCase):
    def test_patch_chain_smoke_passes_ready_artifacts(self) -> None:
        report = build_source_registry_patch_chain_smoke(
            registry_payload=make_registry(),
            update_plan=make_update_plan(),
            patch_approval_review=make_patch_approval_review(),
        )

        self.assertTrue(report["passed"])
        self.assertEqual(report["required_reviews"], [])
        self.assertTrue(report["checks"]["patch_approval_ready"])
        self.assertTrue(report["checks"]["patch_preview_ready"])
        self.assertTrue(report["checks"]["registry_not_modified"])
        self.assertEqual(
            report["reviews"]["patch_preview"]["changes_applied"],
            ["review_status", "coverage.years"],
        )

    def test_patch_chain_smoke_blocks_unready_approval(self) -> None:
        approval_review = make_patch_approval_review()
        approval_review["ready_for_registry_patch_execution"] = False

        report = build_source_registry_patch_chain_smoke(
            registry_payload=make_registry(),
            update_plan=make_update_plan(),
            patch_approval_review=approval_review,
        )

        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["patch_approval_ready"])
        self.assertFalse(report["checks"]["patch_preview_ready"])
        self.assertIn("patch_approval_review_not_ready", {
            issue["code"] for issue in report["issues"]
        })
        self.assertIn(
            "Pass source registry patch approval review.",
            report["required_reviews"],
        )

    def test_patch_chain_smoke_blocks_missing_source_preview(self) -> None:
        report = build_source_registry_patch_chain_smoke(
            registry_payload={"sources": []},
            update_plan=make_update_plan(),
            patch_approval_review=make_patch_approval_review(),
        )

        self.assertFalse(report["passed"])
        self.assertTrue(report["checks"]["patch_approval_ready"])
        self.assertFalse(report["checks"]["patch_preview_ready"])
        self.assertIn(
            "Register the source before previewing the patch.",
            report["required_reviews"],
        )

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "sources.json"
            update_plan_path = tmp_path / "source_registry_update_plan.json"
            approval_review_path = tmp_path / "patch_approval_review.json"
            report_path = tmp_path / "source_registry_patch_chain_smoke.json"
            registry_path.write_text(
                json.dumps(make_registry(), ensure_ascii=False),
                encoding="utf-8",
            )
            update_plan_path.write_text(
                json.dumps(make_update_plan(), ensure_ascii=False),
                encoding="utf-8",
            )
            approval_review_path.write_text(
                json.dumps(make_patch_approval_review(), ensure_ascii=False),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = patch_chain_smoke_cli_main([
                    str(registry_path),
                    str(update_plan_path),
                    str(approval_review_path),
                    "--review-output",
                    str(report_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_payload, file_payload)
        self.assertEqual(
            file_payload["action"],
            "source_registry_patch_chain_smoke",
        )


if __name__ == "__main__":
    unittest.main()
