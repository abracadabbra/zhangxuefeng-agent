"""Source-to-quality chain smoke tests."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_pipeline.pilots.source_to_quality_chain_smoke import (  # noqa: E402
    build_source_to_quality_chain_smoke,
)
from backend.data_pipeline.pilots.source_to_quality_chain_smoke_cli import (  # noqa: E402
    main as chain_smoke_main,
)


ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"


def load_artifact(name: str) -> dict:
    with (ARTIFACTS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


class SourceToQualityChainSmokeTest(unittest.TestCase):
    def test_source_to_quality_chain_smoke_passes_checked_artifacts(self) -> None:
        report = build_source_to_quality_chain_smoke(
            source_to_intake_chain=load_artifact(
                "source_to_intake_chain_smoke_approved_example.json",
            ),
            parser_smoke_review=load_artifact(
                "source_parser_rows_bundle_smoke_approved_example.json",
            ),
            quality_smoke_review=load_artifact(
                "source_quality_smoke_approved_example.json",
            ),
        )

        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["source_to_intake_chain_passed"])
        self.assertTrue(report["checks"]["parser_smoke_ready"])
        self.assertTrue(report["checks"]["quality_smoke_ready"])
        self.assertTrue(report["checks"]["source_scope_matches_parser"])
        self.assertTrue(report["checks"]["parser_scope_matches_quality"])
        self.assertTrue(report["checks"]["quality_source_metadata_matches_parser"])
        self.assertTrue(report["checks"]["candidate_year_matches_source_scope"])
        self.assertEqual(report["required_reviews"], [])
        self.assertEqual(
            report["scope"]["source_id"],
            "synthetic_reviewed_source_example",
        )
        self.assertEqual(report["scope"]["snapshot_id"], "synthetic_snapshot_2025_001")

    def test_source_to_quality_chain_smoke_blocks_parser_mismatch(self) -> None:
        parser_smoke = load_artifact(
            "source_parser_rows_bundle_smoke_approved_example.json",
        )
        parser_smoke["scope"]["source_id"] = "other_source"

        report = build_source_to_quality_chain_smoke(
            source_to_intake_chain=load_artifact(
                "source_to_intake_chain_smoke_approved_example.json",
            ),
            parser_smoke_review=parser_smoke,
            quality_smoke_review=load_artifact(
                "source_quality_smoke_approved_example.json",
            ),
        )

        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["source_scope_matches_parser"])
        self.assertFalse(report["checks"]["parser_scope_matches_quality"])
        self.assertFalse(report["checks"]["quality_source_metadata_matches_parser"])
        self.assertIn(
            "source_scope_matches_parser_failed",
            {issue["code"] for issue in report["issues"]},
        )

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "source_to_quality_chain_smoke.json"
            with redirect_stdout(StringIO()):
                exit_code = chain_smoke_main([
                    "--source-to-intake-chain",
                    str(
                        ARTIFACTS_DIR
                        / "source_to_intake_chain_smoke_approved_example.json"
                    ),
                    "--parser-smoke-review",
                    str(
                        ARTIFACTS_DIR
                        / "source_parser_rows_bundle_smoke_approved_example.json"
                    ),
                    "--quality-smoke-review",
                    str(
                        ARTIFACTS_DIR
                        / "source_quality_smoke_approved_example.json"
                    ),
                    "--review-output",
                    str(output_path),
                ])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["action"], "source_to_quality_chain_smoke")


if __name__ == "__main__":
    unittest.main()
