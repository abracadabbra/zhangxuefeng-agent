# Real Data Guidelines

## Scenario: Auditable Gaokao Real Data Pilot

### 1. Scope / Trigger

Use these rules when changing `backend/real_data/` contracts or any future adapter
that consumes its staging artifacts. The current MVP is isolated: it may define
source, snapshot, raw-row, quality, staging, and citation contracts, but it must
not write production DB tables, mutate `backend/seeds/`, or change existing Agent
tools without a separate approval step.

### 2. Signatures

- `build_citation_metadata(candidate, source_page, snapshot) -> AgentCitationMetadata`
- `write_admission_staging_artifact(..., output_dir: Path) -> StagingArtifact`
- `load_admission_staging_artifact(artifact_path: Path) -> StagingArtifactPayload`
- `project_admission_citation_records(payload) -> tuple[AdmissionCitationRecord, ...]`
- `write_staging_manifest(manifest_path: Path, artifact_paths: Sequence[Path]) -> StagingManifestPayload`
- `load_staging_manifest(manifest_path: Path) -> StagingManifestPayload`
- `load_manifest_reference_candidates(manifest_path: Path) -> tuple[CanonicalAdmissionCandidate, ...]`
- `query_admission_records_from_staging(artifact_path: Path, query: AdmissionQuery) -> AdmissionQueryResult`
- `query_admission_records_from_manifest(manifest_path: Path, query: AdmissionQuery) -> AdmissionQueryResult`
- `query_admission_records_from_approval(approval_path: Path, query: AdmissionQuery) -> AdmissionQueryResult`
- `run_quality_gate(..., reference_candidates: Sequence[CanonicalAdmissionCandidate] = (), allowed_source_types: Sequence[SourceType] = (...)) -> QualityReport`
- `run_reviewed_admission_pilot_bundle_from_artifact(...) -> ReviewedAdmissionPilotBundleResult`
- `backend.real_data.cli.main(argv: Sequence[str] | None = None) -> int`
- `write_manual_approval_artifact(...) -> ManualApprovalArtifactPayload`
- `load_manual_approval_artifact(approval_path: Path) -> ManualApprovalArtifactPayload`

### 3. Contracts

Agent-facing citation metadata must include:

- `source`: human-readable official publisher name.
- `source_url`: official source page URL.
- `snapshot_url`: exact raw file URL or reviewed dynamic data-view URL.
- `year`: admission year.
- `snapshot`: stable snapshot id.
- `confidence`: `high`, `medium`, or `low`.
- `source_batch_id`: source batch id shared with candidates and quality reports.

Staging artifacts must keep `source_page`, `snapshot`, `quality_report`,
`candidates`, and `citations` in the same JSON payload so typed readback can
validate the full lineage before any future consumer reads it.

Reviewed raw rows artifacts must validate row lineage before canonical
normalization. Every row must match the artifact snapshot, and `raw_row_number`
values must be unique within the artifact so citations can point to a single
source row.

The isolated read-only adapter may filter validated staging records in memory,
but it must load data through `load_admission_staging_artifact(...)` first. It is
not a production Agent tool and must not query production DB tables or seed files.

The staging manifest is only a discoverability index. Loading it must revalidate
every referenced staging artifact and reject stale or tampered manifest summaries.
Each manifest entry must include the referenced artifact's `quality_report_id` so
manual approvals can bind to a concrete quality gate report.
Reference candidates loaded from a manifest must come through manifest readback
and typed staging readback; callers must not trust loose artifact paths.

The pilot bundle runner is an isolated orchestrator. It may compose reviewed raw
rows readback, pilot quality gate, staging write, manifest write, and manifest
query tests, but each underlying contract remains owned by its module.

