"""Manual local snapshot collector.

This collector reads a reviewed snapshot directory from disk. It does not
download, crawl, or mutate source files.
"""

import json
from pathlib import Path

from backend.data_pipeline.collectors.base import CollectedSnapshot
from backend.data_pipeline.raw_store.checksums import verify_manifest_files
from backend.data_pipeline.raw_store.manifest import RawSnapshotManifest


class ManualSnapshotCollector:
    """Collect a manually prepared raw snapshot directory."""

    def __init__(self, snapshot_dir: Path | str, manifest_name: str = "manifest.json"):
        self.snapshot_dir = Path(snapshot_dir)
        self.manifest_name = manifest_name

    def collect(self) -> CollectedSnapshot:
        """Load the manifest and verify all referenced local files."""
        manifest_path = self.snapshot_dir / self.manifest_name
        with manifest_path.open(encoding="utf-8") as f:
            payload = json.load(f)

        manifest = RawSnapshotManifest.model_validate(payload)
        issues = tuple(verify_manifest_files(self.snapshot_dir, manifest))
        return CollectedSnapshot(
            root_dir=self.snapshot_dir,
            manifest=manifest,
            file_issues=issues,
        )
