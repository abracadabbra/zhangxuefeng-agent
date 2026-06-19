"""Data source registry contracts."""

from typing import Any

__all__ = [
    "DataSource",
    "SourceCoverage",
    "SourceRegistry",
    "SourceRegistryAudit",
    "SourceRegistryIssue",
]


def __getattr__(name: str) -> Any:
    """Lazily expose source contracts without forcing pydantic imports."""
    if name == "DataSource":
        from backend.data_pipeline.sources.registry import DataSource

        return DataSource
    if name == "SourceCoverage":
        from backend.data_pipeline.sources.registry import SourceCoverage

        return SourceCoverage
    if name == "SourceRegistry":
        from backend.data_pipeline.sources.registry import SourceRegistry

        return SourceRegistry
    if name == "SourceRegistryAudit":
        from backend.data_pipeline.sources.registry import SourceRegistryAudit

        return SourceRegistryAudit
    if name == "SourceRegistryIssue":
        from backend.data_pipeline.sources.registry import SourceRegistryIssue

        return SourceRegistryIssue
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
