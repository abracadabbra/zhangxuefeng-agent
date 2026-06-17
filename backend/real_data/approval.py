"""Manual approval artifacts for audited real-data pilot outputs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.real_data.adapter import AdmissionQuery, query_admission_records_from_manifest
from backend.real_data.manifest import (
    StagingManifestEntry,
    load_staging_manifest,
)

ApprovalDecision = Literal["approved", "rejected"]


class ManualApprovalWriteError(ValueError):
    """Raised when a manual approval artifact cannot be written safely."""


class ManualApprovalReadError(ValueError):
    """Raised when a manual approval artifact cannot be trusted."""


class ManualApprovalChecklist(BaseModel):
    """Human review checklist required before approving real-data pilot outputs."""

    source_verified: bool
    snapshot_verified: bool
    quality_reviewed: bool
    citation_reviewed: bool
    no_production_writes_verified: bool

    def all_checked(self) -> bool:
        """Return whether every approval checklist item is checked."""

        return all(
            (
                self.source_verified,
                self.snapshot_verified,
                self.quality_reviewed,
                self.citation_reviewed,
                self.no_production_writes_verified,
            )
        )


class ManualApprovalArtifactPayload(BaseModel):
    """Manual approval record tied to a validated staging manifest."""

    schema_version: Literal["real_data_manual_approval.v1"]
    manifest_path: Path
    manifest_artifacts: tuple[StagingManifestEntry, ...] = Field(min_length=1)
    citation_record_count: int = Field(ge=0)
    reviewer: str = Field(min_length=1)
    reviewed_at: datetime
    decision: ApprovalDecision
    checklist: ManualApprovalChecklist
    notes: str = ""

    @field_validator("reviewed_at")
    @classmethod
    def validate_reviewed_at_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must include timezone information")
        return value

    @model_validator(mode="after")
    def validate_approval_checklist(self) -> ManualApprovalArtifactPayload:
        if self.decision == "approved" and not self.checklist.all_checked():
            raise ValueError("approved decision requires every checklist item")
        if (
            self.decision == "approved"
            and any(artifact.quality_status == "warning" for artifact in self.manifest_artifacts)
            and not self.notes.strip()
        ):
            raise ValueError("approved warning artifacts require reviewer notes")
        return self


def write_manual_approval_artifact(
    *,
    approval_path: Path,
    manifest_path: Path,
    reviewer: str,
    reviewed_at: datetime,
    decision: ApprovalDecision,
    checklist: ManualApprovalChecklist,
    notes: str = "",
    overwrite: bool = False,
) -> ManualApprovalArtifactPayload:
    """Write a manual approval artifact after validating its staging manifest."""

    if approval_path.exists() and not overwrite:
        raise FileExistsError(f"manual approval artifact already exists: {approval_path}")

    try:
        payload = _payload_from_manifest(
            manifest_path=manifest_path,
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            decision=decision,
            checklist=checklist,
            notes=notes,
        )
    except ValueError as exc:
        raise ManualApprovalWriteError(f"invalid manual approval: {approval_path}") from exc

    approval_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = approval_path.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(approval_path)
    return payload


def load_manual_approval_artifact(approval_path: Path) -> ManualApprovalArtifactPayload:
    """Read an approval artifact and revalidate the referenced staging manifest."""

    try:
        raw_payload = json.loads(approval_path.read_text(encoding="utf-8"))
        payload = ManualApprovalArtifactPayload.model_validate(raw_payload)
        resolved_manifest_path = _resolve_manifest_path(approval_path, payload.manifest_path)
        expected = _payload_from_manifest(
            manifest_path=resolved_manifest_path,
            reviewer=payload.reviewer,
            reviewed_at=payload.reviewed_at,
            decision=payload.decision,
            checklist=payload.checklist,
            notes=payload.notes,
            stored_manifest_path=payload.manifest_path,
        )
        if payload != expected:
            raise ValueError("manual approval does not match staging manifest")
        return payload
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ManualApprovalReadError(f"invalid manual approval artifact: {approval_path}") from exc


def _payload_from_manifest(
    *,
    manifest_path: Path,
    reviewer: str,
    reviewed_at: datetime,
    decision: ApprovalDecision,
    checklist: ManualApprovalChecklist,
    notes: str,
    stored_manifest_path: Path | None = None,
) -> ManualApprovalArtifactPayload:
    manifest = load_staging_manifest(manifest_path)
    query_result = query_admission_records_from_manifest(manifest_path, AdmissionQuery())
    return ManualApprovalArtifactPayload(
        schema_version="real_data_manual_approval.v1",
        manifest_path=stored_manifest_path or manifest_path,
        manifest_artifacts=manifest.artifacts,
        citation_record_count=query_result.total,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        decision=decision,
        checklist=checklist,
        notes=notes,
    )


def _resolve_manifest_path(approval_path: Path, manifest_path: Path) -> Path:
    if manifest_path.is_absolute():
        return manifest_path
    return approval_path.parent / manifest_path
