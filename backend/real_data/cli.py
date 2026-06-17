"""Dry-run CLI for isolated real admission-data pilot bundles."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.real_data.adapter import (
    AdmissionQuery,
    query_admission_records_from_approval,
    query_admission_records_from_manifest,
)
from backend.real_data.approval import (
    ManualApprovalChecklist,
    load_manual_approval_artifact,
    write_manual_approval_artifact,
)
from backend.real_data.bundle import run_reviewed_admission_pilot_bundle_from_artifact
from backend.real_data.manifest import load_staging_manifest
from backend.real_data.staging import load_admission_staging_artifact


def build_parser() -> argparse.ArgumentParser:
    """Build the isolated real-data pilot CLI parser."""

    parser = argparse.ArgumentParser(
        description="Run isolated real-data pilot dry-runs without DB, seed, or Agent writes."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    bundle = subparsers.add_parser(
        "bundle-dry-run",
        help="Run reviewed raw rows through quality, staging, manifest, and citation projection.",
    )
    bundle.add_argument("--reviewed-rows-artifact", required=True, type=Path)
    bundle.add_argument("--output-dir", required=True, type=Path)
    bundle.add_argument("--province", required=True)
    bundle.add_argument("--year", required=True, type=int)
    bundle.add_argument("--batch", required=True)
    bundle.add_argument("--subject-type", required=True)
    bundle.add_argument("--reference-manifest", type=Path)
    bundle.add_argument("--expected-school", action="append", default=[])
    bundle.add_argument("--expected-min-records", type=int, default=1)
    bundle.add_argument("--overwrite", action="store_true")

    approval = subparsers.add_parser(
        "approve-manifest",
        help="Write a manual approval artifact for a validated staging manifest.",
    )
    approval.add_argument("--manifest", required=True, type=Path)
    approval.add_argument("--approval-output", required=True, type=Path)
    approval.add_argument("--reviewer", required=True)
    approval.add_argument("--reviewed-at", required=True)
    approval.add_argument("--decision", choices=("approved", "rejected"), required=True)
    approval.add_argument("--notes", default="")
    approval.add_argument("--source-verified", action="store_true")
    approval.add_argument("--snapshot-verified", action="store_true")
    approval.add_argument("--quality-reviewed", action="store_true")
    approval.add_argument("--citation-reviewed", action="store_true")
    approval.add_argument("--no-production-writes-verified", action="store_true")
    approval.add_argument("--overwrite", action="store_true")

    verify = subparsers.add_parser(
        "verify-approval",
        help="Read and revalidate a manual approval artifact.",
    )
    verify.add_argument("--approval-artifact", required=True, type=Path)

    query = subparsers.add_parser(
        "query-approved",
        help="Query citation records through a verified manual approval artifact.",
    )
    query.add_argument("--approval-artifact", required=True, type=Path)
    _add_query_args(query)

    audit = subparsers.add_parser(
        "audit-approved",
        help="Emit a full audit summary for a verified approved real-data artifact chain.",
    )
    audit.add_argument("--approval-artifact", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the isolated real-data dry-run CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "bundle-dry-run":
        return _run_bundle_dry_run(args)
    if args.command == "approve-manifest":
        return _run_approve_manifest(args)
    if args.command == "verify-approval":
        return _run_verify_approval(args)
    if args.command == "query-approved":
        return _run_query_approved(args)
    if args.command == "audit-approved":
        return _run_audit_approved(args)

    parser.error(f"unknown command: {args.command}")
    return 2


def _run_bundle_dry_run(args: argparse.Namespace) -> int:
    try:
        result = run_reviewed_admission_pilot_bundle_from_artifact(
            reviewed_rows_artifact_path=args.reviewed_rows_artifact,
            province=args.province,
            year=args.year,
            batch=args.batch,
            subject_type=args.subject_type,
            output_dir=args.output_dir,
            reference_manifest_path=args.reference_manifest,
            expected_schools=tuple(args.expected_school),
            expected_min_records=args.expected_min_records,
            overwrite=args.overwrite,
        )
        print(
            json.dumps(
                _summary_from_result(result),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    except Exception as exc:
        print(f"real-data dry-run failed: {exc}", file=sys.stderr)
        return 1

    return 0


def _run_approve_manifest(args: argparse.Namespace) -> int:
    try:
        approval = write_manual_approval_artifact(
            approval_path=args.approval_output,
            manifest_path=args.manifest,
            reviewer=args.reviewer,
            reviewed_at=datetime.fromisoformat(args.reviewed_at),
            decision=args.decision,
            checklist=ManualApprovalChecklist(
                source_verified=args.source_verified,
                snapshot_verified=args.snapshot_verified,
                quality_reviewed=args.quality_reviewed,
                citation_reviewed=args.citation_reviewed,
                no_production_writes_verified=args.no_production_writes_verified,
            ),
            notes=args.notes,
            overwrite=args.overwrite,
        )
        print(json.dumps(_approval_summary(approval), ensure_ascii=False, indent=2, sort_keys=True))
    except Exception as exc:
        print(f"real-data approval failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_verify_approval(args: argparse.Namespace) -> int:
    try:
        approval = load_manual_approval_artifact(args.approval_artifact)
        print(json.dumps(_approval_summary(approval), ensure_ascii=False, indent=2, sort_keys=True))
    except Exception as exc:
        print(f"real-data approval verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_query_approved(args: argparse.Namespace) -> int:
    try:
        query = _query_from_args(args)
        result = query_admission_records_from_approval(args.approval_artifact, query)
        print(
            json.dumps(
                _query_summary(result),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    except Exception as exc:
        print(f"real-data approved query failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_audit_approved(args: argparse.Namespace) -> int:
    try:
        approval = load_manual_approval_artifact(args.approval_artifact)
        result = query_admission_records_from_approval(args.approval_artifact, AdmissionQuery())
        manifest_path = _resolve_manifest_path(args.approval_artifact, approval.manifest_path)
        manifest = load_staging_manifest(manifest_path)
        print(
            json.dumps(
                _approval_audit_summary(
                    approval=approval,
                    approval_artifact_path=args.approval_artifact,
                    manifest_path=manifest_path,
                    manifest=manifest,
                    query_result=result,
                ),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    except Exception as exc:
        print(f"real-data approved audit failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _add_query_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--province")
    parser.add_argument("--year", type=int)
    parser.add_argument("--school-name")
    parser.add_argument("--major-keyword")
    parser.add_argument("--batch")
    parser.add_argument("--subject-type")
    parser.add_argument("--min-score-at-least", type=int)
    parser.add_argument("--min-score-at-most", type=int)


def _query_from_args(args: argparse.Namespace) -> AdmissionQuery:
    return AdmissionQuery(
        province=args.province,
        year=args.year,
        school_name=args.school_name,
        major_keyword=args.major_keyword,
        batch=args.batch,
        subject_type=args.subject_type,
        min_score_at_least=args.min_score_at_least,
        min_score_at_most=args.min_score_at_most,
    )


def _summary_from_result(result: Any) -> dict[str, Any]:
    pilot = result.pilot_result
    quality_report = pilot.quality_report
    source_page = pilot.source_page
    snapshot = pilot.snapshot
    summary: dict[str, Any] = {
        "quality_status": quality_report.status,
        "quality_report_id": quality_report.report_id,
        "schema_status": pilot.schema_report.status,
        "source": {
            "source_page_id": source_page.source_page_id,
            "source_name": source_page.source_name,
            "source_type": source_page.source_type,
            "source_url": source_page.source_url,
            "province": source_page.province,
            "year": source_page.year,
        },
        "snapshot": {
            "source_batch_id": snapshot.source_batch_id,
            "snapshot_id": snapshot.snapshot_id,
            "raw_file_name": snapshot.raw_file_name,
            "raw_file_url": snapshot.raw_file_url,
            "raw_file_sha256": snapshot.raw_file_sha256,
            "captured_at": snapshot.captured_at.isoformat(),
            "operator": snapshot.operator,
        },
        "record_count_raw": quality_report.record_count_raw,
        "record_count_parsed": quality_report.record_count_parsed,
        "record_count_passed": quality_report.record_count_passed,
        "blocked_reasons": list(quality_report.blocked_reasons),
        "coverage": quality_report.coverage_metrics.model_dump(mode="json"),
        "freshness_result": quality_report.freshness_result,
        "confidence_summary": quality_report.confidence_summary,
        "issues": {
            "field_errors": [_issue_summary(issue) for issue in quality_report.field_errors],
            "range_errors": [_issue_summary(issue) for issue in quality_report.range_errors],
            "duplicate_conflicts": [
                _issue_summary(issue) for issue in quality_report.duplicate_conflicts
            ],
            "cross_source_conflicts": [
                _issue_summary(issue) for issue in quality_report.cross_source_conflicts
            ],
            "warnings": [_issue_summary(issue) for issue in quality_report.warning_issues],
        },
        "staging_artifact_path": (
            str(pilot.artifact.artifact_path) if pilot.artifact is not None else None
        ),
        "manifest_path": str(result.manifest_path) if result.manifest_path is not None else None,
        "manifest_artifact_count": len(result.manifest.artifacts) if result.manifest else 0,
        "citation_record_count": 0,
        "sample_citation": None,
    }
    if result.manifest_path is None:
        return summary

    query_result = query_admission_records_from_manifest(result.manifest_path, AdmissionQuery())
    summary["citation_record_count"] = query_result.total
    if query_result.records:
        record = query_result.records[0]
        summary["sample_citation"] = {
            "source": record.source,
            "source_url": record.source_url,
            "snapshot_url": record.snapshot_url,
            "year": record.year,
            "snapshot": record.snapshot,
            "confidence": record.confidence,
            "source_batch_id": record.source_batch_id,
        }
    return summary


def _issue_summary(issue: Any) -> dict[str, Any]:
    return {
        "level": issue.level,
        "code": issue.code,
        "message": issue.message,
        "raw_row_number": issue.raw_row_number,
    }


def _approval_summary(approval: Any) -> dict[str, Any]:
    return {
        "schema_version": approval.schema_version,
        "manifest_path": str(approval.manifest_path),
        "manifest_artifact_count": len(approval.manifest_artifacts),
        "citation_record_count": approval.citation_record_count,
        "reviewer": approval.reviewer,
        "reviewed_at": approval.reviewed_at.isoformat(),
        "decision": approval.decision,
        "checklist": approval.checklist.model_dump(mode="json"),
        "notes": approval.notes,
    }


def _query_summary(result: Any) -> dict[str, Any]:
    return {
        "total": result.total,
        "records": [record.model_dump(mode="json") for record in result.records],
    }


def _approval_audit_summary(
    *,
    approval: Any,
    approval_artifact_path: Path,
    manifest_path: Path,
    manifest: Any,
    query_result: Any,
) -> dict[str, Any]:
    artifact_summaries = []
    for entry in manifest.artifacts:
        artifact_path = _resolve_artifact_path(manifest_path, entry.artifact_path)
        payload = load_admission_staging_artifact(artifact_path)
        quality_report = payload.quality_report
        artifact_summaries.append(
            {
                "artifact_path": str(entry.artifact_path),
                "resolved_artifact_path": str(artifact_path),
                "source": payload.source_page.source_name,
                "source_url": payload.source_page.source_url,
                "snapshot_url": payload.snapshot.raw_file_url,
                "raw_file_sha256": payload.snapshot.raw_file_sha256,
                "captured_at": payload.snapshot.captured_at.isoformat(),
                "operator": payload.snapshot.operator,
                "province": entry.province,
                "year": entry.year,
                "source_batch_id": entry.source_batch_id,
                "snapshot_id": entry.snapshot_id,
                "quality_status": quality_report.status,
                "quality_report_id": quality_report.report_id,
                "record_count_raw": quality_report.record_count_raw,
                "record_count_parsed": quality_report.record_count_parsed,
                "record_count_passed": quality_report.record_count_passed,
                "coverage": quality_report.coverage_metrics.model_dump(mode="json"),
                "freshness_result": quality_report.freshness_result,
                "confidence_summary": quality_report.confidence_summary,
                "warning_issues": [
                    _issue_summary(issue) for issue in quality_report.warning_issues
                ],
                "blocked_reasons": list(quality_report.blocked_reasons),
            }
        )

    sample_record = (
        query_result.records[0].model_dump(mode="json") if query_result.records else None
    )
    return {
        "approval_artifact_path": str(approval_artifact_path),
        "approval": _approval_summary(approval),
        "manifest_path": str(manifest_path),
        "manifest_artifact_count": len(manifest.artifacts),
        "citation_record_count": query_result.total,
        "artifact_summaries": artifact_summaries,
        "sample_citation_record": sample_record,
    }


def _resolve_manifest_path(approval_artifact_path: Path, manifest_path: Path) -> Path:
    if manifest_path.is_absolute():
        return manifest_path
    return approval_artifact_path.parent / manifest_path


def _resolve_artifact_path(manifest_path: Path, artifact_path: Path) -> Path:
    if artifact_path.is_absolute():
        return artifact_path
    return manifest_path.parent / artifact_path


if __name__ == "__main__":
    raise SystemExit(main())
