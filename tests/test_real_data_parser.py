from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.real_data.contracts import run_quality_gate
from backend.real_data.parser import (
    assess_raw_admission_schema,
    build_raw_admission_row,
    extract_raw_admission_rows_from_xls,
    normalize_raw_rows,
)
from backend.real_data.source_registry import (
    SHANDONG_2025_REGULAR_BATCH_1_PAGE,
    build_snapshot,
    sha256_bytes,
)

_REAL_SHANDONG_XLS_PATH = Path("/tmp/sdzk_2025_regular_batch_1.xls")
_REAL_SHANDONG_XLS_SHA256 = "9fdc37c96d3ddceec0f62da7021f8ae01f3cbc6eac7d3698c2efcd202f0c87f1"


def _snapshot():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    return build_snapshot(
        source_page=source,
        attachment=source.attachments[0],
        raw_file_sha256=sha256_bytes(b"pilot parser xls bytes"),
        captured_at=datetime(2026, 6, 9, 10, 0, tzinfo=UTC),
        operator="codex",
    )


def _real_snapshot():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    digest = sha256_bytes(_REAL_SHANDONG_XLS_PATH.read_bytes())
    assert digest == _REAL_SHANDONG_XLS_SHA256
    return build_snapshot(
        source_page=source,
        attachment=source.attachments[0],
        raw_file_sha256=digest,
        captured_at=datetime(2026, 6, 9, 13, 31, tzinfo=UTC),
        operator="codex",
        snapshot_id="sd-2025-regular-batch-1-page-real-snapshot",
    )


def test_parser_normalizes_selected_shandong_rows_with_lineage():
    snapshot = _snapshot()
    rows = [
        build_raw_admission_row(
            snapshot=snapshot,
            raw_row_number=2,
            raw_values={
                "院校代号": "A422",
                "院校名称": "山东大学",
                "专业代号": "01",
                "专业名称": "计算机类",
                "计划数": "12",
                "投档最低分": "620",
                "投档最低位次": "12000",
                "选科要求": "物理,化学",
            },
        ),
        build_raw_admission_row(
            snapshot=snapshot,
            raw_row_number=3,
            raw_values={
                "院校代号": "A423",
                "院校名称": "中国海洋大学",
                "专业代号": "02",
                "专业名称": "电子信息类",
                "计划数": 8,
                "投档最低分": 612,
                "投档最低位次": "15,000",
                "选科要求": "物理,化学",
            },
        ),
    ]

    result = normalize_raw_rows(
        rows=rows,
        province="山东",
        year=2025,
        batch="普通类常规批第1次志愿",
        subject_type="普通类",
    )

    assert result.issues == ()
    assert len(result.candidates) == 2
    assert rows[0].raw_values["院校名称"] == "山东大学"
    first = result.candidates[0]
    assert first.source_batch_id == snapshot.source_batch_id
    assert first.snapshot_id == snapshot.snapshot_id
    assert first.raw_row_number == 2
    assert first.school_name == "山东大学"
    assert first.major_or_group_name == "计算机类"
    assert first.min_score == 620
    assert first.min_rank == 12000
    assert first.plan_count == 12
    assert first.confidence == "high"


def test_parser_output_can_enter_quality_gate_without_db_write():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    rows = [
        build_raw_admission_row(
            snapshot=snapshot,
            raw_row_number=2,
            raw_values={
                "院校代号": "A422",
                "院校名称": "山东大学",
                "专业代号": "01",
                "专业名称": "计算机类",
                "计划数": "12",
                "投档最低分": "620",
                "投档最低位次": "12000",
            },
        )
    ]
    parse_result = normalize_raw_rows(
        rows=rows,
        province="山东",
        year=2025,
        batch="普通类常规批第1次志愿",
        subject_type="普通类",
    )

    report = run_quality_gate(
        candidates=list(parse_result.candidates),
        source_page=source,
        snapshot=snapshot,
        expected_schools=("山东大学",),
        expected_min_records=1,
    )

    assert report.status == "pass"
    assert report.record_count_raw == 1
    assert report.record_count_passed == 1


