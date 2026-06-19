# Real Data MVP Implementation Plan

## Phase 0. Planning Readiness

- [x] Inspect README, data storage docs, seed import scripts, models, CRUD, tools,
      and RAG notes.
- [x] Confirm existing task status is `planning`.
- [x] Document PRD, technical design, and implementation plan.
- [x] User approved implementation of Phase 1, Phase 2, and manual parser work.
- [ ] Start Trellis task status before broader DB/Agent implementation.

## Phase 1. Data Contracts Only

Goal: add contracts without changing production query behavior.

- [x] Add `backend/data_pipeline/` package skeleton.
- [x] Add source registry schema and initial registry entries.
- [x] Add raw snapshot manifest Pydantic model or dataclass.
- [x] Add checksum helper for local snapshot files.
- [x] Add unit tests for registry validation and manifest validation.

Validation:

```bash
python -m pytest tests
python -m ruff check backend tests
```

Current verification status:

- `python3 -m py_compile` passed for the new data pipeline modules and tests.
- `python3 -m json.tool backend/data_pipeline/sources/sources.json` passed.
- A manual 100-column line length scan passed for the touched files.
- Full `pytest` and `ruff` are still pending because this worktree has no
  `.venv`, and system Python is missing project dependencies.

Rollback:

- Remove `backend/data_pipeline/` and related tests.

## Phase 2. Quality Gate Prototype

Goal: validate candidate rows before any DB load.

- [x] Define candidate row types for admission scores and enrollment plans.
- [x] Implement required-field, range, uniqueness, source completeness, freshness,
      and coverage checks.
- [x] Produce a quality report object with `errors`, `warnings`, and `coverage`.
- [x] Add unit tests for passing and failing quality scenarios.

Validation:

```bash
python -m pytest tests
python -m ruff check backend tests
```

Current verification status:

- `python3 -m py_compile` passed for quality modules and tests.
- Manual line length scan passed for the touched quality files.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove quality module and tests; no DB data is touched in this phase.

## Phase 3. Lineage Schema

Goal: persist source/snapshot/lineage metadata while minimizing impact on
existing canonical tables.

- [x] Add SQLAlchemy models for data sources, data snapshots, and data lineage
      records.
- [x] Add Alembic migration for the new tables.
- [x] Ensure `alembic/env.py` imports new models so migrations can detect them.
- [x] Add CRUD/service functions for snapshot and lineage lookup.
- [x] Add tests using an isolated SQLite database.

Validation:

```bash
alembic upgrade head
python -m pytest tests
python -m ruff check backend tests
```

Current verification status:

- `python3 -m py_compile` passed for lineage models, Alembic env, migration,
  and lineage model tests.
- `python3 -m py_compile` passed for lineage service modules and service tests.
- Manual line length scan passed for lineage models, migration, and tests.
- Manual line length scan passed for lineage service modules and tests.
- Migration chain is linear through `004_data_lineage`.
- `alembic upgrade head`, full `pytest`, and `ruff` remain pending until a
  project environment is available and DB migration execution is explicitly run.
- `004_data_lineage` now includes database defaults for status and timestamp
  fields, matching the ORM defaults and reducing raw SQL import risk.

Rollback:

- Downgrade or revert the lineage migration.
- Remove new models/services/tests.

## Phase 4. Manual Pilot Parser

Goal: prove raw snapshot to candidate row flow with a small manually supplied
sample, not a crawler.

- [x] Choose pilot province and years: Shandong, 2025 sample rows.
- [x] Add a small fixture under tests, not production seed data.
- [x] Implement parser for one normalized dict/JSON-style fixture format.
- [x] Validate parser output through the quality gate.
- [x] Do not fetch remote data.

Validation:

```bash
python -m pytest tests
python -m ruff check backend tests
```

Current verification status:

- `python3 -m py_compile` passed for parser modules and tests.
- Manual line length scan passed for parser modules and tests.
- Full `pytest` and `ruff` remain pending until dependencies are installed or a
  project `.venv` is available.

Rollback:

- Remove parser and fixtures.

## Phase 5. Loader Prototype

Goal: load quality-gated candidates into existing canonical tables and attach
lineage records.

- [x] Implement upsert logic for admission score candidates.
- [x] Implement upsert logic for enrollment plan candidates.
- [x] Link lineage records by canonical entity ID when available.
- [x] Add tests for idempotent load and conflict handling.
- [x] Add audit-gated loader wrapper for dry-run approved candidates.
- [x] Add tests proving failed audit blocks loader writes in isolated SQLite.

Validation:

```bash
python -m pytest tests
python -m ruff check backend tests
```

Current verification status:

- `python3 -m py_compile` passed for loader modules and loader tests.
- Manual line length scan passed for loader modules and tests.
- Loader tests target isolated SQLite only and do not touch the real app DB.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Revert loader code.
- Use test DB only until manually approved for local dev DB.

## Phase 6. Agent Source Metadata

Goal: make query results citeable without changing existing item fields.

- [x] Add lineage lookup for returned admission score rows.
- [x] Add lineage lookup for returned enrollment plan rows.
- [x] Add source metadata formatter for one canonical entity.
- [x] Add additive `sources` metadata to admission score tool responses.
- [x] Add additive `sources` metadata to enrollment plan tool responses.
- [x] Keep existing admission score and enrollment plan response item fields stable.
- [x] Add tests for the source metadata envelope formatter.
- [x] Add tests for tool-layer source attachment.

Current scope note:

- Admission score and enrollment plan Agent tools now attach `sources` at the
  item level.
- API routers were intentionally left unchanged; source metadata is added only
  in the Agent tool response layer.

Validation:

```bash
python -m pytest tests
python -m ruff check backend tests
```

Current verification status:

- `python3 -m py_compile` passed for `backend/tools/definitions.py`,
  source metadata formatter, and tool source metadata tests.
- Manual line length scan passed for the new tool source metadata test and this
  implementation plan update. Existing long lines remain in `definitions.py`
  and were not reformatted in this phase.
- `search_enrollment_plan` was compile-checked after registration.
- Targeted `pytest` for source metadata tests could not run because the current
  system Python has no `pytest` module and this worktree has no project `.venv`.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove additive `sources` fields and lineage lookup from tools.
- Remove `backend/data_pipeline/lineage/sources.py` if the source envelope
  contract changes before tool integration.

## Phase 7. Pilot Dry Run

Goal: prove reviewed sample rows can be parsed and quality-gated before any
database write.

- [x] Add in-memory manual pilot dry-run entry point.
- [x] Return snapshot/source/dataset identifiers for auditability.
- [x] Validate optional source registry entry against snapshot manifest.
- [x] Return candidate count, pass/fail status, coverage, and issue counts.
- [x] Return load readiness and blocker reasons for pre-loader gating.
- [x] Add reusable load-readiness guard before canonical loading.
- [x] Add load-ready candidate builder for guarded loader handoff.
- [x] Add bundle-to-candidates builder for guarded loader handoff.
- [x] Export a stable JSON-ready audit dictionary for review/CI consumers.
- [x] Add JSON-like payload entry point for future CLI/CI integration.
- [x] Add single-bundle payload entry point for future CLI/CI integration.
- [x] Add explicit pilot bundle contract for future CLI/CI integration.
- [x] Add read-only CLI module for bundle-to-audit dry-runs.
- [x] Add structured CLI input-error output for invalid pilot bundles.
- [x] Add dry-run usage document and bundle example for manual pilots.
- [x] Add runnable example bundle for pilot dry-run smoke checks.
- [x] Add enrollment plan example bundle for pilot dry-run smoke checks.
- [x] Document audit-gated loader handoff entry point.
- [x] Sync README and tool module comments with enrollment-plan Agent tool.
- [x] Add tests for passing and failing dry-run scenarios.
- [x] Add tests for source/manifest mismatch.
- [x] Add tests for audit dictionary export.
- [x] Add tests for payload-to-audit dry-run entry point.
- [x] Add tests for bundle payload quality-config handling.
- [x] Add tests for explicit pilot bundle contract.
- [x] Add tests for dry-run CLI output and exit codes.
- [x] Add tests for dry-run CLI input-error output.
- [x] Add documentation for dry-run CLI usage and exit codes.
- [x] Add documentation for audit-gated loader handoff.
- [x] Add example bundle JSON validation.
- [x] Add enrollment plan example bundle JSON validation.
- [x] Add tests for load readiness and blocker reasons.
- [x] Add tests for reusable load-readiness guard.
- [x] Add tests for guarded candidate builder.
- [x] Add tests for bundle guarded candidate builder.
- [x] Keep dry-run out of real DB, crawler, and seed-data paths.

Validation:

```bash
python -m pytest tests
python -m ruff check backend tests
```

Current verification status:

- `python3 -m py_compile` passed for pilot dry-run modules and tests.
- Manual line length scan passed for pilot dry-run modules, tests, and this
  implementation plan update.
- `python3 -m json.tool examples/real_data/sd_pilot_bundle.json` passed.
- CLI smoke against the example bundle is pending because the current system
  Python has no project dependencies such as `pydantic`.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `backend/data_pipeline/pilots/` and pilot dry-run tests.

## Phase 8. Architecture Documentation Sync

Goal: keep the project-level data architecture document aligned with the real
data MVP contracts before moving to reviewed official samples.

- [x] Document the real-data MVP flow in `docs/data-storage-architecture.md`.
- [x] Document source registry, raw snapshot, parser, quality, lineage, loader,
      and pilot module boundaries.
- [x] Document the three lineage side tables added by `004_data_lineage`.
- [x] Document dry-run and loader approval gates.
- [x] Document Agent `sources` metadata fields for citeable responses.
- [x] Keep the update documentation-only: no code, DB, seed, crawler, or RAG
      changes.

Validation:

```bash
python -m pytest tests
python -m ruff check backend tests
```

Current verification status:

- Markdown documentation was updated only in project docs and this Trellis
  implementation plan.
- Full `pytest` and `ruff` are still pending until a project environment is
  available; this phase does not add runtime code.

Rollback:

- Revert the new sections in `docs/data-storage-architecture.md`.
- Remove this Phase 8 section if the architecture wording is superseded.

## Phase 9. Pilot Review Checklist

Goal: define the manual review gate for official Shandong/Henan samples before
any dry-run result can be considered for loader approval.

- [x] Add `docs/real-data-pilot-review-checklist.md`.
- [x] Document required source registry review fields.
- [x] Document raw snapshot manifest review fields.
- [x] Document admission-score and enrollment-plan row review fields.
- [x] Document quality-config expectations for pilot scope.
- [x] Document dry-run pass criteria before loader approval.
- [x] Document the separate loader approval packet.
- [x] Link the checklist from the pilot dry-run guide.
- [x] Keep the update documentation-only: no crawler, DB, seed, RAG, or Agent
      runtime changes.

Validation:

```bash
python -m pytest tests
python -m ruff check backend tests
```

Current verification status:

- Markdown documentation was updated only.
- Full `pytest` and `ruff` remain pending until a project environment is
  available; this phase does not add runtime code.

Rollback:

- Remove `docs/real-data-pilot-review-checklist.md`.
- Remove the link from `docs/real-data-pilot-dry-run.md`.
- Remove this Phase 9 section if the pilot review process changes.

## Phase 10. Manual Collector Stub

Goal: create the collector directory and a no-network collector path for reviewed
local raw snapshots before any crawler implementation exists.

- [x] Add `backend/data_pipeline/collectors/` package.
- [x] Add collector result and protocol contracts.
- [x] Add `ManualSnapshotCollector` for local snapshot directories.
- [x] Reuse `RawSnapshotManifest` validation and manifest checksum helpers.
- [x] Add tests for valid local snapshot collection.
- [x] Add tests for checksum mismatch reporting.
- [x] Add tests for missing manifest handling.
- [x] Keep the collector no-network and read-only.

Validation:

```bash
python -m pytest tests/test_data_pipeline_collectors.py
python -m ruff check backend/data_pipeline/collectors tests/test_data_pipeline_collectors.py
```

Current verification status:

- Targeted `py_compile` passed for collector modules and collector tests.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `backend/data_pipeline/collectors/`.
- Remove `tests/test_data_pipeline_collectors.py`.
- Remove this Phase 10 section if collector contracts change.

## Phase 11. Snapshot File Gate Integration

Goal: ensure local raw snapshot file validation participates in dry-run
readiness before any loader handoff can happen.

- [x] Add `snapshot_file_issues` to pilot audit results.
- [x] Add `snapshot_file:*` blockers for missing or mismatched manifest files.
- [x] Add `run_manual_pilot_snapshot_dir(...)` for local raw snapshot dry-runs.
- [x] Add `build_load_ready_candidates_snapshot_dir(...)` for guarded loader
      handoff from local snapshots.
- [x] Add tests that checksum mismatch blocks `load_ready`.
- [x] Add tests that guarded candidate building refuses mismatched files.
- [x] Document the snapshot-dir dry-run handoff.
- [x] Keep the integration no-network, no-DB, no-seed, and no-crawler.

Validation:

```bash
python -m pytest tests/test_data_pipeline_pilot_dry_run.py
python -m ruff check backend/data_pipeline/pilots tests/test_data_pipeline_pilot_dry_run.py
```

Current verification status:

- Targeted `py_compile` passed for pilot modules and dry-run tests.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `snapshot_file_issues` and snapshot-dir helper functions from
  `backend/data_pipeline/pilots/dry_run.py`.
- Remove related exports and tests.
- Revert the dry-run guide additions.
- Remove this Phase 11 section if the audit contract changes.

## Phase 12. Snapshot-dir CLI Dry Run

Goal: expose the local raw snapshot file gate through the dry-run CLI while
preserving the original bundle-only command.

- [x] Add snapshot-dir bundle contract for rows/source/quality config.
- [x] Add `--snapshot-dir` to the dry-run CLI.
- [x] Keep the existing bundle-only CLI behavior compatible.
- [x] Make snapshot-dir CLI mode load `manifest.json` from the local snapshot.
- [x] Make snapshot-dir CLI mode report checksum issues as blockers.
- [x] Add CLI tests for snapshot-dir checksum blocking.
- [x] Document snapshot-dir CLI usage.
- [x] Keep the CLI no-network, no-DB, no-seed, and no-crawler.

Validation:

```bash
python -m pytest tests/test_data_pipeline_pilot_dry_run.py
python -m ruff check backend/data_pipeline/pilots tests/test_data_pipeline_pilot_dry_run.py
```

Current verification status:

- Targeted `py_compile` passed for pilot modules and dry-run tests.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `--snapshot-dir` handling from `backend/data_pipeline/pilots/cli.py`.
- Remove snapshot-dir bundle helpers and tests.
- Revert the dry-run guide additions.
- Remove this Phase 12 section if CLI shape changes.

## Phase 13. Audit Artifact Output

Goal: let dry-run CLI produce a durable audit JSON artifact for human review and
loader approval packets.

- [x] Add optional `--audit-output` to the dry-run CLI.
- [x] Keep stdout output and existing exit-code behavior unchanged.
- [x] Create parent directories for the requested audit output path.
- [x] Write UTF-8 pretty JSON audit artifacts.
- [x] Add tests that audit output matches stdout payload.
- [x] Document audit output usage and approval packet expectations.
- [x] Keep the feature no-network, no-DB, no-seed, and no-crawler.

Validation:

```bash
python -m pytest tests/test_data_pipeline_pilot_dry_run.py
python -m ruff check backend/data_pipeline/pilots tests/test_data_pipeline_pilot_dry_run.py
```

Current verification status:

- Targeted `py_compile` passed for pilot CLI and dry-run tests.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `--audit-output` handling from `backend/data_pipeline/pilots/cli.py`.
- Remove related tests and documentation.
- Remove this Phase 13 section if audit artifact handling changes.

## Phase 14. Audit Review Summary

Goal: make dry-run audit artifacts directly usable in loader approval packets by
including a stable review summary.

- [x] Add `review_status` to audit results.
- [x] Add `review_notes` to audit results.
- [x] Mark blocker-free, warning-free runs as `ready_for_loader_review`.
- [x] Mark warning-only runs as `needs_warning_review`.
- [x] Mark blocker runs as `blocked`.
- [x] Include review summary fields in exported audit JSON.
- [x] Add tests for ready, warning-review, and blocked states.
- [x] Document review summary fields and approval-packet usage.
- [x] Keep the feature no-network, no-DB, no-seed, and no-crawler.

Validation:

```bash
python -m pytest tests/test_data_pipeline_pilot_dry_run.py
python -m ruff check backend/data_pipeline/pilots tests/test_data_pipeline_pilot_dry_run.py
```

Current verification status:

- Targeted `py_compile` passed for pilot dry-run modules and tests.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `review_status` and `review_notes` from pilot audit results.
- Remove related tests and documentation.
- Remove this Phase 14 section if review summary semantics change.

## Phase 15. Loader Review-status Guard

Goal: prevent warning-only dry-runs from entering canonical loader without
explicit review.

- [x] Add `assert_loader_review_ready(...)` guard.
- [x] Keep `assert_load_ready(...)` compatibility for older audit consumers.
- [x] Update `load_candidates_after_audit(...)` to require loader review
      readiness.
- [x] Preserve compatibility for legacy audits without `review_status`.
- [x] Add tests that `needs_warning_review` blocks loader writes.
- [x] Add tests for the stricter pilot guard.
- [x] Document loader requirement for `ready_for_loader_review`.
- [x] Keep the change no-network, no-DB execution, no-seed, and no-crawler.

Validation:

```bash
python -m pytest tests/test_data_pipeline_loader.py tests/test_data_pipeline_pilot_dry_run.py
python -m ruff check backend/data_pipeline tests
```

Current verification status:

- Targeted `py_compile` passed for pilot, loader, and related tests.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Change `load_candidates_after_audit(...)` back to `assert_load_ready(...)`.
- Remove `assert_loader_review_ready(...)` exports and tests.
- Revert the dry-run guide additions.
- Remove this Phase 15 section if loader approval semantics change.

## Phase 16. Loader Approval Packet

Goal: produce a durable, machine-readable approval packet before any canonical
loader run is considered.

- [x] Add `LoaderApprovalPacket`.
- [x] Add `build_loader_approval_packet(...)`.
- [x] Reuse `assert_loader_review_ready(...)` so warning-review audits are
      blocked.
- [x] Include parser name/version and quality status.
- [x] Include candidate count and entity-type counts.
- [x] Include source, snapshot, dataset, and audit summary.
- [x] Include rollback actions and explicit non-goals.
- [x] Add tests for ready and warning-review audits.
- [x] Document approval packet generation.
- [x] Keep the feature no-network, no-DB, no-seed, and no-crawler.

Validation:

```bash
python -m pytest tests/test_data_pipeline_loader_approval.py
python -m ruff check backend/data_pipeline/loaders tests/test_data_pipeline_loader_approval.py
```

Current verification status:

- Targeted `py_compile` passed for loader approval modules and tests.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `backend/data_pipeline/loaders/approval.py`.
- Remove exports, tests, and documentation references.
- Remove this Phase 16 section if approval packet semantics change.

## Phase 17. Approval Packet CLI Output

Goal: let the no-write dry-run CLI produce both audit and loader approval
artifacts for review.

- [x] Add optional `--approval-output` to the dry-run CLI.
- [x] Add parser name/version CLI metadata for approval packets.
- [x] Reuse bundle and snapshot-dir candidate builders.
- [x] Reuse `build_loader_approval_packet(...)`.
- [x] Refuse approval packet output for blocked or warning-review audits.
- [x] Keep stdout audit behavior unchanged.
- [x] Add tests for approval packet output.
- [x] Add tests that warning-review audits do not write approval packets.
- [x] Document approval packet CLI usage.
- [x] Keep the feature no-network, no-DB, no-seed, and no-crawler.

Validation:

```bash
python -m pytest tests/test_data_pipeline_pilot_dry_run.py
python -m ruff check backend/data_pipeline/pilots tests/test_data_pipeline_pilot_dry_run.py
```

Current verification status:

- Targeted `py_compile` passed for pilot CLI and dry-run tests.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `--approval-output`, parser metadata args, and helper logic from CLI.
- Remove related tests and documentation.
- Remove this Phase 17 section if approval artifact flow changes.

## Phase 18. Snapshot-dir Example

Goal: provide a no-write example that exercises raw snapshot manifest checksum
validation and approval artifact generation.

- [x] Add example raw snapshot directory under `examples/real_data/snapshots/`.
- [x] Add example CSV file and matching manifest checksum.
- [x] Add rows-only bundle for `--snapshot-dir` CLI mode.
- [x] Document command that generates audit and approval artifacts.
- [x] Keep the example synthetic and clearly non-official.
- [x] Keep the update no-network, no-DB, no-seed, and no-crawler.

Validation:

```bash
python -m json.tool examples/real_data/sd_snapshot_pilot_rows.json
python -m json.tool examples/real_data/snapshots/sd_pilot_2025_001/manifest.json
python -m py_compile backend/data_pipeline/pilots/cli.py
```

Current verification status:

- JSON validation passed for the new rows bundle and manifest.
- Manual checksum verification confirmed the manifest hash matches the example
  CSV content.
- CLI runtime smoke remains pending until project dependencies are available.

Rollback:

- Remove `examples/real_data/sd_snapshot_pilot_rows.json`.
- Remove `examples/real_data/snapshots/sd_pilot_2025_001/`.
- Revert the dry-run guide example.
- Remove this Phase 18 section if example layout changes.

## Phase 19. Examples Runbook

Goal: make the synthetic examples self-explanatory and safe to use.

- [x] Add `examples/real_data/README.md`.
- [x] Document which example file exercises which dry-run mode.
- [x] Document no-write behavior for example commands.
- [x] Document audit and approval artifact handling.
- [x] Document how to replace synthetic rows with reviewed official samples.
- [x] Link the pilot review checklist before real sample preparation.
- [x] Keep the update documentation-only: no network, DB, seed, or crawler.

Validation:

```bash
python -m json.tool examples/real_data/sd_pilot_bundle.json
python -m json.tool examples/real_data/sd_plan_pilot_bundle.json
python -m json.tool examples/real_data/sd_snapshot_pilot_rows.json
```

Current verification status:

- JSON validation passed for all example bundles and the snapshot manifest.
- Markdown long-line scan passed for the examples README.
- CLI runtime smoke remains pending until project dependencies are available.

Rollback:

- Remove `examples/real_data/README.md`.
- Remove this Phase 19 section if the examples runbook changes.

## Phase 20. MVP Runbook

Goal: provide one end-to-end guide for moving from reviewed source to dry-run
audit and loader approval without unsafe actions.

- [x] Add `docs/real-data-mvp-runbook.md`.
- [x] Document source review, snapshot preparation, rows bundle preparation,
      dry-run, audit review, and loader approval.
- [x] Document commands for no-write dry-run artifacts.
- [x] Document stop points before loader execution.
- [x] Document phased expansion from Shandong pilot to national coverage.
- [x] Add README links to real-data MVP docs.
- [x] Keep the update documentation-only: no network, DB, seed, or crawler.

Validation:

```bash
python -m json.tool examples/real_data/sd_snapshot_pilot_rows.json
python -m json.tool examples/real_data/snapshots/sd_pilot_2025_001/manifest.json
```

Current verification status:

- Markdown long-line scan passed for the runbook and README additions.
- JSON validation for the referenced snapshot example remains available as the
  no-dependency smoke check.
- CLI runtime smoke remains pending until project dependencies are available.

Rollback:

- Remove `docs/real-data-mvp-runbook.md`.
- Remove README links to the real-data MVP docs.
- Remove this Phase 20 section if runbook structure changes.

## Phase 21. Coverage Gate Blockers

Goal: make declared pilot coverage an enforceable loader-readiness contract.

- [x] Treat `coverage.missing_expected_provinces` as dry-run blockers.
- [x] Treat `coverage.missing_expected_years` as dry-run blockers.
- [x] Keep coverage enforcement in the pilot dry-run layer; the quality report
      remains the source of coverage facts.
- [x] Add tests for missing province and missing year blockers.
- [x] Add CLI approval-output regression coverage for missing coverage blockers.
- [x] Document blocker names in dry-run, runbook, and review checklist docs.
- [x] Keep the update no-write: no crawler, DB write, seed edit, or loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/pilots/dry_run.py \
  tests/test_data_pipeline_pilot_dry_run.py
python3 -m pytest tests/test_data_pipeline_pilot_dry_run.py
```

Expected blocker names:

- `coverage_missing:province:<province>`
- `coverage_missing:year:<year>`

Rollback:

- Remove `_coverage_blockers(...)` from pilot blocker construction.
- Restore pilot dry-run coverage test expectations to report-only behavior.
- Remove coverage blocker text from the dry-run, runbook, and checklist docs.
- Remove this Phase 21 section if the coverage gate policy changes.

## Phase 22. Source Registry Scope Audit

Goal: make data source registration reviewable before sample rows are prepared.

- [x] Add source registry audit report contracts.
- [x] Add `SourceRegistry.audit_scope(...)` for planned pilot category,
      province, year, and review-status checks.
- [x] Keep audit read-only: no crawler, network, DB write, or seed change.
- [x] Add tests for passing scope, missing province source, and review warnings.
- [x] Document the source audit in the MVP runbook and architecture guide.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/registry.py \
  tests/test_data_pipeline_contracts.py
python3 -m pytest tests/test_data_pipeline_contracts.py
```

Rollback:

- Remove `SourceRegistryIssue`, `SourceRegistryAudit`, and `audit_scope(...)`.
- Remove the new source registry audit tests.
- Remove source-audit documentation from the runbook and architecture guide.
- Remove this Phase 22 section if source review policy changes.

## Phase 23. Source Registry Audit CLI

Goal: make source registry scope review executable from shell or CI.

- [x] Add `backend/data_pipeline/sources/cli.py`.
- [x] Support data category, repeated province/year arguments, review warnings,
      fail-on-warning, and optional audit artifact output.
- [x] Add CLI tests for passing audit, missing province, warning failure, and
      audit artifact writing.
- [x] Document the CLI in the MVP runbook and architecture guide.
- [x] Keep the command read-only: no crawler, network, DB write, or seed change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/cli.py \
  tests/test_data_pipeline_sources_cli.py
python3 -m pytest tests/test_data_pipeline_sources_cli.py
```

Rollback:

- Remove `backend/data_pipeline/sources/cli.py`.
- Remove `tests/test_data_pipeline_sources_cli.py`.
- Restore source-audit docs to the Python-only API example.
- Remove this Phase 23 section if source audit command shape changes.

## Phase 24. Pilot Artifact Manifest

Goal: connect source audit, dry-run audit, and loader approval artifacts into a
single human-reviewable manifest before any loader execution.

- [x] Add `backend/data_pipeline/pilots/artifacts.py`.
- [x] Add `PilotArtifactManifest` and `build_pilot_artifact_manifest(...)`.
- [x] Summarize artifact paths, source/snapshot/dataset, candidate count,
      readiness, review issues, and non-goals.
- [x] Require source audit, dry-run review, and loader approval evidence before
      `ready_for_loader_execution=true`.
- [x] Add tests for ready and blocked artifact manifests.
- [x] Document artifact manifest review in the MVP runbook.
- [x] Keep the helper no-write: no crawler, DB write, seed edit, or loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/pilots/artifacts.py \
  tests/test_data_pipeline_pilot_artifacts.py
python3 -m pytest tests/test_data_pipeline_pilot_artifacts.py
```

Rollback:

- Remove `backend/data_pipeline/pilots/artifacts.py`.
- Remove artifact exports from `backend/data_pipeline/pilots/__init__.py`.
- Remove `tests/test_data_pipeline_pilot_artifacts.py`.
- Remove artifact manifest docs from the MVP runbook.
- Remove this Phase 24 section if artifact review policy changes.

## Phase 25. Pilot Artifact Manifest CLI

Goal: make the pilot evidence bundle executable from existing JSON artifacts.

- [x] Add `backend/data_pipeline/pilots/artifacts_cli.py`.
- [x] Read source audit, dry-run audit, optional loader approval, rows bundle
      path, and optional snapshot directory path.
- [x] Print manifest JSON and optionally write `--manifest-output`.
- [x] Return `0` only when `ready_for_loader_execution=true`; return `1` for
      review-incomplete manifests and `2` for input errors.
- [x] Add CLI tests for ready output, not-ready output, and artifact writing.
- [x] Document the CLI command in the MVP runbook.
- [x] Keep the command read-only: no crawler, DB write, seed edit, or loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/pilots/artifacts_cli.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
python3 -m pytest tests/test_data_pipeline_pilot_artifacts_cli.py
```

Rollback:

- Remove `backend/data_pipeline/pilots/artifacts_cli.py`.
- Remove `tests/test_data_pipeline_pilot_artifacts_cli.py`.
- Restore artifact manifest docs to the Python-only API example.
- Remove this Phase 25 section if artifact manifest command shape changes.

## Phase 26. MVP Status Page

Goal: provide a short, current-state entry point for the real-data MVP.

- [x] Add `docs/real-data-mvp-status.md`.
- [x] Summarize the no-write pipeline that is currently implemented.
- [x] Document current prohibited actions and verification limits.
- [x] Document entry conditions for a real Shandong small-sample pilot.
- [x] Link the status page from README.
- [x] Keep the update documentation-only: no crawler, DB write, seed edit,
      or loader run.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-mvp-status.md README.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Rollback:

- Remove `docs/real-data-mvp-status.md`.
- Remove the README link.
- Remove this Phase 26 section if status-page scope changes.

## Phase 27. Artifact Readiness Warning Gate

Goal: prevent artifact manifests from reporting loader readiness while source
audit warnings still require review.

- [x] Require source audit warnings to be empty before
      `ready_for_loader_execution=true`.
- [x] Keep source warning review in `required_reviews`.
- [x] Add helper-level test coverage for source-warning not-ready manifests.
- [x] Add CLI-level test coverage for source-warning exit code `1`.
- [x] Update runbook and status page wording.
- [x] Keep the change no-write: no crawler, DB write, seed edit, or loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/pilots/artifacts.py \
  backend/data_pipeline/pilots/artifacts_cli.py \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
python3 -m pytest \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
```

