"""Source usage-to-approval chain smoke tests."""

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

from backend.data_pipeline.sources.usage_to_approval_chain_smoke import (  # noqa: E402
    build_usage_to_approval_chain_smoke,
)
from backend.data_pipeline.sources.usage_to_approval_chain_smoke_cli import (  # noqa: E402
    main as chain_smoke_main,
)


ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"


def load_artifact(name: str) -> dict:
    with (ARTIFACTS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


class SourceUsageToApprovalChainSmokeTest(unittest.TestCase):
    def test_usage_to_approval_chain_passes_checked_artifacts(self) -> None:
        report = build_usage_to_approval_chain_smoke(
            usage_review=load_artifact("source_usage_review_reviewed_example.json"),
            source_approval_review=load_artifact(
                "source_review_approval_reviewed_example_review.json",
            ),
        )

        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["usage_review_passed"])
        self.assertTrue(report["checks"]["usage_review_ready"])
        self.assertTrue(report["checks"]["source_approval_passed"])
        self.assertTrue(report["checks"]["source_approval_ready"])
        self.assertTrue(report["checks"]["source_id_consistent"])
        self.assertTrue(report["checks"]["scope_consistent"])
        self.assertTrue(report["checks"]["approval_evidence_uses_ready_usage_review"])
        self.assertTrue(
            report["checks"]["registry_update_hint_matches_approval_scope"],
        )
        self.assertEqual(report["required_reviews"], [])
        self.assertEqual(
            report["scope"]["source_id"],
            "synthetic_reviewed_source_example",
        )
        self.assertEqual(report["scope"]["target_review_status"], "approved")

    def test_usage_to_approval_chain_blocks_scope_mismatch(self) -> None:
        usage_review = load_artifact("source_usage_review_reviewed_example.json")
        usage_review["scope"]["province"] = "其他省"

        report = build_usage_to_approval_chain_smoke(
            usage_review=usage_review,
            source_approval_review=load_artifact(
                "source_review_approval_reviewed_example_review.json",
            ),
        )

        self.assertFalse(report["passed"])
        self.assertTrue(report["checks"]["source_id_consistent"])
        self.assertFalse(report["checks"]["scope_consistent"])
        self.assertIn(
            "scope_consistent_failed",
            {issue["code"] for issue in report["issues"]},
        )

    def test_cli_writes_review_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "usage_to_approval_chain_smoke.json"
            with redirect_stdout(StringIO()):
                exit_code = chain_smoke_main([
                    "--usage-review",
                    str(ARTIFACTS_DIR / "source_usage_review_reviewed_example.json"),
                    "--source-approval-review",
                    str(
                        ARTIFACTS_DIR
                        / "source_review_approval_reviewed_example_review.json"
                    ),
                    "--review-output",
                    str(output_path),
                ])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["action"],
            "source_usage_to_approval_chain_smoke",
        )


if __name__ == "__main__":
    unittest.main()
