"""Stdlib tests for source snapshot planning readiness."""

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

from backend.data_pipeline.sources.snapshot_planning import (  # noqa: E402
    build_source_snapshot_planning_review,
)
from backend.data_pipeline.sources.snapshot_planning_cli import (  # noqa: E402
    main as snapshot_planning_cli_main,
)


ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"
SOURCE_REGISTRY_PATH = (
    PROJECT_ROOT / "backend" / "data_pipeline" / "sources" / "sources.json"
)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def make_registry(
    *,
    review_status: str = "approved",
    years: list[int] | None = None,
) -> dict:
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
                    "years": [2025] if years is None else years,
                },
                "trust_score": 1.0,
                "update_frequency": "annual",
                "collection_method": "manual_download",
                "license_note": "Official source; dataset terms reviewed.",
                "review_status": review_status,
            }
        ]
    }


class SourceSnapshotPlanningTest(unittest.TestCase):
    def test_snapshot_planning_ready_for_approved_source(self) -> None:
        review = build_source_snapshot_planning_review(
            make_registry(),
            data_category="admission_scores",
            province="山东",
            year=2025,
        )

        self.assertTrue(review["passed"])
        self.assertTrue(review["ready_for_snapshot_planning"])
        self.assertEqual(review["blockers"], [])
        self.assertEqual(review["required_reviews"], [])
        self.assertEqual(review["source_summary"], {
            "matching_source_ids": ["sd_exam_authority"],
            "review_statuses": ["approved"],
            "coverage_years": [2025],
            "has_matching_source": True,
            "has_approved_source": True,
            "has_requested_year": True,
        })

    def test_snapshot_planning_blocks_candidate_source(self) -> None:
        review = build_source_snapshot_planning_review(
            make_registry(review_status="candidate"),
            data_category="admission_scores",
            province="山东",
            year=2025,
        )

        self.assertFalse(review["ready_for_snapshot_planning"])
        self.assertEqual(review["blockers"], ["source_scope:source_not_reviewed"])
        self.assertEqual(review["required_reviews"], [
            "Approve or review the source before preparing a raw snapshot.",
        ])
        self.assertEqual(review["source_summary"]["review_statuses"], ["candidate"])
        self.assertFalse(review["source_summary"]["has_approved_source"])

    def test_checked_in_sd_snapshot_planning_artifact_matches_registry(self) -> None:
        review = build_source_snapshot_planning_review(
            load_json(SOURCE_REGISTRY_PATH),
            data_category="admission_scores",
            province="山东",
            year=2025,
        )

        self.assertFalse(review["ready_for_snapshot_planning"])
        self.assertEqual(review["blockers"], ["source_scope:source_not_reviewed"])
        self.assertEqual(
            review,
            load_json(ARTIFACTS_DIR / "sd_source_snapshot_planning_blocked.json"),
        )

    def test_snapshot_planning_blocks_unregistered_year(self) -> None:
        review = build_source_snapshot_planning_review(
            make_registry(years=[]),
            data_category="admission_scores",
            province="山东",
            year=2025,
        )

        self.assertFalse(review["passed"])
        self.assertEqual(
            review["blockers"],
            ["source_scope:source_years_not_registered"],
        )
        self.assertEqual(review["source_summary"]["coverage_years"], [])
        self.assertFalse(review["source_summary"]["has_requested_year"])

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "sources.json"
            output_path = tmp_path / "snapshot_planning_review.json"
            registry_path.write_text(
                json.dumps(make_registry(), ensure_ascii=False),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = snapshot_planning_cli_main([
                    str(registry_path),
                    "--data-category",
                    "admission_scores",
                    "--province",
                    "山东",
                    "--year",
                    "2025",
                    "--review-output",
                    str(output_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_payload, file_payload)
        self.assertEqual(file_payload["action"], "source_snapshot_planning_review")


if __name__ == "__main__":
    unittest.main()
