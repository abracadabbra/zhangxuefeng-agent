"""Tests for stdlib-only quality smoke review."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest

from backend.data_pipeline.quality.smoke import build_quality_smoke_review
from backend.data_pipeline.quality.smoke_cli import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"
ROWS_BUNDLE = PROJECT_ROOT / "examples" / "real_data" / "sd_snapshot_pilot_rows.json"
PARSER_SMOKE = ARTIFACTS_DIR / "sd_parser_rows_bundle_smoke.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class QualitySmokeTest(unittest.TestCase):
    def test_quality_smoke_passes_checked_in_parser_smoke(self) -> None:
        report = build_quality_smoke_review(
            load_json(PARSER_SMOKE),
            quality_config=load_json(ROWS_BUNDLE)["quality_config"],
        )

        self.assertTrue(report["passed"])
        self.assertTrue(report["ready_for_quality_gate"])
        self.assertEqual(report["coverage"]["total"], 1)
        self.assertEqual(report["coverage"]["missing_expected_provinces"], [])
        self.assertEqual(report["coverage"]["missing_expected_years"], [])
        self.assertEqual(
            report["source_metadata"]["source_ids"],
            ["sd_exam_authority"],
        )
        self.assertEqual(
            report["source_metadata"]["snapshot_ids"],
            ["sd_pilot_2025_001"],
        )
        self.assertEqual(
            report["source_metadata"]["datasets"],
            ["admission_scores"],
        )
        self.assertEqual(report["source_metadata"]["years"], [2025])
        self.assertEqual(report["source_metadata"]["confidence_min"], 0.95)
        self.assertEqual(report["source_metadata"]["confidence_max"], 0.95)
        self.assertEqual(report["source_metadata"]["missing_source_ids"], 0)

    def test_quality_smoke_blocks_conflicting_duplicates(self) -> None:
        parser_smoke = load_json(PARSER_SMOKE)
        duplicate = json.loads(json.dumps(parser_smoke["candidate_previews"][0]))
        duplicate["values"]["min_score"] = 621
        parser_smoke["candidate_previews"].append(duplicate)

        report = build_quality_smoke_review(parser_smoke)

        self.assertFalse(report["passed"])
        self.assertIn(
            "Resolve conflicting duplicate candidate rows.",
            report["required_reviews"],
        )

    def test_quality_smoke_requires_candidate_source_metadata(self) -> None:
        parser_smoke = load_json(PARSER_SMOKE)
        source = parser_smoke["candidate_previews"][0]["source"]
        source.pop("source_id")
        source.pop("dataset")
        source.pop("year")

        report = build_quality_smoke_review(parser_smoke)

        self.assertFalse(report["passed"])
        issue_codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("missing_source_id", issue_codes)
        self.assertIn("missing_source_dataset", issue_codes)
        self.assertIn("missing_source_year", issue_codes)
        self.assertEqual(report["source_metadata"]["missing_source_ids"], 1)
        self.assertIn(
            "Fill candidate source metadata before quality gate.",
            report["required_reviews"],
        )

    def test_quality_smoke_requires_source_metadata_consistency(self) -> None:
        parser_smoke = load_json(PARSER_SMOKE)
        source = parser_smoke["candidate_previews"][0]["source"]
        source["source_id"] = "other_source"
        source["snapshot_id"] = "other_snapshot"
        source["dataset"] = "enrollment_plans"
        source["year"] = 2024

        report = build_quality_smoke_review(parser_smoke)

        self.assertFalse(report["passed"])
        issue_codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("unexpected_source_source_id", issue_codes)
        self.assertIn("unexpected_source_snapshot_id", issue_codes)
        self.assertIn("unexpected_source_dataset", issue_codes)
        self.assertIn("unexpected_source_year", issue_codes)
        self.assertIn(
            "Align candidate source metadata before quality gate.",
            report["required_reviews"],
        )

    def test_quality_smoke_cli_prints_review(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                str(PARSER_SMOKE),
                "--rows-bundle",
                str(ROWS_BUNDLE),
            ])

        report = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["action"], "quality_smoke_review")
        self.assertTrue(report["ready_for_quality_gate"])


if __name__ == "__main__":
    unittest.main()
