"""Parser tests for manually normalized pilot samples."""

import json
from datetime import datetime, timezone

import pytest

from backend.data_pipeline.parsers import ManualSampleParser, ReviewedTabularSampleParser
from backend.data_pipeline.parsers.tabular_cli import main as tabular_cli_main
from backend.data_pipeline.parsers.tabular_samples import normalize_tabular_row
from backend.data_pipeline.quality import QualityGateConfig, run_quality_gate
from backend.data_pipeline.raw_store.manifest import ManifestFile, RawSnapshotManifest


def make_manifest(dataset: str = "admission_scores") -> RawSnapshotManifest:
    return RawSnapshotManifest(
        snapshot_id=f"sd_{dataset}_2025_001",
        source_id="sd_exam_authority",
        dataset=dataset,
        source_url="https://example.gov.cn/manual-sample.csv",
        published_year=2025,
        collected_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        collector="manual",
        collector_version="0.1.0",
        files=[
            ManifestFile(
                path="files/manual-sample.csv",
                sha256="a" * 64,
                content_type="text/csv",
            )
        ],
        license_note="Test fixture only; not production data.",
    )


def test_manual_parser_maps_admission_score_rows_to_candidates():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "avg_score": None,
            "max_score": None,
            "min_rank": 12000,
            "source_record_ref": "row=2",
            "review": {
                "extracted_by": "extractor-a",
                "reviewed_by": "reviewer-a",
                "reviewed_at": "2026-06-07",
                "notes": "Matched official table row.",
            },
        }
    ]

    candidates = ManualSampleParser().parse(rows, make_manifest())

    assert len(candidates) == 1
    assert candidates[0].entity_type == "admission_score"
    assert candidates[0].natural_key["school_name"] == "山东大学"
    assert candidates[0].values["min_score"] == 620
    assert candidates[0].source.snapshot_id == "sd_admission_scores_2025_001"
    assert candidates[0].source.source_record_ref == "row=2"
    assert candidates[0].source.review.reviewed_by == "reviewer-a"
    assert candidates[0].source.review.reviewed_at == "2026-06-07"


def test_manual_parser_maps_enrollment_plan_rows_to_candidates():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": "计算机科学与技术",
            "province": "山东",
            "year": 2025,
            "plan_count": 20,
            "subject_requirement": "物理+化学",
            "batch": "本科批",
            "duration": 4,
            "tuition": 6600,
            "extracted_by": "extractor-a",
            "reviewed_by": "reviewer-a",
            "reviewed_at": "2026-06-07",
            "review_notes": "Flat worksheet fields.",
        }
    ]

    candidates = ManualSampleParser().parse(rows, make_manifest("enrollment_plans"))

    assert len(candidates) == 1
    assert candidates[0].entity_type == "enrollment_plan"
    assert candidates[0].natural_key["major_name"] == "计算机科学与技术"
    assert candidates[0].values["subject_requirement"] == "物理+化学"
    assert candidates[0].source.source_record_ref == "manual_row=1"
    assert candidates[0].source.review.extracted_by == "extractor-a"
    assert candidates[0].source.review.notes == "Flat worksheet fields."


def test_manual_parser_output_passes_quality_gate_for_shandong_pilot():
    rows = [
        {
            "dataset": "admission_scores",
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "avg_score": None,
            "max_score": None,
            "min_rank": 12000,
        },
        {
            "dataset": "enrollment_plans",
            "school_name": "山东大学",
            "major_name": "计算机科学与技术",
            "province": "山东",
            "year": 2025,
            "plan_count": 20,
            "subject_requirement": "物理+化学",
            "batch": "本科批",
            "duration": 4,
            "tuition": 6600,
        },
    ]

    candidates = ManualSampleParser().parse(rows, make_manifest())
    report = run_quality_gate(
        candidates,
        QualityGateConfig(expected_provinces=("山东",), expected_years=(2025,)),
    )

    assert report.passed is True
    assert report.coverage["total"] == 2
    assert report.coverage["by_entity_type"] == {
        "admission_score": 1,
        "enrollment_plan": 1,
    }


def test_manual_parser_rejects_unknown_dataset():
    rows = [{"dataset": "unknown"}]

    with pytest.raises(ValueError, match="unsupported manual sample dataset"):
        ManualSampleParser().parse(rows, make_manifest())


def test_reviewed_tabular_parser_normalizes_cells_and_review_columns():
    rows = [
        {
            "school_name": " 山东大学 ",
            "major_name": "",
            "province": "山东",
            "year": "2025",
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": "620.0",
            "min_rank": "12000",
            "confidence": "0.97",
            "review.extracted_by": "extractor-a",
            "review.reviewed_by": "reviewer-a",
            "review.reviewed_at": "2026-06-07",
            "review.notes": "Matched official worksheet row.",
        }
    ]

    candidates = ReviewedTabularSampleParser(
        dataset="admission_scores"
    ).parse(rows, make_manifest())

    assert candidates[0].natural_key["school_name"] == "山东大学"
    assert candidates[0].natural_key["major_name"] is None
    assert candidates[0].natural_key["year"] == 2025
    assert candidates[0].values["min_score"] == 620
    assert candidates[0].values["min_rank"] == 12000
    assert candidates[0].source.confidence == 0.97
    assert candidates[0].source.review.reviewed_by == "reviewer-a"


def test_normalize_tabular_row_rejects_invalid_numeric_cell():
    with pytest.raises(ValueError, match="min_score must be an integer"):
        normalize_tabular_row({"min_score": "six hundred"})


def test_tabular_cli_writes_rows_bundle(tmp_path, capsys):
    csv_path = tmp_path / "reviewed_rows.csv"
    output_path = tmp_path / "rows_bundle.json"
    csv_path.write_text(
        "school_name,province,year,batch,subject_type,min_score,min_rank,"
        "review.reviewed_by,review.reviewed_at\n"
        "山东大学,山东,2025,本科批,综合,620,12000,reviewer-a,2026-06-07\n",
        encoding="utf-8",
    )

    exit_code = tabular_cli_main(
        [
            str(csv_path),
            "--dataset",
            "admission_scores",
            "--output",
            str(output_path),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout_payload == file_payload
    assert file_payload["rows"][0]["dataset"] == "admission_scores"
    assert file_payload["rows"][0]["year"] == 2025
    assert file_payload["rows"][0]["review"]["reviewed_by"] == "reviewer-a"