def test_schema_report_passes_when_required_aliases_exist():
    snapshot = _snapshot()
    row = build_raw_admission_row(
        snapshot=snapshot,
        raw_row_number=2,
        raw_values={
            "院校名称": "山东大学",
            "专业名称": "计算机类",
            "投档最低分": "620",
            "投档最低位次": "12000",
        },
    )

    report = assess_raw_admission_schema(rows=[row])

    assert report.status == "pass"
    assert report.missing_required_fields == ()
    assert report.matched_fields == {
        "school_name": "院校名称",
        "major_or_group_name": "专业名称",
        "min_score": "投档最低分",
    }


def test_parser_blocks_rows_missing_required_fields_before_quality_gate():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    snapshot = _snapshot()
    row = build_raw_admission_row(
        snapshot=snapshot,
        raw_row_number=5,
        raw_values={
            "院校名称": "",
            "专业名称": "计算机类",
            "投档最低分": "620",
        },
    )

    parse_result = normalize_raw_rows(
        rows=[row],
        province="山东",
        year=2025,
        batch="普通类常规批第1次志愿",
        subject_type="普通类",
    )
    report = run_quality_gate(
        candidates=list(parse_result.candidates),
        source_page=source,
        snapshot=snapshot,
    )

    assert parse_result.candidates == ()
    assert parse_result.issues[0].code == "missing_school_name"
    assert parse_result.issues[0].raw_row_number == 5
    assert report.status == "blocked"
    assert report.blocked_reasons == ("no parsed candidates",)


def test_parser_rejects_non_numeric_score_cells():
    snapshot = _snapshot()
    row = build_raw_admission_row(
        snapshot=snapshot,
        raw_row_number=6,
        raw_values={
            "院校名称": "山东大学",
            "专业名称": "计算机类",
            "投档最低分": "六百二十",
        },
    )

    parse_result = normalize_raw_rows(
        rows=[row],
        province="山东",
        year=2025,
        batch="普通类常规批第1次志愿",
        subject_type="普通类",
    )

    assert parse_result.candidates == ()
    assert parse_result.issues[0].code == "invalid_min_score"
    assert parse_result.issues[0].raw_row_number == 6


def test_real_shandong_legacy_xls_snapshot_extracts_raw_rows_with_lineage():
    pytest.importorskip("xlrd")
    if not _REAL_SHANDONG_XLS_PATH.exists():
        pytest.skip("real 山东 .xls snapshot is not available in /tmp")

    snapshot = _real_snapshot()
    rows = extract_raw_admission_rows_from_xls(
        path=_REAL_SHANDONG_XLS_PATH,
        snapshot=snapshot,
        header_row_number=2,
        max_rows=3,
    )

    assert len(rows) == 3
    assert rows[0].source_batch_id == snapshot.source_batch_id
    assert rows[0].snapshot_id == snapshot.snapshot_id
    assert rows[0].raw_row_number == 3
    assert rows[0].raw_values["专业代号及名称"] == "17文科试验班类(不限选考科目类专业)"
    assert rows[0].raw_values["院校代号及名称"] == "A001北京大学"
    assert rows[0].raw_values["投档计划数"] == 22.0
    assert rows[0].raw_values["最低位次"] == 178.0

    parse_result = normalize_raw_rows(
        rows=[rows[0]],
        province="山东",
        year=2025,
        batch="普通类常规批第1次志愿",
        subject_type="普通类",
    )

    assert parse_result.candidates == ()
    assert [issue.code for issue in parse_result.issues] == ["missing_min_score"]


def test_real_shandong_snapshot_schema_blocks_missing_min_score():
    pytest.importorskip("xlrd")
    if not _REAL_SHANDONG_XLS_PATH.exists():
        pytest.skip("real 山东 .xls snapshot is not available in /tmp")

    rows = extract_raw_admission_rows_from_xls(
        path=_REAL_SHANDONG_XLS_PATH,
        snapshot=_real_snapshot(),
        header_row_number=2,
        max_rows=3,
    )

    report = assess_raw_admission_schema(rows=rows)

    assert report.status == "blocked"
    assert report.observed_columns == ("专业代号及名称", "院校代号及名称", "投档计划数", "最低位次")
    assert report.matched_fields == {
        "school_name": "院校代号及名称",
        "major_or_group_name": "专业代号及名称",
    }
    assert report.missing_required_fields == ("min_score",)