Current verification status:

- `python3 -m py_compile` passed for source audit scope and artifact scope gate
  modules and tests.
- Manual line length scan passed for touched Python, docs, and Trellis files.
- Targeted `pytest` remains pending because the current system Python has no
  `pytest` module.
- `python3 -m backend.data_pipeline.env_check` reports missing `pydantic`,
  `sqlalchemy`, and `pytest`.

Rollback:

- Restore `_is_ready_for_loader_execution(...)` to allow source warnings.
- Remove source-warning readiness tests.
- Restore runbook and status page wording.
- Remove this Phase 27 section if readiness policy changes.

## Phase 28. Artifact Path Readiness Gate

Goal: prevent artifact manifests from reporting loader readiness while referenced
evidence paths are missing.

- [x] Add `artifact_path_issues` to `PilotArtifactManifest`.
- [x] Make artifact path issues block `ready_for_loader_execution`.
- [x] Make artifact path issues produce `Resolve artifact path issues.` review.
- [x] Add CLI path checks for rows bundle and optional snapshot directory.
- [x] Add helper and CLI tests for missing rows bundle paths.
- [x] Update runbook and status page wording.
- [x] Keep the change no-write: no crawler, DB write, seed edit, or loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/pilots/artifacts.py \
  backend/data_pipeline/pilots/artifacts_cli.py \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
python3 -m pytest \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
```

Current verification status:

- `python3 -m py_compile` passed for artifact manifest modules and tests.
- `python3 -m json.tool backend/data_pipeline/sources/sources.json` passed.
- Manual line length scan passed after wrapping runbook wording.
- Targeted `pytest` remains pending because the current system Python has no
  `pytest` module.
- `python3 -m backend.data_pipeline.env_check` reports missing `pydantic`,
  `sqlalchemy`, and `pytest`.

Rollback:

- Remove `artifact_path_issues` from `PilotArtifactManifest`.
- Remove artifact path readiness checks from helper and CLI.
- Remove missing-path tests.
- Restore runbook and status page wording.
- Remove this Phase 28 section if artifact path policy changes.

## Phase 29. Real-data Environment Check

Goal: make missing local dependencies explicit before running real-data MVP CLIs.

- [x] Make `backend/data_pipeline/__init__.py` lazily expose contracts so
      stdlib-only checks can run even when runtime dependencies are missing.
- [x] Add `backend/data_pipeline/env_check.py`.
- [x] Report runtime modules required for contracts, dry-run, loader, and
      lineage.
- [x] Report dev modules required for tests.
- [x] Add tests for ready, missing, runtime-only, and CLI report behavior.
- [x] Document the check as the first runbook step and status-page condition.
- [x] Keep the command no-write: no install, network, DB write, seed edit, or
      loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/__init__.py \
  backend/data_pipeline/env_check.py \
  tests/test_data_pipeline_env_check.py
python3 -m backend.data_pipeline.env_check
python3 -m pytest tests/test_data_pipeline_env_check.py
```

Rollback:

- Restore eager exports in `backend/data_pipeline/__init__.py`.
- Remove `backend/data_pipeline/env_check.py`.
- Remove `tests/test_data_pipeline_env_check.py`.
- Restore runbook and status page wording.
- Remove this Phase 29 section if environment check policy changes.

## Phase 30. Environment Python Version Gate

Goal: make the real-data environment check enforce the project Python version
contract before any MVP CLI is run.

- [x] Add Python version fields to `backend/data_pipeline/env_check.py`.
- [x] Require Python `>=3.11` for `ready_for_cli_runtime=true`.
- [x] Include `python` in `missing_modules` when the interpreter is too old.
- [x] Add tests for Python-version failure.
- [x] Document `python_version_ok` in the runbook and status page.
- [x] Keep the check no-write: no install, network, DB write, seed edit, or
      loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/env_check.py \
  tests/test_data_pipeline_env_check.py
python3 -m backend.data_pipeline.env_check
python3 -m pytest tests/test_data_pipeline_env_check.py
```

Rollback:

- Remove Python version fields from `backend/data_pipeline/env_check.py`.
- Remove Python-version failure tests.
- Restore runbook and status page wording.
- Remove this Phase 30 section if environment check policy changes.

## Phase 31. Environment Install Hints

Goal: keep environment-check remediation aligned with the requested scope.

- [x] Use `pip install -e "."` for runtime-only missing dependencies.
- [x] Use `pip install -e ".[dev]"` when dev/test checks are included.
- [x] Preserve Python-version remediation wording.
- [x] Add runtime-only install-hint test coverage.
- [x] Document runtime vs dev install commands in the MVP runbook.
- [x] Keep the check no-write: no install, network, DB write, seed edit, or
      loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/env_check.py \
  tests/test_data_pipeline_env_check.py
python3 -m backend.data_pipeline.env_check
python3 -m backend.data_pipeline.env_check --runtime-only
python3 -m pytest tests/test_data_pipeline_env_check.py
```

Rollback:

- Restore one-size `pip install -e ".[dev]"` install hints.
- Remove runtime-only install-hint tests.
- Restore runbook wording.
- Remove this Phase 31 section if install-hint policy changes.

## Phase 32. First Shandong Pilot Checklist

Goal: provide a concrete no-write execution checklist for the first real
Shandong `admission_scores` small-sample pilot.

- [x] Add `docs/real-data-first-shandong-pilot.md`.
- [x] Limit first pilot scope to Shandong `admission_scores`, one year, 5 to
      20 rows.
- [x] Document source audit, snapshot, rows bundle, dry-run, artifact manifest,
      and stop gates.
- [x] Make the completion definition explicitly no-write and pre-loader.
- [x] Link the checklist from README and the MVP status page.
- [x] Keep the update documentation-only: no crawler, download, DB write, seed
      edit, or loader run.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-first-shandong-pilot.md \
  docs/real-data-mvp-status.md README.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Rollback:

- Remove `docs/real-data-first-shandong-pilot.md`.
- Remove README and status-page links.
- Remove this Phase 32 section if first-pilot scope changes.

## Phase 33. Source Audit Scope Traceability

Goal: make source audit artifacts self-describing enough for downstream review
without relying on remembered CLI arguments.

- [x] Add audited `scope` to source registry audit reports.
- [x] Include data category, expected provinces, expected years, and reviewed
      requirement in the scope.
- [x] Include source audit scope in pilot artifact manifest review summary.
- [x] Add tests for direct registry, CLI, and artifact manifest output.
- [x] Update runbook and first Shandong pilot checklist.
- [x] Keep the change no-write: no crawler, DB write, seed edit, RAG refresh,
      or loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/registry.py \
  backend/data_pipeline/sources/cli.py \
  backend/data_pipeline/pilots/artifacts.py \
  tests/test_data_pipeline_contracts.py \
  tests/test_data_pipeline_sources_cli.py \
  tests/test_data_pipeline_pilot_artifacts.py
python3 -m pytest \
  tests/test_data_pipeline_contracts.py \
  tests/test_data_pipeline_sources_cli.py \
  tests/test_data_pipeline_pilot_artifacts.py
```

Rollback:

- Remove `SourceAuditScope` and the `scope` field from source audit reports.
- Remove `source_audit_scope` from artifact manifest review summaries.
- Restore tests and docs to the previous `passed/issues` source audit shape.
- Remove this Phase 33 section if source audit scope contract changes.

## Phase 34. Artifact Scope Readiness Gate

Goal: prevent artifact manifests from reporting loader readiness when the source
audit scope does not match the dry-run audit scope.

- [x] Add `artifact_scope_issues` to pilot artifact manifests.
- [x] Block `ready_for_loader_execution` when source audit scope is missing or
      mismatched.
- [x] Compare source audit data category to dry-run dataset.
- [x] Compare source audit expected provinces and years to dry-run coverage.
- [x] Add helper and CLI tests for scope mismatch blockers.
- [x] Update runbook and first Shandong pilot checklist.
- [x] Keep the change no-write: no crawler, DB write, seed edit, RAG refresh,
      or loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/pilots/artifacts.py \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
python3 -m pytest \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
```

Rollback:

- Remove `artifact_scope_issues` from artifact manifests.
- Restore readiness gating to path/source/dry-run/loader approval checks only.
- Remove scope mismatch tests and docs.
- Remove this Phase 34 section if artifact scope policy changes.

## Phase 35. Loader Approval Consistency Gate

Goal: prevent artifact manifests from reporting loader readiness when the
loader approval packet does not match the dry-run audit it claims to approve.

- [x] Add `loader_approval_issues` to pilot artifact manifests.
- [x] Block `ready_for_loader_execution` when loader approval identity or
      counts do not match the dry-run audit.
- [x] Compare source ID, snapshot ID, dataset, and candidate count.
- [x] Compare loader approval `entity_counts` to dry-run coverage entity counts.
- [x] Add helper and CLI tests for loader approval mismatch blockers.
- [x] Update runbook, status page, first Shandong pilot checklist, dry-run
      guide, and example README.
- [x] Keep the change no-write: no crawler, DB write, seed edit, RAG refresh,
      or loader run.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/pilots/artifacts.py \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
python3 -m pytest \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
```

Rollback:

- Remove `loader_approval_issues` from artifact manifests.
- Restore readiness gating to source, dry-run, path, scope, and approval
  allowed checks only.
- Remove loader approval mismatch tests and docs.
- Remove this Phase 35 section if loader approval consistency policy changes.

## Phase 36. Artifact-Guarded Loader Entry

Goal: provide a stricter canonical loader entry point that reuses the complete
pilot artifact manifest gate before any candidate write.

- [x] Add `load_candidates_after_artifact_manifest(...)`.
- [x] Keep `load_candidates_after_audit(...)` as the lower-level dry-run guard.
- [x] Export the stricter loader entry from `backend.data_pipeline.loaders`.
- [x] Add isolated SQLite tests for ready and not-ready artifact manifests.
- [x] Update runbook, dry-run guide, and architecture doc.
- [x] Keep the change no-write for real app state: tests use isolated SQLite
      only, with no crawler, seed edit, real DB write, RAG refresh, or loader
      run command execution.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/loaders/canonical.py \
  backend/data_pipeline/loaders/__init__.py \
  tests/test_data_pipeline_loader.py
python3 -m pytest tests/test_data_pipeline_loader.py
```

Current verification status:

- `python3 -m py_compile ...` passed for the loader entry, package export, and
  loader tests.
- `python3 -m pytest tests/test_data_pipeline_loader.py` is pending because the
  local interpreter reports `No module named pytest`.
- `python3 -m backend.data_pipeline.env_check` reports missing `pydantic`,
  `sqlalchemy`, and `pytest`; no dependency install was attempted.
- Line-length scan is clean for the Phase 36 loader, export, tests, runbook,
  dry-run guide, and this task section.

Rollback:

- Remove `load_candidates_after_artifact_manifest(...)`.
- Remove its export and tests.
- Restore docs to recommend `load_candidates_after_audit(...)` only.
- Remove this Phase 36 section if loader entry policy changes.

## Phase 37. Artifact Loader Handoff Contract

Goal: make pilot artifact manifests self-describe how they may be handed to the
canonical loader without implying automatic write approval.

- [x] Add additive `loader_handoff` metadata to pilot artifact manifests.
- [x] Record the recommended loader entry point:
      `load_candidates_after_artifact_manifest`.
- [x] Record that a separate loader run command is still required.
- [x] Keep readiness behavior unchanged: `ready_for_loader_execution` remains
      the machine gate, and the manifest still does not execute writes.
- [x] Add tests for the ready manifest handoff metadata.
- [x] Update runbook, dry-run guide, and MVP status docs.
- [x] Keep the change no-write for real app state: no crawler, seed edit, DB
      write, RAG refresh, or loader run command execution.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/pilots/artifacts.py \
  tests/test_data_pipeline_pilot_artifacts.py
python3 -m pytest tests/test_data_pipeline_pilot_artifacts.py
```

Current verification status:

- `python3 -m py_compile ...` passed for artifact manifest code and tests.
- Line-length scan is clean for the Phase 37 code, tests, docs, and task
  section.
- `python3 -m pytest tests/test_data_pipeline_pilot_artifacts.py` is pending
  because the local interpreter reports `No module named pytest`.
- `python3 -m backend.data_pipeline.env_check` still reports missing
  `pydantic`, `sqlalchemy`, and `pytest`; no dependency install was attempted.

Rollback:

- Remove `loader_handoff` from `PilotArtifactManifest`.
- Remove the helper, tests, and documentation references.
- Remove this Phase 37 section if artifact handoff policy changes.

## Phase 38. Agent Source Envelope Review Fields

Goal: make Agent/tool `sources` metadata carry enough source-review context for
future answers to cite real data with caution instead of only reporting numbers.

- [x] Add source registry review fields to lineage source metadata:
      `source_type`, `trust_score`, `review_status`, and `license_note`.
- [x] Keep the change additive: existing source metadata fields and tool result
      core fields remain unchanged.
- [x] Add lineage formatter tests for the expanded source envelope.
- [x] Add tool-level tests proving score and plan results receive the fields.
- [x] Update architecture and MVP status docs.
- [x] Keep the change no-write for real app state: no crawler, seed edit, DB
      write, RAG refresh, or loader run command execution.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/lineage/sources.py \
  tests/test_data_lineage_sources.py \
  tests/test_tool_source_metadata.py
python3 -m pytest \
  tests/test_data_lineage_sources.py \
  tests/test_tool_source_metadata.py
```

Current verification status:

- `python3 -m py_compile ...` passed for the source formatter and source
  metadata tests.
- Line-length scan is clean for Phase 38 code, tests, MVP status docs, and this
  task section.
- `docs/data-storage-architecture.md` still has pre-existing long lines; not
  reflowed to avoid unrelated documentation churn.
- `python3 -m pytest tests/test_data_lineage_sources.py
  tests/test_tool_source_metadata.py` is pending because the local interpreter
  reports `No module named pytest`.
- `python3 -m backend.data_pipeline.env_check` still reports missing
  `pydantic`, `sqlalchemy`, and `pytest`; no dependency install was attempted.

Rollback:

- Remove the added source envelope fields from
  `backend/data_pipeline/lineage/sources.py`.
- Remove the related test assertions and documentation references.
- Remove this Phase 38 section if Agent source envelope policy changes.

## Phase 39. Agent Source Summary

Goal: make Agent/tool results expose a compact citation-readiness summary so
answers can lower certainty when a result lacks reviewed, fresh, trusted
sources.

- [x] Add `summarize_sources(...)` for source metadata lists.
- [x] Export the helper from `backend.data_pipeline.lineage`.
- [x] Attach additive `source_summary` to score and enrollment-plan result
      items through the existing tool source metadata hook.
- [x] Add tests for citation-ready and missing-source summaries.
- [x] Add tool-level tests proving `source_summary` reaches enriched results.
- [x] Update architecture and MVP status docs.
- [x] Keep the change no-write for real app state: no crawler, seed edit, DB
      write, RAG refresh, or loader run command execution.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/lineage/sources.py \
  backend/data_pipeline/lineage/__init__.py \
  backend/tools/definitions.py \
  tests/test_data_lineage_sources.py \
  tests/test_tool_source_metadata.py
python3 -m pytest \
  tests/test_data_lineage_sources.py \
  tests/test_tool_source_metadata.py
```

Current verification status:

- `python3 -m py_compile ...` passed for the source summary helper, lineage
  export, tool attachment, and source metadata tests.
- Line-length scan is clean for the new Phase 39 helper/tests/docs/task section.
- `backend/tools/definitions.py` still has pre-existing long lines; not
  reflowed to avoid unrelated tool-definition churn.
- `python3 -m pytest tests/test_data_lineage_sources.py
  tests/test_tool_source_metadata.py` is pending because the local interpreter
  reports `No module named pytest`.
- `python3 -m backend.data_pipeline.env_check` still reports missing
  `pydantic`, `sqlalchemy`, and `pytest`; no dependency install was attempted.

Rollback:

- Remove `summarize_sources(...)` and its export.
- Remove `source_summary` from `_attach_sources_to_items(...)`.
- Remove related tests, documentation references, and this Phase 39 section.

## Phase 40. Agent Source Summary Incomplete-metadata Guard

Goal: make Agent/tool citation summaries cautious when source metadata is
present but missing key confidence or review evidence.

- [x] Treat missing `confidence` as `needs_caution=true`.
- [x] Treat missing `trust_score` as `needs_caution=true`.
- [x] Treat missing `review_status` as `needs_caution=true`.
- [x] Keep the change additive: `source_summary` fields remain stable.
- [x] Add unit coverage for incomplete source metadata.
- [x] Update architecture and MVP status docs.
- [x] Keep the change no-write for real app state: no crawler, seed edit, DB
      write, RAG refresh, or loader run command execution.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/lineage/sources.py \
  tests/test_data_lineage_sources.py
python3 -m pytest tests/test_data_lineage_sources.py
```

Current verification status:

- `python3 -m py_compile ...` passed for the source summary helper and lineage
  source tests.
- Line-length scan is clean for the Phase 40 source helper, test, MVP status
  doc, and this task section.
- `python3 -m pytest tests/test_data_lineage_sources.py` is pending because the
  local interpreter reports `No module named pytest`.
- `python3 -m backend.data_pipeline.env_check` still reports missing
  `pydantic`, `sqlalchemy`, and `pytest`; no dependency install was attempted.

Rollback:

- Restore `summarize_sources(...)` caution logic to the Phase 39 behavior.
- Remove the incomplete-metadata test and documentation references.
- Remove this Phase 40 section if Agent caution policy changes.

## Phase 41. Tool Result Source Summary

Goal: expose response-level source coverage so Agent answers can judge the
whole result set without scanning every item manually.

- [x] Add `_summarize_result_sources(...)` for enriched tool result items.
- [x] Add top-level `source_summary` to `search_admission` success responses.
- [x] Add top-level `source_summary` to `search_enrollment_plan` success
      responses.
- [x] Add top-level `source_summary` to `calculate_match` success responses.
- [x] Keep the change additive: existing result arrays and item fields remain
      stable.
- [x] Add tool-level tests for mixed sourced/unsourced and single sourced
      results.
- [x] Update architecture and MVP status docs.
- [x] Keep the change no-write for real app state: no crawler, seed edit, DB
      write, RAG refresh, or loader run command execution.

Validation:

```bash
python3 -m py_compile \
  backend/tools/definitions.py \
  tests/test_tool_source_metadata.py
python3 -m pytest tests/test_tool_source_metadata.py
```

Current verification status:

- `python3 -m py_compile ...` passed for tool definitions and tool source
  metadata tests.
- Focused line-length scan is clean for the new helper plus related tests,
  MVP status doc, and this task section.
- `python3 -m pytest tests/test_tool_source_metadata.py` is pending because the
  local interpreter reports `No module named pytest`.

Rollback:

- Remove `_summarize_result_sources(...)`.
- Remove the top-level `source_summary` additions from tool responses.
- Remove related tests and documentation references.
- Remove this Phase 41 section if response-level source summaries change.

## Phase 42. Shandong Official Entry Candidates

Goal: make the first Shandong pilot easier to review by recording official
source entry candidates before any sample rows are prepared.

- [x] Add official Shandong Education Admissions Examination Institute entry
      candidates to the first-pilot guide.
- [x] Distinguish admission-score candidates from policy/background sources.
- [x] Mark every entry as candidate-only pending human review.
- [x] Require an official URL before using a first-volunteer filing table as a
      snapshot source.
- [x] Keep the change documentation-only: no crawler, no file download, no DB
      write, no seed edit, no RAG refresh, and no loader command.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-first-shandong-pilot.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Line-length scan passed for the first-pilot guide and this task section.
- No code, crawler, file download, DB write, seed edit, RAG refresh, or loader
  command was run in this phase.

Rollback:

- Remove the official-entry candidate table from the first-pilot guide.
- Remove this Phase 42 section if source-candidate policy changes.

## Phase 43. Shandong Manual Row Worksheet

Goal: make the first Shandong sample rows auditable before any rows bundle is
created.

- [x] Add manual row worksheet guidance to the first-pilot guide.
- [x] Require source URL, snapshot, original file, and row/page/sheet location.
- [x] Require natural-key and score-field review before normalized rows.
- [x] Require reviewer/date evidence and row-level blocker checks.
- [x] Keep the change documentation-only: no generated sample rows, no crawler,
      no file download, no DB write, no seed edit, no RAG refresh, and no loader
      command.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-first-shandong-pilot.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Line-length scan passed for the first-pilot guide and this task section.
- No code, generated sample rows, crawler, file download, DB write, seed edit,
  RAG refresh, or loader command was run in this phase.

Rollback:

- Remove the manual row worksheet section from the first-pilot guide.
- Remove this Phase 43 section if row-review policy changes.

## Phase 44. Candidate Row Review Metadata

Goal: keep row-level human review evidence attached to parser-produced
candidates and make it enforceable for the Shandong pilot.

- [x] Add `CandidateReviewMetadata` to the candidate source contract.
- [x] Preserve nested `review` metadata from manual sample rows.
- [x] Preserve flat worksheet fields from manual sample rows.
- [x] Make `QualityGateConfig` a Pydantic model so CLI payload validation works.
- [x] Add optional `require_review_metadata` quality gate enforcement.
- [x] Keep review enforcement disabled by default for backward compatibility.
- [x] Update the Shandong pilot guide to require review metadata in
      `quality_config`.
- [x] Keep the change no-write: no crawler, no file download, no DB write,
      no seed edit, no RAG refresh, no migration run, and no loader command.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/quality/candidates.py \
  backend/data_pipeline/parsers/manual_samples.py \
  backend/data_pipeline/quality/checks.py \
  backend/data_pipeline/quality/__init__.py \
  tests/test_data_pipeline_parsers.py \
  tests/test_data_pipeline_quality.py

python3 -m pytest \
  tests/test_data_pipeline_parsers.py \
  tests/test_data_pipeline_quality.py
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the
  candidate, parser, quality gate, export, and related test files.
- Focused line-length scan passed for the touched code, tests, Shandong pilot
  guide, and this task section.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.
- A runtime import probe could not run because the local interpreter reports
  `No module named 'pydantic'`.

Rollback:

- Remove `CandidateReviewMetadata` and `CandidateSource.review`.
- Remove parser review-field mapping and review metadata quality checks.
- Restore `QualityGateConfig` to its previous contract if CLI config parsing
  changes.
- Remove related tests and this Phase 44 section.

## Phase 45. Reviewed Pilot Bundle Examples

Goal: make the no-write Shandong dry-run examples demonstrate the reviewed row
contract added in Phase 44.

- [x] Add row-level `review` metadata to admission-score bundle examples.
- [x] Add row-level `review` metadata to enrollment-plan bundle examples.
- [x] Add row-level `review` metadata to snapshot-dir rows bundle examples.
- [x] Enable `quality_config.require_review_metadata=true` in examples.
- [x] Add tests that load repository examples and run dry-run gates.
- [x] Assert example dry-runs are load-ready with no blockers.
- [x] Document that example review metadata is synthetic and must be replaced
      before real pilots.
- [x] Keep the change no-write: no crawler, no file download, no DB write,
      no seed edit, no RAG refresh, no migration run, and no loader command.

Validation:

```bash
python3 -m json.tool examples/real_data/sd_pilot_bundle.json
python3 -m json.tool examples/real_data/sd_plan_pilot_bundle.json
python3 -m json.tool examples/real_data/sd_snapshot_pilot_rows.json
python3 -m pytest tests/test_data_pipeline_pilot_dry_run.py
```

Current verification status:

- `python3 -m json.tool ...` passed for the three real-data example bundles.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the
  updated dry-run tests.
- Focused line-length scan passed for the touched examples, docs, tests, and
  this task section.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Remove `review` metadata and `require_review_metadata` from the examples.
- Remove example-driven dry-run tests.
- Remove this Phase 45 section if the reviewed bundle shape changes.

## Phase 46. Static Pilot Evidence Chain Example

Goal: make the synthetic Shandong pilot examples include a full no-write
evidence chain that reviewers can inspect before any loader run is discussed.

- [x] Add checked-in static source audit, dry-run audit, loader approval, and
      artifact manifest examples under `examples/real_data/artifacts/`.
- [x] Keep the artifacts synthetic and clearly non-official.
- [x] Add tests that compare the static artifact manifest with
      `build_pilot_artifact_manifest(...)` output.
- [x] Assert the manifest has no path, scope, or loader approval issues.
- [x] Assert the manifest still requires a separate loader run command.
- [x] Document that checked-in artifacts are examples only and must be replaced
      by generated, reviewed artifacts for a real pilot.
- [x] Keep the change no-write: no crawler, no file download, no DB write,
      no seed edit, no RAG refresh, no migration run, and no loader command.

Validation:

```bash
python3 -m json.tool examples/real_data/artifacts/sd_source_audit.json
python3 -m json.tool examples/real_data/artifacts/sd_snapshot_pilot_audit.json
python3 -m json.tool examples/real_data/artifacts/sd_snapshot_pilot_approval.json
python3 -m json.tool examples/real_data/artifacts/sd_pilot_artifact_manifest.json
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  tests/test_data_pipeline_pilot_artifacts.py
python3 -m pytest tests/test_data_pipeline_pilot_artifacts.py
```

Current verification status:

- `python3 -m json.tool ...` passed for all four checked-in artifact JSON
  examples.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the
  updated artifact manifest tests.
- Focused line-length scan passed for the artifact JSON examples, tests, docs,
  and this task section.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Remove `examples/real_data/artifacts/sd_pilot_artifact_manifest.json`.
- Remove static example assertions from `tests/test_data_pipeline_pilot_artifacts.py`.
- Remove checked-in artifact wording from example and dry-run docs.
- Remove this Phase 46 section if static evidence examples are no longer kept.

## Phase 47. Shandong Official Sample Intake Template

Goal: give the first real Shandong sample a structured intake packet before any
rows bundle or raw snapshot is created.

- [x] Add `examples/real_data/sd_official_sample_intake_template.json`.
- [x] Mark the template as not a dry-run bundle.
- [x] Include pilot scope, source review, snapshot review, row review columns,
      quality config, stop gates, and non-goals.
- [x] Document the template in `examples/real_data/README.md`.
- [x] Link the template into the first Shandong pilot flow before rows bundle
      preparation.
- [x] Keep the change no-write: no crawler, no file download, no DB write,
      no seed edit, no RAG refresh, no migration run, and no loader command.

Validation:

```bash
python3 -m json.tool examples/real_data/sd_official_sample_intake_template.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  examples/real_data/sd_official_sample_intake_template.json \
  examples/real_data/README.md \
  docs/real-data-first-shandong-pilot.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m json.tool ...` passed for the official sample intake template.
- Focused line-length scan passed for the intake template, example README,
  Shandong pilot guide, and this task section.

Rollback:

- Remove `examples/real_data/sd_official_sample_intake_template.json`.
- Remove intake-template wording from example and Shandong pilot docs.
- Remove this Phase 47 section if intake templates move elsewhere.

## Phase 48. Shandong Official Entry Web Check Notes

Goal: record a dated no-download web check of official Shandong source
candidates before anyone prepares the first real intake packet.

- [x] Verify the Shandong Education Admissions Examination Institute homepage
      is reachable as the `sd_exam_authority` homepage candidate.
- [x] Record official 2025 filing-table page candidates for manual intake.
- [x] Record that the 2025 control-line page is background-only and should not
      be mixed into school filing rows.
- [x] Record the site footer authorization caution as a required
      `license_note` review input.
- [x] Keep the change no-write: no crawler, no attachment download, no raw
      snapshot, no DB write, no seed edit, no RAG refresh, and no loader command.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-first-shandong-pilot.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Focused line-length scan passed for the first Shandong pilot guide and this
  task section.

Rollback:

- Remove the dated web-check notes from the first Shandong pilot guide.
- Remove this Phase 48 section if official-source notes move elsewhere.

## Phase 49. Shandong Source Registry Coverage Alignment

Goal: align the bundled source registry with the no-download 2025 Shandong
official page candidate check, while keeping source review status conservative.

- [x] Register `2025` under `sd_exam_authority.coverage.years`.
- [x] Keep `sd_exam_authority.review_status` as `candidate`.
- [x] Add a source note that 2025 page candidates were web-checked on
      2026-06-07 and still need per-snapshot license and attachment review.
- [x] Update bundled source registry audit expectations so the 2025 Shandong
      source audit warning is only `source_not_reviewed`.
- [x] Document that the registry year means candidate coverage only, not
      loader approval or production use.
- [x] Keep the change no-write: no crawler, no attachment download, no raw
      snapshot, no DB write, no seed edit, no RAG refresh, and no loader
      command.

Validation:

```bash
python3 -m json.tool backend/data_pipeline/sources/sources.json
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  tests/test_data_pipeline_contracts.py \
  tests/test_data_pipeline_pilot_artifacts.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/sources.json \
  tests/test_data_pipeline_contracts.py \
  docs/real-data-first-shandong-pilot.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m json.tool backend/data_pipeline/sources/sources.json` passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for
  `tests/test_data_pipeline_contracts.py` and
  `tests/test_data_pipeline_pilot_artifacts.py`.
- Focused line-length scan shows only pre-existing long URL/license_note lines
  in `backend/data_pipeline/sources/sources.json`; the new registry note is
  under the 100-character threshold.
- Runtime source audit CLI could not run because the local interpreter reports
  `No module named 'pydantic'`.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Change `sd_exam_authority.coverage.years` back to `[]`.
