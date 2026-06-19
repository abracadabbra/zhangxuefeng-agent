"""Data source registry contracts and loading helpers."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


SourceType = Literal[
    "ministry",
    "provincial_exam_authority",
    "university",
    "ranking_provider",
    "employment_report",
    "licensed_provider",
    "media",
    "other",
]
CollectionMethod = Literal["manual_download", "api", "crawler_stub", "crawler", "licensed_feed"]
ReviewStatus = Literal["candidate", "reviewed", "approved", "rejected"]
IssueSeverity = Literal["error", "warning", "info"]


class SourceCoverage(BaseModel):
    """Coverage information advertised or reviewed for a source."""

    provinces: list[str] = Field(default_factory=list)
    years: list[int] = Field(default_factory=list)

    @field_validator("years")
    @classmethod
    def years_are_reasonable(cls, value: list[int]) -> list[int]:
        invalid = [year for year in value if year < 2000 or year > 2100]
        if invalid:
            raise ValueError(f"invalid coverage years: {invalid}")
        return value


class DataSource(BaseModel):
    """A registered official or authorized education data source."""

    source_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_type: SourceType
    homepage_url: HttpUrl
    data_categories: list[str] = Field(min_length=1)
    coverage: SourceCoverage = Field(default_factory=SourceCoverage)
    trust_score: float = Field(ge=0, le=1)
    update_frequency: str = Field(min_length=1)
    collection_method: CollectionMethod
    license_note: str = Field(min_length=1)
    review_status: ReviewStatus = "candidate"
    notes: str = ""

    @field_validator("source_id")
    @classmethod
    def source_id_is_slug_like(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        if any(c not in allowed for c in value):
            raise ValueError("source_id must contain only letters, numbers, hyphen, or underscore")
        return value


class SourceRegistryIssue(BaseModel):
    """Review issue found while auditing a source registry or pilot scope."""

    severity: IssueSeverity
    code: str
    message: str
    source_id: str | None = None


class SourceAuditScope(BaseModel):
    """Scope parameters used to produce a source registry audit."""

    data_category: str
    expected_provinces: list[str] = Field(default_factory=list)
    expected_years: list[int] = Field(default_factory=list)
    require_reviewed: bool = False


class SourceRegistryAudit(BaseModel):
    """Stable source registry audit report for pilot planning and CI checks."""

    scope: SourceAuditScope
    passed: bool
    issues: list[SourceRegistryIssue] = Field(default_factory=list)

    @property
    def errors(self) -> list[SourceRegistryIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[SourceRegistryIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def to_dict(self) -> dict:
        """Return a JSON-ready audit report."""
        return {
            "scope": self.scope.model_dump(),
            "passed": self.passed,
            "issues": [issue.model_dump() for issue in self.issues],
        }


class SourceRegistry(BaseModel):
    """Validated collection of data source entries."""

    sources: list[DataSource] = Field(default_factory=list)

    @field_validator("sources")
    @classmethod
    def source_ids_must_be_unique(cls, value: list[DataSource]) -> list[DataSource]:
        source_ids = [source.source_id for source in value]
        duplicates = sorted(
            {source_id for source_id in source_ids if source_ids.count(source_id) > 1}
        )
        if duplicates:
            raise ValueError(f"duplicate source_id values: {duplicates}")
        return value

    @classmethod
    def from_json_file(cls, path: Path | str) -> "SourceRegistry":
        with Path(path).open(encoding="utf-8") as f:
            payload = json.load(f)
        return cls.model_validate(payload)

    def get(self, source_id: str) -> DataSource | None:
        return next((source for source in self.sources if source.source_id == source_id), None)

    def require(self, source_id: str) -> DataSource:
        source = self.get(source_id)
        if source is None:
            raise KeyError(f"unknown data source: {source_id}")
        return source

    def by_category(self, category: str) -> list[DataSource]:
        return [source for source in self.sources if category in source.data_categories]

    def audit_scope(
        self,
        *,
        data_category: str,
        expected_provinces: list[str] | tuple[str, ...] = (),
        expected_years: list[int] | tuple[int, ...] = (),
        require_reviewed: bool = False,
    ) -> SourceRegistryAudit:
        """Audit whether registered sources can support a planned pilot scope."""
        issues: list[SourceRegistryIssue] = []
        scope = SourceAuditScope(
            data_category=data_category,
            expected_provinces=list(expected_provinces),
            expected_years=list(expected_years),
            require_reviewed=require_reviewed,
        )
        category_sources = self.by_category(data_category)
        if not category_sources:
            issues.append(
                SourceRegistryIssue(
                    severity="error",
                    code="missing_category_source",
                    message=f"no source covers data category: {data_category}",
                )
            )
            return SourceRegistryAudit(scope=scope, passed=False, issues=issues)

        for province in expected_provinces:
            matching_sources = [
                source
                for source in category_sources
                if _covers_province(source, province)
            ]
            if not matching_sources:
                issues.append(
                    SourceRegistryIssue(
                        severity="error",
                        code="missing_province_source",
                        message=f"no {data_category} source covers province: {province}",
                    )
                )
                continue

            issues.extend(
                _review_issues_for_sources(
                    matching_sources,
                    expected_years=expected_years,
                    require_reviewed=require_reviewed,
                )
            )

        return SourceRegistryAudit(
            scope=scope,
            passed=not any(issue.severity == "error" for issue in issues),
            issues=issues,
        )


def _covers_province(source: DataSource, province: str) -> bool:
    provinces = source.coverage.provinces
    return "全国" in provinces or province in provinces


def _review_issues_for_sources(
    sources: list[DataSource],
    *,
    expected_years: list[int] | tuple[int, ...],
    require_reviewed: bool,
) -> list[SourceRegistryIssue]:
    issues: list[SourceRegistryIssue] = []
    for source in sources:
        if require_reviewed and source.review_status not in ("reviewed", "approved"):
            issues.append(
                SourceRegistryIssue(
                    severity="warning",
                    code="source_not_reviewed",
                    source_id=source.source_id,
                    message=f"source is not reviewed or approved: {source.source_id}",
                )
            )
        if expected_years and not source.coverage.years:
            issues.append(
                SourceRegistryIssue(
                    severity="warning",
                    code="source_years_not_registered",
                    source_id=source.source_id,
                    message=f"source has no registered coverage years: {source.source_id}",
                )
            )
            continue

        missing_years = [
            year for year in expected_years if year not in source.coverage.years
        ]
        for year in missing_years:
            issues.append(
                SourceRegistryIssue(
                    severity="warning",
                    code="source_year_not_registered",
                    source_id=source.source_id,
                    message=f"source does not register coverage for year {year}",
                )
            )
    return issues
