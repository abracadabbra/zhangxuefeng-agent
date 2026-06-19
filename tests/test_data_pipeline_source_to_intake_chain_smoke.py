"""Source-to-intake chain smoke tests."""

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

from backend.data_pipeline.pilots.source_to_intake_chain_smoke import (  # noqa: E402
    build_source_to_intake_chain_smoke,
)
from backend.data_pipeline.pilots.source_to_intake_chain_smoke_cli import (  # noqa: E402
    main as chain_smoke_main,
)


ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"


def load_artifact(name: str) -> dict:
    with (ARTIFACTS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


class SourceToIntakeChainSmokeTest(unittest.TestCase):
    def test_source_to_intake_chain_smoke_passes_checked_artifacts(self) -> None:
        report = build_source_to_intake_chain_smoke(
            source_review_chain=load_artifact(
                "source_review_chain_smoke_reviewed_example.json",
            ),
            registry_patch_chain=load_artifact(
                "source_registry_patch_chain_smoke_reviewed_example.json",
            ),
            snapshot_planning_review=load_artifact(
                "source_snapshot_planning_approved_example.json",
            ),
            intake_review=load_artifact("source_intake_review_approved_example.json"),
        )

        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["source_review_chain_passed"])
        self.assertTrue(report["checks"]["source_review_update_plan_ready"])
        self.assertTrue(report["checks"]["patch_chain_passed"])
        self.assertTrue(report["checks"]["patch_chain_registry_not_modified"])
        self.assertTrue(report["checks"]["snapshot_planning_ready"])
        self.assertTrue(report["checks"]["intake_ready"])
        self.assertTrue(report["checks"]["source_id_consistent"])
        self.assertTrue(report["checks"]["scope_consistent"])
        self.assertEqual(report["required_reviews"], [])
        self.assertEqual(report["scope"]["source_id"], "synthetic_reviewed_source_example")

    def test_source_to_intake_chain_smoke_blocks_source_mismatch(self) -> None:
        intake_review = load_artifact("source_intake_review_approved_example.json")
        intake_review["scope"]["source_id"] = "other_source"

        report = build_source_to_intake_chain_smoke(
            source_review_chain=load_artifact(
                "source_review_chain_smoke_reviewed_example.json",
            ),
            registry_patch_chain=load_artifact(
                "source_registry_patch_chain_smoke_reviewed_example.json",
            ),
            snapshot_planning_review=load_artifact(
                "source_snapshot_planning_approved_example.json",
            ),
            intake_review=intake_review,
        )

        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["source_id_consistent"])
        self.assertIn(
            "source_id_consistent_failed",
            {issue["code"] for issue in report["issues"]},
        )

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "source_to_intake_chain_smoke.json"
            with redirect_stdout(StringIO()):
                exit_code = chain_smoke_main([
                    "--source-review-chain",
                    str(
                        ARTIFACTS_DIR
                        / "source_review_chain_smoke_reviewed_example.json"
                    ),
                    "--registry-patch-chain",
                    str(
                        ARTIFACTS_DIR
                        / "source_registry_patch_chain_smoke_reviewed_example.json"
                    ),
                    "--snapshot-planning-review",
                    str(
                        ARTIFACTS_DIR
                        / "source_snapshot_planning_approved_example.json"
                    ),
                    "--intake-review",
                    str(
                        ARTIFACTS_DIR
                        / "source_intake_review_approved_example.json"
                    ),
                    "--review-output",
                    str(output_path),
                ])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["action"], "source_to_intake_chain_smoke")


if __name__ == "__main__":
    unittest.main()