- Remove the 2025 web-check source note from the registry.
- Restore bundled registry audit warning expectations.
- Remove the registry-alignment note from the Shandong pilot guide.
- Remove this Phase 49 section if registry candidate coverage is reverted.

## Phase 50. Reviewed Tabular Sample Parser

Goal: let a manually reviewed official worksheet become a rows bundle without
writing JSON rows by hand or adding crawler/spreadsheet dependencies.

- [x] Add `ReviewedTabularSampleParser` for reviewed CSV-like rows.
- [x] Normalize blank cells, integer fields, confidence, and `review.*` fields.
- [x] Delegate candidate creation to the existing `ManualSampleParser`.
- [x] Add a no-write CSV normalization CLI that outputs `{ "rows": [...] }`.
- [x] Export the parser helpers from `backend.data_pipeline.parsers`.
- [x] Add parser and CLI tests for normalization, review metadata, and invalid
      numeric cells.
- [x] Document the CSV-to-rows-bundle step in examples and the Shandong pilot
      guide.
- [x] Keep the change no-write: no crawler, no remote attachment parsing, no
      DB write, no seed edit, no RAG refresh, and no loader command.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/parsers/tabular_samples.py \
  backend/data_pipeline/parsers/tabular_cli.py \
  backend/data_pipeline/parsers/__init__.py \
  tests/test_data_pipeline_parsers.py
python3 -m backend.data_pipeline.parsers.tabular_cli \
  /tmp/reviewed_rows.csv \
  --dataset admission_scores
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/parsers/tabular_samples.py \
  backend/data_pipeline/parsers/tabular_cli.py \
  tests/test_data_pipeline_parsers.py \
  examples/real_data/README.md \
  docs/real-data-first-shandong-pilot.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the
  tabular parser, CLI, parser exports, and parser tests.
- No focused line-length issues were found in the tabular parser, CLI, parser
  tests, example README, Shandong pilot guide, or this task section.
- No-write CLI smoke passed against `/private/tmp/reviewed_rows.csv`; it printed
  a rows bundle with normalized integers, dataset, and nested review metadata.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Remove `backend/data_pipeline/parsers/tabular_samples.py`.
- Remove `backend/data_pipeline/parsers/tabular_cli.py`.
- Remove tabular exports from `backend/data_pipeline/parsers/__init__.py`.
- Remove tabular parser tests from `tests/test_data_pipeline_parsers.py`.
- Remove CSV-to-rows-bundle wording from examples and the pilot guide.
- Remove this Phase 50 section.

## Phase 51. Official Sample Intake Readiness Gate

Goal: add a machine-checkable no-write gate before a reviewed official sample
is allowed to become a raw snapshot or rows bundle.

- [x] Add `backend.data_pipeline.intake.review_intake_payload`.
- [x] Validate pilot scope, source review, snapshot review, checksum shape, and
      quality config alignment.
- [x] Add `backend.data_pipeline.intake.cli` for local intake JSON review.
- [x] Keep the intake CLI independent from `pydantic` and database imports.
- [x] Add tests for blank-template blocking, ready packet passing, quality scope
      mismatch blocking, and CLI output.
- [x] Document intake review in the Shandong pilot guide and MVP runbook.
- [x] Keep the change no-write: no crawler, no attachment download, no raw
      snapshot creation, no row parsing, no DB write, no seed edit, no RAG
      refresh, and no loader command.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/intake/__init__.py \
  backend/data_pipeline/intake/review.py \
  backend/data_pipeline/intake/cli.py \
  tests/test_data_pipeline_intake.py
python3 -m backend.data_pipeline.intake.cli \
  examples/real_data/sd_official_sample_intake_template.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/intake/__init__.py \
  backend/data_pipeline/intake/review.py \
  backend/data_pipeline/intake/cli.py \
  tests/test_data_pipeline_intake.py \
  docs/real-data-first-shandong-pilot.md \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for intake
  review, intake CLI, and intake tests.
- The checked-in blank Shandong intake template correctly failed readiness with
  `passed=false`, `ready_for_snapshot=false`, and 14 blocking errors.
- A complete `/private/tmp/ready_intake.json` smoke packet passed with
  `passed=true`, `ready_for_snapshot=true`, and zero issues.
- Focused line-length scan found no issues in intake code, intake tests,
  Shandong pilot guide, runbook, or this task section.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Remove `backend/data_pipeline/intake/`.
- Remove `tests/test_data_pipeline_intake.py`.
- Remove intake review CLI wording from the Shandong pilot guide and runbook.
- Remove this Phase 51 section.

## Phase 52. Intake Review In Artifact Manifest

Goal: make the final pilot artifact manifest include the official intake review
gate, so loader readiness cannot ignore pre-snapshot human review evidence.

- [x] Add `intake_review` and `intake_review_path` inputs to the artifact
      manifest builder.
- [x] Add `--intake-review` to the artifact manifest CLI.
- [x] Add `intake_review_issues` to artifact manifests.
- [x] Require intake review to pass and be ready for snapshot before
      `ready_for_loader_execution=true`.
- [x] Include intake review status, issue counts, and scope in
      `review_summary`.
- [x] Add a checked-in synthetic `sd_intake_review.json` artifact.
- [x] Update the static Shandong artifact manifest example.
- [x] Add builder and CLI tests for ready, missing, and failed intake review.
- [x] Update examples, dry-run docs, runbook, and Shandong pilot guide.
- [x] Keep the change no-write: no crawler, no attachment download, no raw
      snapshot creation, no row parsing, no DB write, no seed edit, no RAG
      refresh, and no loader command.

Validation:

```bash
python3 -m json.tool examples/real_data/artifacts/sd_intake_review.json
python3 -m json.tool examples/real_data/artifacts/sd_pilot_artifact_manifest.json
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/pilots/artifacts.py \
  backend/data_pipeline/pilots/artifacts_cli.py \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/pilots/artifacts.py \
  backend/data_pipeline/pilots/artifacts_cli.py \
  tests/test_data_pipeline_pilot_artifacts.py \
  tests/test_data_pipeline_pilot_artifacts_cli.py \
  examples/real_data/README.md \
  docs/real-data-first-shandong-pilot.md \
  docs/real-data-mvp-runbook.md \
  docs/real-data-pilot-dry-run.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m json.tool ...` passed for the synthetic intake review artifact
  and the updated Shandong artifact manifest example.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for artifact
  manifest code, CLI, builder tests, and CLI tests.
- Focused line-length scan found no issues in artifact code, artifact tests,
  examples, docs, or this task section.
- Runtime artifact manifest CLI could not run because the local interpreter
  reports `No module named 'pydantic'`.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Remove intake review inputs and readiness checks from artifact manifest code.
- Remove `--intake-review` from the artifact manifest CLI.
- Remove `examples/real_data/artifacts/sd_intake_review.json`.
- Restore the static Shandong artifact manifest example.
- Restore artifact manifest tests and CLI tests.
- Remove intake-review manifest wording from examples and docs.
- Remove this Phase 52 section.

## Phase 53. Loader Gate Includes Intake Review Issues

Goal: keep the canonical loader artifact-manifest gate aligned with the new
intake review evidence field.

- [x] Add `intake_review_issues` to loader artifact manifest blocker
      collection.
- [x] Add a loader test that surfaces intake review issues in
      `PilotLoadNotReadyError`.
- [x] Keep the change no-write: no loader execution, no DB write, no seed edit,
      no crawler, no RAG refresh, and no Agent tool change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/loaders/canonical.py \
  tests/test_data_pipeline_loader.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/loaders/canonical.py \
  tests/test_data_pipeline_loader.py \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the
  canonical loader and loader tests.
- Focused line-length scan found no issues in the loader, loader tests, or this
  task section.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Remove `intake_review_issues` from the loader blocker field list.
- Remove the intake issue assertion from `tests/test_data_pipeline_loader.py`.
- Remove this Phase 53 section.

## Phase 54. Agent Answer Source Policy

Goal: make tool responses expose an explicit answer-level citation policy
derived from the existing source summary, without recalculating lineage.

- [x] Add `build_answer_source_policy(...)` in the lineage source metadata
      helper.
- [x] Export the helper through `backend.data_pipeline.lineage`.
- [x] Add additive `answer_source_policy` to `search_admission`,
      `search_enrollment_plan`, and `calculate_match` success responses.
- [x] Keep existing `sources` and `source_summary` contracts unchanged.
- [x] Add focused tests for citeable, cautious, unsupported, and missing-summary
      policy states.
- [x] Document the answer policy and current tool coverage.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/lineage/sources.py \
  backend/data_pipeline/lineage/__init__.py \
  backend/tools/definitions.py \
  tests/test_data_lineage_sources.py \
  tests/test_tool_source_metadata.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/lineage/sources.py \
  tests/test_data_lineage_sources.py \
  tests/test_tool_source_metadata.py \
  docs/data-storage-architecture.md \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
python3 -m pytest tests/test_data_lineage_sources.py tests/test_tool_source_metadata.py
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the
  lineage source helper, lineage export, tool definitions, and focused tests.
- Focused line-length scan found no issues in changed Python files, focused
  tests, MVP status doc, or this task section. Existing long lines remain in
  `docs/data-storage-architecture.md` and were not reformatted in this phase.
- Runtime import smoke for `build_answer_source_policy` could not run because
  the local interpreter reports `No module named sqlalchemy`.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.
- `python3 -m backend.data_pipeline.env_check` reports Python `3.14.5` is OK,
  but `ready_for_cli_runtime=false` because `pydantic` and `sqlalchemy` are
  missing; `ready_for_tests=false` because `pytest` is missing.

Rollback:

- Remove `build_answer_source_policy(...)` and its export.
- Remove `answer_source_policy` from the three tool success responses.
- Remove the new policy assertions and docs.
- Remove this Phase 54 section.

## Phase 55. Lineage Policy Lazy Import Boundary

Goal: keep answer-source policy smoke checks independent from lineage DB
runtime dependencies.

- [x] Move `build_answer_source_policy(...)` to stdlib-only
      `backend/data_pipeline/lineage/policy.py`.
- [x] Keep `backend.data_pipeline.lineage.build_answer_source_policy`
      available through a lazy export.
- [x] Make lineage DB helpers lazy exports so importing the policy does not
      require `sqlalchemy`.
- [x] Keep `summarize_sources(...)`, `get_sources_for_entity(...)`, and DB
      helper names unchanged for existing callers.
- [x] Move focused policy tests into `tests/test_data_lineage_policy.py`.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/lineage/policy.py \
  backend/data_pipeline/lineage/sources.py \
  backend/data_pipeline/lineage/__init__.py \
  backend/tools/definitions.py \
  tests/test_data_lineage_policy.py \
  tests/test_data_lineage_sources.py \
  tests/test_tool_source_metadata.py
python3 -c \
  "from backend.data_pipeline.lineage import build_answer_source_policy as b; \
print(b(dict(source_count=1, citation_ready=True, needs_caution=False))['answer_mode'])"
python3 -c \
  "from backend.data_pipeline.lineage.policy import build_answer_source_policy as b; \
print(b(None)['reasons'][0])"
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/lineage/policy.py \
  backend/data_pipeline/lineage/sources.py \
  backend/data_pipeline/lineage/__init__.py \
  tests/test_data_lineage_policy.py \
  tests/test_data_lineage_sources.py \
  tests/test_tool_source_metadata.py \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
python3 -m pytest \
  tests/test_data_lineage_policy.py \
  tests/test_data_lineage_sources.py \
  tests/test_tool_source_metadata.py
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the
  lineage policy, lazy export, source formatter, tool definitions, and focused
  tests.
- Policy import smoke via `backend.data_pipeline.lineage` passed and printed
  `citeable`.
- Direct policy module smoke passed and printed `missing_source_summary`.
- Focused line-length scan found no issues in the changed Python files, tests,
  MVP status doc, or this task section.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.
- `python3 -m backend.data_pipeline.env_check` still reports Python `3.14.5`
  is OK, but runtime modules `pydantic` and `sqlalchemy` plus dev module
  `pytest` are missing.

Rollback:

- Move `build_answer_source_policy(...)` back into
  `backend/data_pipeline/lineage/sources.py`.
- Restore eager imports in `backend/data_pipeline/lineage/__init__.py`.
- Remove `backend/data_pipeline/lineage/policy.py`.
- Move or remove `tests/test_data_lineage_policy.py`.
- Remove this Phase 55 section.

## Phase 56. Answer Source Policy CLI

Goal: make Agent answer-source policy review executable as a no-write local
artifact check.

- [x] Add stdlib-only `backend/data_pipeline/lineage/policy_cli.py`.
- [x] Accept either a tool response JSON with top-level `source_summary` or a
      standalone summary JSON via `--summary-only`.
- [x] Return an `answer_source_policy_review` JSON payload with `passed`,
      `source_summary`, `answer_source_policy`, and no-write non-goals.
- [x] Return non-zero for `answer_mode=unsupported`.
- [x] Add focused CLI tests to `tests/test_data_lineage_policy.py`.
- [x] Document the CLI in the MVP runbook, status doc, and real-data examples.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/lineage/policy.py \
  backend/data_pipeline/lineage/policy_cli.py \
  tests/test_data_lineage_policy.py
python3 -m backend.data_pipeline.lineage.policy_cli \
  /private/tmp/tool_response_policy_ok.json \
  --policy-output /private/tmp/answer_source_policy_ok.json
python3 -m backend.data_pipeline.lineage.policy_cli \
  /private/tmp/source_summary_policy_block.json \
  --summary-only
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/lineage/policy.py \
  backend/data_pipeline/lineage/policy_cli.py \
  tests/test_data_lineage_policy.py \
  docs/real-data-mvp-runbook.md \
  docs/real-data-mvp-status.md \
  examples/real_data/README.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
python3 -m pytest tests/test_data_lineage_policy.py
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for policy,
  policy CLI, and focused policy tests.
- Focused line-length scan found no issues in the changed policy, CLI, test,
  runbook/status/example docs, or this task section.
- Citeable tool-response smoke passed with exit code 0 and wrote
  `/private/tmp/answer_source_policy_ok.json`.
- Unsupported summary-only smoke returned exit code 1 with
  `answer_mode=unsupported`.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Remove `backend/data_pipeline/lineage/policy_cli.py`.
- Remove the CLI tests from `tests/test_data_lineage_policy.py`.
- Remove runbook/status/example mentions of the policy CLI.
- Remove this Phase 56 section.

## Phase 57. Agent Visibility Activation Review

Goal: add a no-write gate that separates loader readiness from Agent/RAG
visibility.

- [x] Add stdlib-only `backend/data_pipeline/activation/review.py`.
- [x] Add `backend/data_pipeline/activation/cli.py`.
- [x] Require artifact manifest loader readiness, answer source policy review,
      separate Agent visibility approval, confirmed loader run, reviewer
      metadata, and scope alignment.
- [x] Keep the gate no-write: no loader execution, no DB write, no seed edit,
      no RAG refresh, and no Agent visibility change.
- [x] Add focused activation review and CLI tests.
- [x] Document activation review in the runbook and MVP status.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/activation/__init__.py \
  backend/data_pipeline/activation/review.py \
  backend/data_pipeline/activation/cli.py \
  tests/test_data_pipeline_activation.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/activation/__init__.py \
  backend/data_pipeline/activation/review.py \
  backend/data_pipeline/activation/cli.py \
  tests/test_data_pipeline_activation.py \
  docs/real-data-mvp-runbook.md \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
python3 -m backend.data_pipeline.activation.cli \
  --artifact-manifest /private/tmp/agent_activation_manifest.json \
  --answer-policy-review /private/tmp/agent_activation_answer_policy.json
python3 -m backend.data_pipeline.activation.cli \
  --artifact-manifest /private/tmp/agent_activation_manifest.json \
  --answer-policy-review /private/tmp/agent_activation_answer_policy.json \
  --activation-approval /private/tmp/agent_visibility_approval.json \
  --review-output /private/tmp/agent_visibility_activation_review.json
python3 -m pytest tests/test_data_pipeline_activation.py
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for activation
  package files and focused tests.
- Focused line-length scan found no issues in changed activation files/tests.
- Missing approval CLI smoke returned exit code 1 with
  `missing_agent_visibility_approval`.
- Complete approval CLI smoke returned exit code 0 and wrote
  `/private/tmp/agent_visibility_activation_review.json`.
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Remove `backend/data_pipeline/activation/`.
- Remove `tests/test_data_pipeline_activation.py`.
- Remove runbook/status mentions of Agent visibility activation review.
- Remove this Phase 57 section.

## Phase 58. Synthetic Agent Visibility Evidence Examples

Goal: make the checked-in synthetic evidence chain show that Agent visibility
is blocked by default even when loader artifacts are ready.

- [x] Add `examples/real_data/artifacts/sd_answer_source_policy.json`.
- [x] Add
      `examples/real_data/artifacts/sd_agent_visibility_activation_review.json`.
- [x] Keep the activation review intentionally blocked because no real
      `agent_visibility_approval` exists.
- [x] Add static artifact consistency checks to focused policy and activation
      tests.
- [x] Update `examples/real_data/README.md` with the new evidence files and
      no-write activation command.

Validation:

```bash
python3 -m json.tool \
  examples/real_data/artifacts/sd_answer_source_policy.json
python3 -m json.tool \
  examples/real_data/artifacts/sd_agent_visibility_activation_review.json
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  tests/test_data_lineage_policy.py \
  tests/test_data_pipeline_activation.py
python3 -m backend.data_pipeline.lineage.policy_cli \
  /private/tmp/sd_example_source_summary.json \
  --summary-only \
  --policy-output /private/tmp/sd_answer_source_policy_check.json
python3 -m backend.data_pipeline.activation.cli \
  --artifact-manifest examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --answer-policy-review examples/real_data/artifacts/sd_answer_source_policy.json \
  --review-output /private/tmp/sd_agent_visibility_activation_review_check.json
cmp -s /private/tmp/sd_answer_source_policy_check.json \
  examples/real_data/artifacts/sd_answer_source_policy.json
cmp -s /private/tmp/sd_agent_visibility_activation_review_check.json \
  examples/real_data/artifacts/sd_agent_visibility_activation_review.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  examples/real_data/README.md \
  tests/test_data_lineage_policy.py \
  tests/test_data_pipeline_activation.py \
  .trellis/tasks/05-31-real-data-todo/implement.md
python3 -m pytest tests/test_data_lineage_policy.py tests/test_data_pipeline_activation.py
```

Current verification status:

- `python3 -m json.tool ...` passed for both new static artifacts.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for focused
  tests.
- Focused line-length scan found no issues in the examples README, focused
  tests, or this task section.
- Regenerated answer policy artifact matched the checked-in artifact
  byte-for-byte (`cmp` exit code 0).
- Regenerated activation review artifact matched the checked-in artifact
  byte-for-byte (`cmp` exit code 0).
- Targeted `pytest` could not run because the local interpreter reports
  `No module named pytest`.

Rollback:

- Remove `examples/real_data/artifacts/sd_answer_source_policy.json`.
- Remove
  `examples/real_data/artifacts/sd_agent_visibility_activation_review.json`.
- Remove the static artifact assertions from focused tests.
- Remove the README additions and this Phase 58 section.

## Phase 59. Shandong Pilot Post-loader Gates

Goal: keep the first Shandong pilot guide aligned with answer policy and Agent
visibility activation gates.

- [x] Add post-loader answer source policy review commands to
      `docs/real-data-first-shandong-pilot.md`.
- [x] Add separate Agent visibility activation review command and approval
      requirements.
- [x] Update stop points for unsupported answer policy and failed Agent
      visibility activation.
- [x] Update no-write completion definition to keep Agent/RAG default use
      blocked.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-first-shandong-pilot.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Focused line-length scan found no issues in the Shandong pilot guide or this
  task section.

Rollback:

- Remove the Step 6 / Step 7 additions from
  `docs/real-data-first-shandong-pilot.md`.
- Restore the stop points and completion definition to the Phase 58 state.
- Remove this Phase 59 section.

## Phase 60. Review Checklist Answer/Activation Gates

Goal: keep the manual review checklist aligned with answer policy and Agent
visibility activation gates.

- [x] Update checklist objective to include Agent/RAG visibility approval.
- [x] Add answer source policy review requirements and blockers.
- [x] Add Agent visibility activation approval requirements and blockers.
- [x] Keep the update documentation-only: no loader run, DB write, seed edit,
      RAG refresh, or Agent visibility change.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-pilot-review-checklist.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Focused line-length scan found no issues in the review checklist or this task
  section.

Rollback:

- Remove sections 7 and 8 from `docs/real-data-pilot-review-checklist.md`.
- Restore the checklist objective to the Phase 59 wording.
- Remove this Phase 60 section.

## Phase 61. Architecture Answer/Activation Alignment

Goal: keep the storage architecture document aligned with the full real-data
MVP evidence chain.

- [x] Add answer source policy review and Agent visibility activation review to
      the target pipeline.
- [x] Add `backend/data_pipeline/activation/` to the MVP module table.
- [x] Document answer policy and activation no-write CLI usage.
- [x] Update the summary to include activation review as part of the controlled
      visibility boundary.
- [x] Keep the update documentation-only: no loader run, DB write, seed edit,
      RAG refresh, or Agent visibility change.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/data-storage-architecture.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Focused line-length scan found no issues in this task section or the new
  architecture additions. Existing long lines remain in
  `docs/data-storage-architecture.md` and were not reformatted in this phase.

Rollback:

- Remove the answer policy / activation additions from
  `docs/data-storage-architecture.md`.
- Restore the summary to the Phase 60 wording.
- Remove this Phase 61 section.

## Phase 62. README and Startup Entry Alignment

Goal: keep the top-level onboarding docs aligned with the current no-write
real-data MVP evidence chain.

- [x] Add the full source-to-activation evidence chain to `README.md`.
- [x] Document the current no-write boundary in `README.md`.
- [x] Point readers to synthetic example artifacts without treating them as
      real imported data.
- [x] Add real-data environment check commands to `docs/STARTUP.md`.
- [x] Keep the update documentation-only: no crawler, DB write, seed edit,
      loader run, RAG refresh, or Agent visibility change.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  README.md \
  docs/STARTUP.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Focused line-length scan found no issues in the new README, STARTUP, or task
  section additions. Existing long lines remain in README/STARTUP and were not
  reformatted in this phase.
- No code tests are required for this docs-only phase.

Rollback:

- Remove the real-data MVP chain and example-artifact note from `README.md`.
- Remove the real-data environment check commands from `docs/STARTUP.md`.
- Remove this Phase 62 section.

## Phase 63. Agent Visibility Approval Template

Goal: provide a safe human-fillable approval input for the activation review
gate without authorizing Agent/RAG visibility by default.

- [x] Add `examples/real_data/agent_visibility_approval_template.json`.
- [x] Default the template to `allow_agent_visibility=false` and
      `loader_run_confirmed=false`.
- [x] Document that activation review needs a separate approval input.
- [x] Keep the update example/docs-only: no loader run, DB write, seed edit,
      RAG refresh, or Agent visibility change.

Validation:

```bash
python3 -m json.tool examples/real_data/agent_visibility_approval_template.json
python3 -m backend.data_pipeline.activation.cli \
  --artifact-manifest examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --answer-policy-review examples/real_data/artifacts/sd_answer_source_policy.json \
  --activation-approval examples/real_data/agent_visibility_approval_template.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  examples/real_data/agent_visibility_approval_template.json \
  examples/real_data/README.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m json.tool` passed for the activation approval template.
- Activation CLI with the default template exited 1 as expected, with
  `ready_for_agent_visibility=false`.
- Focused line-length scan found no issues in the template, examples README,
  or this task section.
- No code tests are required for this example/docs-only phase.

Rollback:

- Remove `examples/real_data/agent_visibility_approval_template.json`.
- Remove the activation approval template note from `examples/real_data/README.md`.
- Remove this Phase 63 section.

## Phase 64. Loader Run Evidence Activation Gate

Goal: make Agent visibility activation depend on auditable loader run evidence,
not only a boolean confirmation.

- [x] Require `loader_run_evidence` when `loader_run_confirmed=true`.
- [x] Require run id, completed timestamp, artifact manifest path, succeeded
      status, and loaded counts.
- [x] Compare loader run loaded count with artifact manifest candidate count.
- [x] Update activation tests for passing evidence, missing evidence, and count
      mismatch.
- [x] Update the activation approval template and runbook requirements.
- [x] Keep the change no-write: no crawler, DB write, seed edit, loader run,
      RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/activation/review.py \
  tests/test_data_pipeline_activation.py
python3 -m json.tool examples/real_data/agent_visibility_approval_template.json
python3 -m backend.data_pipeline.activation.cli \
  --artifact-manifest examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --answer-policy-review examples/real_data/artifacts/sd_answer_source_policy.json \
  --activation-approval examples/real_data/agent_visibility_approval_template.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/activation/review.py \
  tests/test_data_pipeline_activation.py \
  examples/real_data/agent_visibility_approval_template.json \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for activation
  review and activation tests.
- `python3 -m json.tool` passed for the activation approval template.
- Activation CLI with the default template exited 1 as expected, with
  `ready_for_agent_visibility=false`.
- Function-level smoke confirmed valid loader evidence passes and mismatched
  loaded counts block activation.
- Focused line-length scan found no issues in touched Phase 64 files.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Remove the `loader_run_evidence` validation from activation review.
- Restore activation tests to the Phase 63 contract.
- Remove `loader_run_evidence` fields from the approval template and runbook.
- Remove this Phase 64 section.

## Phase 65. Loader Run Evidence Review

Goal: add a no-write review step for post-loader run evidence before it is used
in Agent visibility approval.

- [x] Add stdlib-only `build_loader_run_evidence_review(...)`.
- [x] Add `backend.data_pipeline.activation.loader_evidence_cli`.
- [x] Require matching artifact manifest path, source id, snapshot id, dataset,
      loader entrypoint, succeeded status, and loaded counts.
- [x] Compare loaded counts to artifact manifest `candidate_count`.
- [x] Add a human-fillable canonical loader run record template.
- [x] Add focused tests and documentation for the new review step.
- [x] Keep the step no-write: no crawler, DB write, seed edit, loader run,
      RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/activation/loader_evidence.py \
  backend/data_pipeline/activation/loader_evidence_cli.py \
  backend/data_pipeline/activation/__init__.py \
  tests/test_data_pipeline_loader_evidence.py
python3 -m json.tool examples/real_data/canonical_loader_run_record_template.json
python3 -m backend.data_pipeline.activation.loader_evidence_cli \
  --artifact-manifest examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --loader-run-record examples/real_data/canonical_loader_run_record_template.json
python3 -m pytest tests/test_data_pipeline_loader_evidence.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/activation/loader_evidence.py \
  backend/data_pipeline/activation/loader_evidence_cli.py \
  tests/test_data_pipeline_loader_evidence.py \
  examples/real_data/canonical_loader_run_record_template.json \
  examples/real_data/README.md \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for loader
  evidence modules and tests.
- `python3 -m json.tool` passed for the canonical loader run record template.
- Loader evidence CLI with the default template exited 1 as expected, with
  `ready_for_activation_evidence=false`.
- Loader evidence CLI with a `/private/tmp` valid smoke record exited 0, with
  `ready_for_activation_evidence=true`.
- Import smoke passed for the activation package exports.
- Focused line-length scan found no issues in touched Phase 65 files.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Remove `backend/data_pipeline/activation/loader_evidence.py`.
- Remove `backend/data_pipeline/activation/loader_evidence_cli.py`.
- Restore `backend/data_pipeline/activation/__init__.py`.
- Remove `tests/test_data_pipeline_loader_evidence.py`.
- Remove `examples/real_data/canonical_loader_run_record_template.json`.
- Remove loader evidence review docs from examples README and runbook.
- Remove this Phase 65 section.

## Phase 66. Activation Evidence Review Link

Goal: make Agent visibility activation verify that approval evidence came from
a passed loader run evidence review.

- [x] Add optional `loader_run_evidence_review` input to activation review.
- [x] Add `--loader-run-evidence-review` to activation CLI.
- [x] Require the review when `loader_run_confirmed=true`.
- [x] Verify evidence review action, passed/ready status, scope, and exact
      evidence match with activation approval.
- [x] Add focused tests for missing and mismatched evidence review.
- [x] Document the new CLI input in runbook and examples README.
- [x] Keep the step no-write: no crawler, DB write, seed edit, loader run,
      RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/activation/review.py \
  backend/data_pipeline/activation/cli.py \
  tests/test_data_pipeline_activation.py
python3 -m backend.data_pipeline.activation.cli \
  --artifact-manifest examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --answer-policy-review examples/real_data/artifacts/sd_answer_source_policy.json
python3 -m pytest tests/test_data_pipeline_activation.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/activation/review.py \
  backend/data_pipeline/activation/cli.py \
  tests/test_data_pipeline_activation.py \
  docs/real-data-mvp-runbook.md \
  examples/real_data/README.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for activation
  review, CLI, and tests.
- Activation CLI without approval still exited 1 with
  `missing_agent_visibility_approval`.
- Activation CLI with `/private/tmp` synthetic approval and matching loader
  evidence review exited 0 with `ready_for_agent_visibility=true`.
- Focused line-length scan found no issues in touched Phase 66 files.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Remove `loader_run_evidence_review` from activation review and CLI.
- Restore activation tests to the Phase 65 contract.
- Remove the new activation CLI argument from runbook and examples README.
- Remove this Phase 66 section.

## Phase 67. Key Province Source Registry Candidates

Goal: prepare the registry for priority province expansion without collecting
or approving any real datasets.

- [x] Add Guangdong, Jiangsu, Zhejiang, Hebei, Sichuan, and Hubei provincial
      exam authority homepage candidates.
