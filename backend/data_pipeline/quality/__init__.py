"""Quality gate contracts for parsed real-data candidates."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.data_pipeline.quality.candidates import (
        CandidateReviewMetadata,
        CandidateSource,
        CanonicalCandidate,
    )
    from backend.data_pipeline.quality.checks import (
        QualityGateConfig,
        run_quality_gate,
    )
    from backend.data_pipeline.quality.report import QualityIssue, QualityReport

__all__ = [
    "CandidateSource",
    "CandidateReviewMetadata",
    "CanonicalCandidate",
    "QualityGateConfig",
    "QualityIssue",
    "QualityReport",
    "run_quality_gate",
]


def __getattr__(name: str) -> Any:
    """Lazily expose pydantic-backed quality contracts."""
    if name in {
        "CandidateSource",
        "CandidateReviewMetadata",
        "CanonicalCandidate",
    }:
        from backend.data_pipeline.quality import candidates

        return getattr(candidates, name)
    if name in {"QualityGateConfig", "run_quality_gate"}:
        from backend.data_pipeline.quality import checks

        return getattr(checks, name)
    if name in {"QualityIssue", "QualityReport"}:
        from backend.data_pipeline.quality import report

        return getattr(report, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
