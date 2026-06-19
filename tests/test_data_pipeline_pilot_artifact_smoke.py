"""Pilot artifact manifest smoke review tests."""

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

from backend.data_pipeline.pilots.artifact_smoke import (  # noqa: E402
    build_pilot_artifact_smoke_review,
)
from backend.data_pipeline.pilots.artifact_smoke_cli import main as smoke_main  # noqa: E402


def make_manifest(base_dir: Path) -> dict:
    source_audit = base_dir / "source.json"
    dry_run = base_dir / "dry_run.json"
    rows = base_dir / "rows.json"
    snapshot_dir = base_dir / "snapshot"
    source_audit.write_text(
        json.dumps({
            "scope": {"data_category": "admission_scores"},
            "passed": True,
            "issues": [],
        }),
        encoding="utf-8",
    )
    dry_run.write_text(
        json.dumps({
            "source_id": "sd_exam_authority",
            "snapshot_id": "sd_pilot_2025_001",
            "dataset": "admission_scores",
            "candidate_count": 1,
            "passed": True,
            "load_ready": True,
        }),
        encoding="utf-8",
    )
    rows.write_text("{}", encoding="utf-8")
    snapshot_dir.mkdir()
    return {
        "action": "real_data_pilot_artifact_manifest",
        "source_id": "sd_exam_authority",
        "snapshot_id": "sd_pilot_2025_001",
        "dataset": "admission_scores",
        "candidate_count": 1,
        "ready_for_loader_execution": True,
        "artifact_paths": {
            "source_audit": str(source_audit),
            "dry_run_audit": str(dry_run),
            "rows_bundle": str(rows),
            "snapshot_dir": str(snapshot_dir),
        },
        "artifact_path_issues": [],
        "intake_review_issues": [],
        "artifact_scope_issues": [],
        "loader_approval_issues": [],
        "review_summary": {},
        "loader_handoff": {
            "recommended_entrypoint": "load_candidates_after_artifact_manifest",
            "requires_separate_loader_run_command": True,
        },
        "required_reviews": ["Provide a separate approved loader run command."],
        "non_goals": ["Does not approve loader execution."],
    }


class PilotArtifactSmokeTest(unittest.TestCase):
    def test_smoke_review_passes_ready_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            review = build_pilot_artifact_smoke_review(
                make_manifest(Path(tmpdir)),
                expected_source_id="sd_exam_authority",
                expected_snapshot_id="sd_pilot_2025_001",
                expected_dataset="admission_scores",
            )

        self.assertTrue(review["passed"])
        self.assertEqual(review["issue_counts"]["error"], 0)
        self.assertEqual(review["scope"]["candidate_count"], 1)

    def test_smoke_review_blocks_non_empty_artifact_issues(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = make_manifest(Path(tmpdir))
            manifest["artifact_path_issues"] = ["missing rows bundle"]
            review = build_pilot_artifact_smoke_review(manifest)

        self.assertFalse(review["passed"])
        self.assertIn(
            "non_empty_artifact_path_issues",
            {issue["code"] for issue in review["issues"]},
        )

    def test_smoke_review_blocks_missing_required_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = make_manifest(Path(tmpdir))
            Path(manifest["artifact_paths"]["rows_bundle"]).unlink()
            review = build_pilot_artifact_smoke_review(manifest)

        self.assertFalse(review["passed"])
        self.assertIn(
            "missing_artifact_file_rows_bundle",
            {issue["code"] for issue in review["issues"]},
        )

    def test_smoke_review_blocks_dry_run_scope_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            manifest = make_manifest(base_dir)
            dry_run_path = Path(manifest["artifact_paths"]["dry_run_audit"])
            payload = json.loads(dry_run_path.read_text(encoding="utf-8"))
            payload["snapshot_id"] = "other_snapshot"
            dry_run_path.write_text(json.dumps(payload), encoding="utf-8")

            review = build_pilot_artifact_smoke_review(manifest)

        self.assertFalse(review["passed"])
        self.assertIn(
            "dry_run_audit_snapshot_id_mismatch",
            {issue["code"] for issue in review["issues"]},
        )

    def test_smoke_cli_writes_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            manifest_path = base_dir / "manifest.json"
            review_path = base_dir / "review.json"
            manifest_path.write_text(
                json.dumps(make_manifest(base_dir), ensure_ascii=False),
                encoding="utf-8",
            )

            with redirect_stdout(StringIO()):
                exit_code = smoke_main([
                    str(manifest_path),
                    "--expect-source-id",
                    "sd_exam_authority",
                    "--expect-snapshot-id",
                    "sd_pilot_2025_001",
                    "--expect-dataset",
                    "admission_scores",
                    "--review-output",
                    str(review_path),
                ])
            file_payload = json.loads(review_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(file_payload["action"], "pilot_artifact_manifest_smoke_review")


if __name__ == "__main__":
    unittest.main()
