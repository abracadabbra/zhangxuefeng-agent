"""Stdlib tests for source registry scope smoke audit."""

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

from backend.data_pipeline.sources.scope_smoke import (  # noqa: E402
    build_source_scope_smoke_audit,
)
from backend.data_pipeline.sources.scope_smoke_cli import (  # noqa: E402
    main as scope_smoke_main,
)


def make_source(
    *,
    province: str = "山东",
    source_id: str = "sd_exam_authority",
    years: list[int] | None = None,
    review_status: str = "reviewed",
) -> dict:
    return {
        "source_id": source_id,
        "name": f"{province} Education Admissions Examination Institute",
        "source_type": "provincial_exam_authority",
        "homepage_url": "https://example.gov.cn",
        "data_categories": ["admission_scores"],
        "coverage": {
            "provinces": [province],
            "years": years if years is not None else [2025],
        },
        "trust_score": 1.0,
        "update_frequency": "annual",
        "collection_method": "manual_download",
        "license_note": "Official public source; review citation requirements.",
        "review_status": review_status,
    }


class SourceScopeSmokeAuditTest(unittest.TestCase):
    def test_scope_smoke_matches_source_audit_shape(self) -> None:
        audit = build_source_scope_smoke_audit(
            {"sources": [make_source()]},
            data_category="admission_scores",
            expected_provinces=["山东"],
            expected_years=[2025],
            require_reviewed=True,
        )

        self.assertEqual(audit, {
            "scope": {
                "data_category": "admission_scores",
                "expected_provinces": ["山东"],
                "expected_years": [2025],
                "require_reviewed": True,
            },
            "passed": True,
            "issues": [],
        })

    def test_scope_smoke_reports_missing_province(self) -> None:
        audit = build_source_scope_smoke_audit(
            {"sources": [make_source()]},
            data_category="admission_scores",
            expected_provinces=["河南"],
            expected_years=[2025],
        )

        self.assertFalse(audit["passed"])
        self.assertEqual(audit["issues"][0]["code"], "missing_province_source")

    def test_scope_smoke_can_fail_on_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "sources.json"
            registry_path.write_text(
                json.dumps({
                    "sources": [
                        make_source(years=[], review_status="candidate"),
                    ],
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = scope_smoke_main([
                    str(registry_path),
                    "--data-category",
                    "admission_scores",
                    "--province",
                    "山东",
                    "--year",
                    "2025",
                    "--require-reviewed",
                    "--fail-on-warning",
                ])

        output = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertTrue(output["passed"])
        self.assertEqual(
            [issue["code"] for issue in output["issues"]],
            ["source_not_reviewed", "source_years_not_registered"],
        )

    def test_scope_smoke_cli_writes_audit_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "sources.json"
            audit_path = tmp_path / "audit" / "source_audit.json"
            registry_path.write_text(
                json.dumps({"sources": [make_source()]}, ensure_ascii=False),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = scope_smoke_main([
                    str(registry_path),
                    "--data-category",
                    "admission_scores",
                    "--province",
                    "山东",
                    "--year",
                    "2025",
                    "--audit-output",
                    str(audit_path),
                ])

            stdout_payload = json.loads(stdout.getvalue())
            file_payload = json.loads(audit_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(file_payload, stdout_payload)


if __name__ == "__main__":
    unittest.main()
