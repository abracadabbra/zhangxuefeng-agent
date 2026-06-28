"""Source registry audit CLI tests."""

import json

from backend.data_pipeline.sources.cli import main as sources_cli_main


def write_registry(tmp_path, sources):
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps({"sources": sources}, ensure_ascii=False),
        encoding="utf-8",
    )
    return registry_path


def make_source(*, province: str = "山东", years=None, review_status="reviewed"):
    return {
        "source_id": _safe_source_id(province),
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


def _safe_source_id(province: str) -> str:
    """Convert Chinese province name to ASCII-safe source_id."""
    return f"{province}_exam_authority".encode("ascii", "ignore").decode().strip("_") or "exam_authority"


def test_sources_cli_prints_passing_audit(tmp_path, capsys):
    registry_path = write_registry(tmp_path, [make_source()])

    exit_code = sources_cli_main(
        [
            str(registry_path),
            "--data-category",
            "admission_scores",
            "--province",
            "山东",
            "--year",
            "2025",
            "--require-reviewed",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output == {
        "scope": {
            "data_category": "admission_scores",
            "expected_provinces": ["山东"],
            "expected_years": [2025],
            "require_reviewed": True,
        },
        "passed": True,
        "issues": [],
    }


def test_sources_cli_returns_nonzero_for_missing_province(tmp_path, capsys):
    registry_path = write_registry(tmp_path, [make_source()])

    exit_code = sources_cli_main(
        [
            str(registry_path),
            "--data-category",
            "admission_scores",
            "--province",
            "河南",
            "--year",
            "2025",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["passed"] is False
    assert output["scope"]["expected_provinces"] == ["河南"]
    assert output["scope"]["expected_years"] == [2025]
    assert output["issues"][0]["code"] == "missing_province_source"


def test_sources_cli_can_fail_on_warning(tmp_path, capsys):
    registry_path = write_registry(
        tmp_path,
        [make_source(years=[], review_status="candidate")],
    )

    exit_code = sources_cli_main(
        [
            str(registry_path),
            "--data-category",
            "admission_scores",
            "--province",
            "山东",
            "--year",
            "2025",
            "--require-reviewed",
            "--fail-on-warning",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["passed"] is True
    assert [issue["code"] for issue in output["issues"]] == [
        "source_not_reviewed",
        "source_years_not_registered",
    ]


def test_sources_cli_writes_optional_audit_output(tmp_path, capsys):
    registry_path = write_registry(tmp_path, [make_source()])
    audit_path = tmp_path / "audit" / "source_audit.json"

    exit_code = sources_cli_main(
        [
            str(registry_path),
            "--data-category",
            "admission_scores",
            "--province",
            "山东",
            "--year",
            "2025",
            "--audit-output",
            str(audit_path),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(audit_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert file_payload == stdout_payload
