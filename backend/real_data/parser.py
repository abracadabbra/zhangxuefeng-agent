"""Parser boundary for audited real admission-data pilot rows."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from backend.real_data.contracts import CanonicalAdmissionCandidate, Confidence
from backend.real_data.source_registry import SourceSnapshot

RawCellValue = str | int | float | None
ParseIssueLevel = Literal["error", "warning"]
SchemaStatus = Literal["pass", "blocked"]


class RawAdmissionRow(BaseModel):
    """One manually extracted or parser-extracted row from a source snapshot."""

    source_batch_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    raw_row_number: int = Field(ge=1)
    raw_values: dict[str, RawCellValue] = Field(min_length=1)


class AdmissionParseIssue(BaseModel):
    """A parse-time issue before canonical candidates enter the quality gate."""

    level: ParseIssueLevel
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    raw_row_number: int = Field(ge=1)


class AdmissionParseResult(BaseModel):
    """Parsed canonical candidates plus row-level parse issues."""

    candidates: tuple[CanonicalAdmissionCandidate, ...]
    issues: tuple[AdmissionParseIssue, ...] = ()


class AdmissionSchemaReport(BaseModel):
    """Header-level fit report before raw rows become canonical candidates."""

    status: SchemaStatus
    observed_columns: tuple[str, ...]
    required_fields: tuple[str, ...]
    matched_fields: dict[str, str]
    missing_required_fields: tuple[str, ...] = ()


_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "school_name": ("院校名称", "院校代号及名称", "学校名称", "院校", "学校"),
    "major_or_group_name": ("专业名称", "专业(类)名称", "专业类名称", "专业代号及名称", "专业"),
    "min_score": ("最低投档线", "投档最低分", "最低分", "最低分数"),
    "min_rank": ("最低位次", "投档最低位次", "投档最低排名", "位次"),
    "plan_count": ("计划数", "招生计划", "投档计划数", "计划"),
    "school_code": ("院校代号", "院校代码", "学校代码"),
    "major_code": ("专业代号", "专业代码"),
    "selection_requirement": ("选科要求", "选考科目要求", "科目要求"),
    "notes": ("备注", "说明"),
}

_EMPTY_MARKERS = {"", "-", "--", "—", "——", "/", "无"}


def build_raw_admission_row(
    *,
    snapshot: SourceSnapshot,
    raw_row_number: int,
    raw_values: Mapping[str, RawCellValue],
) -> RawAdmissionRow:
    """Attach source lineage to one extracted raw row."""

    return RawAdmissionRow(
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
        raw_row_number=raw_row_number,
        raw_values=dict(raw_values),
    )


def extract_raw_admission_rows_from_xls(
    *,
    path: Path,
    snapshot: SourceSnapshot,
    header_row_number: int,
    sheet_index: int = 0,
    data_start_row_number: int | None = None,
    max_rows: int | None = None,
) -> tuple[RawAdmissionRow, ...]:
    """Extract lineage-preserving raw rows from a legacy Excel ``.xls`` snapshot."""

    if header_row_number < 1:
        raise ValueError("header_row_number must be 1-based")
    if data_start_row_number is not None and data_start_row_number <= header_row_number:
        raise ValueError("data_start_row_number must be after header_row_number")
    if max_rows is not None and max_rows < 1:
        raise ValueError("max_rows must be at least 1")

    xlrd = _load_xlrd()
    book = xlrd.open_workbook(str(path), on_demand=True)
    try:
        sheet = book.sheet_by_index(sheet_index)
        header_index = header_row_number - 1
        if header_index >= sheet.nrows:
            raise ValueError("header_row_number is outside the worksheet")

        headers = [
            _text_cell(sheet.cell_value(header_index, col_index))
            for col_index in range(sheet.ncols)
        ]
        if not any(headers):
            raise ValueError("header row does not contain any usable columns")

        first_data_index = (
            data_start_row_number - 1
            if data_start_row_number is not None
            else header_index + 1
        )
        rows: list[RawAdmissionRow] = []
        for row_index in range(first_data_index, sheet.nrows):
            raw_values: dict[str, RawCellValue] = {}
            has_value = False
            for col_index, header in enumerate(headers):
                if header is None:
                    continue
                value = _xls_cell_value(sheet.cell_value(row_index, col_index))
                raw_values[header] = value
                if _text_cell(value) is not None:
                    has_value = True

            if not has_value:
                continue
            rows.append(
                build_raw_admission_row(
                    snapshot=snapshot,
                    raw_row_number=row_index + 1,
                    raw_values=raw_values,
                )
            )
            if max_rows is not None and len(rows) >= max_rows:
                break

        return tuple(rows)
    finally:
        book.release_resources()


def assess_raw_admission_schema(
    *,
    rows: Sequence[RawAdmissionRow],
    required_fields: tuple[str, ...] = ("school_name", "major_or_group_name", "min_score"),
) -> AdmissionSchemaReport:
    """Check whether raw rows expose the columns required by the canonical contract."""

    observed_columns = _observed_columns(rows)
    matched_fields: dict[str, str] = {}
    for field_name in required_fields:
        matched_column = _match_observed_column(field_name, observed_columns)
        if matched_column is not None:
            matched_fields[field_name] = matched_column

    missing_required_fields = tuple(
        field_name for field_name in required_fields if field_name not in matched_fields
    )
    return AdmissionSchemaReport(
        status="blocked" if missing_required_fields else "pass",
        observed_columns=observed_columns,
        required_fields=required_fields,
        matched_fields=matched_fields,
        missing_required_fields=missing_required_fields,
    )


def normalize_raw_rows(
    *,
    rows: Sequence[RawAdmissionRow],
    province: str,
    year: int,
    batch: str,
    subject_type: str,
    default_confidence: Confidence = "high",
) -> AdmissionParseResult:
    """Normalize selected raw rows into canonical candidates without DB writes."""

    candidates: list[CanonicalAdmissionCandidate] = []
    issues: list[AdmissionParseIssue] = []

    for row in rows:
        normalized_values = _normalize_keys(row.raw_values)
        row_issues = _validate_required_cells(row, normalized_values)
        issues.extend(row_issues)
        if any(issue.level == "error" for issue in row_issues):
            continue

        confidence = _confidence_for_row(normalized_values, default_confidence)
        candidate_data = {
            "province": province,
            "year": year,
            "school_name": _text_cell(normalized_values["school_name"]),
            "major_or_group_name": _text_cell(normalized_values["major_or_group_name"]),
            "batch": batch,
            "subject_type": subject_type,
            "min_score": _int_cell(normalized_values["min_score"]),
            "min_rank": _int_cell(normalized_values.get("min_rank")),
            "plan_count": _int_cell(normalized_values.get("plan_count")),
            "source_batch_id": row.source_batch_id,
            "snapshot_id": row.snapshot_id,
            "raw_row_number": row.raw_row_number,
            "confidence": confidence,
            "school_code": _text_cell(normalized_values.get("school_code")),
            "major_code": _text_cell(normalized_values.get("major_code")),
            "selection_requirement": _text_cell(normalized_values.get("selection_requirement")),
            "notes": _text_cell(normalized_values.get("notes")),
        }
        try:
            candidates.append(CanonicalAdmissionCandidate.model_validate(candidate_data))
        except ValidationError as exc:
            issues.append(
                AdmissionParseIssue(
                    level="error",
                    code="canonical_validation_failed",
                    message=str(exc),
                    raw_row_number=row.raw_row_number,
                )
            )

    return AdmissionParseResult(candidates=tuple(candidates), issues=tuple(issues))


def _load_xlrd() -> Any:
    try:
        import xlrd  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("xlrd is required to read legacy .xls snapshots") from exc
    return xlrd


def _xls_cell_value(value: Any) -> RawCellValue:
    if value == "":
        return None
    if isinstance(value, str | int | float) or value is None:
        return value
    return str(value)


def _observed_columns(rows: Sequence[RawAdmissionRow]) -> tuple[str, ...]:
    observed: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for raw_key in row.raw_values:
            key = raw_key.strip()
            if key and key not in seen:
                seen.add(key)
                observed.append(key)
    return tuple(observed)


def _match_observed_column(field_name: str, observed_columns: Sequence[str]) -> str | None:
    aliases = _FIELD_ALIASES.get(field_name, ())
    for alias in aliases:
        if alias in observed_columns:
            return alias
    return None


def _normalize_keys(raw_values: Mapping[str, RawCellValue]) -> dict[str, RawCellValue]:
    stripped = {key.strip(): value for key, value in raw_values.items()}
    normalized: dict[str, RawCellValue] = {}
    for canonical_name, aliases in _FIELD_ALIASES.items():
        for alias in aliases:
            if alias in stripped:
                normalized[canonical_name] = stripped[alias]
                break
    return normalized


def _validate_required_cells(
    row: RawAdmissionRow,
    normalized_values: Mapping[str, RawCellValue],
) -> list[AdmissionParseIssue]:
    issues: list[AdmissionParseIssue] = []
    for field_name in ("school_name", "major_or_group_name", "min_score"):
        if _text_cell(normalized_values.get(field_name)) is None:
            issues.append(
                AdmissionParseIssue(
                    level="error",
                    code=f"missing_{field_name}",
                    message=f"raw row is missing required field {field_name}",
                    raw_row_number=row.raw_row_number,
                )
            )

    for field_name in ("min_score", "min_rank", "plan_count"):
        value = normalized_values.get(field_name)
        if _text_cell(value) is not None and _int_cell(value) is None:
            issues.append(
                AdmissionParseIssue(
                    level="error",
                    code=f"invalid_{field_name}",
                    message=f"raw row has non-integer field {field_name}",
                    raw_row_number=row.raw_row_number,
                )
            )

    return issues


def _confidence_for_row(
    normalized_values: Mapping[str, RawCellValue],
    default_confidence: Confidence,
) -> Confidence:
    if default_confidence != "high":
        return default_confidence
    if _text_cell(normalized_values.get("school_code")) is None:
        return "medium"
    if _text_cell(normalized_values.get("major_code")) is None:
        return "medium"
    return "high"


def _text_cell(value: RawCellValue) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in _EMPTY_MARKERS:
        return None
    return text


def _int_cell(value: RawCellValue) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None

    text = _text_cell(value)
    if text is None:
        return None
    normalized = text.replace(",", "").replace("，", "").strip()
    if re.fullmatch(r"\d+(?:\.0+)?", normalized):
        return int(float(normalized))
    return None
