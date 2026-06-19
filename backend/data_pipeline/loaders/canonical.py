"""Prototype loader for quality-gated canonical candidates."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.data_pipeline.lineage import create_lineage_record
from backend.data_pipeline.pilots import PilotLoadNotReadyError, assert_loader_review_ready
from backend.data_pipeline.quality.candidates import CanonicalCandidate
from backend.models.admission_score import AdmissionScore
from backend.models.enrollment_plan import EnrollmentPlan
from backend.models.major import Major
from backend.models.school import School


@dataclass(frozen=True)
class LoadResult:
    """Result of loading one candidate into canonical storage."""

    entity_type: str
    entity_id: int
    created: bool


def load_candidates(
    db: Session,
    candidates: list[CanonicalCandidate],
    *,
    parser_name: str,
    parser_version: str,
    quality_status: str = "passed",
) -> list[LoadResult]:
    """Load candidates and attach lineage records in the same transaction scope."""
    return [
        load_candidate(
            db,
            candidate,
            parser_name=parser_name,
            parser_version=parser_version,
            quality_status=quality_status,
        )
        for candidate in candidates
    ]


def load_candidates_after_audit(
    db: Session,
    candidates: list[CanonicalCandidate],
    audit: dict,
    *,
    parser_name: str,
    parser_version: str,
    quality_status: str = "passed",
) -> list[LoadResult]:
    """Load candidates only after a dry-run audit says they are load-ready."""
    assert_loader_review_ready(audit)
    return load_candidates(
        db,
        candidates,
        parser_name=parser_name,
        parser_version=parser_version,
        quality_status=quality_status,
    )


def load_candidates_after_artifact_manifest(
    db: Session,
    candidates: list[CanonicalCandidate],
    artifact_manifest: dict,
    *,
    parser_name: str,
    parser_version: str,
    quality_status: str = "passed",
) -> list[LoadResult]:
    """Load candidates only after the full pilot artifact manifest is ready."""
    _assert_artifact_manifest_ready(artifact_manifest)
    return load_candidates(
        db,
        candidates,
        parser_name=parser_name,
        parser_version=parser_version,
        quality_status=quality_status,
    )


def load_candidate(
    db: Session,
    candidate: CanonicalCandidate,
    *,
    parser_name: str,
    parser_version: str,
    quality_status: str = "passed",
) -> LoadResult:
    """Load one candidate into its canonical table and persist lineage."""
    if candidate.entity_type == "admission_score":
        result = _load_admission_score(db, candidate)
    elif candidate.entity_type == "enrollment_plan":
        result = _load_enrollment_plan(db, candidate)
    else:
        raise ValueError(f"unsupported candidate entity_type: {candidate.entity_type}")

    create_lineage_record(
        db,
        candidate,
        parser_name=parser_name,
        parser_version=parser_version,
        quality_status=quality_status,
        entity_id=result.entity_id,
    )
    return result


def _load_admission_score(db: Session, candidate: CanonicalCandidate) -> LoadResult:
    school = _require_school(db, candidate.natural_key.get("school_name"))
    major = _optional_major(db, candidate.natural_key.get("major_name"))

    row = (
        db.query(AdmissionScore)
        .filter(
            AdmissionScore.school_id == school.id,
            AdmissionScore.major_id == (major.id if major else None),
            AdmissionScore.province == candidate.natural_key.get("province"),
            AdmissionScore.year == candidate.natural_key.get("year"),
            AdmissionScore.batch == candidate.natural_key.get("batch"),
            AdmissionScore.subject_type == candidate.natural_key.get("subject_type"),
        )
        .first()
    )
    created = row is None
    if row is None:
        row = AdmissionScore(
            school_id=school.id,
            major_id=major.id if major else None,
            province=candidate.natural_key["province"],
            year=candidate.natural_key["year"],
            batch=candidate.natural_key["batch"],
            subject_type=candidate.natural_key["subject_type"],
        )
        db.add(row)

    _assign(
        row,
        candidate.values,
        ["min_score", "avg_score", "max_score", "min_rank", "plan_count"],
    )
    db.flush()
    return LoadResult(entity_type="admission_score", entity_id=row.id, created=created)


def _load_enrollment_plan(db: Session, candidate: CanonicalCandidate) -> LoadResult:
    school = _require_school(db, candidate.natural_key.get("school_name"))
    major = _require_major(db, candidate.natural_key.get("major_name"))

    row = (
        db.query(EnrollmentPlan)
        .filter(
            EnrollmentPlan.school_id == school.id,
            EnrollmentPlan.major_id == major.id,
            EnrollmentPlan.province == candidate.natural_key.get("province"),
            EnrollmentPlan.year == candidate.natural_key.get("year"),
        )
        .first()
    )
    created = row is None
    if row is None:
        row = EnrollmentPlan(
            school_id=school.id,
            major_id=major.id,
            province=candidate.natural_key["province"],
            year=candidate.natural_key["year"],
        )
        db.add(row)

    _assign(
        row,
        candidate.values,
        ["plan_count", "subject_requirement", "batch", "duration", "tuition"],
    )
    db.flush()
    return LoadResult(entity_type="enrollment_plan", entity_id=row.id, created=created)


def _require_school(db: Session, name: object) -> School:
    if not isinstance(name, str) or not name:
        raise ValueError("candidate is missing school_name")
    school = db.query(School).filter(School.name == name).first()
    if school is None:
        raise ValueError(f"unknown school_name: {name}")
    return school


def _require_major(db: Session, name: object) -> Major:
    if not isinstance(name, str) or not name:
        raise ValueError("candidate is missing major_name")
    major = db.query(Major).filter(Major.name == name).first()
    if major is None:
        raise ValueError(f"unknown major_name: {name}")
    return major


def _optional_major(db: Session, name: object) -> Major | None:
    if name is None or name == "":
        return None
    return _require_major(db, name)


def _assign(row: object, values: dict, fields: list[str]) -> None:
    for field in fields:
        if field in values:
            setattr(row, field, values[field])


def _assert_artifact_manifest_ready(artifact_manifest: dict) -> None:
    if artifact_manifest.get("ready_for_loader_execution") is True:
        return

    blockers = list(artifact_manifest.get("required_reviews") or [])
    for field in (
        "artifact_path_issues",
        "intake_review_issues",
        "artifact_scope_issues",
        "loader_approval_issues",
    ):
        blockers.extend(f"{field}:{issue}" for issue in artifact_manifest.get(field) or [])
    if not blockers:
        blockers = ["artifact_manifest:not_ready"]
    raise PilotLoadNotReadyError(blockers)
