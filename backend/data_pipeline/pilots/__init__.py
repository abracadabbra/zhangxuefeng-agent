"""Pilot dry-run helpers for reviewed real-data samples."""

from typing import Any

__all__ = [
    "PilotArtifactManifest",
    "PilotDryRunResult",
    "PilotDryRunBundle",
    "PilotLoadNotReadyError",
    "PilotSnapshotDirBundle",
    "assert_loader_review_ready",
    "assert_load_ready",
    "build_pilot_artifact_manifest",
    "build_load_ready_candidates",
    "build_load_ready_candidates_bundle",
    "build_load_ready_candidates_snapshot_dir",
    "run_manual_pilot",
    "run_manual_pilot_bundle",
    "run_manual_pilot_payload",
    "run_manual_pilot_snapshot_dir",
    "run_manual_pilot_snapshot_dir_bundle",
    "run_manual_pilot_snapshot_dir_payload",
]


def __getattr__(name: str) -> Any:
    """Lazily expose pilot helpers without forcing pydantic imports."""
    if name in {"PilotArtifactManifest", "build_pilot_artifact_manifest"}:
        from backend.data_pipeline.pilots import artifacts

        return getattr(artifacts, name)
    if name in {
        "PilotDryRunResult",
        "PilotDryRunBundle",
        "PilotLoadNotReadyError",
        "PilotSnapshotDirBundle",
        "assert_loader_review_ready",
        "assert_load_ready",
        "build_load_ready_candidates",
        "build_load_ready_candidates_bundle",
        "build_load_ready_candidates_snapshot_dir",
        "run_manual_pilot",
        "run_manual_pilot_bundle",
        "run_manual_pilot_payload",
        "run_manual_pilot_snapshot_dir",
        "run_manual_pilot_snapshot_dir_bundle",
        "run_manual_pilot_snapshot_dir_payload",
    }:
        from backend.data_pipeline.pilots import dry_run

        return getattr(dry_run, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