- [x] Keep each new source at `review_status=candidate`.
- [x] Keep `coverage.years=[]` to avoid implying any dataset year was reviewed.
- [x] Document that these are homepage candidates, not snapshot-approved
      dataset sources.
- [x] Keep the change registry/docs-only: no crawler, data download, DB write,
      seed edit, loader run, RAG refresh, or Agent visibility change.

Validation:

```bash
python3 -m json.tool backend/data_pipeline/sources/sources.json
python3 -m backend.data_pipeline.sources.cli \
  backend/data_pipeline/sources/sources.json \
  --data-category admission_scores \
  --province 广东 \
  --province 江苏 \
  --province 浙江 \
  --province 河北 \
  --province 四川 \
  --province 湖北 \
  --year 2025 \
  --require-reviewed
python3 -m pytest tests/test_data_pipeline_sources_cli.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/sources.json \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m json.tool` passed for `sources.json`.
- Stdlib structure smoke confirmed nine total sources, unique `source_id`
  values, and the six added province sources are `candidate` with empty
  `coverage.years`.
- Source audit CLI remains pending because the current Python environment has
  no `pydantic` module.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.
- Focused line-length scan found no issues in the new Phase 67 content. Existing
  long lines remain in the MOE source entry and were not reformatted.

Rollback:

- Remove the six new province source entries from
  `backend/data_pipeline/sources/sources.json`.
- Remove the registry expansion note from `docs/real-data-mvp-status.md`.
- Remove this Phase 67 section.

## Phase 68. Source Registry Stdlib Smoke Review

Goal: provide a no-dependency source registry smoke check for environments
where the formal pydantic audit cannot run yet.

- [x] Make `backend.data_pipeline.sources` exports lazy so stdlib-only submodules
      do not import pydantic through package initialization.
- [x] Add `build_source_registry_smoke_review(...)`.
- [x] Add `backend.data_pipeline.sources.smoke_cli`.
- [x] Check JSON shape, required source fields, duplicate source ids, URL shape,
      coverage shape, trust score, and review status.
- [x] Add focused tests for passing, duplicate, missing field, and CLI output.
- [x] Document the smoke CLI in MVP status.
- [x] Keep smoke review scoped: no remote fetch, no formal source audit, no DB
      write, no seed edit, no crawler, no RAG/Agent refresh.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/sources/__init__.py \
  backend/data_pipeline/sources/smoke.py \
  backend/data_pipeline/sources/smoke_cli.py \
  tests/test_data_pipeline_source_registry_smoke.py
python3 -m backend.data_pipeline.sources.smoke_cli \
  backend/data_pipeline/sources/sources.json
python3 -m pytest tests/test_data_pipeline_source_registry_smoke.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/__init__.py \
  backend/data_pipeline/sources/smoke.py \
  backend/data_pipeline/sources/smoke_cli.py \
  tests/test_data_pipeline_source_registry_smoke.py \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for source smoke
  modules and tests.
- `python3 -m backend.data_pipeline.sources.smoke_cli ...` exited 0 with
  `passed=true`, `source_count=9`, and zero issues.
- Focused line-length scan found no issues in touched Phase 68 files.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Restore eager imports in `backend/data_pipeline/sources/__init__.py`.
- Remove `backend/data_pipeline/sources/smoke.py`.
- Remove `backend/data_pipeline/sources/smoke_cli.py`.
- Remove `tests/test_data_pipeline_source_registry_smoke.py`.
- Remove the smoke CLI note from `docs/real-data-mvp-status.md`.
- Remove this Phase 68 section.

## Phase 69. Runbook Source Smoke Ordering

Goal: document how to use source registry smoke review when runtime
dependencies are not installed yet.

- [x] Add source smoke CLI to runbook Step 1 as a dependency-light fallback.
- [x] Clarify that smoke review does not replace formal source scope audit.
- [x] Clarify that formal source audit must be rerun after runtime dependencies
      are available.
- [x] Keep the update docs-only: no crawler, data download, DB write, seed edit,
      loader run, RAG refresh, or Agent visibility change.

Validation:

```bash
python3 -m backend.data_pipeline.sources.smoke_cli \
  backend/data_pipeline/sources/sources.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m backend.data_pipeline.sources.smoke_cli ...` exited 0 with
  `passed=true`, `source_count=9`, and zero issues.
- Focused line-length scan found no issues in the runbook or this task section.

Rollback:

- Remove the source smoke fallback from `docs/real-data-mvp-runbook.md`.
- Remove this Phase 69 section.

## Phase 70. Source Smoke Expectation Checks

Goal: let the stdlib-only source registry smoke review assert expected registry
coverage when formal pydantic audit is unavailable.

- [x] Add expected source id, province, and data category parameters to
      `build_source_registry_smoke_review(...)`.
- [x] Add repeatable `--expect-source-id`, `--expect-province`, and
      `--expect-data-category` CLI options.
- [x] Add a focused test for missing expected province.
- [x] Update runbook smoke command to check priority provinces and first
      datasets.
- [x] Keep smoke review scoped: no remote fetch, no formal source audit, no DB
      write, no seed edit, no crawler, no RAG/Agent refresh.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/sources/smoke.py \
  backend/data_pipeline/sources/smoke_cli.py \
  tests/test_data_pipeline_source_registry_smoke.py
python3 -m backend.data_pipeline.sources.smoke_cli \
  backend/data_pipeline/sources/sources.json \
  --expect-province 山东 \
  --expect-province 河南 \
  --expect-province 广东 \
  --expect-province 江苏 \
  --expect-province 浙江 \
  --expect-province 河北 \
  --expect-province 四川 \
  --expect-province 湖北 \
  --expect-data-category admission_scores \
  --expect-data-category enrollment_plans
python3 -m pytest tests/test_data_pipeline_source_registry_smoke.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/smoke.py \
  backend/data_pipeline/sources/smoke_cli.py \
  tests/test_data_pipeline_source_registry_smoke.py \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for source smoke
  modules and tests.
- Smoke CLI with expected priority provinces and first datasets exited 0 with
  `passed=true`, `source_count=9`, and zero issues.
- Focused line-length scan found no issues in touched Phase 70 files.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Remove expectation parameters from source smoke review and CLI.
- Restore source smoke tests to the Phase 69 contract.
- Restore the shorter source smoke command in the runbook.
- Remove this Phase 70 section.

## Phase 71. Conservative Policy For Untraced Tools

Goal: make legacy/untraced tool success responses explicit about unsupported
source status instead of silently returning uncited facts.

- [x] Add `_unsupported_source_summary(...)`.
- [x] Add conservative `source_summary` and `answer_source_policy` to successful
      `search_employment`, `compare_schools`, `search_policy`, and
      `semantic_search` responses.
- [x] Keep original business fields unchanged.
- [x] Add a focused helper test for unsupported legacy summaries.
- [x] Document that these tools are still not real-data citation entrances.
- [x] Keep the change additive: no DB write, seed edit, loader run, crawler,
      RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/tools/definitions.py \
  tests/test_tool_source_metadata.py
python3 -m pytest tests/test_tool_source_metadata.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/tools/definitions.py \
  tests/test_tool_source_metadata.py \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for tool
  definitions and source metadata tests.
- Focused line-length scan found no issues in the new Phase 71 content. Existing
  long descriptions and policy text remain in `backend/tools/definitions.py`.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Remove `_unsupported_source_summary(...)`.
- Remove the new source policy fields from untraced tool success responses.
- Remove the helper test and status doc note.
- Remove this Phase 71 section.

## Phase 72. Legacy Untraced Answer Policy Reason

Goal: make unsupported answer policy reasons distinguish legacy untraced tools
from other missing-source cases.

- [x] Add `source_status=legacy_untraced` to unsupported legacy summaries.
- [x] Add `legacy_untraced_tool` reason in `build_answer_source_policy(...)`.
- [x] Keep answer mode unchanged as `unsupported`.
- [x] Add focused policy and tool helper tests.
- [x] Keep the change additive: no DB write, seed edit, loader run, crawler,
      RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/lineage/policy.py \
  backend/tools/definitions.py \
  tests/test_data_lineage_policy.py \
  tests/test_tool_source_metadata.py
python3 -m pytest tests/test_data_lineage_policy.py tests/test_tool_source_metadata.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/lineage/policy.py \
  backend/tools/definitions.py \
  tests/test_data_lineage_policy.py \
  tests/test_tool_source_metadata.py \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for policy,
  tool definitions, and tests.
- Stdlib policy smoke returned reasons including `legacy_untraced_tool`.
- Focused line-length scan found no issues in the new Phase 72 content. Existing
  long descriptions and policy text remain in `backend/tools/definitions.py`.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Remove `source_status=legacy_untraced` from unsupported summaries.
- Remove `legacy_untraced_tool` from answer policy reasons.
- Restore policy/tool test expectations.
- Remove this Phase 72 section.

## Phase 73. Agent Prompt Source Policy Alignment

Goal: make the Agent system prompt respect tool-level answer source policy
before presenting facts to users.

- [x] Add `answer_source_policy` handling rules to `SKILL.md`.
- [x] Require citeable results to carry source/year/snapshot/confidence when
      available.
- [x] Require cautious results to lower certainty.
- [x] Require unsupported and `legacy_untraced_tool` results to be described as
      unverified rather than factual evidence.
- [x] Keep the change prompt-only: no tool schema change, DB write, seed edit,
      loader run, crawler, RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile backend/agent/core.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  SKILL.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile backend/agent/core.py`
  passed.
- Focused line-length scan still reports existing long lines in `SKILL.md`,
  but the new Phase 73 source-policy block has been wrapped under 100 columns.
- Full Agent runtime tests remain pending because the current environment has
  no project test dependencies.

Rollback:

- Remove the tool source policy section from `SKILL.md`.
- Remove this Phase 73 section.

## Phase 74. Agent Prompt Source Policy Regression

Goal: keep the Agent prompt source-policy contract from being accidentally
removed by future prompt edits.

- [x] Add a stdlib `unittest` check for the `SKILL.md` source-policy section.
- [x] Assert the prompt mentions `answer_source_policy`, all three answer
      modes, `legacy_untraced_tool`, and the no-real-data-evidence rule.
- [x] Keep the test dependency-light so it can run without project runtime
      dependencies.
- [x] Keep the change test-only: no Agent runtime logic, tool schema change,
      DB write, seed edit, loader run, crawler, RAG refresh, or Agent visibility
      change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  tests/test_agent_prompt_source_policy.py
python3 tests/test_agent_prompt_source_policy.py
python3 -m pytest tests/test_agent_prompt_source_policy.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  tests/test_agent_prompt_source_policy.py \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile
  tests/test_agent_prompt_source_policy.py` passed.
- `python3 tests/test_agent_prompt_source_policy.py` passed with one unittest.
- Focused line-length scan found no issues in the new prompt contract test or
  this Phase 74 section.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Remove `tests/test_agent_prompt_source_policy.py`.
- Remove this Phase 74 section.

## Phase 75. Prompt Source Policy Documentation Sync

Goal: document that answer source policy now has both tool-level review and
prompt-level handling, without implying Agent/RAG activation.

- [x] Update the MVP status doc to mention `SKILL.md` prompt-level handling.
- [x] Add prompt source policy contract check to the pre-real-sample gates.
- [x] Add the stdlib prompt contract test command to the runbook source-policy
      review step.
- [x] Keep the update docs-only: no code-level enforcement, DB write, seed edit,
      loader run, crawler, RAG refresh, or Agent visibility change.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-mvp-status.md \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Focused line-length scan found no issues in the status doc, runbook, or this
  Phase 75 section.
- `python3 tests/test_agent_prompt_source_policy.py` remains passing after the
  documentation sync.

Rollback:

- Remove the prompt-policy notes from the status doc and runbook.
- Remove this Phase 75 section.

## Phase 76. AgentCore Answer Source Policy Review

Goal: expose a structured source-policy review from non-streaming AgentCore
responses so callers can see whether tool-backed answers are citeable,
cautious, or unsupported.

- [x] Add stdlib-only `backend.agent.source_policy` helper.
- [x] Summarize per-tool `answer_source_policy` into one conservative review.
- [x] Add additive `answer_source_policy_review` to `AgentCore.chat()`
      non-streaming returns.
- [x] Treat missing policy on tool results as unsupported/cautious.
- [x] Add stdlib `unittest` coverage for no-tool, citeable, cautious,
      unsupported, and missing-policy cases.
- [x] Keep stream, tool schemas, DB, seeds, loader, crawler, RAG refresh, and
      Agent visibility unchanged.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/agent/source_policy.py \
  backend/agent/core.py \
  tests/test_agent_answer_source_policy_review.py
python3 tests/test_agent_answer_source_policy_review.py
python3 -m pytest tests/test_agent_answer_source_policy_review.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/agent/source_policy.py \
  backend/agent/core.py \
  tests/test_agent_answer_source_policy_review.py \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the new
  source-policy helper, AgentCore, and review tests.
- `python3 tests/test_agent_answer_source_policy_review.py` passed with seven
  stdlib unit tests.
- Focused line-length scan found no issues in the new helper, new tests, or
  this Phase 76 section. Existing long log lines remain in `backend/agent/core.py`.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Remove `backend/agent/source_policy.py`.
- Remove `answer_source_policy_review` from `AgentCore.chat()` returns.
- Remove `tests/test_agent_answer_source_policy_review.py`.
- Remove this Phase 76 section.

## Phase 77. AgentCore Source Policy Documentation Sync

Goal: document the new non-streaming `AgentCore.chat()` source-policy review
field without implying stream or Agent visibility changes.

- [x] Update the MVP status doc to mention additive
      `answer_source_policy_review`.
- [x] Update the storage architecture doc to explain conservative aggregation
      behavior.
- [x] Clarify that the field does not change stream events, RAG refresh, or
      Agent default visibility.
- [x] Keep the update docs-only: no new runtime behavior, DB write, seed edit,
      loader run, crawler, RAG refresh, or Agent visibility change.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-mvp-status.md \
  docs/data-storage-architecture.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 tests/test_agent_answer_source_policy_review.py` remains passing after
  the documentation sync.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` remains passing for
  Agent source-policy modules and tests.
- Full-file line-length scan still reports existing long lines in
  `docs/data-storage-architecture.md`, but the new AgentCore review paragraph,
  status doc paragraph, and this Phase 77 section are wrapped under 100 columns.

Rollback:

- Remove the AgentCore review notes from the status and architecture docs.
- Remove this Phase 77 section.

## Phase 78. Chat API Source Policy Propagation

Goal: propagate answer source policy review through the `/chat` API without
changing existing response fields or SSE event semantics.

- [x] Add optional `answer_source_policy_review` to `ChatResponse`.
- [x] Pass non-streaming AgentCore review through the `/chat` response.
- [x] Emit additive `answer_source_policy_review` SSE messages after
      `tool_result` messages.
- [x] Use conservative aggregation for streaming AgentCore and LangChain tool
      results.
- [x] Document non-streaming and streaming API propagation.
- [x] Keep old `reply`, `tool_calls`, `usage`, and text/tool_call/tool_result
      /done SSE events unchanged.
- [x] Keep frontend display, DB, seeds, loader, crawler, RAG refresh, and Agent
      visibility unchanged.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/routes/chat.py \
  backend/agent/source_policy.py \
  backend/agent/core.py
python3 tests/test_agent_answer_source_policy_review.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/routes/chat.py \
  docs/real-data-mvp-status.md \
  docs/data-storage-architecture.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for chat route,
  Agent source-policy helper, and AgentCore.
- `python3 tests/test_agent_answer_source_policy_review.py` passed with seven
  stdlib unit tests.
- Full-file line-length scan still reports existing long lines in
  `backend/routes/chat.py` and `docs/data-storage-architecture.md`; focused
  scans found no issues in the new helper/API/doc/Phase 78 ranges.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Remove `answer_source_policy_review` from `ChatResponse` and `/chat`
  responses.
- Remove SSE `answer_source_policy_review` message emission.
- Remove the API propagation notes from docs.
- Remove this Phase 78 section.

## Phase 79. Reviewed Intake Example Reproducibility

Goal: make the synthetic Shandong intake review artifact reproducible from a
checked-in filled intake example, not only from an empty template.

- [x] Add `sd_official_sample_intake_reviewed_example.json`.
- [x] Keep the original blank intake template unchanged.
- [x] Reuse the synthetic snapshot manifest URL, checksum, and scope.
- [x] Document that the filled example is synthetic and not official data.
- [x] Add the intake review command to the examples README and runbook.
- [x] Keep the change example/docs-only: no remote download, raw snapshot write,
      parser run, DB write, seed edit, loader run, crawler, RAG refresh, or
      Agent visibility change.

Validation:

```bash
python3 -m json.tool \
  examples/real_data/sd_official_sample_intake_reviewed_example.json
python3 -m backend.data_pipeline.intake.cli \
  examples/real_data/sd_official_sample_intake_reviewed_example.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  examples/real_data/sd_official_sample_intake_reviewed_example.json \
  examples/real_data/README.md \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m json.tool
  examples/real_data/sd_official_sample_intake_reviewed_example.json` passed.
- `python3 -m backend.data_pipeline.intake.cli
  examples/real_data/sd_official_sample_intake_reviewed_example.json` passed
  with `passed=true`, `ready_for_snapshot=true`, and zero issues.
- Focused line-length scan found no issues in the reviewed intake example,
  examples README, runbook, or this Phase 79 section.

Rollback:

- Remove `examples/real_data/sd_official_sample_intake_reviewed_example.json`.
- Remove the reviewed-example notes from the examples README and runbook.
- Remove this Phase 79 section.

## Phase 80. Pilot Artifact Manifest Smoke Review

Goal: let static pilot artifact manifests be smoke-reviewed when pydantic
runtime dependencies are unavailable.

- [x] Make `backend.data_pipeline.pilots` exports lazy to avoid eager pydantic
      imports during stdlib-only CLI startup.
- [x] Add `backend.data_pipeline.pilots.artifact_smoke`.
- [x] Add `backend.data_pipeline.pilots.artifact_smoke_cli`.
- [x] Check manifest action, scope, ready flag, issue lists, loader handoff, and
      local artifact paths.
- [x] Add stdlib `unittest` coverage for passing, issue-blocked, missing-path,
      and CLI-output cases.
- [x] Document the smoke command as a dependency-light fallback, not a
      replacement for the formal pydantic artifact builder.
- [x] Keep the change no-write: no parser run, quality gate, DB write, seed
      edit, loader run, crawler, RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/pilots/__init__.py \
  backend/data_pipeline/pilots/artifact_smoke.py \
  backend/data_pipeline/pilots/artifact_smoke_cli.py \
  tests/test_data_pipeline_pilot_artifact_smoke.py
python3 -m backend.data_pipeline.pilots.artifact_smoke_cli \
  examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --expect-source-id sd_exam_authority \
  --expect-snapshot-id sd_pilot_2025_001 \
  --expect-dataset admission_scores
python3 tests/test_data_pipeline_pilot_artifact_smoke.py
python3 -m pytest tests/test_data_pipeline_pilot_artifact_smoke.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/pilots/__init__.py \
  backend/data_pipeline/pilots/artifact_smoke.py \
  backend/data_pipeline/pilots/artifact_smoke_cli.py \
  tests/test_data_pipeline_pilot_artifact_smoke.py \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for pilot lazy
  exports, artifact smoke modules, and smoke tests.
- `python3 -m backend.data_pipeline.pilots.artifact_smoke_cli ...` passed for
  `examples/real_data/artifacts/sd_pilot_artifact_manifest.json` with zero
  issues and all referenced paths present.
- `python3 tests/test_data_pipeline_pilot_artifact_smoke.py` passed with four
  stdlib unit tests.
- Focused line-length scan found no issues in pilot artifact smoke modules,
  tests, runbook, or this Phase 80 section.
- Focused pytest remains pending because the current Python environment has no
  `pytest` module.

Rollback:

- Restore eager imports in `backend/data_pipeline/pilots/__init__.py`.
- Remove artifact smoke modules and tests.
- Remove artifact smoke fallback docs.
- Remove this Phase 80 section.

## Phase 81. Cross-artifact Scope Smoke

Goal: make the stdlib artifact smoke read referenced artifacts and catch obvious
scope drift across the checked-in evidence chain.

- [x] Read referenced source audit, intake review, dry-run audit, and loader
      approval JSON when local paths exist.
- [x] Check source audit passed and data category matches manifest dataset.
- [x] Check intake review passed, snapshot-ready, and source/dataset scope
      matches the manifest.
- [x] Check dry-run audit passed, load-ready, and source/snapshot/dataset/count
      match the manifest.
- [x] Check loader approval allows load and source/snapshot/dataset/count match
      the manifest.
- [x] Add a focused test for dry-run snapshot mismatch.
- [x] Document that smoke includes referenced artifact scope consistency.
- [x] Keep the change no-write and stdlib-only: no parser, quality gate, DB,
      seed, loader, crawler, RAG refresh, or Agent visibility action.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/pilots/artifact_smoke.py \
  tests/test_data_pipeline_pilot_artifact_smoke.py
python3 -m backend.data_pipeline.pilots.artifact_smoke_cli \
  examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --expect-source-id sd_exam_authority \
  --expect-snapshot-id sd_pilot_2025_001 \
  --expect-dataset admission_scores
python3 tests/test_data_pipeline_pilot_artifact_smoke.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/pilots/artifact_smoke.py \
  tests/test_data_pipeline_pilot_artifact_smoke.py \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for artifact
  smoke and tests.
- `python3 -m backend.data_pipeline.pilots.artifact_smoke_cli ...` passed for
  the checked-in Shandong pilot artifact manifest with zero issues and matching
  referenced artifact scope.
- `python3 tests/test_data_pipeline_pilot_artifact_smoke.py` passed with five
  stdlib unit tests.
- Focused line-length scan found no issues in artifact smoke, tests, runbook,
  or this Phase 81 section.

Rollback:

- Remove referenced-artifact reads and scope checks from artifact smoke.
- Remove the dry-run mismatch test.
- Restore runbook wording to path-only artifact smoke.
- Remove this Phase 81 section.

## Phase 82. Answer Policy Tool Response Example

Goal: make the synthetic answer source policy review reproducible from a
checked-in tool response input.

- [x] Add `examples/real_data/sd_tool_response_with_sources.json`.
- [x] Include item-level `sources`, item-level `source_summary`, top-level
      `source_summary`, and top-level `answer_source_policy`.
- [x] Keep the top-level `source_summary` aligned with
      `artifacts/sd_answer_source_policy.json`.
- [x] Document the policy CLI command in the examples README and runbook.
- [x] Keep the example synthetic and no-write: no real tool invocation, DB
      write, seed edit, loader run, crawler, RAG refresh, or Agent visibility.

Validation:

```bash
python3 -m json.tool examples/real_data/sd_tool_response_with_sources.json
python3 -m backend.data_pipeline.lineage.policy_cli \
  examples/real_data/sd_tool_response_with_sources.json \
  --policy-output /private/tmp/sd_answer_source_policy_check.json
cmp -s /private/tmp/sd_answer_source_policy_check.json \
  examples/real_data/artifacts/sd_answer_source_policy.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  examples/real_data/sd_tool_response_with_sources.json \
  examples/real_data/README.md \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m json.tool examples/real_data/sd_tool_response_with_sources.json`
  passed.
- `python3 -m backend.data_pipeline.lineage.policy_cli ...` generated
  `/private/tmp/sd_answer_source_policy_check.json` with `passed=true` and
  `answer_mode=citeable`.
- `cmp -s /private/tmp/sd_answer_source_policy_check.json
  examples/real_data/artifacts/sd_answer_source_policy.json` passed.
- Focused line-length scan found no issues in the tool response example,
  examples README, runbook, or this Phase 82 section.

Rollback:

- Remove `examples/real_data/sd_tool_response_with_sources.json`.
- Remove the answer-policy example notes from README and runbook.
- Remove this Phase 82 section.

## Phase 83. Blocked Activation Review Reproducibility

Goal: document how to reproduce the checked-in blocked Agent visibility review
without providing an activation approval.

- [x] Confirm `sd_agent_visibility_activation_review.json` is reproducible by
      running activation CLI without `--activation-approval`.
- [x] Document the blocked review command in the examples README.
- [x] Document the blocked review command in the runbook before the full
      approval/evidence activation command.
- [x] Keep the change docs-only: no Agent visibility approval, loader run, DB
      write, seed edit, crawler, RAG refresh, or artifact overwrite.

Validation:

```bash
python3 -m backend.data_pipeline.activation.cli \
  --artifact-manifest examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --answer-policy-review examples/real_data/artifacts/sd_answer_source_policy.json \
  --review-output /private/tmp/sd_activation_review_no_approval_check.json
cmp -s /private/tmp/sd_activation_review_no_approval_check.json \
  examples/real_data/artifacts/sd_agent_visibility_activation_review.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  examples/real_data/README.md \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m backend.data_pipeline.activation.cli ...` returned exit code 1
  as expected for the blocked no-approval review, with
  `missing_agent_visibility_approval`.
- `cmp -s /private/tmp/sd_activation_review_no_approval_check.json
  examples/real_data/artifacts/sd_agent_visibility_activation_review.json`
  passed.
- Focused line-length scan found no issues in README, runbook, or this Phase 83
  section.

Rollback:

- Remove the blocked activation review command from README and runbook.
- Remove this Phase 83 section.

## Phase 84. Example Chain Aggregate Smoke

Goal: provide one stdlib-only command that checks the synthetic Shandong
evidence chain is internally consistent when runtime dependencies are missing.

- [x] Add `backend.data_pipeline.pilots.example_chain_smoke`.
- [x] Add `backend.data_pipeline.pilots.example_chain_smoke_cli`.
- [x] Aggregate intake review, artifact manifest smoke, answer policy review,
      and blocked activation review.
- [x] Confirm activation remains blocked without separate approval.
- [x] Optionally compare computed blocked activation review with checked-in
      expected review.
- [x] Add stdlib `unittest` coverage for passing examples, missing
      `source_summary`, and CLI output.
- [x] Document the aggregate smoke in runbook and examples README.
- [x] Keep the smoke no-write: no parser, quality gate, pydantic builder, DB,
      seed, loader, crawler, RAG refresh, or Agent visibility approval.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/pilots/example_chain_smoke.py \
  backend/data_pipeline/pilots/example_chain_smoke_cli.py \
  tests/test_data_pipeline_example_chain_smoke.py
python3 -m backend.data_pipeline.pilots.example_chain_smoke_cli \
  --intake examples/real_data/sd_official_sample_intake_reviewed_example.json \
  --artifact-manifest examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --tool-response examples/real_data/sd_tool_response_with_sources.json \
  --expected-activation-review \
    examples/real_data/artifacts/sd_agent_visibility_activation_review.json \
  --expect-source-id sd_exam_authority \
  --expect-snapshot-id sd_pilot_2025_001 \
  --expect-dataset admission_scores
python3 tests/test_data_pipeline_example_chain_smoke.py
python3 -m pytest tests/test_data_pipeline_example_chain_smoke.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/pilots/example_chain_smoke.py \
  backend/data_pipeline/pilots/example_chain_smoke_cli.py \
  tests/test_data_pipeline_example_chain_smoke.py \
  docs/real-data-mvp-runbook.md \
  examples/real_data/README.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the
  example chain smoke modules and stdlib test.
- `python3 -m backend.data_pipeline.pilots.example_chain_smoke_cli ...`
  passed with `passed=true`, all five aggregate checks true, and zero issues.
- `python3 tests/test_data_pipeline_example_chain_smoke.py` passed with three
  stdlib tests.
- `python3 -m pytest tests/test_data_pipeline_example_chain_smoke.py` remains
  pending because the local interpreter reports `No module named pytest`.
- Phase 84 touched-file line-length scan returned no issues.

Rollback:

- Remove example chain smoke modules and tests.
- Remove aggregate smoke commands from runbook and examples README.
- Remove this Phase 84 section.

## Phase 85. Source Coverage Report

Goal: provide one stdlib-only command that answers current source coverage
status for priority-province expansion without implying real data is loaded.

- [x] Add `backend.data_pipeline.sources.coverage`.
- [x] Add `backend.data_pipeline.sources.coverage_cli`.
- [x] Reuse source registry smoke review for structural validation.
- [x] Summarize review status counts, per-province sources/categories/years,
      per-category provinces/years, and priority gaps.
- [x] Report priority provinces with no registered year and no approved source.
- [x] Add stdlib `unittest` coverage for priority gaps, passing priority
      registration, and CLI output.
- [x] Document the coverage report in the MVP status doc.
- [x] Keep the report no-write: no crawler, download, raw snapshot, parser,
      quality gate, DB, seed, loader, RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/sources/coverage.py \
  backend/data_pipeline/sources/coverage_cli.py \
  tests/test_data_pipeline_source_coverage.py
python3 -m backend.data_pipeline.sources.coverage_cli \
  backend/data_pipeline/sources/sources.json \
  --priority-province 山东 \
  --priority-province 河南 \
  --priority-province 广东 \
  --priority-province 江苏 \
  --priority-province 浙江 \
  --priority-province 河北 \
  --priority-province 四川 \
  --priority-province 湖北 \
  --priority-data-category admission_scores \
  --priority-data-category enrollment_plans
python3 tests/test_data_pipeline_source_coverage.py
python3 -m pytest tests/test_data_pipeline_source_coverage.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/coverage.py \
  backend/data_pipeline/sources/coverage_cli.py \
  tests/test_data_pipeline_source_coverage.py \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for source
  coverage modules and stdlib test.
- `python3 -m backend.data_pipeline.sources.coverage_cli ...` passed with
  `passed=true`, `source_count=9`, zero errors, seven warnings for priority
  provinces without registered years, and eight info items for priority
  provinces without approved sources.
