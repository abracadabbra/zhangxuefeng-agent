"""Tests for stdlib-only parser rows bundle smoke review."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest

from backend.data_pipeline.parsers.rows_bundle_smoke import (
    build_parser_rows_bundle_smoke,
)
from backend.data_pipeline.parsers.rows_bundle_smoke_cli import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROWS_BUNDLE = PROJECT_ROOT / "examples" / "real_data" / "sd_snapshot_pilot_rows.json"
SNAPSHOT_MANIFEST = (
    PROJECT_ROOT
    / "examples"
    / "real_data"
    / "snapshots"
    / "sd_pilot_2025_001"
    / "manifest.json"
)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class ParserRowsBundleSmokeTest(unittest.TestCase):
    def test_reviewed_rows_bundle_is_ready_for_parser(self) -> None:
        report = build_parser_rows_bundle_smoke(
            load_json(ROWS_BUNDLE),
            snapshot_manifest=load_json(SNAPSHOT_MANIFEST),
            expected_source_id="sd_exam_authority",
            expected_snapshot_id="sd_pilot_2025_001",
            expected_dataset="admission_scores",
        )

        self.assertTrue(report["passed"])
        self.assertTrue(report["ready_for_parser"])
        self.assertEqual(report["scope"]["row_count"], 1)
        preview = report["candidate_previews"][0]
        self.assertEqual(preview["entity_type"], "admission_score")
        self.assertEqual(preview["source"]["source_id"], "sd_exam_authority")
        self.assertEqual(preview["source"]["snapshot_id"], "sd_pilot_2025_001")
        self.assertEqual(preview["source"]["dataset"], "admission_scores")
        self.assertEqual(preview["source"]["year"], 2025)
        self.assertEqual(preview["source"]["confidence"], 0.95)
        self.assertTrue(preview["source"]["has_review_metadata"])

    def test_review_metadata_is_required_when_config_requires_it(self) -> None:
        bundle = load_json(ROWS_BUNDLE)
        bundle["rows"][0]["review"] = {}

        report = build_parser_rows_bundle_smoke(
            bundle,
            snapshot_manifest=load_json(SNAPSHOT_MANIFEST),
        )

        self.assertFalse(report["passed"])
        self.assertIn(
            "Fill row review metadata before parser handoff.",
            report["required_reviews"],
        )

    def test_cli_prints_parser_smoke_report(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    str(ROWS_BUNDLE),
                    "--snapshot-manifest",
                    str(SNAPSHOT_MANIFEST),
                    "--expect-source-id",
                    "sd_exam_authority",
                    "--expect-snapshot-id",
                    "sd_pilot_2025_001",
                    "--expect-dataset",
                    "admission_scores",
                ]
            )

        report = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["action"], "parser_rows_bundle_smoke")
        self.assertTrue(report["ready_for_parser"])


if __name__ == "__main__":
    unittest.main()
