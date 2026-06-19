"""Parser contracts for raw snapshot data."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.data_pipeline.parsers.base import CandidateParser
    from backend.data_pipeline.parsers.manual_samples import ManualSampleParser
    from backend.data_pipeline.parsers.tabular_samples import (
        ReviewedTabularSampleParser,
    )

__all__ = [
    "CandidateParser",
    "ManualSampleParser",
    "ReviewedTabularSampleParser",
    "normalize_tabular_row",
    "normalize_tabular_rows",
]


def __getattr__(name: str) -> Any:
    if name == "CandidateParser":
        from backend.data_pipeline.parsers.base import CandidateParser

        return CandidateParser
    if name == "ManualSampleParser":
        from backend.data_pipeline.parsers.manual_samples import ManualSampleParser

        return ManualSampleParser
    if name in {
        "ReviewedTabularSampleParser",
        "normalize_tabular_row",
        "normalize_tabular_rows",
    }:
        from backend.data_pipeline.parsers import tabular_samples

        return getattr(tabular_samples, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