- CLI output confirmed no missing priority provinces; Shandong has registered
  year `2025`, while Henan, Guangdong, Jiangsu, Zhejiang, Hebei, Sichuan, and
  Hubei still have empty `coverage.years`.
- `python3 tests/test_data_pipeline_source_coverage.py` passed with three
  stdlib tests.
- `python3 -m pytest tests/test_data_pipeline_source_coverage.py` remains
  pending because the local interpreter reports `No module named pytest`.
- Phase 85 touched-file line-length scan returned no issues.

Rollback:

- Remove source coverage report modules and tests.
- Remove coverage report command and status notes from the MVP status doc.
- Remove this Phase 85 section.

## Phase 86. Source Coverage Readiness Signal

Goal: make the coverage report explicit that registry smoke success does not
mean data is ready for snapshot, loader, or Agent visibility.

- [x] Add a `readiness` object to the source coverage report.
- [x] Keep `passed` tied to structural errors, while readiness carries
      progression blockers.
- [x] Block snapshot planning when priority provinces are missing, lack
      registered years, or lack approved sources.
- [x] Keep loader and Agent visibility discussion blocked until later evidence
      exists.
- [x] Add stdlib `unittest` coverage for readiness blockers and the approved
      source/year case.
- [x] Document that `passed=true` is not production readiness.
- [x] Keep the change no-write: no crawler, download, raw snapshot, parser,
      quality gate, DB, seed, loader, RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/sources/coverage.py \
  tests/test_data_pipeline_source_coverage.py
python3 -m backend.data_pipeline.sources.coverage_cli \
  backend/data_pipeline/sources/sources.json \
  --priority-province 山东 \
  --priority-province 河南 \
  --priority-province 广东 \
  --priority-province 江苏 \
  --priority-province 浙江 \
  --priority-province 河北 \
  --priority-province 四川 \
  --priority-province 湖北 \
  --priority-data-category admission_scores \
  --priority-data-category enrollment_plans
python3 tests/test_data_pipeline_source_coverage.py
python3 -m pytest tests/test_data_pipeline_source_coverage.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/coverage.py \
  tests/test_data_pipeline_source_coverage.py \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for source
  coverage readiness code and stdlib test.
- `python3 -m backend.data_pipeline.sources.coverage_cli ...` passed with
  `passed=true`, `readiness.ready_for_snapshot_planning=false`,
  `readiness.ready_for_loader_discussion=false`, and
  `readiness.ready_for_agent_visibility_discussion=false`.
- CLI output lists snapshot planning blockers:
  `priority_provinces_without_years` and
  `priority_provinces_without_approved_source`.
- `python3 tests/test_data_pipeline_source_coverage.py` passed with four
  stdlib tests.
- `python3 -m pytest tests/test_data_pipeline_source_coverage.py` remains
  pending because the local interpreter reports `No module named pytest`.
- Phase 86 touched-file line-length scan returned no issues.

Rollback:

- Remove the `readiness` object and related tests from source coverage.
- Remove readiness notes from the MVP status doc.
- Remove this Phase 86 section.

## Phase 87. Source Scope Smoke Audit Fallback

Goal: make source scope audit evidence available in missing-runtime
environments without replacing the formal pydantic audit.

- [x] Add `backend.data_pipeline.sources.scope_smoke`.
- [x] Add `backend.data_pipeline.sources.scope_smoke_cli`.
- [x] Output the source audit core shape: `scope`, `passed`, and `issues`.
- [x] Support data category, repeated province/year arguments,
      `--require-reviewed`, `--fail-on-warning`, and optional audit output.
- [x] Reuse source registry smoke review for structural error detection.
- [x] Add stdlib `unittest` coverage for passing shape, missing province,
      warning exit behavior, and audit output writing.
- [x] Document the fallback in the runbook as a missing-dependency precheck,
      not a replacement for formal source audit.
- [x] Keep the fallback no-write except optional local audit JSON output: no
      crawler, download, raw snapshot, parser, quality gate, DB, seed, loader,
      RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/sources/scope_smoke.py \
  backend/data_pipeline/sources/scope_smoke_cli.py \
  tests/test_data_pipeline_source_scope_smoke.py
python3 -m backend.data_pipeline.sources.scope_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  --data-category admission_scores \
  --province 山东 \
  --year 2025 \
  --require-reviewed
python3 tests/test_data_pipeline_source_scope_smoke.py
python3 -m pytest tests/test_data_pipeline_source_scope_smoke.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/scope_smoke.py \
  backend/data_pipeline/sources/scope_smoke_cli.py \
  tests/test_data_pipeline_source_scope_smoke.py \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for source
  scope smoke modules and stdlib test.
- `python3 -m backend.data_pipeline.sources.scope_smoke_cli ...` exited 0 and
  produced source-audit-shaped output for Shandong 2025 admission scores.
- The current Shandong source output includes warning `source_not_reviewed`,
  because `sd_exam_authority.review_status` is still `candidate`.
- `python3 tests/test_data_pipeline_source_scope_smoke.py` passed with four
  stdlib tests.
- `python3 -m pytest tests/test_data_pipeline_source_scope_smoke.py` remains
  pending because the local interpreter reports `No module named pytest`.
- Phase 87 touched-file line-length scan returned no issues.

Rollback:

- Remove source scope smoke modules and tests.
- Remove the fallback command from the runbook.
- Remove this Phase 87 section.

## Phase 88. Source Review Approval Template

Goal: make `source_not_reviewed` resolvable through an explicit human approval
packet before any registry metadata update is discussed.

- [x] Add `backend.data_pipeline.sources.review_approval`.
- [x] Add `backend.data_pipeline.sources.review_approval_cli`.
- [x] Add `examples/real_data/source_review_approval_template.json` with
      approval disabled by default.
- [x] Require approval action, allow flag, target approved status, source id,
      scope category/province/years, evidence URL, citation notes, confirmation
      booleans, reviewer, and review timestamp.
- [x] Return `ready_for_registry_update` and a registry update hint, but do not
      edit source registry JSON.
- [x] Add stdlib `unittest` coverage for blocked template-style payload,
      passing approval, missing evidence URL, and CLI output.
- [x] Document the approval review in the runbook as the next step after
      `source_not_reviewed`.
- [x] Keep the change no-write except optional local review JSON output: no
      crawler, download, raw snapshot, parser, quality gate, DB, seed, loader,
      RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/sources/review_approval.py \
  backend/data_pipeline/sources/review_approval_cli.py \
  tests/test_data_pipeline_source_review_approval.py
python3 -m json.tool examples/real_data/source_review_approval_template.json
python3 -m backend.data_pipeline.sources.review_approval_cli \
  examples/real_data/source_review_approval_template.json
python3 tests/test_data_pipeline_source_review_approval.py
python3 -m pytest tests/test_data_pipeline_source_review_approval.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/review_approval.py \
  backend/data_pipeline/sources/review_approval_cli.py \
  tests/test_data_pipeline_source_review_approval.py \
  examples/real_data/source_review_approval_template.json \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for source
  review approval modules and stdlib test.
- `python3 -m json.tool examples/real_data/source_review_approval_template.json`
  passed.
- `python3 -m backend.data_pipeline.sources.review_approval_cli ...` returned
  exit code 1 as expected for the disabled blank template, with
  `ready_for_registry_update=false` and eight blocking errors.
- `python3 tests/test_data_pipeline_source_review_approval.py` passed with four
  stdlib tests.
- `python3 -m pytest tests/test_data_pipeline_source_review_approval.py`
  remains pending because the local interpreter reports `No module named
  pytest`.
- Phase 88 touched-file line-length scan returned no issues.

Rollback:

- Remove source review approval modules, tests, and template.
- Remove source review approval command from the runbook.
- Remove this Phase 88 section.

## Phase 89. Source Registry Update Plan

Goal: turn a passed source review approval into a no-write registry patch plan
before any `sources.json` edit is discussed.

- [x] Add `backend.data_pipeline.sources.update_plan`.
- [x] Add `backend.data_pipeline.sources.update_plan_cli`.
- [x] Read registry JSON plus source review approval review JSON.
- [x] Block the plan when approval review is not ready or source id is missing.
- [x] Report planned `review_status`, `data_categories`,
      `coverage.provinces`, and `coverage.years` changes without editing files.
- [x] Add stdlib `unittest` coverage for passing plan, unready approval,
      missing source, and CLI output.
- [x] Document the no-write update plan in the runbook.
- [x] Keep the change no-write except optional local plan JSON output: no
      registry edit, crawler, download, raw snapshot, parser, quality gate, DB,
      seed, loader, RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/sources/update_plan.py \
  backend/data_pipeline/sources/update_plan_cli.py \
  tests/test_data_pipeline_source_update_plan.py
python3 tests/test_data_pipeline_source_update_plan.py
python3 -m pytest tests/test_data_pipeline_source_update_plan.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/update_plan.py \
  backend/data_pipeline/sources/update_plan_cli.py \
  tests/test_data_pipeline_source_update_plan.py \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for source
  registry update plan modules and stdlib test.
- `python3 tests/test_data_pipeline_source_update_plan.py` passed with four
  stdlib tests.
- `python3 -m pytest tests/test_data_pipeline_source_update_plan.py` remains
  pending because the local interpreter reports `No module named pytest`.
- Phase 89 touched-file line-length scan returned no issues.

Rollback:

- Remove source registry update plan modules and tests.
- Remove update plan command from the runbook.
- Remove this Phase 89 section.

## Phase 90. Source Review Chain Smoke

Goal: provide one stdlib-only smoke that checks the no-write path from
`source_not_reviewed` to a registry update plan.

- [x] Add `backend.data_pipeline.sources.review_chain_smoke`.
- [x] Add `backend.data_pipeline.sources.review_chain_smoke_cli`.
- [x] Reuse source scope smoke, source review approval review, and registry
      update plan builders.
- [x] Derive source scope from the approval packet to avoid duplicate CLI args.
- [x] Report checks for source scope audit, approval review, update plan, and
      no registry mutation.
- [x] Add stdlib `unittest` coverage for passing chain, disabled approval, and
      CLI output.
- [x] Document the aggregate smoke in the runbook.
- [x] Keep the change no-write except optional local review JSON output: no
      registry edit, crawler, download, raw snapshot, parser, quality gate, DB,
      seed, loader, RAG refresh, or Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/sources/review_chain_smoke.py \
  backend/data_pipeline/sources/review_chain_smoke_cli.py \
  tests/test_data_pipeline_source_review_chain_smoke.py
python3 tests/test_data_pipeline_source_review_chain_smoke.py
python3 -m pytest tests/test_data_pipeline_source_review_chain_smoke.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/review_chain_smoke.py \
  backend/data_pipeline/sources/review_chain_smoke_cli.py \
  tests/test_data_pipeline_source_review_chain_smoke.py \
  docs/real-data-mvp-runbook.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for source
  review chain smoke modules and stdlib test.
- `python3 tests/test_data_pipeline_source_review_chain_smoke.py` passed with
  three stdlib tests.
- `python3 -m backend.data_pipeline.sources.review_chain_smoke_cli ...` with
  the blank template returned exit code 1 as expected: source scope audit
  passed with `source_not_reviewed`, approval review did not pass, and update
  plan was not ready.
- `python3 -m pytest tests/test_data_pipeline_source_review_chain_smoke.py`
  remains pending because the local interpreter reports `No module named
  pytest`.
- Phase 90 touched-file line-length scan returned no issues.

Rollback:

- Remove source review chain smoke modules and tests.
- Remove aggregate smoke command from the runbook.
- Remove this Phase 90 section.

## Phase 91. Examples Source Review Precheck Docs

Goal: make the example directory document the new source review approval and
registry update planning gates before snapshot or rows preparation.

- [x] Add `source_review_approval_template.json` to the examples file table.
- [x] Add a source review precheck section before no-write dry-run examples.
- [x] Document source approval review, registry update plan, and aggregate
      chain smoke commands.
- [x] Clarify that the checked-in approval template is expected to stay blocked
      until real reviewer and source evidence are filled.
- [x] Keep the update docs-only: no registry edit, crawler, download, raw
      snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or Agent
      visibility change.

Validation:

```bash
python3 -m json.tool examples/real_data/source_review_approval_template.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  examples/real_data/README.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m json.tool examples/real_data/source_review_approval_template.json`
  passed.
- Focused line-length scan found no issues in examples README or this Phase 91
  section.

Rollback:

- Remove the source review precheck section from examples README.
- Remove `source_review_approval_template.json` from the examples file table.
- Remove this Phase 91 section.

## Phase 92. MVP Status Source Review Gates

Goal: keep the MVP status document aligned with the new source review approval
and registry update planning gates.

- [x] Add source review approval and registry update plan to current gates.
- [x] Document the stdlib source review chain smoke and its expected blocked
      result for the blank template.
- [x] Add source approval review and registry update plan to real-sample
      preconditions.
- [x] Update recommended next steps so source evidence and registry patch
      review happen before sample row preparation.
- [x] Keep the update docs-only: no registry edit, crawler, download, raw
      snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or Agent
      visibility change.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Focused line-length scan found no issues in the MVP status doc or this
  Phase 92 section.

Rollback:

- Remove source review approval, registry update plan, and chain smoke notes
  from the MVP status doc.
- Restore the previous recommended next-step ordering.
- Remove this Phase 92 section.

## Phase 93. Source Review Gate Combined Verification

Goal: verify the source review pre-snapshot gate works as a combined stdlib
chain in the current missing-runtime environment.

- [x] Run combined `py_compile` for source coverage, scope smoke, approval
      review, update plan, chain smoke, CLIs, and related stdlib tests.
- [x] Run source coverage, scope smoke, approval review, update plan, and chain
      smoke stdlib tests together.
- [x] Run coverage CLI against current priority province registry state.
- [x] Run source review chain smoke against the checked-in blank approval
      template and confirm it remains blocked.
- [x] Keep this verification no-write: no registry edit, crawler, download,
      raw snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or
      Agent visibility change.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/sources/coverage.py \
  backend/data_pipeline/sources/scope_smoke.py \
  backend/data_pipeline/sources/review_approval.py \
  backend/data_pipeline/sources/update_plan.py \
  backend/data_pipeline/sources/review_chain_smoke.py \
  backend/data_pipeline/sources/coverage_cli.py \
  backend/data_pipeline/sources/scope_smoke_cli.py \
  backend/data_pipeline/sources/review_approval_cli.py \
  backend/data_pipeline/sources/update_plan_cli.py \
  backend/data_pipeline/sources/review_chain_smoke_cli.py \
  tests/test_data_pipeline_source_coverage.py \
  tests/test_data_pipeline_source_scope_smoke.py \
  tests/test_data_pipeline_source_review_approval.py \
  tests/test_data_pipeline_source_update_plan.py \
  tests/test_data_pipeline_source_review_chain_smoke.py
python3 tests/test_data_pipeline_source_coverage.py
python3 tests/test_data_pipeline_source_scope_smoke.py
python3 tests/test_data_pipeline_source_review_approval.py
python3 tests/test_data_pipeline_source_update_plan.py
python3 tests/test_data_pipeline_source_review_chain_smoke.py
python3 -m backend.data_pipeline.sources.coverage_cli \
  backend/data_pipeline/sources/sources.json \
  --priority-province 山东 \
  --priority-province 河南 \
  --priority-province 广东 \
  --priority-province 江苏 \
  --priority-province 浙江 \
  --priority-province 河北 \
  --priority-province 四川 \
  --priority-province 湖北 \
  --priority-data-category admission_scores \
  --priority-data-category enrollment_plans
python3 -m backend.data_pipeline.sources.review_chain_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  examples/real_data/source_review_approval_template.json
```

Current verification status:

- Combined `py_compile` passed.
- Source coverage, scope smoke, approval review, update plan, and chain smoke
  stdlib tests all passed: 4 + 4 + 4 + 4 + 3 tests.
- Coverage CLI returned `passed=true` but
  `readiness.ready_for_snapshot_planning=false`; blockers are
  `priority_provinces_without_years` and
  `priority_provinces_without_approved_source`.
- Chain smoke with the blank approval template returned exit code 1 as
  expected: approval review did not pass and update plan was not ready.

Rollback:

- Remove this Phase 93 section.

## Phase 94. Shandong Official First-choice Candidate URL

Goal: record the official Shandong 2025 first-choice filing table candidate
without downloading or approving the source.

- [x] Verify the Shandong official filing-status list page contains 2025
      ordinary regular batch first, second, and third choice filing tables.
- [x] Add the first-choice official `NewsInfo` URL as the preferred initial
      `admission_scores` candidate.
- [x] Update the webpage verification record date to 2026-06-08.
- [x] Keep the source conservative: candidate only, no source approval, no
      attachment download, no raw snapshot, no row extraction, no registry edit.

Validation:

```bash
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  docs/real-data-first-shandong-pilot.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Focused line-length scan found no issues in the Shandong pilot doc or this
  Phase 94 section.

Rollback:

- Remove the `NewsID=6996` candidate notes from the Shandong pilot doc.
- Restore the previous webpage verification record date and second-choice note.
- Remove this Phase 94 section.

## Phase 95. Shandong Source Review Approval Candidate Draft

Goal: preserve the verified Shandong first-choice source URL in a blocked
source review approval draft without marking it approved.

- [x] Add `examples/real_data/sd_source_review_approval_candidate.json`.
- [x] Pre-fill source id, admission score scope, and official candidate page
      URL for `NewsID=6996`.
- [x] Keep `allow_source_review_approval=false`, confirmation booleans false,
      and reviewer fields empty.
- [x] Document the candidate draft in examples README as blocked until human
      source, attachment, year, and usage/citation review is complete.
- [x] Keep the change no-write: no source approval, registry edit, download,
      raw snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or
      Agent visibility change.

Validation:

```bash
python3 -m json.tool \
  examples/real_data/sd_source_review_approval_candidate.json
python3 -m backend.data_pipeline.sources.review_approval_cli \
  examples/real_data/sd_source_review_approval_candidate.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  examples/real_data/sd_source_review_approval_candidate.json \
  examples/real_data/README.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m json.tool
  examples/real_data/sd_source_review_approval_candidate.json` passed.
- `python3 -m backend.data_pipeline.sources.review_approval_cli ...` returned
  exit code 1 as expected, with `ready_for_registry_update=false` and six
  blocking errors.
- Focused line-length scan found no issues in the candidate draft, examples
  README, or this Phase 95 section.

Rollback:

- Remove `examples/real_data/sd_source_review_approval_candidate.json`.
- Remove the candidate draft note from examples README.
- Remove this Phase 95 section.

## Phase 96. Source Review Evidence Summary

Goal: make blocked source review approval drafts easier to inspect without
changing any approval decision.

- [x] Add additive `evidence_summary` to source review approval output.
- [x] Summarize dataset page URL, attachment URL, citation notes, confirmation
      booleans, reviewer, and review timestamp presence.
- [x] Keep `passed`, `ready_for_registry_update`, issues, registry update hint,
      and CLI exit-code behavior unchanged.
- [x] Add stdlib tests for complete approval and blocked candidate-style
      evidence summaries.
- [x] Document that `evidence_summary` is explanatory only.
- [x] Keep the change no-write: no source approval, registry edit, download,
      raw snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or
      Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/review_approval.py \
  backend/data_pipeline/sources/review_approval_cli.py \
  tests/test_data_pipeline_source_review_approval.py
python3 tests/test_data_pipeline_source_review_approval.py
python3 -m backend.data_pipeline.sources.review_approval_cli \
  examples/real_data/sd_source_review_approval_candidate.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/review_approval.py \
  tests/test_data_pipeline_source_review_approval.py \
  examples/real_data/README.md \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for source review approval code, CLI, and
  stdlib test.
- `python3 tests/test_data_pipeline_source_review_approval.py` passed 5 tests.
- Candidate approval CLI still returns exit code 1 as expected, with
  `ready_for_registry_update=false`, six blocking errors, and an
  `evidence_summary` showing the dataset page URL and citation notes are
  present while reviewer and confirmation fields are missing.
- Source update-plan and review-chain smoke stdlib tests still pass.
- Blank-template review-chain CLI still returns exit code 1 as expected, with
  approval review and update plan blocked.
- Focused line-length scan found no issues in the touched code, tests, docs, or
  this Phase 96 section.

Rollback:

- Remove `evidence_summary` from source review approval output.
- Remove the evidence summary tests and documentation notes.
- Remove this Phase 96 section.

## Phase 97. Source Review Required Actions

Goal: turn source review approval blockers into a reviewer-facing action list
without changing approval behavior.

- [x] Add additive `required_reviews` to source review approval output.
- [x] Derive required review actions from existing issue codes so the pass/fail
      gate remains single-sourced.
- [x] Keep successful approval reviews with an empty `required_reviews` list.
- [x] Add stdlib assertions for complete approval, missing URL, and blocked
      candidate-style review actions.
- [x] Document that `required_reviews` is a human checklist only.
- [x] Keep the change no-write: no source approval, registry edit, download,
      raw snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or
      Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/review_approval.py \
  backend/data_pipeline/sources/review_approval_cli.py \
  backend/data_pipeline/sources/update_plan.py \
  backend/data_pipeline/sources/update_plan_cli.py \
  backend/data_pipeline/sources/review_chain_smoke.py \
  backend/data_pipeline/sources/review_chain_smoke_cli.py \
  tests/test_data_pipeline_source_review_approval.py \
  tests/test_data_pipeline_source_update_plan.py \
  tests/test_data_pipeline_source_review_chain_smoke.py
python3 tests/test_data_pipeline_source_review_approval.py
python3 tests/test_data_pipeline_source_update_plan.py
python3 tests/test_data_pipeline_source_review_chain_smoke.py
python3 -m backend.data_pipeline.sources.review_approval_cli \
  examples/real_data/sd_source_review_approval_candidate.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/review_approval.py \
  tests/test_data_pipeline_source_review_approval.py \
  examples/real_data/README.md \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for source review approval, update plan,
  review-chain modules, CLIs, and stdlib tests.
- `python3 tests/test_data_pipeline_source_review_approval.py` passed 5 tests.
- `python3 tests/test_data_pipeline_source_update_plan.py` passed 4 tests.
- `python3 tests/test_data_pipeline_source_review_chain_smoke.py` passed 3
  tests.
- Candidate approval CLI still returns exit code 1 as expected, with
  `ready_for_registry_update=false` and `required_reviews` listing the
  remaining human-review actions.
- Blank-template review-chain CLI still returns exit code 1 as expected, with
  approval review and update plan blocked.
- Focused line-length scan found no issues in the touched code, tests, docs, or
  this Phase 97 section.

Rollback:

- Remove `required_reviews` from source review approval output.
- Remove the required review helper, tests, documentation notes, and this
  Phase 97 section.

## Phase 98. Source Review Chain Required Actions

Goal: make the aggregate source review chain smoke expose reviewer-facing next
actions at the top level.

- [x] Add additive top-level `required_reviews` to source review chain smoke.
- [x] Reuse `approval_review.required_reviews` instead of duplicating source
      approval gate logic.
- [x] Add update-plan actions for missing registry source and approval-review
      not-ready blockers.
- [x] Keep passing chain smoke reports with an empty `required_reviews` list.
- [x] Add stdlib tests for passing, disabled approval, and missing source
      scenarios.
- [x] Document that chain smoke top-level required actions are reviewer guidance.
- [x] Keep the change no-write: no source approval, registry edit, download,
      raw snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or
      Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/review_approval.py \
  backend/data_pipeline/sources/review_approval_cli.py \
  backend/data_pipeline/sources/update_plan.py \
  backend/data_pipeline/sources/update_plan_cli.py \
  backend/data_pipeline/sources/review_chain_smoke.py \
  backend/data_pipeline/sources/review_chain_smoke_cli.py \
  tests/test_data_pipeline_source_review_approval.py \
  tests/test_data_pipeline_source_update_plan.py \
  tests/test_data_pipeline_source_review_chain_smoke.py
python3 tests/test_data_pipeline_source_review_approval.py
python3 tests/test_data_pipeline_source_update_plan.py
python3 tests/test_data_pipeline_source_review_chain_smoke.py
python3 -m backend.data_pipeline.sources.review_chain_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  examples/real_data/source_review_approval_template.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/review_chain_smoke.py \
  tests/test_data_pipeline_source_review_chain_smoke.py \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for source review approval, update plan,
  review-chain modules, CLIs, and stdlib tests.
- `python3 tests/test_data_pipeline_source_review_approval.py` passed 5 tests.
- `python3 tests/test_data_pipeline_source_update_plan.py` passed 4 tests.
- `python3 tests/test_data_pipeline_source_review_chain_smoke.py` passed 4
  tests.
- Blank-template review-chain CLI still returns exit code 1 as expected, with
  top-level `required_reviews` listing source approval and registry patch
  prerequisites.
- Focused line-length scan found no issues in the touched code, tests, docs, or
  this Phase 98 section.

Rollback:

- Remove top-level `required_reviews` from source review chain smoke.
- Remove chain required-review helpers, tests, documentation notes, and this
  Phase 98 section.

## Phase 99. Source Registry Patch Approval Review

Goal: add a no-write approval gate between a ready registry update plan and any
future `sources.json` edit.

- [x] Add stdlib `review_source_registry_patch_approval(...)`.
- [x] Add `backend.data_pipeline.sources.patch_approval_cli`.
- [x] Require a ready `source_registry_update_plan` artifact.
- [x] Require a separate `source_registry_patch_approval` packet with explicit
      allow flag, matching source id, planned-update confirmation, reviewer,
      and review timestamp.
- [x] Add a disabled registry patch approval template under examples.
- [x] Add stdlib tests for passing approval, disabled template-style approval,
      source-id mismatch, and CLI artifact output.
- [x] Document the new gate in examples README and MVP status docs.
- [x] Keep the change no-write: no registry edit, source approval, download,
      raw snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or
      Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/patch_approval.py \
  backend/data_pipeline/sources/patch_approval_cli.py \
  tests/test_data_pipeline_source_patch_approval.py
python3 tests/test_data_pipeline_source_patch_approval.py
python3 -m json.tool \
  examples/real_data/source_registry_patch_approval_template.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/patch_approval.py \
  backend/data_pipeline/sources/patch_approval_cli.py \
  tests/test_data_pipeline_source_patch_approval.py \
  examples/real_data/source_registry_patch_approval_template.json \
  examples/real_data/README.md \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for registry patch approval code, CLI, and
  stdlib test.
- `python3 tests/test_data_pipeline_source_patch_approval.py` passed 4 tests.
- `python3 -m json.tool
  examples/real_data/source_registry_patch_approval_template.json` passed.
- Focused line-length scan found no issues in the touched code, tests, example
  template, docs, or this Phase 99 section.

Rollback:

- Remove `backend/data_pipeline/sources/patch_approval.py`.
- Remove `backend/data_pipeline/sources/patch_approval_cli.py`.
- Remove `tests/test_data_pipeline_source_patch_approval.py`.
- Remove `examples/real_data/source_registry_patch_approval_template.json`.
- Remove registry patch approval documentation notes and this Phase 99 section.

## Phase 100. Source Registry Patch Preview

Goal: preview the exact source registry entry produced by an approved patch
plan without writing `sources.json`.

- [x] Add stdlib `build_source_registry_patch_preview(...)`.
- [x] Add `backend.data_pipeline.sources.patch_preview_cli`.
- [x] Require a ready update plan and a ready registry patch approval review.
- [x] Apply planned updates in memory to produce `patched_source`.
- [x] Report `changes_applied`, issues, and required reviews.
- [x] Add stdlib tests for passing preview, no mutation, unready approval
      review, missing source, and CLI artifact output.
- [x] Document the preview command in examples README and MVP status docs.
- [x] Keep the change no-write: no registry edit, source approval, download,
      raw snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or
      Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/patch_preview.py \
  backend/data_pipeline/sources/patch_preview_cli.py \
  tests/test_data_pipeline_source_patch_preview.py
python3 tests/test_data_pipeline_source_patch_preview.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/patch_preview.py \
  backend/data_pipeline/sources/patch_preview_cli.py \
  tests/test_data_pipeline_source_patch_preview.py \
  examples/real_data/README.md \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for registry patch preview code, CLI, and
  stdlib test.
- `python3 tests/test_data_pipeline_source_patch_preview.py` passed 4 tests.
- `python3 tests/test_data_pipeline_source_patch_approval.py` still passed 4
  tests after adding the preview gate.
- Focused line-length scan found no issues in the touched code, tests, docs, or
  this Phase 100 section.

Rollback:

- Remove `backend/data_pipeline/sources/patch_preview.py`.
- Remove `backend/data_pipeline/sources/patch_preview_cli.py`.
- Remove `tests/test_data_pipeline_source_patch_preview.py`.
- Remove registry patch preview documentation notes and this Phase 100 section.

## Phase 101. Source Registry Patch Chain Smoke

Goal: provide one no-write smoke check for registry patch approval and preview
before any future `sources.json` edit.

- [x] Add stdlib `build_source_registry_patch_chain_smoke(...)`.
- [x] Add `backend.data_pipeline.sources.patch_chain_smoke_cli`.
- [x] Reuse patch approval review and patch preview instead of duplicating gate
      logic.
- [x] Report checks for patch approval readiness, patch preview readiness, and
      registry-not-modified.
- [x] Aggregate required reviews from patch approval review and patch preview.
- [x] Add stdlib tests for ready artifacts, unready approval review, missing
      source preview, and CLI artifact output.
- [x] Document the chain smoke command in examples README and MVP status docs.
- [x] Keep the change no-write: no registry edit, source approval, download,
      raw snapshot, parser, quality gate, DB, seed, loader, RAG refresh, or
      Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/patch_chain_smoke.py \
  backend/data_pipeline/sources/patch_chain_smoke_cli.py \
  tests/test_data_pipeline_source_patch_chain_smoke.py