The dry-run CLI is an operator wrapper over the bundle runner. It must emit a
structured JSON summary and must remain isolated from production DB, seed, and
Agent tool paths.
Its summary must expose quality review fields from `QualityReport`, including
coverage, freshness, confidence counts, blocked reasons, warning issues, and
categorized blocking issues.
For `pass`, `warning`, and `blocked` outcomes alike, the summary must always
include `quality_report_id` plus structured `source` and `snapshot` metadata so
operators can audit which official page and reviewed snapshot were gated.
When dry-run quality is `blocked`, the CLI must still surface the audit evidence
above even though no downstream staging artifact, manifest, or sample citation
is allowed to exist.
Medium-confidence candidates must produce row-level warning issues so reviewers
can trace which raw rows need attention; low-confidence candidates remain
blocking.

The quality gate may receive reviewed reference candidates for conflict checks.
When a candidate shares a canonical key with a reference from a different source
batch or snapshot, differing `min_score`, `min_rank`, or `plan_count` values must
produce a blocking `cross_source_conflict`.
The dry-run bundle and CLI may accept a reference manifest to feed this check,
but the reference manifest is read-only and must be revalidated before use.
The quality gate must also verify that the snapshot belongs to the source page
being gated, and may restrict allowed source types for a specific pilot run.
When `published_at` is known, a snapshot captured before the source publish date
is invalid lineage and must block before staging.

Documented dry-run fixtures belong under `tests/fixtures/real_data/`. They are
repeatable operator samples, not production data, and tests must prove the
documented command shape still returns stable citation metadata.

Manual approval artifacts are review records for staging manifests. They must
record reviewer, timezone-aware review time, decision, checklist, referenced
manifest entries, and citation record count. Loading an approval must revalidate
the referenced manifest so stale approvals fail closed.
Approved decisions for manifests containing warning-quality artifacts must include
reviewer notes explaining that the warning issues were reviewed and accepted.
The CLI may write and verify approval artifacts, but it must only call the
isolated approval APIs and must not make approval imply production availability.
Approval-gated read-only querying must verify the approval artifact first and
must reject any decision other than `approved`.
The CLI may expose this as an operator query command, but it must call
`query_admission_records_from_approval(...)` rather than reading manifests or
staging artifacts directly.
The CLI may also expose an operator audit command, but it must revalidate the
approval, manifest, and each staging artifact before projecting quality and
citation evidence. Audit summaries must include structured warning issues, not
only the final quality status. They must include `quality_report_id`, raw file
hash, capture time, and operator for each artifact. When a warning-quality
manifest is approved, audit summaries must expose both the approval notes and the
structured warning issues.

### 4. Validation & Error Matrix

- Blocked quality report -> staging write/read must fail.
- Warning status or warning conditions -> quality report and dry-run summary must
  preserve structured warning issues.
- Medium-confidence candidate -> quality report must include a row-level warning issue.
- Candidate `source_batch_id` mismatch -> staging write/read must fail.
- Candidate `snapshot_id` mismatch -> staging write/read must fail.
- Duplicate `raw_row_number` values in reviewed raw rows -> artifact write/read must fail.
- Citation payload differs from `build_citation_metadata(...)` -> readback must fail.
- Snapshot `source_page_id` differs from source page -> citation/staging validation must fail.
- Missing or tampered `snapshot_url` -> typed staging readback must fail.
- Manifest entry differs from its referenced staging artifact -> manifest readback must fail.
- Manifest quality report id differs from its referenced staging artifact -> manifest readback must fail.
- Duplicate `(source_batch_id, snapshot_id)` entries -> manifest write/read must fail.
- Invalid query score bounds -> query construction must fail.
- Cross-source conflict on the same canonical key -> quality report must block.
- Snapshot/source-page mismatch -> quality report must block.
- Source type outside the pilot allowed list -> quality report must block.
- Snapshot captured before source publish date -> quality report must block.
- Reference manifest conflict in dry-run -> no new staging or manifest may be written.
- Schema-blocked or tampered reviewed raw rows artifact -> bundle must not write staging or manifest artifacts.
- Blocked dry-run summary missing `quality_report_id`, `source`, or `snapshot`
  evidence -> CLI contract failure even when downstream writes are correctly skipped.
