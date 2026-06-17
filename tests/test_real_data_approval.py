import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.real_data.approval import (
    ManualApprovalArtifactPayload,
    ManualApprovalChecklist,
    ManualApprovalReadError,
    ManualApprovalWriteError,
    load_manual_approval_artifact,
    write_manual_approval_artifact,
)
from backend.real_data.bundle import run_reviewed_admission_pilot_bundle_from_artifact

FIXTURE_PATH = Path("tests/fixtures/real_data/henan_reviewed_rows_sample.json")


def _checklist(**overrides):
    data = {
        "source_verified": True,
        "snapshot_verified": True,
        "quality_reviewed": True,
        "citation_reviewed": True,
        "no_production_writes_verified": True,
    }
    data.update(overrides)
    return ManualApprovalChecklist.model_validate(data)


def _bundle(tmp_path: Path):
    return run_reviewed_admission_pilot_bundle_from_artifact(
        reviewed_rows_artifact_path=FIXTURE_PATH,
        province="河南",
        year=2025,
        batch="本科批",
        subject_type="物理类",
        output_dir=tmp_path / "bundle",
        expected_schools=("郑州大学",),
    )


def _warning_bundle(tmp_path: Path):
    return run_reviewed_admission_pilot_bundle_from_artifact(
        reviewed_rows_artifact_path=FIXTURE_PATH,
        province="河南",
        year=2025,
        batch="本科批",
        subject_type="物理类",
        output_dir=tmp_path / "warning_bundle",
        expected_schools=("郑州大学", "河南大学"),
    )


def test_manual_approval_artifact_writes_and_revalidates_manifest(tmp_path: Path):
    bundle = _bundle(tmp_path)
    assert bundle.manifest_path is not None
    approval_path = tmp_path / "approval.json"
    reviewed_at = datetime(2026, 6, 9, 18, 0, tzinfo=UTC)

    written = write_manual_approval_artifact(
        approval_path=approval_path,
        manifest_path=bundle.manifest_path,
        reviewer="codex-reviewer",
        reviewed_at=reviewed_at,
        decision="approved",
        checklist=_checklist(),
        notes="fixture dry-run reviewed",
    )
    loaded = load_manual_approval_artifact(approval_path)

    assert written == loaded
    assert loaded.schema_version == "real_data_manual_approval.v1"
    assert loaded.reviewer == "codex-reviewer"
    assert loaded.reviewed_at == reviewed_at
    assert loaded.decision == "approved"
    assert loaded.citation_record_count == 1
    assert loaded.manifest_artifacts[0].province == "河南"
    assert loaded.manifest_artifacts[0].snapshot_id == "ha-2025-undergrad-physical-dry-run-fixture"
    assert (
        loaded.manifest_artifacts[0].quality_report_id
        == "ha-2025-undergrad-physical-dry-run-fixture-quality"
    )


def test_manual_approval_requires_all_checks_for_approved_decision(tmp_path: Path):
    bundle = _bundle(tmp_path)
    assert bundle.manifest_path is not None

    with pytest.raises(ManualApprovalWriteError, match="invalid manual approval"):
        write_manual_approval_artifact(
            approval_path=tmp_path / "approval.json",
            manifest_path=bundle.manifest_path,
            reviewer="codex-reviewer",
            reviewed_at=datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
            decision="approved",
            checklist=_checklist(citation_reviewed=False),
        )


def test_manual_approval_requires_notes_for_approved_warning_manifest(tmp_path: Path):
    bundle = _warning_bundle(tmp_path)
    assert bundle.manifest_path is not None
    assert bundle.manifest is not None
    assert bundle.manifest.artifacts[0].quality_status == "warning"

    with pytest.raises(ManualApprovalWriteError, match="invalid manual approval"):
        write_manual_approval_artifact(
            approval_path=tmp_path / "approval.json",
            manifest_path=bundle.manifest_path,
            reviewer="codex-reviewer",
            reviewed_at=datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
            decision="approved",
            checklist=_checklist(),
        )

    approval = write_manual_approval_artifact(
        approval_path=tmp_path / "approval-with-notes.json",
        manifest_path=bundle.manifest_path,
        reviewer="codex-reviewer",
        reviewed_at=datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
        decision="approved",
        checklist=_checklist(),
        notes="warning reviewed: pilot coverage gap accepted for dry-run sample",
    )

    assert approval.decision == "approved"
    assert approval.notes.startswith("warning reviewed")