python3 tests/test_data_pipeline_source_patch_chain_smoke.py
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/patch_chain_smoke.py \
  backend/data_pipeline/sources/patch_chain_smoke_cli.py \
  tests/test_data_pipeline_source_patch_chain_smoke.py \
  examples/real_data/README.md \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for registry patch chain smoke code, CLI,
  and stdlib test.
- `python3 tests/test_data_pipeline_source_patch_chain_smoke.py` passed 4 tests.
- Registry patch approval, preview, and chain smoke stdlib tests all pass
  together: 4 tests each.
- Focused line-length scan found no issues in the touched code, tests, docs, or
  this Phase 101 section.

Rollback:

- Remove `backend/data_pipeline/sources/patch_chain_smoke.py`.
- Remove `backend/data_pipeline/sources/patch_chain_smoke_cli.py`.
- Remove `tests/test_data_pipeline_source_patch_chain_smoke.py`.
- Remove registry patch chain smoke documentation notes and this Phase 101
  section.

## Phase 102. Source Snapshot Planning Review

Goal: prevent reviewed-source warnings from slipping into raw snapshot
preparation.

- [x] Add stdlib `build_source_snapshot_planning_review(...)`.
- [x] Add `backend.data_pipeline.sources.snapshot_planning_cli`.
- [x] Reuse source scope smoke with `require_reviewed=true`.
- [x] Treat both source scope errors and warnings as snapshot planning blockers.
- [x] Add required review actions for unreviewed sources, missing source
      coverage year, missing province source, and missing category source.
- [x] Add stdlib tests for approved source readiness, candidate source blocking,
      missing year blocking, and CLI artifact output.
- [x] Document the snapshot planning review in examples README and MVP status
      docs.
- [x] Keep the change no-write: no source approval, registry edit, download,
      raw snapshot creation, parser, quality gate, DB, seed, loader, RAG
      refresh, or Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/snapshot_planning.py \
  backend/data_pipeline/sources/snapshot_planning_cli.py \
  tests/test_data_pipeline_source_snapshot_planning.py
python3 tests/test_data_pipeline_source_snapshot_planning.py
python3 -m backend.data_pipeline.sources.snapshot_planning_cli \
  backend/data_pipeline/sources/sources.json \
  --data-category admission_scores \
  --province 山东 \
  --year 2025
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/snapshot_planning.py \
  backend/data_pipeline/sources/snapshot_planning_cli.py \
  tests/test_data_pipeline_source_snapshot_planning.py \
  examples/real_data/README.md \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for source snapshot planning code, CLI,
  and stdlib test.
- `python3 tests/test_data_pipeline_source_snapshot_planning.py` passed 4 tests.
- Snapshot planning CLI against current `sources.json` for Shandong 2025 exits
  1 as expected, with `ready_for_snapshot_planning=false` and blocker
  `source_scope:source_not_reviewed`.
- Focused line-length scan found no issues in the touched code, tests, docs, or
  this Phase 102 section.

Rollback:

- Remove `backend/data_pipeline/sources/snapshot_planning.py`.
- Remove `backend/data_pipeline/sources/snapshot_planning_cli.py`.
- Remove `tests/test_data_pipeline_source_snapshot_planning.py`.
- Remove snapshot planning review documentation notes and this Phase 102
  section.

## Phase 103. Snapshot Planning Source Summary

Goal: make snapshot planning reviews directly show which registered source
matches the requested scope.

- [x] Add additive `source_summary` to source snapshot planning review output.
- [x] Summarize matching source ids, review statuses, coverage years, approved
      source presence, and requested-year presence.
- [x] Keep pass/fail, blockers, required reviews, and CLI exit-code behavior
      unchanged.
- [x] Add stdlib assertions for ready source summary, candidate source status,
      and missing requested year.
- [x] Document `source_summary` in the MVP status page.
- [x] Keep the change no-write: no source approval, registry edit, download,
      raw snapshot creation, parser, quality gate, DB, seed, loader, RAG
      refresh, or Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/sources/snapshot_planning.py \
  backend/data_pipeline/sources/snapshot_planning_cli.py \
  tests/test_data_pipeline_source_snapshot_planning.py
python3 tests/test_data_pipeline_source_snapshot_planning.py
python3 -m backend.data_pipeline.sources.snapshot_planning_cli \
  backend/data_pipeline/sources/sources.json \
  --data-category admission_scores \
  --province 山东 \
  --year 2025
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/sources/snapshot_planning.py \
  tests/test_data_pipeline_source_snapshot_planning.py \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for source snapshot planning code, CLI,
  and stdlib test.
- `python3 tests/test_data_pipeline_source_snapshot_planning.py` passed 4 tests.
- Snapshot planning CLI against current `sources.json` for Shandong 2025 exits
  1 as expected, with `ready_for_snapshot_planning=false`, blocker
  `source_scope:source_not_reviewed`, and `source_summary` showing
  `sd_exam_authority` is still `candidate` while year 2025 is registered.
- Focused line-length scan found no issues in the touched code, test, docs, or
  this Phase 103 section.

Rollback:

- Remove `source_summary` from source snapshot planning review output.
- Remove related helper functions, test assertions, documentation notes, and
  this Phase 103 section.

## Phase 104. Intake Requires Snapshot Planning Review

Goal: prevent official sample intake packets from bypassing the source snapshot
planning gate.

- [x] Require `snapshot_planning_review.action=source_snapshot_planning_review`.
- [x] Require `snapshot_planning_review.ready_for_snapshot_planning=true`.
- [x] Verify snapshot planning scope data category, province, and year match
      the intake pilot scope.
- [x] Include snapshot planning readiness and source summary in intake review
      output.
- [x] Update intake tests for passing and not-ready snapshot planning review.
- [x] Update intake template, reviewed example, and static intake review
      artifact.
- [x] Document that official intake packets must include snapshot planning
      review evidence.
- [x] Keep the change no-write: no source approval, registry edit, download,
      raw snapshot creation, parser, quality gate, DB, seed, loader, RAG
      refresh, or Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/intake/review.py \
  backend/data_pipeline/intake/cli.py \
  tests/test_data_pipeline_intake.py
python3 -m json.tool examples/real_data/sd_official_sample_intake_template.json
python3 -m json.tool \
  examples/real_data/sd_official_sample_intake_reviewed_example.json
python3 -m json.tool examples/real_data/artifacts/sd_intake_review.json
python3 -m backend.data_pipeline.intake.cli \
  examples/real_data/sd_official_sample_intake_reviewed_example.json
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/intake/review.py \
  tests/test_data_pipeline_intake.py \
  examples/real_data/README.md \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for intake review, intake CLI, and intake
  test module.
- JSON validation passed for intake template, reviewed intake example, and
  static intake review artifact.
- Intake CLI against `sd_official_sample_intake_reviewed_example.json` exits 0
  and includes snapshot planning review readiness/source summary.
- Static `sd_intake_review.json` matches the current intake CLI output for the
  reviewed example.
- Function-level smoke confirms an intake packet is blocked when
  `snapshot_planning_review.ready_for_snapshot_planning=false`.
- Focused line-length scan found no issues in the touched code, test, examples,
  docs, or this Phase 104 section.

Rollback:

- Remove snapshot planning review validation from intake review.
- Restore intake examples, static intake review artifact, tests, documentation,
  and this Phase 104 section.

## Phase 105. Intake Snapshot Planning Source Binding

Goal: ensure intake review cannot pair a pilot source id with a snapshot
planning review for a different source.

- [x] Check `snapshot_planning_review.source_summary.matching_source_ids`.
- [x] Require the list to include `pilot_scope.source_id`.
- [x] Add a focused intake test for source-id mismatch.
- [x] Keep existing reviewed intake example passing.
- [x] Document that intake snapshot planning evidence must match scope and
      source id.
- [x] Keep the change no-write: no source approval, registry edit, download,
      raw snapshot creation, parser, quality gate, DB, seed, loader, RAG
      refresh, or Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/intake/review.py \
  tests/test_data_pipeline_intake.py
python3 -m backend.data_pipeline.intake.cli \
  examples/real_data/sd_official_sample_intake_reviewed_example.json
python3 -c "<function smoke for source-id mismatch>"
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/intake/review.py \
  tests/test_data_pipeline_intake.py \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for intake review and intake test module.
- Intake CLI against `sd_official_sample_intake_reviewed_example.json` still
  exits 0.
- Function-level smoke confirms intake is blocked when
  `snapshot_planning_review.source_summary.matching_source_ids` does not include
  `pilot_scope.source_id`.
- Focused line-length scan found no issues in the touched code, test, docs, or
  this Phase 105 section.

Rollback:

- Remove snapshot planning source-id binding from intake review.
- Remove the focused mismatch test, documentation note, and this Phase 105
  section.

## Phase 106. Intake Required Reviews

Goal: make official sample intake blockers easier for reviewers to act on.

- [x] Add additive `required_reviews` to intake review output.
- [x] Derive required review actions from existing issue codes.
- [x] Keep passing intake reviews with an empty required review list.
- [x] Add assertions for ready intake and not-ready snapshot planning blockers.
- [x] Update the static intake review artifact.
- [x] Document intake required reviews in the MVP status page.
- [x] Keep the change no-write: no source approval, registry edit, download,
      raw snapshot creation, parser, quality gate, DB, seed, loader, RAG
      refresh, or Agent visibility change.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/intake/review.py \
  tests/test_data_pipeline_intake.py
python3 -m json.tool examples/real_data/artifacts/sd_intake_review.json
python3 -m backend.data_pipeline.intake.cli \
  examples/real_data/sd_official_sample_intake_reviewed_example.json
python3 -c "<static artifact equals CLI output>"
python3 -c "<function smoke for not-ready snapshot planning required review>"
awk 'length($0)>100 {print FILENAME ":" FNR ":" length($0) ":" $0}' \
  backend/data_pipeline/intake/review.py \
  tests/test_data_pipeline_intake.py \
  examples/real_data/artifacts/sd_intake_review.json \
  docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- `python3 -m py_compile ...` passed for intake review and intake test module.
- JSON validation passed for the static intake review artifact.
- Intake CLI against `sd_official_sample_intake_reviewed_example.json` exits 0
  and includes `required_reviews=[]`.
- Static `sd_intake_review.json` matches the current intake CLI output for the
  reviewed example.
- Function-level smoke confirms not-ready snapshot planning adds
  `Resolve source snapshot planning blockers.` to intake `required_reviews`.
- Focused line-length scan found no issues in the touched code, test, artifact,
  docs, or this Phase 106 section.

Rollback:

- Remove `required_reviews` from intake review output.
- Remove helper functions, test assertions, static artifact update,
  documentation note, and this Phase 106 section.

## Phase 107. Evidence Chain Static Artifacts

Goal: make the no-write real-data evidence chain easier to audit and safer to
resume by checking in reproducible blocked/aggregate review artifacts and
surfacing the remaining human-review actions.

- [x] Add optional Agent visibility approval and loader-run record inputs to the
      aggregate example chain smoke CLI.
- [x] Add aggregate example chain checks for intake snapshot planning readiness,
      source binding, answer-policy citeability, and optional activation
      evidence readiness.
- [x] Expose nested `reviews.loader_run_evidence` in aggregate smoke whenever a
      loader-run record is provided.
- [x] Add independent aggregate `loader_run_evidence_ready_when_provided` check.
- [x] Add top-level aggregate `required_reviews` so reviewers can see remaining
      loader and Agent visibility actions without drilling into nested reviews.
- [x] Add static aggregate smoke artifacts:
      `sd_example_chain_smoke.json` and
      `sd_example_chain_smoke_templates_blocked.json`.
- [x] Add static template-blocked loader evidence artifact:
      `sd_loader_run_evidence_templates_blocked.json`.
- [x] Add current-registry snapshot planning blocked artifact:
      `sd_source_snapshot_planning_blocked.json`.
- [x] Improve activation and loader evidence required-review messages for
      incomplete approval/template inputs.
- [x] Bind static artifacts to focused tests so output drift is visible.
- [x] Add a static evidence artifact smoke test for pass/blocked readiness and
      no-write non-goals.
- [x] Add static artifact smoke coverage for aggregate
      `reviews.loader_run_evidence`.
- [x] Update `examples/real_data/README.md` artifact index and usage notes.
- [x] Update `docs/real-data-mvp-status.md` with the extended answer-policy and
      activation review chain plus static evidence artifact status.
- [x] Update `docs/real-data-mvp-runbook.md` with snapshot planning, loader
      evidence, and aggregate smoke commands.
- [x] Keep all changes no-write: no crawler, no official file download, no raw
      snapshot creation, no parser, no quality gate execution on real rows, no
      DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/pilots/example_chain_smoke.py \
  backend/data_pipeline/pilots/example_chain_smoke_cli.py \
  backend/data_pipeline/activation/review.py \
  backend/data_pipeline/activation/loader_evidence.py \
  tests/test_data_pipeline_example_chain_smoke.py \
  tests/test_data_pipeline_activation.py \
  tests/test_data_pipeline_loader_evidence.py \
  tests/test_data_pipeline_source_snapshot_planning.py \
  tests/test_data_pipeline_evidence_artifacts.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_data_pipeline_example_chain_smoke.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_data_pipeline_source_snapshot_planning.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_data_pipeline_evidence_artifacts.py
python3 -m json.tool examples/real_data/artifacts/sd_example_chain_smoke.json
python3 -m json.tool \
  examples/real_data/artifacts/sd_example_chain_smoke_templates_blocked.json
python3 -m json.tool \
  examples/real_data/artifacts/sd_loader_run_evidence_templates_blocked.json
python3 -m json.tool \
  examples/real_data/artifacts/sd_source_snapshot_planning_blocked.json
python3 -c "<loader evidence template artifact equals builder output>"
python3 -c "<targeted activation/loader evidence smoke checks>"
python3 -c "<focused line-length scan>"
```

Current verification status:

- `py_compile` passed for the changed smoke, activation, loader-evidence, and
  snapshot-planning test modules.
- `tests/test_data_pipeline_example_chain_smoke.py` passed 7 unittest tests.
- `tests/test_data_pipeline_source_snapshot_planning.py` passed 5 unittest tests.
- `tests/test_data_pipeline_evidence_artifacts.py` passed 4 unittest tests.
- JSON validation passed for all four new or refreshed static artifacts.
- Loader evidence template artifact matches current builder output.
- Targeted activation required-review and loader evidence smoke checks passed.
- Focused line-length scans passed for touched code, tests, README, and this
  Phase 107 section.
- Focused line-length scans passed for the MVP status page and runbook after
  documentation sync.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove top-level aggregate `required_reviews` and optional activation evidence
  inputs from example chain smoke/CLI.
- Remove the new static artifacts and related consistency tests.
- Restore activation and loader-evidence required-review wording.
- Revert the README, MVP status, and runbook documentation sync.
- Remove this Phase 107 section.

## Phase 108. Evidence Artifact Inventory

Goal: make the growing static evidence artifact set easier to review without
running real-data collection or loader steps.

- [x] Add a stdlib-only evidence artifact inventory builder.
- [x] Add a CLI that scans `examples/real_data/artifacts` by default.
- [x] Require the current MVP evidence artifacts by default.
- [x] Summarize each artifact's action, passed value, ready fields,
      required-review count, and no-write evidence.
- [x] Aggregate unique `required_reviews` so the remaining human actions are
      visible in one report.
- [x] Keep older artifacts without `action` as warnings, not blockers.
- [x] Add focused tests for the checked-in artifact directory and missing
      required artifacts.
- [x] Document the inventory command in the examples README and runbook.
- [x] Keep all changes no-write: no crawler, no official file download, no raw
      snapshot creation, no parser, no quality gate execution on real rows, no
      DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/pilots/evidence_inventory.py \
  backend/data_pipeline/pilots/evidence_inventory_cli.py \
  tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
```

Current verification status:

- `py_compile` passed for the new inventory modules and test.
- `tests/test_data_pipeline_evidence_inventory.py` passed 4 unittest tests.
- Inventory CLI against `examples/real_data/artifacts` exits 0, reports 11
  artifacts, and preserves the default required artifact list.
- Inventory initially reported two warnings for existing early artifacts without
  `action`; these were treated as review prompts, not blockers.

Rollback:

- Remove `evidence_inventory.py`, `evidence_inventory_cli.py`, and the focused
  inventory test.
- Remove the README/runbook command notes and this Phase 108 section.

## Phase 109. Static Artifact Self-description

Goal: resolve the inventory warnings by making early static evidence artifacts
self-describing.

- [x] Add `action` and no-write `non_goals` to `sd_source_audit.json`.
- [x] Add `action` and no-write `non_goals` to `sd_snapshot_pilot_audit.json`.
- [x] Update inventory tests to expect zero inventory warnings for checked-in
      evidence artifacts.
- [x] Document that checked-in evidence artifacts should include `action` and
      `non_goals`.
- [x] Keep all changes no-write: no crawler, no official file download, no raw
      snapshot creation, no parser, no quality gate execution on real rows, no
      DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
python3 -m json.tool examples/real_data/artifacts/sd_source_audit.json
python3 -m json.tool examples/real_data/artifacts/sd_snapshot_pilot_audit.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
```

Current verification status:

- JSON validation passed for `sd_source_audit.json` and
  `sd_snapshot_pilot_audit.json`.
- Inventory CLI against `examples/real_data/artifacts` exits 0 with
  `issue_counts.error=0` and `issue_counts.warning=0`.
- `tests/test_data_pipeline_evidence_inventory.py` passed 4 unittest tests.
- Artifact manifest smoke still passes against the checked-in manifest and
  referenced artifacts.

Rollback:

- Remove the added `action` and `non_goals` fields from the two static
  artifacts.
- Restore the inventory test expectation and remove this Phase 109 section.

## Phase 110. Parser Rows Bundle Smoke

Goal: add a stdlib-only evidence point between reviewed normalized rows and the
formal parser/quality dry-run.

- [x] Add parser rows bundle smoke builder.
- [x] Add parser rows bundle smoke CLI.
- [x] Check rows bundle shape, source/snapshot/dataset scope, natural-key
      fields, and required review metadata.
- [x] Output candidate previews with entity type, natural key, values,
      snapshot id, source record ref, confidence, and review metadata presence.
- [x] Add a checked-in Shandong parser rows bundle smoke artifact.
- [x] Add the parser smoke artifact to the evidence inventory required list.
- [x] Add static evidence artifact coverage for parser smoke readiness.
- [x] Document the command in the MVP runbook and example artifact index.
- [x] Keep all changes no-write: no crawler, no official file download, no raw
      snapshot creation, no formal parser/quality execution on real rows, no
      DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  backend/data_pipeline/parsers/rows_bundle_smoke.py \
  backend/data_pipeline/parsers/rows_bundle_smoke_cli.py \
  tests/test_data_pipeline_parser_rows_bundle_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_parser_rows_bundle_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.parsers.rows_bundle_smoke_cli \
    examples/real_data/sd_snapshot_pilot_rows.json \
    --snapshot-manifest examples/real_data/snapshots/sd_pilot_2025_001/manifest.json \
    --expect-source-id sd_exam_authority \
    --expect-snapshot-id sd_pilot_2025_001 \
    --expect-dataset admission_scores \
    --review-output examples/real_data/artifacts/sd_parser_rows_bundle_smoke.json
```

Current verification status:

- `py_compile` passed for parser rows bundle smoke modules, inventory module,
  and focused tests.
- `tests/test_data_pipeline_parser_rows_bundle_smoke.py` passed 3 unittest
  tests.
- `tests/test_data_pipeline_evidence_inventory.py` passed 4 unittest tests.
- Parser rows bundle smoke CLI exits 0 against the checked-in Shandong rows and
  snapshot manifest, and writes `sd_parser_rows_bundle_smoke.json`.
- `sd_parser_rows_bundle_smoke.json` passes JSON validation.
- Evidence inventory CLI exits 0 with 12 artifacts and zero issues.
- Static evidence artifact tests still pass after adding parser smoke coverage.
- Aggregate example chain smoke tests still pass.
- Focused line-length scan passed for touched code, tests, docs, and artifact.

Rollback:

- Remove parser rows bundle smoke modules, test, and static artifact.
- Remove the artifact from evidence inventory defaults.
- Remove README/runbook notes and this Phase 110 section.

## Phase 111. Aggregate Chain Parser Smoke Binding

Goal: make the aggregate no-write evidence chain verify parser rows bundle smoke
readiness before loader or Agent visibility discussion.

- [x] Add optional `parser_smoke_review` input to aggregate example chain smoke.
- [x] Add aggregate checks for parser smoke readiness and scope matching.
- [x] Compare parser smoke source id, snapshot id, dataset, and row count with
      the pilot artifact manifest.
- [x] Expose `reviews.parser_rows_bundle_smoke` in aggregate smoke output.
- [x] Add CLI `--parser-smoke-review`.
- [x] Regenerate checked-in aggregate smoke artifacts with parser smoke review.
- [x] Add focused test coverage for parser smoke scope mismatch.
- [x] Add static artifact test coverage for aggregate parser smoke review.
- [x] Document the parser smoke input in aggregate smoke README/runbook commands.
- [x] Keep all changes no-write: no crawler, no official file download, no raw
      snapshot creation, no formal parser/quality execution on real rows, no
      DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_data_pipeline_example_chain_smoke.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_data_pipeline_evidence_artifacts.py
python3 -m json.tool examples/real_data/artifacts/sd_example_chain_smoke.json
python3 -m json.tool \
  examples/real_data/artifacts/sd_example_chain_smoke_templates_blocked.json
```

Current verification status:

- `tests/test_data_pipeline_example_chain_smoke.py` passed 8 unittest tests.
- `tests/test_data_pipeline_evidence_artifacts.py` passed 5 unittest tests.
- `py_compile` passed for aggregate smoke modules and focused tests.
- Evidence inventory CLI exits 0 with 12 artifacts and zero issues.
- JSON validation passed for both aggregate smoke artifacts.
- Focused line-length scan passed for touched code, tests, docs, and artifacts.

Rollback:

- Remove parser smoke inputs/checks/review output from aggregate smoke and CLI.
- Restore the two aggregate smoke static artifacts.
- Remove parser aggregate assertions from focused tests.
- Remove README/runbook command notes and this Phase 111 section.

## Phase 112. Quality Smoke Evidence

Goal: add a stdlib-only quality evidence point between parser candidate previews
and the formal pydantic quality gate.

- [x] Add quality smoke builder and CLI.
- [x] Make `backend.data_pipeline.quality` exports lazy so stdlib smoke can run
      when pydantic is unavailable.
- [x] Check parser smoke readiness, required natural keys, value ranges,
      freshness, confidence, duplicate conflicts, coverage, and review metadata.
- [x] Generate checked-in `sd_quality_smoke.json`.
- [x] Add quality smoke to evidence inventory required artifacts.
- [x] Add quality smoke to static artifact readiness tests.
- [x] Add optional aggregate chain `quality_smoke_review` input and CLI flag.
- [x] Add aggregate checks for quality smoke readiness and scope matching.
- [x] Regenerate aggregate smoke artifacts with quality smoke review.
- [x] Document quality smoke and aggregate quality smoke inputs in README and
      runbook.
- [x] Keep all changes no-write: no crawler, no official file download, no raw
      snapshot creation, no formal parser/quality execution on real rows, no
      DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python3 tests/test_data_pipeline_quality_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.quality.smoke_cli \
    examples/real_data/artifacts/sd_parser_rows_bundle_smoke.json \
    --rows-bundle examples/real_data/sd_snapshot_pilot_rows.json \
    --review-output examples/real_data/artifacts/sd_quality_smoke.json
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_data_pipeline_example_chain_smoke.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
```

Current verification status:

- `py_compile` passed for quality smoke, aggregate smoke, inventory, and
  focused tests.
- `tests/test_data_pipeline_quality_smoke.py` passed 3 unittest tests.
- `tests/test_data_pipeline_example_chain_smoke.py` passed 9 unittest tests.
- `tests/test_data_pipeline_evidence_artifacts.py` passed 6 unittest tests.
- `tests/test_data_pipeline_evidence_inventory.py` passed 4 unittest tests.
- Quality smoke CLI exits 0 and writes `sd_quality_smoke.json`.
- Evidence inventory CLI exits 0 with 13 artifacts and zero issues.
- JSON validation passed for `sd_quality_smoke.json` and aggregate smoke
  artifacts.
- Focused line-length scan passed for touched code, tests, docs, and artifacts.

Rollback:

- Remove quality smoke modules, test, static artifact, and inventory entry.
- Restore eager quality package exports if desired.
- Remove quality smoke input/checks from aggregate smoke and CLI.
- Restore aggregate smoke static artifacts and focused tests.
- Remove README/runbook notes and this Phase 112 section.

## Phase 113. MVP Status Sync for Parser and Quality Smoke

Goal: keep the status document aligned with the current no-write evidence chain.

- [x] Update `docs/real-data-mvp-status.md` flow to include parser rows bundle
      smoke and quality smoke review.
- [x] Document parser smoke and quality smoke as stdlib-only evidence, not
      replacements for formal parser or pydantic quality gate.
- [x] Update static evidence artifact status to include parser/quality smoke.
- [x] Update aggregate chain description to include parser and quality smoke.
- [x] Document current stdlib-only commands and inventory expectation.
- [x] Add parser and quality smoke readiness to real pilot preconditions.

Validation:

```bash
rg -n ".{101}" docs/real-data-mvp-status.md \
  .trellis/tasks/05-31-real-data-todo/implement.md
```

Current verification status:

- Focused line-length scan passed for `docs/real-data-mvp-status.md` and this
  Phase 113 section.
- `tests/test_data_pipeline_example_chain_smoke.py` still passed 9 unittest
  tests.
- Evidence inventory CLI still exits 0 with 13 artifacts and zero issues.

Rollback:

- Restore the previous MVP status wording and remove this Phase 113 section.

## Phase 114. MVP Readiness Summary

Goal: make the current no-write evidence package hard to misread as real-data
readiness.

- [x] Add a stdlib-only MVP readiness summary builder.
- [x] Add a CLI that summarizes source snapshot planning, aggregate chain smoke,
      and evidence inventory.
- [x] Generate checked-in `sd_mvp_readiness_summary.json`.
- [x] Add the summary artifact to the evidence inventory required list.
- [x] Add focused tests for current blocked real snapshot readiness.
- [x] Add static evidence artifact coverage for the summary.
- [x] Document the readiness summary in the example README, runbook, and status.
- [x] Keep all changes no-write: no crawler, no official file download, no raw
      snapshot creation, no formal parser/quality execution on real rows, no
      DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.readiness_summary_cli
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
```

Current verification status:

- `sd_mvp_readiness_summary.json` reports `passed=false`,
  `synthetic_chain_ready=true`, `evidence_inventory_ready=true`, and
  `ready_for_real_snapshot=false`.
- Evidence inventory now expects 14 checked-in artifacts.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove readiness summary modules, tests, and static artifact.
- Remove the artifact from evidence inventory defaults.
- Remove README/runbook/status notes and this Phase 114 section.

## Phase 115. Source Review Candidate Evidence Artifact

Goal: make the first real-source blocker concrete before registry updates or
snapshot planning.

- [x] Generate checked-in
      `sd_source_review_approval_candidate_review.json` from the Shandong 2025
      candidate approval draft.
- [x] Keep the review blocked until category, published year, license review,
      reviewer, review time, and allow flag are confirmed.
- [x] Add the source review candidate artifact to evidence inventory defaults.
- [x] Refresh `sd_mvp_readiness_summary.json` so inventory reports 15 artifacts
      and aggregates source review candidate required reviews.
- [x] Add static evidence tests for the blocked source review candidate.
- [x] Document the candidate artifact in README, runbook, and MVP status.
- [x] Keep all changes no-write: no registry patch, no crawler, no official file
      download, no raw snapshot creation, no parser/quality execution on real
      rows, no DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.review_approval_cli \
    examples/real_data/sd_source_review_approval_candidate.json \
    --review-output \
      examples/real_data/artifacts/sd_source_review_approval_candidate_review.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.readiness_summary_cli
```

Current verification status:

- Candidate source review CLI exits 1 by design and reports
  `ready_for_registry_update=false`.
- It preserves a dataset page URL, but still requires human confirmation for
  dataset category, published year, license review, reviewer, and review time.
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false`.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `sd_source_review_approval_candidate_review.json`.
- Remove the artifact from evidence inventory defaults.
- Remove static artifact test assertions and README/runbook/status notes.
- Restore `sd_mvp_readiness_summary.json` to the previous inventory count.
- Remove this Phase 115 section.

## Phase 116. Blocked Registry Update Plan Artifact

Goal: prove the source registry still cannot be patched while the source review
candidate remains blocked.

- [x] Generate checked-in `sd_source_registry_update_plan_blocked.json` from the
      current registry and the blocked source review candidate artifact.
- [x] Keep `ready_for_registry_patch=false` while the approval review is not
      ready.
- [x] Preserve planned update visibility without modifying `sources.json`.
- [x] Add the blocked update plan artifact to evidence inventory defaults.
- [x] Refresh `sd_mvp_readiness_summary.json` so inventory reports 16 artifacts.
- [x] Add static evidence tests for the blocked update plan.
- [x] Document the blocked update plan in README, runbook, and MVP status.
- [x] Keep all changes no-write: no registry patch, no crawler, no official file
      download, no raw snapshot creation, no parser/quality execution on real
      rows, no DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.update_plan_cli \
    backend/data_pipeline/sources/sources.json \
    examples/real_data/artifacts/sd_source_review_approval_candidate_review.json \
    --plan-output \
      examples/real_data/artifacts/sd_source_registry_update_plan_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
```

Current verification status:

- Update plan CLI exits 1 by design and reports
  `ready_for_registry_patch=false`.
