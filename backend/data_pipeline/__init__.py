"""Contracts for the auditable real-data pipeline."""

from typing import Any

__all__ = ["DataSource", "RawSnapshotManifest", "SourceRegistry"]


def __getattr__(name: str) -> Any:
    """Lazily expose pipeline contracts without forcing optional imports."""
    if name == "DataSource":
        from backend.data_pipeline.sources.registry import DataSource

        return DataSource
    if name == "SourceRegistry":
        from backend.data_pipeline.sources.registry import SourceRegistry

        return SourceRegistry
    if name == "RawSnapshotManifest":
        from backend.data_pipeline.raw_store.manifest import RawSnapshotManifest

        return RawSnapshotManifest
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
