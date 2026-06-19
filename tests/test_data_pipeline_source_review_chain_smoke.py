"""Stdlib tests for source review chain smoke."""

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

from backend.data_pipeline.sources.review_chain_smoke import (  # noqa: E402
    build_source_review_chain_smoke,
)
from backend.data_pipeline.sources.review_chain_smoke_cli import (  # noqa: E402
    main as chain_smoke_main,
)


def make_registry() -> dict:
    return {
        "sources": [
            {
                "source_id": "sd_exam_authority",
                "name": "Shandong Education Admissions Examination Institute",
                "source_type": "provincial_exam_authority",
                "homepage_url": "https://www.sdzk.cn/default.aspx",
                "data_categories": ["admission_scores"],
                "coverage": {
                    "provinces": ["山东"],
                    "years": [2025],
                },
                "trust_score": 1.0,
                "update_frequency": "annual",
                "collection_method": "manual_download",
                "license_note": "Official source; dataset/citation need review.",
                "review_status": "candidate",
            }
        ]
    }


def make_approval(*, allow: bool = True) -> dict:
    return {
        "action": "source_review_approval",
        "allow_source_review_approval": allow,
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
        "reviewed_by": "reviewer-a",
        "reviewed_at": "2026-06-08",
    }


class SourceReviewChainSmokeTest(unittest.TestCase):
    def test_review_chain_smoke_passes_with_complete_approval(self) -> None:
        report = build_source_review_chain_smoke(
            registry_payload=make_registry(),
            approval_payload=make_approval(),
        )

        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["source_scope_audit_passed"])
        self.assertTrue(report["checks"]["approval_review_passed"])
        self.assertTrue(report["checks"]["update_plan_ready"])
        self.assertEqual(report["issue_counts"], {"error": 0, "warning": 0, "info": 0})
        self.assertEqual(report["required_reviews"], [])
        self.assertEqual(
            report["reviews"]["update_plan"]["planned_updates"]["review_status"],
            {"current": "candidate", "target": "approved", "will_update": True},
        )

    def test_review_chain_smoke_blocks_disabled_approval(self) -> None:
        report = build_source_review_chain_smoke(
            registry_payload=make_registry(),
            approval_payload=make_approval(allow=False),
        )

        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["approval_review_passed"])
        self.assertIn("approval_review_not_passed", {
            issue["code"] for issue in report["issues"]
        })
        self.assertEqual(report["required_reviews"], [
            "Set allow_source_review_approval=true only after human review.",
            "Pass source review approval before registry patch planning.",
        ])

    def test_review_chain_smoke_reports_missing_registry_source(self) -> None:
        report = build_source_review_chain_smoke(
            registry_payload={"sources": []},
            approval_payload=make_approval(),
        )

        self.assertFalse(report["passed"])
        self.assertIn("source_scope_audit_not_passed", {
            issue["code"] for issue in report["issues"]
        })
        self.assertEqual(report["required_reviews"], [
            "Resolve source scope audit errors.",
            "Register the source before planning metadata patch.",
        ])

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "sources.json"
            approval_path = tmp_path / "source_review_approval.json"
            output_path = tmp_path / "source_review_chain_smoke.json"
            registry_path.write_text(
                json.dumps(make_registry(), ensure_ascii=False),
                encoding="utf-8",
            )
            approval_path.write_text(
                json.dumps(make_approval(), ensure_ascii=False),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = chain_smoke_main([
                    str(registry_path),
                    str(approval_path),
                    "--review-output",
                    str(output_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_payload, file_payload)
        self.assertEqual(file_payload["action"], "source_review_chain_smoke")


if __name__ == "__main__":
    unittest.main()