- The artifact exposes the potential review-status patch direction while
  preserving `Does not modify sources.json.`
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false`.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `sd_source_registry_update_plan_blocked.json`.
- Remove the artifact from evidence inventory defaults.
- Remove static artifact test assertions and README/runbook/status notes.
- Restore `sd_mvp_readiness_summary.json` to the previous inventory count.
- Remove this Phase 116 section.

## Phase 117. Blocked Registry Patch Approval Artifact

Goal: prove a registry update plan still cannot modify `sources.json` without a
separate patch approval.

- [x] Generate checked-in `sd_source_registry_patch_approval_blocked.json` from
      the blocked update plan and the default patch approval template.
- [x] Keep `ready_for_registry_patch_execution=false` while update plan,
      allow flag, planned update confirmation, reviewer, and review time are not
      ready.
- [x] Add the blocked patch approval artifact to evidence inventory defaults.
- [x] Refresh `sd_mvp_readiness_summary.json` so inventory reports 17 artifacts.
- [x] Add static evidence tests for the blocked patch approval review.
- [x] Document the blocked patch approval in README, runbook, and MVP status.
- [x] Keep all changes no-write: no registry patch, no crawler, no official file
      download, no raw snapshot creation, no parser/quality execution on real
      rows, no DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.patch_approval_cli \
    examples/real_data/artifacts/sd_source_registry_update_plan_blocked.json \
    examples/real_data/source_registry_patch_approval_template.json \
    --review-output \
      examples/real_data/artifacts/sd_source_registry_patch_approval_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
```

Current verification status:

- Patch approval CLI exits 1 by design and reports
  `ready_for_registry_patch_execution=false`.
- The artifact preserves required reviews for update plan blockers, allow flag,
  planned updates confirmation, reviewer, and review time.
- It preserves `Does not modify sources.json.`
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false`.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `sd_source_registry_patch_approval_blocked.json`.
- Remove the artifact from evidence inventory defaults.
- Remove static artifact test assertions and README/runbook/status notes.
- Restore `sd_mvp_readiness_summary.json` to the previous inventory count.
- Remove this Phase 117 section.

## Phase 118. Blocked Registry Patch Preview Artifact

Goal: prove no executable registry patch preview is produced while registry
patch gates remain blocked.

- [x] Generate checked-in `sd_source_registry_patch_preview_blocked.json` from
      the current registry, blocked update plan, and blocked patch approval
      review.
- [x] Keep `ready_for_registry_patch_preview=false`.
- [x] Verify the blocked preview has `changes_applied=[]` and
      `patched_source={}`.
- [x] Add the blocked patch preview artifact to evidence inventory defaults.
- [x] Refresh `sd_mvp_readiness_summary.json` so inventory reports 18 artifacts.
- [x] Add static evidence tests for the blocked patch preview.
- [x] Document the blocked patch preview in README, runbook, and MVP status.
- [x] Keep all changes no-write: no registry patch, no crawler, no official file
      download, no raw snapshot creation, no parser/quality execution on real
      rows, no DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.patch_preview_cli \
    backend/data_pipeline/sources/sources.json \
    examples/real_data/artifacts/sd_source_registry_update_plan_blocked.json \
    examples/real_data/artifacts/sd_source_registry_patch_approval_blocked.json \
    --preview-output \
      examples/real_data/artifacts/sd_source_registry_patch_preview_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
```

Current verification status:

- Patch preview CLI exits 1 by design and reports
  `ready_for_registry_patch_preview=false`.
- The artifact has no applied changes and no patched source while upstream gates
  remain blocked.
- It preserves `Does not modify sources.json.`
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false`.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `sd_source_registry_patch_preview_blocked.json`.
- Remove the artifact from evidence inventory defaults.
- Remove static artifact test assertions and README/runbook/status notes.
- Restore `sd_mvp_readiness_summary.json` to the previous inventory count.
- Remove this Phase 118 section.

## Phase 119. Blocked Registry Patch Chain Smoke Artifact

Goal: provide one aggregate no-write artifact for the blocked registry patch
approval and preview chain.

- [x] Generate checked-in `sd_source_registry_patch_chain_smoke_blocked.json`
      from the current registry, blocked update plan, and blocked patch approval
      review.
- [x] Keep `patch_approval_ready=false` and `patch_preview_ready=false`.
- [x] Preserve `registry_not_modified=true`.
- [x] Add the blocked patch chain smoke artifact to evidence inventory defaults.
- [x] Refresh `sd_mvp_readiness_summary.json` so inventory reports 19 artifacts.
- [x] Add static evidence tests for the blocked patch chain smoke.
- [x] Document the blocked patch chain smoke in README, runbook, and MVP status.
- [x] Keep all changes no-write: no registry patch, no crawler, no official file
      download, no raw snapshot creation, no parser/quality execution on real
      rows, no DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.patch_chain_smoke_cli \
    backend/data_pipeline/sources/sources.json \
    examples/real_data/artifacts/sd_source_registry_update_plan_blocked.json \
    examples/real_data/artifacts/sd_source_registry_patch_approval_blocked.json \
    --review-output \
      examples/real_data/artifacts/sd_source_registry_patch_chain_smoke_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
```

Current verification status:

- Patch chain smoke CLI exits 1 by design and reports `passed=false`.
- The artifact keeps approval and preview readiness false while confirming
  `registry_not_modified=true`.
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false`.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `sd_source_registry_patch_chain_smoke_blocked.json`.
- Remove the artifact from evidence inventory defaults.
- Remove static artifact test assertions and README/runbook/status notes.
- Restore `sd_mvp_readiness_summary.json` to the previous inventory count.
- Remove this Phase 119 section.

## Phase 120. Source Review Human Checklist Artifact

Goal: make the remaining Shandong source-review human actions explicit before
any source approval can unblock registry updates.

- [x] Add checked-in `sd_source_review_human_checklist_blocked.json`.
- [x] Tie the checklist to the candidate source review packet and blocked
      candidate review artifact.
- [x] Keep `ready_for_source_review_approval=false` while verified items and
      remaining pending items are explicit.
- [x] Add the checklist artifact to evidence inventory defaults.
- [x] Refresh `sd_mvp_readiness_summary.json` so inventory reports 20 artifacts.
- [x] Add static evidence tests for the blocked human checklist.
- [x] Document the checklist in README, runbook, and MVP status.
- [x] Keep all changes no-write: no source approval, no registry patch, no
      crawler, no official file download, no raw snapshot creation, no
      parser/quality execution on real rows, no DB/seed/loader writes, and no
      Agent/RAG refresh.

Validation:

```bash
python3 -m json.tool \
  examples/real_data/artifacts/sd_source_review_human_checklist_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
```

Current verification status:

- The checklist reports `ready_for_source_review_approval=false`.
- It now marks the official page, attachment/table, category, and published year
  as verified or confirmed, while license/citation, reviewer, review time, and
  allow flag remain pending.
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false`.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `sd_source_review_human_checklist_blocked.json`.
- Remove the artifact from evidence inventory defaults.
- Remove static artifact test assertions and README/runbook/status notes.
- Restore `sd_mvp_readiness_summary.json` to the previous inventory count.
- Remove this Phase 120 section.

## Phase 121. Source Review Handoff Artifact

Goal: summarize the blocked Shandong source-review handoff so the next human
reviewer can continue without treating the candidate source as approved.

- [x] Add checked-in `sd_source_review_handoff_blocked.json`.
- [x] Link the handoff to the human checklist, candidate review, blocked
      registry patch chain, and readiness summary artifacts.
- [x] Keep `ready_for_source_review_handoff=false` while completed and pending
      manual actions are explicit.
- [x] Add the handoff artifact to evidence inventory defaults.
- [x] Refresh `sd_mvp_readiness_summary.json` so inventory reports 21 artifacts.
- [x] Add static evidence tests for the blocked handoff.
- [x] Document the handoff in README, runbook, and MVP status.
- [x] Keep all changes no-write: no source approval, no registry patch, no
      crawler, no official file download, no raw snapshot creation, no
      parser/quality execution on real rows, no DB/seed/loader writes, and no
      Agent/RAG refresh.

Validation:

```bash
python3 -m json.tool \
  examples/real_data/artifacts/sd_source_review_handoff_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
```

Current verification status:

- The handoff reports `ready_for_source_review_handoff=false`.
- It keeps source review, registry update, registry patch chain, and real
  snapshot readiness blocked while confirming `registry_not_modified=true`.
- It now marks official page, attachment/table, and dataset scope checks as
  verified or confirmed; usage/citation review, reviewer record, and separate
  approval remain pending.
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false`.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `sd_source_review_handoff_blocked.json`.
- Remove the artifact from evidence inventory defaults.
- Remove static artifact test assertions and README/runbook/status notes.
- Restore `sd_mvp_readiness_summary.json` to the previous inventory count.
- Remove this Phase 121 section.

## Phase 122. Synthetic Source Approval Positive Example

Goal: provide a checked-in positive source approval packet shape without
approving any real source or touching registry data.

- [x] Add `source_review_approval_reviewed_example.json` as a synthetic
      complete source approval packet.
- [x] Generate checked-in
      `source_review_approval_reviewed_example_review.json` from the existing
      source review approval CLI.
- [x] Keep the example source id synthetic and outside real registry approval.
- [x] Add the review artifact to evidence inventory defaults.
- [x] Refresh `sd_mvp_readiness_summary.json` so inventory reports 22 artifacts.
- [x] Add source review, static artifact, and inventory tests.
- [x] Document that the positive example is not Shandong approval and does not
      authorize registry patch.
- [x] Keep all changes no-write: no source registry edit, no crawler, no
      official file download, no raw snapshot creation, no parser/quality
      execution on real rows, no DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
python3 -m json.tool \
  examples/real_data/source_review_approval_reviewed_example.json
python3 -m json.tool \
  examples/real_data/artifacts/source_review_approval_reviewed_example_review.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_review_approval.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
```

Current verification status:

- The synthetic example review reports `ready_for_registry_update=true`.
- The review scope uses `synthetic_reviewed_source_example`, not
  `sd_exam_authority`.
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false` for the real Shandong path.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `source_review_approval_reviewed_example.json`.
- Remove `source_review_approval_reviewed_example_review.json`.
- Remove the artifact from evidence inventory defaults.
- Remove source review/static artifact/inventory test assertions.
- Remove README/runbook/status notes.
- Restore `sd_mvp_readiness_summary.json` to the previous inventory count.
- Remove this Phase 122 section.

## Phase 123. Synthetic Source Approval Registry Isolation Artifact

Goal: prove the synthetic positive source approval example cannot accidentally
unlock the real source registry update path.

- [x] Generate checked-in
      `source_review_approval_reviewed_example_update_plan_blocked.json`
      from the current registry and the synthetic approval review artifact.
- [x] Keep `ready_for_registry_patch=false` with `source_not_found`.
- [x] Keep `planned_updates={}` and `Does not modify sources.json.`
- [x] Add the blocked synthetic update plan artifact to evidence inventory
      defaults.
- [x] Refresh `sd_mvp_readiness_summary.json` so inventory reports 23 artifacts.
- [x] Add static evidence, inventory, and source update plan tests.
- [x] Document that positive source approval packet review does not bypass
      registry source matching.
- [x] Keep all changes no-write: no source registry edit, no crawler, no
      official file download, no raw snapshot creation, no parser/quality
      execution on real rows, no DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
python3 -m json.tool \
  examples/real_data/artifacts/\
source_review_approval_reviewed_example_update_plan_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_update_plan.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
    examples/real_data/artifacts
```

Current verification status:

- The synthetic update plan exits blocked by design with `source_not_found`.
- The artifact keeps `planned_updates={}` and `ready_for_registry_patch=false`.
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false` for the real Shandong path.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove `source_review_approval_reviewed_example_update_plan_blocked.json`.
- Remove the artifact from evidence inventory defaults.
- Remove source update plan/static artifact/inventory test assertions.
- Remove README/runbook/status notes.
- Restore `sd_mvp_readiness_summary.json` to the previous inventory count.
- Remove this Phase 123 section.

## Phase 124. Parser and Quality Source Metadata Visibility

Goal: make parser/quality smoke evidence expose source/year/confidence metadata
directly for future Agent citations.

- [x] Add `source_id`, `dataset`, and `year` to parser candidate source
      previews while preserving existing source fields.
- [x] Add quality smoke `source_metadata` summary for source ids, snapshot ids,
      datasets, years, confidence min/max, and missing source/snapshot counts.
- [x] Regenerate checked-in `sd_parser_rows_bundle_smoke.json`.
- [x] Regenerate checked-in `sd_quality_smoke.json`.
- [x] Add parser, quality, and static evidence artifact assertions.
- [x] Document the additive source metadata fields in README, runbook, and MVP
      status.
- [x] Keep all changes no-write: no parser execution on real rows, no quality
      gate on real rows, no DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_parser_rows_bundle_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_quality_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
python3 -m json.tool examples/real_data/artifacts/sd_parser_rows_bundle_smoke.json
python3 -m json.tool examples/real_data/artifacts/sd_quality_smoke.json
```

Current verification status:

- Parser smoke candidate source now includes source id, snapshot id, dataset,
  year, source record ref, confidence, and review metadata presence.
- Quality smoke now reports source metadata coverage and confidence min/max.
- Existing scope readiness remains no-write and synthetic only.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove the added parser candidate source fields.
- Remove quality smoke `source_metadata`.
- Regenerate parser/quality smoke artifacts with the prior shape.
- Remove parser/quality/static artifact test assertions.
- Remove README/runbook/status notes.
- Remove this Phase 124 section.

## Phase 125. Quality Smoke Source Metadata Gate

Goal: make source metadata required by quality smoke instead of only visible in
summaries.

- [x] Block quality smoke when candidate source is missing `source_id`.
- [x] Keep existing `snapshot_id` block and add blocks for missing `dataset`
      and `year`.
- [x] Add required review text for missing candidate source metadata.
- [x] Add quality smoke tests for missing source id, dataset, and year.
- [x] Regenerate checked-in quality and aggregate smoke artifacts from the new
      gate logic.
- [x] Document that source metadata is part of the quality smoke gate.
- [x] Keep all changes no-write: no parser/quality execution on real rows, no
      DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_quality_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_example_chain_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
python3 -m json.tool examples/real_data/artifacts/sd_quality_smoke.json
```

Current verification status:

- Existing synthetic quality smoke still passes because source metadata is
  complete.
- A candidate missing source id, dataset, or year is blocked by quality smoke.
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false` for the real Shandong path.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove the added source metadata checks from quality smoke.
- Remove the new missing metadata test assertions.
- Regenerate quality and aggregate smoke artifacts with the prior behavior.
- Remove runbook/status notes.
- Remove this Phase 125 section.

## Phase 126. Quality Smoke Source Metadata Consistency Gate

Goal: make quality smoke reject inconsistent source metadata, not just missing
source metadata.

- [x] Require candidate source id, snapshot id, and dataset to match parser
      smoke scope when both sides are present.
- [x] Require candidate source year to match natural key year.
- [x] Add required review text for source metadata mismatch.
- [x] Add quality smoke test coverage for source id, snapshot id, dataset, and
      year mismatches.
- [x] Regenerate checked-in quality and aggregate smoke artifacts from the new
      consistency gate.
- [x] Document the consistency rule in runbook and MVP status.
- [x] Keep all changes no-write: no parser/quality execution on real rows, no
      DB/seed/loader writes, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_quality_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_example_chain_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
python3 -m json.tool examples/real_data/artifacts/sd_quality_smoke.json
```

Current verification status:

- Existing synthetic quality smoke still passes because source metadata is
  aligned.
- A candidate with mismatched source id, snapshot id, dataset, or year is
  blocked by quality smoke.
- Readiness summary still reports `passed=false` and
  `ready_for_real_snapshot=false` for the real Shandong path.
- Full `pytest` and `ruff` remain pending until a project environment is
  available.

Rollback:

- Remove source metadata consistency checks from quality smoke.
- Remove the new mismatch test assertions.
- Regenerate quality and aggregate smoke artifacts with the prior behavior.
- Remove runbook/status notes.
- Remove this Phase 126 section.

## Phase 127. Approved Source Answer Policy Alignment

Goal: align Agent/tool source summaries with the source review approval status
used by the registry gates.

- [x] Treat `approved` as an accepted reviewed source status alongside
      `reviewed` in tool source summaries.
- [x] Keep `candidate`, missing review status, stale freshness, low confidence,
      or low trust score in the caution path.
- [x] Add tool source metadata test coverage for an approved source producing
      a citeable answer policy.
- [x] Document the `reviewed` / `approved` source status rule in MVP status.
- [x] Keep all changes no-write: no DB migration, no seed update, no loader
      run, and no Agent/RAG refresh.

Validation:

```bash
python3 -m py_compile \
  backend/data_pipeline/lineage/sources.py \
  tests/test_tool_source_metadata.py
```

Current verification status:

- `py_compile` is expected to pass for changed files.
- `tests/test_tool_source_metadata.py` still requires SQLAlchemy at runtime;
  the current environment lacks `sqlalchemy`, so the executable test remains
  pending until project runtime dependencies are installed.
- Static answer policy artifacts remain no-write and synthetic only.

Rollback:

- Restore source summary review status acceptance to the previous single
  `reviewed` status.
- Remove approved-source test assertions.
- Remove MVP status note.
- Remove this Phase 127 section.

## Phase 128. Answer Policy Source Metadata Completeness Gate

Goal: prevent otherwise citeable summaries from being used as answer evidence
when their source metadata is incomplete.

- [x] Make `build_answer_source_policy(...)` treat explicit
      `source_metadata_complete=false` as unsupported.
- [x] Add `source_metadata_incomplete` to answer policy reasons.
- [x] Include `source_metadata_complete` in tool-level source summaries.
- [x] Require source ID, snapshot ID, published year, and confidence in source
      summary completeness checks.
- [x] Update static synthetic answer-policy examples and aggregate artifacts.
- [x] Document the metadata completeness rule in MVP status.
- [x] Keep all changes no-write: no crawler, no DB write, no seed update,
      no loader run, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python3 tests/test_data_lineage_policy.py
python3 -m py_compile \
  backend/data_pipeline/lineage/policy.py \
  backend/data_pipeline/lineage/sources.py \
  backend/tools/definitions.py \
  tests/test_data_lineage_policy.py \
  tests/test_tool_source_metadata.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
  examples/real_data/artifacts
```

Current verification status:

- `python3 -m py_compile` passed for the answer policy, source summary, tool
  definition, and related test files.
- `python3 -m json.tool` passed for the static tool response and answer policy
  artifact.
- `backend.data_pipeline.lineage.policy_cli` regenerated
  `sd_answer_source_policy.json` with `source_metadata_complete=true`.
- `backend.data_pipeline.pilots.example_chain_smoke_cli` refreshed the passing
  synthetic aggregate and the blocked template aggregate.
- `backend.data_pipeline.pilots.readiness_summary_cli` refreshed
  `sd_mvp_readiness_summary.json` and exited non-zero as expected because real
  source snapshot planning is still blocked.
- `backend.data_pipeline.pilots.evidence_inventory_cli` passed with 23
  artifacts and zero inventory issues.
- A direct policy import check confirmed explicit incomplete metadata returns
  `answer_mode=unsupported` with `source_metadata_incomplete`.
- `tests/test_tool_source_metadata.py` still requires SQLAlchemy at runtime;
  direct execution fails in this worktree with `No module named 'sqlalchemy'`,
  so use `py_compile` until project runtime dependencies are available.
- Readiness summary must remain `passed=false` and
  `ready_for_real_snapshot=false`.

Rollback:

- Remove `source_metadata_complete` from tool summaries and static examples.
- Remove `source_metadata_incomplete` from answer policy reasons.
- Restore answer policy behavior so explicit incomplete metadata does not
  affect citation readiness.
- Remove this Phase 128 section.

## Phase 129. Shandong Source Candidate Evidence Narrowing

Goal: move the real Shandong 2025 source review closer to approval without
crossing the authorization boundary.

- [x] Verify the official Shandong exam authority page for the 2025 first-choice
      filing table.
- [x] Record the official `.xls` attachment URL in the candidate source review
      packet without downloading it.
- [x] Mark data category and published year evidence as confirmed.
- [x] Keep `allow_source_review_approval=false` and
      `license_reviewed=false` because usage/citation authorization is still
      not approved.
- [x] Regenerate the blocked source review and registry update-plan artifacts.
- [x] Update human checklist and handoff artifacts so only the true remaining
      manual actions are pending.
- [x] Fix readiness summary generation so stale required reviews from the
      previous summary artifact do not feed back into the next summary.
- [x] Keep all changes no-write: no crawler, no official file download, no raw
      snapshot, no parser over real rows, no registry patch, no DB/seed write,
      and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.review_approval_cli \
  examples/real_data/sd_source_review_approval_candidate.json \
  --review-output \
  examples/real_data/artifacts/sd_source_review_approval_candidate_review.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.update_plan_cli \
  backend/data_pipeline/sources/sources.json \
  examples/real_data/artifacts/sd_source_review_approval_candidate_review.json \
  --plan-output \
  examples/real_data/artifacts/sd_source_registry_update_plan_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.readiness_summary_cli \
  --summary-output examples/real_data/artifacts/sd_mvp_readiness_summary.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
  examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Source review remains blocked with four errors: allow flag, license/citation
  review, reviewer, and review time.
- Registry update plan remains blocked because source review is not ready.
- Evidence inventory passes with 23 artifacts and zero inventory issues.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.
- `tests/test_data_pipeline_evidence_artifacts.py`,
  `tests/test_data_pipeline_evidence_inventory.py`, and
  `tests/test_data_pipeline_readiness_summary.py` pass under system Python.
- `py_compile` passes for the changed readiness/inventory modules and related
  tests.

Rollback:

- Remove the attachment URL and confirmed evidence fields from
  `sd_source_review_approval_candidate.json`.
- Restore the previous blocked source review, checklist, handoff, update-plan,
  and readiness artifacts.
- Remove the readiness summary self-review exclusion and related tests.
- Remove this Phase 129 section.

## Phase 130. Source Usage and Citation Review Gate

Goal: make source usage/citation authorization an explicit no-write gate before
source approval can unblock real-data ingestion.

- [x] Add stdlib-only `review_source_usage(...)`.
- [x] Add `backend.data_pipeline.sources.usage_review_cli`.
- [x] Add tests for approved, blocked, inconsistent, and CLI usage-review
      payloads.
- [x] Add a Shandong 2025 usage review input packet and blocked review artifact.
- [x] Record the official page copyright/usage notice and keep
      `allow_real_data_ingestion=false`.
- [x] Add the usage review artifact to evidence inventory defaults.
- [x] Refresh readiness summary; artifact count is now 24 and real snapshot
      readiness remains blocked.
- [x] Document the usage review gate in README and MVP status.
- [x] Keep all changes no-write: no crawler, no official file download, no raw
      snapshot, no registry patch, no parser over real rows, no DB/seed write,
      and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.usage_review_cli \
  examples/real_data/sd_source_usage_review_blocked.json \
  --review-output \
  examples/real_data/artifacts/sd_source_usage_review_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.readiness_summary_cli \
  --summary-output examples/real_data/artifacts/sd_mvp_readiness_summary.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
  examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_usage_review.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
```

Current verification status:

- Usage review remains blocked with four errors: license review, ingestion
  approval, reviewer, and reviewed-at timestamp.
- Evidence inventory passes with 24 artifacts and zero inventory issues.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.
- Source approval and registry update remain blocked.
- Targeted unittest and `py_compile` checks pass in this worktree.

Rollback:

- Remove `usage_review.py`, `usage_review_cli.py`, and usage-review tests.
- Remove `sd_source_usage_review_blocked.json` input and artifact files.
- Remove the usage review artifact from evidence inventory defaults and docs.
- Restore readiness summary to the previous 23-artifact inventory.
- Remove this Phase 130 section.

## Phase 131. Source Approval Requires Usage Review

Goal: prevent source approval packets from bypassing the explicit
usage/citation review gate.

- [x] Make `review_source_approval(...)` require a `usage_review` summary.
- [x] Require `usage_review.action=source_usage_review`.
- [x] Require `ready_for_source_approval_license_review=true`.
- [x] Check usage review scope against the source approval source/category/
      province/year scope.
- [x] Add source approval tests for complete, blocked, and usage-not-ready
      packets.
- [x] Update source review chain smoke tests so complete approvals include
      ready usage review evidence.
- [x] Update the source approval template, synthetic reviewed example, and
      Shandong candidate packet.
- [x] Refresh Shandong blocked source approval review, synthetic positive
      review, registry update plans, and MVP readiness summary.
- [x] Keep all changes no-write: no registry patch, no crawler, no official file
      download, no raw snapshot, no parser over real rows, no DB/seed write, and
      no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_review_approval.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_review_chain_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
python3 -m py_compile \
  backend/data_pipeline/sources/review_approval.py \
  tests/test_data_pipeline_source_review_approval.py \
  tests/test_data_pipeline_source_review_chain_smoke.py \
  tests/test_data_pipeline_evidence_artifacts.py \
  tests/test_data_pipeline_evidence_inventory.py
```

Current verification status:

- Targeted unittest and `py_compile` checks pass in this worktree.
- Shandong source approval remains blocked and now includes
  `source_usage_review_not_ready`.
- Synthetic reviewed example still passes because it includes a ready usage
  review summary, but it remains blocked at update planning because its source
  id is synthetic and absent from `sources.json`.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove `usage_review` checks from `review_source_approval(...)`.
- Remove `usage_review` summaries from templates/examples/candidate packets.
- Restore regenerated source approval and update-plan artifacts.
- Remove this Phase 131 section.

## Phase 132. Shandong Source Review Chain Artifact

Goal: expose the current Shandong source precheck chain in one no-write artifact.

- [x] Generate `sd_source_review_chain_smoke_blocked.json` from current
      `sources.json` and the Shandong candidate source approval packet.
- [x] Show source scope audit passes while approval review and registry update
      planning remain blocked.
