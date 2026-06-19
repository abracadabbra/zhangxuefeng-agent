"""Load quality-gated candidates into canonical tables."""

from backend.data_pipeline.loaders.approval import (
    LoaderApprovalPacket,
    build_loader_approval_packet,
)
from backend.data_pipeline.loaders.canonical import (
    LoadResult,
    load_candidate,
    load_candidates,
    load_candidates_after_audit,
    load_candidates_after_artifact_manifest,
)

__all__ = [
    "LoaderApprovalPacket",
    "LoadResult",
    "build_loader_approval_packet",
    "load_candidate",
    "load_candidates",
    "load_candidates_after_audit",
    "load_candidates_after_artifact_manifest",
]
