"""End-to-end artifact bundle orchestration for reviewed admission pilots."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from backend.real_data.manifest import (
    StagingManifestPayload,
    load_manifest_reference_candidates,
    write_staging_manifest,
)
from backend.real_data.pilot import (
    ReviewedAdmissionPilotResult,
    run_reviewed_admission_pilot_from_artifact,
)


class ReviewedAdmissionPilotBundleResult(BaseModel):
    """Artifacts produced by one isolated reviewed-row admission pilot run."""

    pilot_result: ReviewedAdmissionPilotResult
    manifest_path: Path | None = None
    manifest: StagingManifestPayload | None = None


def run_reviewed_admission_pilot_bundle_from_artifact(
    *,
    reviewed_rows_artifact_path: Path,
    province: str,
    year: int,
    batch: str,
    subject_type: str,
    output_dir: Path,
    reference_manifest_path: Path | None = None,
    expected_schools: tuple[str, ...] = (),
    expected_min_records: int = 1,
    overwrite: bool = False,
) -> ReviewedAdmissionPilotBundleResult:
    """Run reviewed rows to staging, then register the staging artifact in a manifest."""

    staging_dir = output_dir / "staging"
    manifest_path = output_dir / "staging_manifest.json"
    reference_candidates = (
        load_manifest_reference_candidates(reference_manifest_path)
        if reference_manifest_path is not None
        else ()
    )
    pilot_result = run_reviewed_admission_pilot_from_artifact(
        reviewed_rows_artifact_path=reviewed_rows_artifact_path,
        province=province,
        year=year,
        batch=batch,
        subject_type=subject_type,
        output_dir=staging_dir,
        reference_candidates=reference_candidates,
        expected_schools=expected_schools,
        expected_min_records=expected_min_records,
        overwrite=overwrite,
    )
    if pilot_result.artifact is None:
        return ReviewedAdmissionPilotBundleResult(pilot_result=pilot_result)

    manifest = write_staging_manifest(
        manifest_path=manifest_path,
        artifact_paths=[pilot_result.artifact.artifact_path],
        overwrite=overwrite,
    )
    return ReviewedAdmissionPilotBundleResult(
        pilot_result=pilot_result,
        manifest_path=manifest_path,
        manifest=manifest,
    )