- [x] Preserve `registry_not_modified=true`.
- [x] Add the chain artifact to evidence inventory defaults.
- [x] Add static evidence tests for the chain artifact.
- [x] Document the artifact in README and MVP status.
- [x] Keep all changes no-write: no source approval, no registry patch, no
      crawler, no official file download, no raw snapshot, no parser over real
      rows, no DB/seed write, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.review_chain_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  examples/real_data/sd_source_review_approval_candidate.json \
  --review-output \
  examples/real_data/artifacts/sd_source_review_chain_smoke_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.evidence_inventory_cli \
  examples/real_data/artifacts
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
```

Current verification status:

- The chain artifact is blocked with two top-level errors:
  `approval_review_not_passed` and `update_plan_not_ready`.
- It reports `source_scope_audit_passed=true` and `registry_not_modified=true`.
- Evidence inventory now reports 26 artifacts after the Phase 133 positive
  synthetic chain artifact was added.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove `sd_source_review_chain_smoke_blocked.json`.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh readiness summary back to the previous artifact inventory.
- Remove this Phase 132 section.

## Phase 133. Synthetic Source Review Chain Positive Artifact

Goal: prove the approved source precheck path can reach a ready no-write
registry update plan without approving Shandong or editing the real registry.

- [x] Add `synthetic_reviewed_sources_registry.json` as a temporary registry
      input that includes `synthetic_reviewed_source_example`.
- [x] Generate
      `artifacts/source_review_chain_smoke_reviewed_example.json` with the
      existing `review_chain_smoke_cli`.
- [x] Show usage/source approval and update planning all pass for the
      synthetic source.
- [x] Preserve `registry_not_modified=true` and no-write non-goals.
- [x] Add the positive chain artifact to evidence inventory defaults.
- [x] Add static artifact and inventory tests.
- [x] Document that this artifact does not approve Shandong or modify
      `backend/data_pipeline/sources/sources.json`.
- [x] Keep all changes no-write: no source approval for real sources, no
      registry patch, no crawler, no official file download, no raw snapshot,
      no parser over real rows, no DB/seed write, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.review_chain_smoke_cli \
  examples/real_data/synthetic_reviewed_sources_registry.json \
  examples/real_data/source_review_approval_reviewed_example.json \
  --review-output \
  examples/real_data/artifacts/source_review_chain_smoke_reviewed_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Synthetic chain artifact passes with `source_scope_audit_passed=true`,
  `approval_review_passed=true`, `update_plan_ready=true`, and
  `registry_not_modified=true`.
- Update plan shows a synthetic `reviewed -> approved` status patch plan.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove `synthetic_reviewed_sources_registry.json`.
- Remove `source_review_chain_smoke_reviewed_example.json`.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh readiness summary back to the previous artifact inventory.
- Remove this Phase 133 section.

## Phase 134. Synthetic Registry Patch Positive Artifact

Goal: prove the ready source update plan can continue through no-write patch
approval, patch preview, and patch chain smoke without executing a real
registry edit.

- [x] Add `source_registry_patch_approval_reviewed_example.json` as a
      synthetic patch approval packet.
- [x] Generate
      `artifacts/source_review_chain_smoke_reviewed_example_update_plan.json`
      from the synthetic source approval review and temporary registry input.
- [x] Generate
      `artifacts/source_registry_patch_approval_reviewed_example_review.json`.
- [x] Generate
      `artifacts/source_registry_patch_preview_reviewed_example.json`.
- [x] Generate
      `artifacts/source_registry_patch_chain_smoke_reviewed_example.json`.
- [x] Show patch approval and patch preview both ready while
      `registry_not_modified=true`.
- [x] Add the positive patch artifacts to evidence inventory defaults.
- [x] Add static artifact and inventory tests.
- [x] Update the patch chain test fixture to include the required
      `usage_review` summary in the source approval packet.
- [x] Document that these artifacts do not approve Shandong, do not execute a
      registry patch, and do not modify `sources.json`.
- [x] Keep all changes no-write: no source approval for real sources, no
      registry patch, no crawler, no official file download, no raw snapshot,
      no parser over real rows, no DB/seed write, and no Agent/RAG refresh.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.update_plan_cli \
  examples/real_data/synthetic_reviewed_sources_registry.json \
  examples/real_data/artifacts/source_review_approval_reviewed_example_review.json \
  --plan-output \
  examples/real_data/artifacts/source_review_chain_smoke_reviewed_example_update_plan.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.patch_approval_cli \
  examples/real_data/artifacts/source_review_chain_smoke_reviewed_example_update_plan.json \
  examples/real_data/source_registry_patch_approval_reviewed_example.json \
  --review-output \
  examples/real_data/artifacts/source_registry_patch_approval_reviewed_example_review.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.patch_preview_cli \
  examples/real_data/synthetic_reviewed_sources_registry.json \
  examples/real_data/artifacts/source_review_chain_smoke_reviewed_example_update_plan.json \
  examples/real_data/artifacts/source_registry_patch_approval_reviewed_example_review.json \
  --preview-output \
  examples/real_data/artifacts/source_registry_patch_preview_reviewed_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.patch_chain_smoke_cli \
  examples/real_data/synthetic_reviewed_sources_registry.json \
  examples/real_data/artifacts/source_review_chain_smoke_reviewed_example_update_plan.json \
  examples/real_data/artifacts/source_registry_patch_approval_reviewed_example_review.json \
  --review-output \
  examples/real_data/artifacts/source_registry_patch_chain_smoke_reviewed_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_patch_chain_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Synthetic patch chain artifact passes with `patch_approval_ready=true`,
  `patch_preview_ready=true`, and `registry_not_modified=true`.
- Patch preview only applies the synthetic `review_status` change to
  `approved`.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove `source_registry_patch_approval_reviewed_example.json`.
- Remove the four synthetic patch artifacts.
- Remove the artifacts from evidence inventory defaults, docs, and tests.
- Restore the previous patch chain test fixture if needed.
- Refresh readiness summary back to the previous artifact inventory.
- Remove this Phase 134 section.

## Phase 135. Synthetic Snapshot Planning Positive Artifact

Goal: prove the next source gate becomes ready only after an approved source
covers the requested data category, province, and year, without creating any
raw snapshot files.

- [x] Add `synthetic_approved_sources_registry.json` as a temporary approved
      source registry input.
- [x] Generate
      `artifacts/source_snapshot_planning_approved_example.json` with the
      existing `snapshot_planning_cli`.
- [x] Show `ready_for_snapshot_planning=true` with no blockers for the
      synthetic approved source.
- [x] Preserve no-write non-goals: no remote fetch, no raw snapshot, no parser,
      no loader, no DB/seed/RAG/Agent writes.
- [x] Add the positive snapshot planning artifact to evidence inventory
      defaults.
- [x] Add static artifact and inventory tests.
- [x] Document that this artifact does not approve Shandong and does not create
      raw snapshots.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.snapshot_planning_cli \
  examples/real_data/synthetic_approved_sources_registry.json \
  --data-category admission_scores \
  --province 示例省 \
  --year 2025 \
  --review-output \
  examples/real_data/artifacts/source_snapshot_planning_approved_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_snapshot_planning.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Synthetic snapshot planning artifact passes with
  `ready_for_snapshot_planning=true`.
- Current Shandong snapshot planning remains blocked because
  `sd_exam_authority` is still `candidate`.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove `synthetic_approved_sources_registry.json`.
- Remove `source_snapshot_planning_approved_example.json`.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh readiness summary back to the previous artifact inventory.
- Remove this Phase 135 section.

## Phase 136. Synthetic Intake Positive Artifact

Goal: prove an intake packet can become ready for snapshot preparation only
after it carries a ready source snapshot planning review, without downloading
files or creating raw snapshots.

- [x] Add `synthetic_official_sample_intake_reviewed_example.json` as a
      synthetic intake packet chained from approved snapshot planning.
- [x] Generate `artifacts/source_intake_review_approved_example.json` with the
      existing intake review CLI.
- [x] Show `ready_for_snapshot=true` with no intake review blockers.
- [x] Preserve no-write non-goals: no remote fetch, no raw snapshot, no parser,
      no loader, no DB/seed/RAG/Agent writes.
- [x] Add the positive intake artifact to evidence inventory defaults.
- [x] Add static artifact and inventory tests.
- [x] Document that this artifact does not approve Shandong and does not create
      raw snapshots.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.intake.cli \
  examples/real_data/synthetic_official_sample_intake_reviewed_example.json \
  --review-output \
  examples/real_data/artifacts/source_intake_review_approved_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_intake.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Synthetic intake artifact passes with `ready_for_snapshot=true`.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove `synthetic_official_sample_intake_reviewed_example.json`.
- Remove `source_intake_review_approved_example.json`.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh readiness summary back to the previous artifact inventory.
- Remove this Phase 136 section.

## Phase 137. Source-to-Intake Chain Smoke

Goal: aggregate the synthetic pre-snapshot gates into one no-write review so
reviewers can verify source id and scope continuity before raw snapshot work.

- [x] Add `backend/data_pipeline/pilots/source_to_intake_chain_smoke.py`.
- [x] Add `backend/data_pipeline/pilots/source_to_intake_chain_smoke_cli.py`.
- [x] Add `tests/test_data_pipeline_source_to_intake_chain_smoke.py`.
- [x] Generate
      `artifacts/source_to_intake_chain_smoke_approved_example.json`.
- [x] Check source review chain, registry patch chain, snapshot planning, and
      intake review are all ready.
- [x] Check source id and data category/province/year scope are consistent.
- [x] Preserve no-write non-goals: no registry edit, no remote fetch, no raw
      snapshot, no parser, no loader, no DB/seed/RAG/Agent writes.
- [x] Add the aggregate artifact to evidence inventory defaults.
- [x] Add static artifact and inventory tests.
- [x] Document that this artifact does not approve Shandong and does not create
      raw snapshots.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.source_to_intake_chain_smoke_cli \
  --source-review-chain \
  examples/real_data/artifacts/source_review_chain_smoke_reviewed_example.json \
  --registry-patch-chain \
  examples/real_data/artifacts/source_registry_patch_chain_smoke_reviewed_example.json \
  --snapshot-planning-review \
  examples/real_data/artifacts/source_snapshot_planning_approved_example.json \
  --intake-review \
  examples/real_data/artifacts/source_intake_review_approved_example.json \
  --review-output \
  examples/real_data/artifacts/source_to_intake_chain_smoke_approved_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_to_intake_chain_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Synthetic source-to-intake chain artifact passes with all readiness and
  consistency checks true.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove `source_to_intake_chain_smoke.py` and its CLI.
- Remove `test_data_pipeline_source_to_intake_chain_smoke.py`.
- Remove `source_to_intake_chain_smoke_approved_example.json`.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh readiness summary back to the previous artifact inventory.
- Remove this Phase 137 section.

## Phase 138. Synthetic Parser and Quality Positive Artifacts

Goal: continue the same synthetic source/snapshot from intake readiness into
parser and quality smoke, proving source metadata survives candidate preview
and quality checks.

- [x] Add `synthetic_snapshot_pilot_rows.json` for the synthetic approved
      source and snapshot.
- [x] Add `snapshots/synthetic_snapshot_2025_001/manifest.json`.
- [x] Generate
      `artifacts/source_parser_rows_bundle_smoke_approved_example.json`.
- [x] Generate `artifacts/source_quality_smoke_approved_example.json`.
- [x] Show parser smoke carries `source_id`, `snapshot_id`, dataset, year,
      confidence, and review metadata.
- [x] Show quality smoke passes coverage, source metadata, confidence, and
      review metadata checks.
- [x] Preserve no-write non-goals: no remote fetch, no real raw snapshot file,
      no formal parser contract, no formal quality gate, no loader, no
      DB/seed/RAG/Agent writes.
- [x] Add the artifacts to evidence inventory defaults.
- [x] Add static artifact and inventory tests.
- [x] Document that these artifacts do not approve Shandong and do not create
      real data.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.parsers.rows_bundle_smoke_cli \
  examples/real_data/synthetic_snapshot_pilot_rows.json \
  --snapshot-manifest \
  examples/real_data/snapshots/synthetic_snapshot_2025_001/manifest.json \
  --expect-source-id synthetic_reviewed_source_example \
  --expect-snapshot-id synthetic_snapshot_2025_001 \
  --expect-dataset admission_scores \
  --review-output \
  examples/real_data/artifacts/source_parser_rows_bundle_smoke_approved_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.quality.smoke_cli \
  examples/real_data/artifacts/source_parser_rows_bundle_smoke_approved_example.json \
  --rows-bundle examples/real_data/synthetic_snapshot_pilot_rows.json \
  --review-output \
  examples/real_data/artifacts/source_quality_smoke_approved_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Synthetic parser smoke passes with `ready_for_parser=true`.
- Synthetic quality smoke passes with `ready_for_quality_gate=true`.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove `synthetic_snapshot_pilot_rows.json`.
- Remove `snapshots/synthetic_snapshot_2025_001/manifest.json`.
- Remove the synthetic parser and quality smoke artifacts.
- Remove the artifacts from evidence inventory defaults, docs, and tests.
- Refresh readiness summary back to the previous artifact inventory.
- Remove this Phase 138 section.

## Phase 139. Source-to-Quality Chain Smoke

Goal: aggregate the synthetic source-to-intake, parser smoke, and quality smoke
artifacts into one no-write review so reviewers can verify scope continuity
before any loader discussion.

- [x] Add `backend/data_pipeline/pilots/source_to_quality_chain_smoke.py`.
- [x] Add `backend/data_pipeline/pilots/source_to_quality_chain_smoke_cli.py`.
- [x] Add `tests/test_data_pipeline_source_to_quality_chain_smoke.py`.
- [x] Generate
      `artifacts/source_to_quality_chain_smoke_approved_example.json`.
- [x] Check source-to-intake, parser smoke, and quality smoke readiness.
- [x] Check source id, snapshot id, dataset, candidate count, and source year
      continuity across the no-write artifacts.
- [x] Preserve no-write non-goals: no registry edit, no remote fetch, no raw
      snapshot, no formal parser, no formal quality gate, no loader, no
      DB/seed/RAG/Agent writes.
- [x] Add the aggregate artifact to evidence inventory defaults.
- [x] Add static artifact and inventory tests.
- [x] Document that this artifact does not approve Shandong and does not load
      real data.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.source_to_quality_chain_smoke_cli \
  --source-to-intake-chain \
  examples/real_data/artifacts/source_to_intake_chain_smoke_approved_example.json \
  --parser-smoke-review \
  examples/real_data/artifacts/source_parser_rows_bundle_smoke_approved_example.json \
  --quality-smoke-review \
  examples/real_data/artifacts/source_quality_smoke_approved_example.json \
  --review-output \
  examples/real_data/artifacts/source_to_quality_chain_smoke_approved_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_to_quality_chain_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Synthetic source-to-quality chain artifact passes with all readiness and
  consistency checks true.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove `source_to_quality_chain_smoke.py` and its CLI.
- Remove `test_data_pipeline_source_to_quality_chain_smoke.py`.
- Remove `source_to_quality_chain_smoke_approved_example.json`.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh readiness summary back to the previous artifact inventory.
- Remove this Phase 139 section.

## Phase 140. Readiness Summary Source-to-Quality Signal

Goal: make the MVP readiness summary explicitly report whether the synthetic
source-to-quality chain is ready, instead of relying on evidence inventory
presence alone.

- [x] Add optional `source_to_quality_chain_smoke` input to
      `build_mvp_readiness_summary(...)`.
- [x] Auto-load `source_to_quality_chain_smoke_approved_example.json` from the
      artifacts directory when present.
- [x] Add `--source-to-quality-chain-smoke` to the readiness summary CLI.
- [x] Add `source_to_quality_chain_ready` to the summary output.
- [x] Add `scope.source_to_quality_chain` for source/snapshot/dataset review.
- [x] Add `source_to_quality_chain_not_ready` blocker when a provided chain
      artifact fails.
- [x] Refresh `sd_mvp_readiness_summary.json`.
- [x] Add tests for ready checked-in artifacts and failed chain blocking.
- [x] Document the explicit readiness summary signal.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.readiness_summary_cli \
  --summary-output examples/real_data/artifacts/sd_mvp_readiness_summary.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Checked-in MVP readiness summary now reports
  `source_to_quality_chain_ready=true`.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.
- MVP readiness remains `passed=false` and `ready_for_real_snapshot=false`.

Rollback:

- Remove the source-to-quality input and summary fields.
- Remove the CLI argument and tests.
- Regenerate `sd_mvp_readiness_summary.json`.
- Remove this Phase 140 section.

## Phase 141. MVP Manual Action Queue

Goal: convert the current blocked readiness state into an ordered human action
queue, so the Shandong pilot advances through source review before deferred
loader or Agent visibility approvals.

- [x] Add `backend/data_pipeline/pilots/action_queue.py`.
- [x] Add `backend/data_pipeline/pilots/action_queue_cli.py`.
- [x] Add `tests/test_data_pipeline_mvp_action_queue.py`.
- [x] Generate `artifacts/sd_mvp_action_queue.json`.
- [x] Prioritize pending source review actions from
      `sd_source_review_handoff_blocked.json`.
- [x] Add an explicit source snapshot planning blocker before loader or Agent
      visibility approvals.
- [x] Defer loader run command and Agent visibility approval until source review
      and real snapshot planning pass.
- [x] Add the action queue artifact to evidence inventory defaults.
- [x] Add static artifact and inventory tests.
- [x] Document that this queue does not approve a source or execute data
      movement.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.action_queue_cli \
  --review-output examples/real_data/artifacts/sd_mvp_action_queue.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_mvp_action_queue.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
```

Current verification status:

- Action queue is ready for human review and keeps source review first, then
  source snapshot planning, then deferred loader / Agent approvals.
- Loader and Agent approvals remain deferred.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.

Rollback:

- Remove `action_queue.py` and its CLI.
- Remove `test_data_pipeline_mvp_action_queue.py`.
- Remove `sd_mvp_action_queue.json`.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Remove this Phase 141 section.

## Phase 142. Synthetic Source Usage Positive Artifact

Goal: demonstrate the positive shape of the usage/citation review gate without
approving Shandong or any real source.

- [x] Add `examples/real_data/source_usage_review_reviewed_example.json`.
- [x] Generate `artifacts/source_usage_review_reviewed_example.json`.
- [x] Show `ready_for_source_approval_license_review=true` when reviewer,
      review time, license review, usage status, and allow flag are present.
- [x] Preserve no-write non-goals: no registry edit, no remote fetch, no raw
      snapshot, no parser, no quality gate, no loader, no DB/seed/RAG/Agent
      writes.
- [x] Add the positive usage artifact to evidence inventory defaults.
- [x] Add static artifact and inventory tests.
- [x] Document that this artifact does not approve Shandong or any real source.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.usage_review_cli \
  examples/real_data/source_usage_review_reviewed_example.json \
  --review-output \
  examples/real_data/artifacts/source_usage_review_reviewed_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
```

Current verification status:

- Synthetic usage review passes with no issues and no required reviews.
- Current Shandong usage review remains blocked pending human authorization.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.

Rollback:

- Remove the synthetic usage review input and artifact.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh readiness summary and action queue artifacts.
- Remove this Phase 142 section.

## Phase 143. Source Usage-to-Approval Chain Smoke

Goal: prove the source usage/citation gate and source approval gate can be
reviewed together before any registry patch or real source approval.

- [x] Add `backend/data_pipeline/sources/usage_to_approval_chain_smoke.py`.
- [x] Add `backend/data_pipeline/sources/usage_to_approval_chain_smoke_cli.py`.
- [x] Add `tests/test_data_pipeline_source_usage_to_approval_chain_smoke.py`.
- [x] Generate
      `artifacts/source_usage_to_approval_chain_smoke_reviewed_example.json`.
- [x] Check usage review readiness, source approval readiness, source id,
      category/province/year scope, ready usage evidence, and registry update
      hint continuity.
- [x] Preserve no-write non-goals: no registry edit, no real source approval,
      no remote fetch, no raw snapshot, no parser, no quality gate, no loader,
      no DB/seed/RAG/Agent writes.
- [x] Add the chain smoke artifact to evidence inventory defaults.
- [x] Add static artifact and inventory tests.
- [x] Refresh readiness summary and action queue artifacts.
- [x] Document that this artifact does not approve Shandong or any real source.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.usage_to_approval_chain_smoke_cli \
  --usage-review \
  examples/real_data/artifacts/source_usage_review_reviewed_example.json \
  --source-approval-review \
  examples/real_data/artifacts/source_review_approval_reviewed_example_review.json \
  --review-output \
  examples/real_data/artifacts/source_usage_to_approval_chain_smoke_reviewed_example.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_usage_to_approval_chain_smoke.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_mvp_action_queue.py
```

Current verification status:

- Synthetic usage-to-approval chain artifact passes with all readiness and
  consistency checks true.
- Evidence inventory now includes 39 checked no-write artifacts.
- Current Shandong usage review remains blocked pending human authorization.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.

Rollback:

- Remove `usage_to_approval_chain_smoke.py` and its CLI.
- Remove `test_data_pipeline_source_usage_to_approval_chain_smoke.py`.
- Remove `source_usage_to_approval_chain_smoke_reviewed_example.json`.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh readiness summary and action queue artifacts.
- Remove this Phase 143 section.

## Phase 144. Readiness Summary Usage-to-Approval Signal

Goal: make the MVP readiness summary and manual action queue explicitly report
the synthetic usage-to-approval chain state instead of relying on evidence
inventory presence alone.

- [x] Add optional `usage_to_approval_chain_smoke` input to
      `build_mvp_readiness_summary(...)`.
- [x] Auto-load
      `source_usage_to_approval_chain_smoke_reviewed_example.json` from the
      artifacts directory when present.
- [x] Add `--usage-to-approval-chain-smoke` to the readiness summary CLI.
- [x] Add `usage_to_approval_chain_ready` to the summary output.
- [x] Add `scope.usage_to_approval_chain` for source/scope review.
- [x] Add `usage_to_approval_chain_not_ready` blocker when a provided chain
      artifact fails.
- [x] Add `usage_to_approval_chain_ready` to action queue current state.
- [x] Refresh `sd_mvp_readiness_summary.json`.
- [x] Refresh `sd_mvp_action_queue.json`.
- [x] Add tests for ready checked-in artifacts and failed chain blocking.
- [x] Document that this signal remains synthetic no-write evidence and does
      not approve Shandong.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.readiness_summary_cli \
  --summary-output examples/real_data/artifacts/sd_mvp_readiness_summary.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.action_queue_cli \
  --review-output examples/real_data/artifacts/sd_mvp_action_queue.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_mvp_action_queue.py
```

Current verification status:

- Checked-in MVP readiness summary now reports
  `usage_to_approval_chain_ready=true`.
- Checked-in action queue now reports
  `current_state.usage_to_approval_chain_ready=true`.
- Current Shandong usage review remains blocked pending human authorization.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.

Rollback:

- Remove the usage-to-approval input and summary fields.
- Remove the CLI argument and tests.
- Regenerate `sd_mvp_readiness_summary.json` and `sd_mvp_action_queue.json`.
- Remove this Phase 144 section.

## Phase 145. Action Queue Source Review Context

Goal: make the manual action queue directly actionable for a human reviewer
without approving or collecting real data.

- [x] Add `source_review_context` to the MVP action queue output.
- [x] Include candidate official page URL, attachment URL, upstream artifact
      refs, verified action ids, and pending action ids.
- [x] Refresh `sd_mvp_action_queue.json`.
- [x] Add tests that the checked-in queue exposes the Shandong candidate URL
      and pending usage/citation review action.
- [x] Document that the context is review aid only and does not approve the
      source.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.pilots.action_queue_cli \
  --review-output examples/real_data/artifacts/sd_mvp_action_queue.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_mvp_action_queue.py
```

Current verification status:

- Checked-in action queue now includes `source_review_context`.
- Current Shandong usage review remains blocked pending human authorization.
- Current Shandong source and snapshot planning remain blocked because
  `sd_exam_authority` is still `candidate`.

Rollback:

- Remove `source_review_context` construction and test assertions.
- Regenerate `sd_mvp_action_queue.json`.
- Remove this Phase 145 section.

## Phase 146. Source Usage Review Template

Goal: make the source usage/citation review gate reusable for future provinces
instead of relying on the Shandong blocked packet as the only example.

- [x] Add `examples/real_data/source_usage_review_template.json`.
- [x] Keep the template blocked by default with
      `usage_status=blocked_pending_authorization`.
- [x] Document that usage/citation review must pass before source approval.
- [x] Update the pilot review checklist with required usage review fields.
- [x] Update the MVP runbook source-review order.
- [x] Keep no-write non-goals: no registry edit, no remote fetch, no raw
      snapshot, no parser, no quality gate, no loader, no DB/seed/RAG/Agent
      writes.

Validation:

```bash
python3 -m json.tool examples/real_data/source_usage_review_template.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.usage_review_cli \
  examples/real_data/source_usage_review_template.json
```

Current verification status:

- The template is valid JSON.
- The template remains blocked by default and does not approve any source.

Rollback:

- Remove `source_usage_review_template.json`.
- Remove the README, runbook, checklist, and implement-plan references.
- Remove this Phase 146 section.

## Phase 147. Source Usage Template Blocked Contract Test

Goal: prevent the checked-in source usage review template from drifting into an
accidentally approvable packet.

- [x] Add a unit test that reads
      `examples/real_data/source_usage_review_template.json`.
- [x] Assert the template remains blocked by default.
- [x] Assert missing source id and ingestion-not-allowed issues remain present.
- [x] Keep the test no-write and independent of registry, snapshots, loader,
      DB, seed, RAG, or Agent state.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_usage_review.py
```

Current verification status:

- The checked-in template remains blocked by default.
- The test suite protects the usage/citation gate from accidental template
  approval.

Rollback:

- Remove the template-blocking test.
- Remove this Phase 147 section.

## Phase 148. Priority Province Coverage Artifact

Goal: make the priority-province expansion stage visible as checked no-write
evidence without
registering new years, approving sources, or collecting data.

- [x] Generate
      `examples/real_data/artifacts/priority_source_coverage_report.json`.
- [x] Cover Shandong, Henan, Guangdong, Jiangsu, Zhejiang, Hebei, Sichuan,
      and Hubei.
- [x] Include priority categories `admission_scores` and `enrollment_plans`.
- [x] Add the coverage report to evidence inventory defaults.
- [x] Add static artifact tests that snapshot planning remains blocked.
- [x] Refresh `sd_mvp_readiness_summary.json` and `sd_mvp_action_queue.json`.
- [x] Document that the report only summarizes registered candidates and does
      not approve any source.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.coverage_cli \
  backend/data_pipeline/sources/sources.json \
  --priority-province 山东 \
  --priority-province 河南 \
  --priority-province 广东 \
  --priority-province 江苏 \
  --priority-province 浙江 \
  --priority-province 河北 \
  --priority-province 四川 \
  --priority-province 湖北 \
  --priority-data-category admission_scores \
  --priority-data-category enrollment_plans \
  --report-output examples/real_data/artifacts/priority_source_coverage_report.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Evidence inventory now includes 40 checked no-write artifacts.
- Priority source coverage report passes structurally but keeps snapshot
  planning blocked because priority provinces lack approved sources and most
  priority provinces still lack registered dataset years.
- Current Shandong usage review remains blocked pending human authorization.

Rollback:

- Remove `priority_source_coverage_report.json`.
- Remove the artifact from evidence inventory defaults, tests, and docs.
- Refresh `sd_mvp_readiness_summary.json` and `sd_mvp_action_queue.json`.
- Remove this Phase 148 section.

## Phase 149. Priority Source Coverage Action Queue

Goal: turn priority-province coverage gaps into a checked no-write human action
queue without approving sources, registering years, collecting data, or changing
the canonical registry.

- [x] Add `backend.data_pipeline.sources.coverage_action_queue` and CLI.
- [x] Generate
      `examples/real_data/artifacts/priority_source_coverage_action_queue.json`.
- [x] Keep the queue blocked for real execution with
      `ready_for_human_review=true`.
- [x] Add the queue artifact to evidence inventory defaults.
- [x] Add static tests for the 15 current priority actions.
- [x] Document that the queue only records review work and does not authorize
      snapshot planning, loader execution, or Agent/RAG refresh.
- [x] Refresh `sd_mvp_readiness_summary.json` and `sd_mvp_action_queue.json`.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.coverage_action_queue_cli \
  examples/real_data/artifacts/priority_source_coverage_report.json \
  --review-output examples/real_data/artifacts/priority_source_coverage_action_queue.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_coverage_action_queue.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Priority coverage action queue exposes 15 pending human actions:
  7 dataset-year reviews and 8 source-approval reviews.
- Evidence inventory includes the queue artifact as required no-write evidence.
- Current readiness remains blocked for real snapshot planning because no
  priority province source is approved yet.

Rollback:

- Remove `priority_source_coverage_action_queue.json`.
- Remove the artifact from evidence inventory defaults, tests, and docs.
- Refresh `sd_mvp_readiness_summary.json` and `sd_mvp_action_queue.json`.
- Remove this Phase 149 section.

## Phase 150. Source Year Review Gate

Goal: make priority province dataset-year review executable as a no-write human
review packet before any source registry year can be added.

- [x] Add `backend.data_pipeline.sources.year_review` and CLI.
- [x] Add `examples/real_data/source_year_review_template.json`.
- [x] Add blocked Henan input
      `examples/real_data/ha_source_year_review_blocked.json`.
- [x] Generate
      `examples/real_data/artifacts/ha_source_year_review_blocked.json`.
- [x] Add the blocked year review artifact to evidence inventory defaults.
- [x] Add tests proving templates and missing-year reviews stay blocked.
- [x] Document that this gate does not mutate `sources.json`.
- [x] Refresh `sd_mvp_readiness_summary.json` and `sd_mvp_action_queue.json`.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.year_review_cli \
  examples/real_data/ha_source_year_review_blocked.json \
  --review-output examples/real_data/artifacts/ha_source_year_review_blocked.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_year_review.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Henan source year review is blocked with no candidate years, no official year
  evidence, no reviewer, and no registry update permission.
- Evidence inventory includes the blocked year review as required no-write
  evidence.
- Current readiness remains blocked for real snapshot planning.

Rollback:

- Remove `backend/data_pipeline/sources/year_review.py` and
  `backend/data_pipeline/sources/year_review_cli.py`.
- Remove source year review examples and artifacts.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh `sd_mvp_readiness_summary.json` and `sd_mvp_action_queue.json`.
- Remove this Phase 150 section.

## Phase 151. Source Year Review Coverage Report

Goal: make missing priority province dataset-year review packets visible before
any source registry year update plan can be prepared.

- [x] Add `backend.data_pipeline.sources.year_review_coverage` and CLI.
- [x] Add tests proving the report stays blocked when review packets are
      missing or not ready.
- [x] Generate
      `examples/real_data/artifacts/priority_source_year_review_coverage_report.json`.
- [x] Add the coverage report artifact to evidence inventory defaults.
- [x] Document that this report does not mutate `sources.json`.
- [x] Refresh `sd_mvp_readiness_summary.json` and `sd_mvp_action_queue.json`.

Validation:

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 -m backend.data_pipeline.sources.year_review_coverage_cli \
  examples/real_data/artifacts/priority_source_coverage_report.json \
  --artifacts-dir examples/real_data/artifacts \
  --report-output \
  examples/real_data/artifacts/priority_source_year_review_coverage_report.json
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_source_year_review_coverage.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_artifacts.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_evidence_inventory.py
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  python3 tests/test_data_pipeline_readiness_summary.py
```

Current verification status:

- Priority source year review coverage is blocked: 7 priority provinces need
  dataset-year review, Henan has a blocked packet, and 6 provinces still have
  no packet.
- Evidence inventory includes the coverage report as required no-write
  evidence.
- Current readiness remains blocked for real snapshot planning.

Rollback:

- Remove `backend/data_pipeline/sources/year_review_coverage.py` and
  `backend/data_pipeline/sources/year_review_coverage_cli.py`.
- Remove `priority_source_year_review_coverage_report.json`.
- Remove the artifact from evidence inventory defaults, docs, and tests.
- Refresh `sd_mvp_readiness_summary.json` and `sd_mvp_action_queue.json`.
- Remove this Phase 151 section.

## First Pilot Recommendation

Use Shandong as the first province unless the user chooses otherwise. Reasons:

- It is a high-demand consulting province.
- The current product examples already include Shandong-style user prompts.
- The new-gaokao `综合` category exercises existing subject-type logic.

Pilot scope:

- Province: Shandong
- Years: 2024 and 2025 if available from official sources
- Universities: 10 to 20 high-interest schools
- Datasets: admission scores first, enrollment plans second

## Review Gates

Do not proceed to the next gate without review:

- Gate A: contracts and quality report shape reviewed.
- Gate B: lineage schema reviewed before migration is added.
- Gate C: pilot source and license/citation notes reviewed before real data is
  placed under raw storage.
- Gate D: Agent source envelope reviewed before tool response changes.

## Known Risks

- Official sites may publish PDFs with inconsistent table layouts.
- Source licensing/citation rules may vary by provider.
- Existing seed data may conflict with pilot real data.
- Current Alembic environment imports only part of the model set and should be
  checked before adding new schema.
- The worktree is currently detached because branch creation was blocked by
  sandbox permissions.
- `__pycache__` files were generated by local compile checks and remain
  untracked because deletion approval failed earlier.
