"""Base parser protocol for raw snapshot candidates."""

from typing import Protocol

from backend.data_pipeline.quality.candidates import CanonicalCandidate
from backend.data_pipeline.raw_store.manifest import RawSnapshotManifest


class CandidateParser(Protocol):
    """Parser interface that turns raw rows into canonical candidates."""

    def parse(self, rows: list[dict], manifest: RawSnapshotManifest) -> list[CanonicalCandidate]:
        """Parse raw rows from one snapshot into canonical candidates."""
