"""Quality gate report models."""

from typing import Any, Literal

from pydantic import BaseModel, Field


IssueSeverity = Literal["error", "warning", "info"]


class QualityIssue(BaseModel):
    """One quality finding emitted by the MVP quality gate."""

    severity: IssueSeverity
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    candidate_index: int | None = None
    field: str | None = None


class QualityReport(BaseModel):
    """Aggregated result of candidate quality checks."""

    issues: list[QualityIssue] = Field(default_factory=list)
    coverage: dict[str, Any] = Field(default_factory=dict)

    @property
    def errors(self) -> list[QualityIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[QualityIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def passed(self) -> bool:
        return not self.errors