- Tampered reviewed raw rows artifact in the dry-run CLI -> non-zero exit and no downstream writes.
- Approved manual approval with any unchecked checklist item -> write/read must fail.
- Approved manual approval for a warning manifest without reviewer notes -> write/read must fail.
- Manual approval summary differs from its referenced manifest -> readback must fail.
- Approval-gated query with `decision != approved` -> query must fail.

### 5. Good / Base / Bad Cases

- Good: official page URL and reviewed snapshot/data-view URL are both present and distinct.
- Base: static official attachment uses `snapshot.raw_file_url` as `snapshot_url`.
- Bad: using only the article page URL for a dynamic score table; future Agent answers
  cannot cite the reviewed source view.

### 6. Tests Required

- Quality gate tests for source, year, snapshot, confidence, medium-confidence
  row warnings, lineage fields, allowed source types, snapshot/source-page mismatch,
  snapshot publish-time order, and cross-source conflicts.
- Staging tests proving pass/warning artifacts write and blocked artifacts do not.
- Reviewed raw rows tests proving row lineage matches the snapshot and raw row
  numbers are unique.
- Typed readback tests rejecting tampered candidate lineage, citation snapshot id, and
  citation `snapshot_url`.
- Pilot tests proving reviewed raw-row artifacts project citation records without touching
  DB, seeds, or existing Agent tools.
- Adapter tests proving filtered results preserve citation fields and tampered artifacts
  fail before records are returned.
- Manifest tests proving registered artifacts are revalidated on read, duplicate snapshots
  are rejected, quality report ids are preserved, and multi-artifact queries preserve
  citation fields.
- Bundle tests proving reviewed raw rows can run to manifest-backed citation queries and
  blocked/tampered inputs stop before downstream artifacts are written.
- Bundle and CLI tests proving a reference manifest can block cross-source conflicts
  before downstream staging/manifest writes.
- CLI tests proving structured summaries include quality counts, artifact paths, citation
  metadata, and blocked/tampered cases do not write downstream artifacts.
- CLI tests proving quality review summaries include coverage, freshness, confidence,
  blocked reasons, warning issues, and categorized issue details.
- CLI tests proving `pass`, `warning`, and `blocked` dry-run summaries always expose
  `quality_report_id`, `source`, and `snapshot` metadata even when downstream writes
  are skipped.
- Fixture tests proving documented reviewed-row samples still run through the dry-run CLI
  and return stable source, snapshot, year, and confidence metadata.
- Approval tests proving approved decisions require every checklist item, approvals revalidate
  referenced manifests, approved warning manifests require reviewer notes, and stale/tampered
  approval records fail closed.
- CLI approval tests proving operators can write/verify approval artifacts and incomplete
  approved checklists fail without writing approval output.
- Adapter approval tests proving records are returned only after verified approval and
  rejected/tampered approval artifacts fail closed.
- CLI approval-query tests proving records are returned only through verified approved
  artifacts and rejected approvals fail closed.
- CLI approval-audit tests proving approval, manifest, quality, and citation evidence
  are summarized only after the artifact chain revalidates, including quality report ids,
  snapshot hash/capture metadata, warning issues, and warning approval notes.
- Boundary audit with `rg` must show no references from `backend/real_data` tests to
  production DB, seed import paths, or Agent tool registration.

### 7. Wrong vs Correct

#### Wrong

```python
build_citation_metadata(candidate, source_page)
```

This loses the exact reviewed snapshot URL and lets citation payloads drift from
the snapshot that was actually quality-gated.

#### Correct

```python
build_citation_metadata(candidate, source_page, snapshot)
```

The citation projection can verify source page, source batch, and snapshot lineage,
then expose both the official page URL and the exact raw/snapshot URL.