def test_manual_approval_allows_rejected_decision_with_unchecked_items(tmp_path: Path):
    bundle = _bundle(tmp_path)
    assert bundle.manifest_path is not None

    approval = write_manual_approval_artifact(
        approval_path=tmp_path / "approval.json",
        manifest_path=bundle.manifest_path,
        reviewer="codex-reviewer",
        reviewed_at=datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
        decision="rejected",
        checklist=_checklist(citation_reviewed=False),
        notes="citation not reviewed",
    )

    assert approval.decision == "rejected"
    assert approval.checklist.citation_reviewed is False


def test_manual_approval_rejects_naive_review_time():
    with pytest.raises(ValidationError, match="reviewed_at"):
        ManualApprovalArtifactPayload.model_validate(
            {
                "schema_version": "real_data_manual_approval.v1",
                "manifest_path": "manifest.json",
                "manifest_artifacts": [
                    {
                        "artifact_path": "admission_candidates.json",
                        "source_page_id": "page",
                        "source_batch_id": "batch",
                        "snapshot_id": "snapshot",
                        "province": "河南",
                        "year": 2025,
                        "quality_status": "pass",
                        "quality_report_id": "snapshot-quality",
                        "candidate_count": 1,
                    }
                ],
                "citation_record_count": 1,
                "reviewer": "codex-reviewer",
                "reviewed_at": "2026-06-09T18:00:00",
                "decision": "approved",
                "checklist": _checklist().model_dump(),
                "notes": "",
            }
        )


def test_manual_approval_read_rejects_tampered_manifest_summary(tmp_path: Path):
    bundle = _bundle(tmp_path)
    assert bundle.manifest_path is not None
    approval_path = tmp_path / "approval.json"
    write_manual_approval_artifact(
        approval_path=approval_path,
        manifest_path=bundle.manifest_path,
        reviewer="codex-reviewer",
        reviewed_at=datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
        decision="approved",
        checklist=_checklist(),
    )
    payload = json.loads(approval_path.read_text(encoding="utf-8"))
    payload["citation_record_count"] = 999
    approval_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ManualApprovalReadError, match="invalid manual approval"):
        load_manual_approval_artifact(approval_path)


def test_manual_approval_read_rejects_tampered_referenced_manifest(tmp_path: Path):
    bundle = _bundle(tmp_path)
    assert bundle.manifest_path is not None
    approval_path = tmp_path / "approval.json"
    write_manual_approval_artifact(
        approval_path=approval_path,
        manifest_path=bundle.manifest_path,
        reviewer="codex-reviewer",
        reviewed_at=datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
        decision="approved",
        checklist=_checklist(),
    )
    manifest_payload = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))
    manifest_payload["artifacts"][0]["candidate_count"] = 999
    bundle.manifest_path.write_text(
        json.dumps(manifest_payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ManualApprovalReadError, match="invalid manual approval"):
        load_manual_approval_artifact(approval_path)


def test_manual_approval_rejects_default_overwrite(tmp_path: Path):
    bundle = _bundle(tmp_path)
    assert bundle.manifest_path is not None
    approval_path = tmp_path / "approval.json"
    kwargs = {
        "approval_path": approval_path,
        "manifest_path": bundle.manifest_path,
        "reviewer": "codex-reviewer",
        "reviewed_at": datetime(2026, 6, 9, 18, 0, tzinfo=UTC),
        "decision": "approved",
        "checklist": _checklist(),
    }
    write_manual_approval_artifact(**kwargs)

    with pytest.raises(FileExistsError, match="manual approval artifact already exists"):
        write_manual_approval_artifact(**kwargs)
