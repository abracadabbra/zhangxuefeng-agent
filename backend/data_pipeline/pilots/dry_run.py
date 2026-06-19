"""In-memory pilot dry-run from reviewed sample rows to quality report."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.data_pipeline.collectors import ManualSnapshotCollector
from backend.data_pipeline.parsers import ManualSampleParser
from backend.data_pipeline.quality.checks import QualityGateConfig, run_quality_gate
from backend.data_pipeline.quality.candidates import CanonicalCandidate
from backend.data_pipeline.quality.report import QualityReport
from backend.data_pipeline.raw_store.manifest import RawSnapshotManifest
from backend.data_pipeline.sources.registry import DataSource


class PilotLoadNotReadyError(ValueError):
    """Raised when a pilot audit report is not ready for canonical loading."""

    def __init__(self, blockers: list[str]):
        self.blockers = blockers
        message = "pilot dry-run is not load-ready"
        if blockers:
            message = f"{message}: {'; '.join(blockers)}"
        super().__init__(message)


class PilotDryRunResult(BaseModel):
    """Auditable outcome for a no-write pilot data run."""

    snapshot_id: str
    source_id: str
    dataset: str
    candidate_count: int
    passed: bool
    load_ready: bool
    blockers: list[str] = Field(default_factory=list)
    source_validation_issues: list[str] = Field(default_factory=list)
    snapshot_file_issues: list[str] = Field(default_factory=list)
    coverage: dict[str, Any] = Field(default_factory=dict)
    issue_counts: dict[str, int] = Field(default_factory=dict)
    review_status: str
    review_notes: list[str] = Field(default_factory=list)
    quality_report: QualityReport

    def to_audit_dict(self) -> dict[str, Any]:
        """Return a stable JSON-ready report for review or CI checks."""
        return {
            "snapshot_id": self.snapshot_id,
            "source_id": self.source_id,
            "dataset": self.dataset,
            "candidate_count": self.candidate_count,
            "passed": self.passed,
            "load_ready": self.load_ready,
            "blockers": self.blockers,
            "source_validation_issues": self.source_validation_issues,
            "snapshot_file_issues": self.snapshot_file_issues,
            "coverage": self.coverage,
            "issue_counts": self.issue_counts,
            "review_status": self.review_status,
            "review_notes": self.review_notes,
            "issues": [
                issue.model_dump()
                for issue in self.quality_report.issues
            ],
        }


class PilotDryRunBundle(BaseModel):
    """JSON-like bundle accepted by the pilot dry-run entry points."""

    rows: list[dict]
    manifest: dict[str, Any]
    source: dict[str, Any] | None = None
    quality_config: dict[str, Any] | None = None


class PilotSnapshotDirBundle(BaseModel):
    """JSON-like bundle accepted with an external snapshot directory."""

    rows: list[dict]
    source: dict[str, Any] | None = None
    quality_config: dict[str, Any] | None = None
    manifest_name: str = "manifest.json"


def run_manual_pilot(
    rows: list[dict],
    manifest: RawSnapshotManifest,
    config: QualityGateConfig | None = None,
    *,
    source: DataSource | None = None,
    snapshot_file_issues: list[str] | tuple[str, ...] | None = None,
) -> PilotDryRunResult:
    """Parse reviewed manual rows and run quality checks without DB writes."""
    candidates = ManualSampleParser().parse(rows, manifest)
    quality_report = run_quality_gate(candidates, config)
    source_issues = _validate_source_manifest(source, manifest)
    file_issues = list(snapshot_file_issues or [])
    blockers = _build_blockers(quality_report, source_issues, file_issues)
    review_status, review_notes = _build_review_summary(
        blockers,
        quality_report,
    )

    return PilotDryRunResult(
        snapshot_id=manifest.snapshot_id,
        source_id=manifest.source_id,
        dataset=manifest.dataset,
        candidate_count=len(candidates),
        passed=not blockers,
        load_ready=not blockers,
        blockers=blockers,
        source_validation_issues=source_issues,
        snapshot_file_issues=file_issues,
        coverage=quality_report.coverage,
        issue_counts=_count_issues_by_severity(quality_report),
        review_status=review_status,
        review_notes=review_notes,
        quality_report=quality_report,
    )


def run_manual_pilot_payload(
    rows: list[dict],
    manifest_payload: dict[str, Any],
    config: QualityGateConfig | None = None,
    *,
    source_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a manual pilot from JSON-like payloads and return an audit dict."""
    manifest = RawSnapshotManifest.model_validate(manifest_payload)
    source = (
        DataSource.model_validate(source_payload)
        if source_payload is not None
        else None
    )
    return run_manual_pilot(
        rows,
        manifest,
        config,
        source=source,
    ).to_audit_dict()


