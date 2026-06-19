"""Raw snapshot collector interfaces and local MVP collectors."""

from backend.data_pipeline.collectors.base import CollectedSnapshot, SnapshotCollector
from backend.data_pipeline.collectors.manual import ManualSnapshotCollector

__all__ = [
    "CollectedSnapshot",
    "ManualSnapshotCollector",
    "SnapshotCollector",
]
