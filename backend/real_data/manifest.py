"""Manifest contracts for discoverable real-data staging artifacts."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.real_data.contracts import CanonicalAdmissionCandidate
from backend.real_data.staging import (
    StagingArtifactPayload,
    load_admission_staging_artifact,
)


class StagingManifestWriteError(ValueError):
    """Raised when staging artifacts cannot be registered safely."""


class StagingManifestReadError(ValueError):
    """Raised when a staging manifest cannot be trusted."""


class StagingManifestEntry(BaseModel):
    """One validated staging artifact registered for read-only discovery."""

    artifact_path: Path
    source_page_id: str = Field(min_length=1)
    source_batch_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    province: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    quality_status: Literal["pass", "warning"]
    quality_report_id: str = Field(min_length=1)
    candidate_count: int = Field(ge=0)


class StagingManifestPayload(BaseModel):
    """Validated manifest of staging artifacts available for read-only queries."""

    schema_version: Literal["real_data_staging_manifest.v1"]
    artifacts: tuple[StagingManifestEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_snapshots(self) -> StagingManifestPayload:
        seen: set[tuple[str, str]] = set()
        for artifact in self.artifacts:
            key = (artifact.source_batch_id, artifact.snapshot_id)
            if key in seen:
                raise ValueError("duplicate artifact snapshot in manifest")
            seen.add(key)
        return self


def write_staging_manifest(
    *,
    manifest_path: Path,
    artifact_paths: Sequence[Path],
    overwrite: bool = False,
) -> StagingManifestPayload:
    """Write a discoverable manifest after validating each staging artifact."""

    if not artifact_paths:
        raise StagingManifestWriteError("manifest requires at least one artifact")
    if manifest_path.exists() and not overwrite:
        raise FileExistsError(f"staging manifest already exists: {manifest_path}")

    try:
        payload = StagingManifestPayload(
            schema_version="real_data_staging_manifest.v1",
            artifacts=tuple(
                _entry_from_payload(
                    artifact_path=artifact_path,
                    payload=load_admission_staging_artifact(artifact_path),
                )
                for artifact_path in artifact_paths
            ),
        )
    except ValueError as exc:
        raise StagingManifestWriteError(f"invalid staging manifest: {manifest_path}") from exc

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = manifest_path.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(manifest_path)
    return payload


def load_staging_manifest(manifest_path: Path) -> StagingManifestPayload:
    """Read a manifest and revalidate every referenced staging artifact."""

    try:
        raw_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload = StagingManifestPayload.model_validate(raw_payload)
        for entry in payload.artifacts:
            artifact_path = _resolve_artifact_path(manifest_path, entry.artifact_path)
            actual = _entry_from_payload(
                artifact_path=entry.artifact_path,
                payload=load_admission_staging_artifact(artifact_path),
            )
            if entry != actual:
                raise ValueError("manifest entry does not match staging artifact")
        return payload
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise StagingManifestReadError(f"invalid staging manifest: {manifest_path}") from exc


def iter_manifest_artifact_paths(manifest_path: Path) -> tuple[Path, ...]:
    """Return resolved artifact paths from a trusted staging manifest."""

    payload = load_staging_manifest(manifest_path)
    return tuple(
        _resolve_artifact_path(manifest_path, entry.artifact_path)
        for entry in payload.artifacts
    )


def load_manifest_reference_candidates(
    manifest_path: Path,
) -> tuple[CanonicalAdmissionCandidate, ...]:
    """Load canonical candidates from every artifact in a trusted staging manifest."""

    return tuple(
        candidate
        for artifact_path in iter_manifest_artifact_paths(manifest_path)
        for candidate in load_admission_staging_artifact(artifact_path).candidates
    )


def _entry_from_payload(
    *,
    artifact_path: Path,
    payload: StagingArtifactPayload,
) -> StagingManifestEntry:
    quality_status = payload.quality_report.status
    if quality_status == "blocked":
        raise ValueError("blocked quality report cannot be registered in manifest")

    return StagingManifestEntry(
        artifact_path=artifact_path,
        source_page_id=payload.source_page.source_page_id,
        source_batch_id=payload.snapshot.source_batch_id,
        snapshot_id=payload.snapshot.snapshot_id,
        province=payload.source_page.province,
        year=payload.source_page.year,
        quality_status=quality_status,
        quality_report_id=payload.quality_report.report_id,
        candidate_count=len(payload.candidates),
    )


def _resolve_artifact_path(manifest_path: Path, artifact_path: Path) -> Path:
    if artifact_path.is_absolute():
        return artifact_path
    return manifest_path.parent / artifact_path