def run_manual_pilot_snapshot_dir(
    rows: list[dict],
    snapshot_dir: Path | str,
    config: QualityGateConfig | None = None,
    *,
    source: DataSource | None = None,
    manifest_name: str = "manifest.json",
) -> PilotDryRunResult:
    """Run a no-write pilot from a reviewed local raw snapshot directory."""
    collected = ManualSnapshotCollector(snapshot_dir, manifest_name).collect()
    return run_manual_pilot(
        rows,
        collected.manifest,
        config,
        source=source,
        snapshot_file_issues=collected.file_issues,
    )


def run_manual_pilot_snapshot_dir_payload(
    rows: list[dict],
    snapshot_dir: Path | str,
    config: QualityGateConfig | None = None,
    *,
    source_payload: dict[str, Any] | None = None,
    manifest_name: str = "manifest.json",
) -> dict[str, Any]:
    """Run a local snapshot-dir pilot from JSON-like payloads."""
    source = (
        DataSource.model_validate(source_payload)
        if source_payload is not None
        else None
    )
    return run_manual_pilot_snapshot_dir(
        rows,
        snapshot_dir,
        config,
        source=source,
        manifest_name=manifest_name,
    ).to_audit_dict()


def run_manual_pilot_snapshot_dir_bundle(
    payload: dict[str, Any],
    snapshot_dir: Path | str,
) -> dict[str, Any]:
    """Run a manual pilot from one bundle plus a local snapshot directory."""
    bundle = PilotSnapshotDirBundle.model_validate(payload)
    config_payload = bundle.quality_config
    config = (
        QualityGateConfig.model_validate(config_payload)
        if config_payload is not None
        else None
    )
    return run_manual_pilot_snapshot_dir_payload(
        rows=bundle.rows,
        snapshot_dir=snapshot_dir,
        config=config,
        source_payload=bundle.source,
        manifest_name=bundle.manifest_name,
    )


def run_manual_pilot_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    """Run a manual pilot from one JSON-like bundle payload."""
    bundle = PilotDryRunBundle.model_validate(payload)
    config_payload = bundle.quality_config
    config = (
        QualityGateConfig.model_validate(config_payload)
        if config_payload is not None
        else None
    )
    return run_manual_pilot_payload(
        rows=bundle.rows,
        manifest_payload=bundle.manifest,
        config=config,
        source_payload=bundle.source,
    )


def assert_load_ready(audit: dict[str, Any] | PilotDryRunResult) -> None:
    """Raise if a dry-run audit report should not proceed to loader."""
    if isinstance(audit, PilotDryRunResult):
        load_ready = audit.load_ready
        blockers = audit.blockers
    else:
        load_ready = bool(audit.get("load_ready"))
        blockers = list(audit.get("blockers") or [])

    if not load_ready:
        raise PilotLoadNotReadyError(blockers)


def assert_loader_review_ready(audit: dict[str, Any] | PilotDryRunResult) -> None:
    """Raise unless an audit is ready for canonical loader approval."""
    assert_load_ready(audit)

    if isinstance(audit, PilotDryRunResult):
        review_status = audit.review_status
    else:
        review_status = audit.get("review_status")

    if review_status in (None, "ready_for_loader_review"):
        return

    raise PilotLoadNotReadyError([f"review_status:{review_status}"])


def build_load_ready_candidates(
    rows: list[dict],
    manifest: RawSnapshotManifest,
    config: QualityGateConfig | None = None,
    *,
    source: DataSource | None = None,
) -> list[CanonicalCandidate]:
    """Return parser candidates only after dry-run load readiness passes."""
    audit = run_manual_pilot(
        rows,
        manifest,
        config,
        source=source,
    )
    assert_load_ready(audit)
    return ManualSampleParser().parse(rows, manifest)


def build_load_ready_candidates_snapshot_dir(
    rows: list[dict],
    snapshot_dir: Path | str,
    config: QualityGateConfig | None = None,
    *,
    source: DataSource | None = None,
    manifest_name: str = "manifest.json",
) -> list[CanonicalCandidate]:
    """Return candidates from a local snapshot only after full audit passes."""
    collected = ManualSnapshotCollector(snapshot_dir, manifest_name).collect()
    audit = run_manual_pilot(
        rows,
        collected.manifest,
        config,
        source=source,
        snapshot_file_issues=collected.file_issues,
    )
    assert_load_ready(audit)
    return ManualSampleParser().parse(rows, collected.manifest)


def build_load_ready_candidates_bundle(
    payload: dict[str, Any],
) -> list[CanonicalCandidate]:
    """Return parser candidates from a bundle only after readiness passes."""
    bundle = PilotDryRunBundle.model_validate(payload)
    manifest = RawSnapshotManifest.model_validate(bundle.manifest)
    source_payload = bundle.source
    source = (
        DataSource.model_validate(source_payload)
        if source_payload is not None
        else None
    )
    config_payload = bundle.quality_config
    config = (
        QualityGateConfig.model_validate(config_payload)
        if config_payload is not None
        else None
    )
    return build_load_ready_candidates(
        bundle.rows,
        manifest,
        config,
        source=source,
    )


def _validate_source_manifest(
    source: DataSource | None,
    manifest: RawSnapshotManifest,
) -> list[str]:
    if source is None:
        return []

    issues = []
    if source.source_id != manifest.source_id:
        issues.append(
            f"manifest source_id {manifest.source_id} does not match source {source.source_id}"
        )
    if manifest.dataset not in source.data_categories:
        issues.append(f"manifest dataset {manifest.dataset} is not covered by source")
    if (
        source.coverage.years
        and manifest.published_year not in source.coverage.years
    ):
        issues.append(f"manifest year {manifest.published_year} is not covered by source")
    return issues


def _build_blockers(
    report: QualityReport,
    source_issues: list[str],
    snapshot_file_issues: list[str],
) -> list[str]:
    blockers = [f"source_validation:{issue}" for issue in source_issues]
    blockers.extend(f"snapshot_file:{issue}" for issue in snapshot_file_issues)
    blockers.extend(_coverage_blockers(report))
    blockers.extend(
        f"quality_error:{issue.code}"
        for issue in report.errors
    )
    return blockers


def _coverage_blockers(report: QualityReport) -> list[str]:
    coverage = report.coverage
    blockers = [
        f"coverage_missing:province:{province}"
        for province in coverage.get("missing_expected_provinces", [])
    ]
    blockers.extend(
        f"coverage_missing:year:{year}"
        for year in coverage.get("missing_expected_years", [])
    )
    return blockers


def _count_issues_by_severity(report: QualityReport) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in report.issues:
        counts[issue.severity] += 1
    return counts


def _build_review_summary(
    blockers: list[str],
    report: QualityReport,
) -> tuple[str, list[str]]:
    if blockers:
        return "blocked", [f"blocked by {blocker}" for blocker in blockers]

    warning_codes = sorted({issue.code for issue in report.warnings})
    if warning_codes:
        return (
            "needs_warning_review",
            [f"warning requires review: {code}" for code in warning_codes],
        )

    return "ready_for_loader_review", ["dry-run passed with no blockers or warnings"]
