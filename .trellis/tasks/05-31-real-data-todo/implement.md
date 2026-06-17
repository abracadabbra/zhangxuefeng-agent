# 真实高考数据 MVP 执行计划

## Phase 0: Planning Gate

- [x] Review `prd.md` and `design.md` with the user.
- [x] Confirm pilot province remains 山东.
- [x] Confirm first implementation writes only isolated artifacts, not production DB.
- [x] Submit a fresh approval packet before any code, file download, parser, DB, seed, or Agent tool edit.

## Phase 1: Source Registry and Snapshot Contract

- [x] Create a source metadata fixture for the 山东 2025 official投档表.
- [x] Register 河南 2025 本科批平行投档分数线 as the next official source candidate for score-bearing pilot data.
- [x] Define snapshot id and raw file hash handling.
- [x] Support reviewed manual/browser snapshots for official dynamic source views without adding a scraper.
- [x] Validate that every source batch has source URL, province, year, authority, captured time, and snapshot id.

Verification:

- Unit test rejects source metadata missing source URL, year, snapshot id, or hash.
- Manual evidence links back to the official 山东省教育招生考试院 page.
- Unit test records that the 河南 source page is official metadata only and has no automatic snapshot attachment yet.
- Unit test proves a 河南 datacenter view can be represented as a reviewed manual snapshot with URL, hash, operator, and timezone-aware capture time.

Rollback:

- Remove only the new isolated source metadata files and tests.

## Phase 2: Pilot Parser on Small Sample

- [x] Parse only a small selected subset from the 山东 official table shape.
- [x] Preserve raw row number and raw values.
- [x] Normalize to canonical candidate fields without writing production tables.
- [x] Prove the parser boundary against the actual legacy `.xls` snapshot after approving an Excel reader dependency or extractor.
- [x] Add a parser-level schema fit report so official sources missing canonical required fields are blocked before staging.

Verification:

- Unit test proves every canonical candidate includes `source_batch_id`, `snapshot_id`, and `raw_row_number`.
- Unit test proves parsed candidate count equals selected sample count.
- Unit test proves missing/invalid required fields stop before quality gate and result in blocked output.
- Unit test proves the actual 山东 `.xls` schema blocks the current admission-score contract because `min_score` is absent.

Rollback:

- Remove parser and isolated sample artifact.

## Phase 3: Quality Gate

- [x] Implement required field checks.
- [x] Implement score, rank, year, and plan count range checks.
- [x] Implement duplicate canonical key detection.
- [x] Implement optional cross-source/cross-snapshot conflict detection against reviewed reference candidates.
- [x] Implement source authority, snapshot hash, snapshot/source-page lineage, and snapshot publish-time order checks.
- [x] Implement coverage, freshness, and confidence summaries.
- [x] Persist structured warning issues in quality reports and dry-run summaries.
- [x] Emit row-level warning issues for medium-confidence candidates.

Verification:

- Tests cover pass, warning, and blocked reports.
- Tests cover missing field, out-of-range score, duplicate key, cross-source conflict, missing hash, disallowed source type, snapshot/source-page mismatch, snapshot captured before publish, and low confidence.
- Tests cover warning issue details for coverage gaps in both warning and blocked summaries.
- Tests cover row-level warning issue details for medium-confidence candidates.
- Blocked report prevents any staging write.

Rollback:

- Remove quality gate module and report artifacts.

## Phase 4: Isolated Staging Artifact

- [x] Write passing canonical candidates to an isolated staging artifact only after quality gate.
- [x] Write reviewed raw rows to a separate audited artifact before canonical staging.
- [x] Include quality report alongside canonical candidates.
- [x] Read staging artifacts back through a typed validator before any future consumer uses them.
- [x] Add an isolated reviewed-row pilot runner for `schema → normalize → quality → staging → citation` without DB/seed/Agent writes.
- [x] Add a reviewed-row artifact runner so real small-sample pilots start from a validated raw artifact.
- [x] Reject reviewed raw rows artifacts with duplicate `raw_row_number` values so row lineage remains unique.
- [x] Keep existing seed JSON and DB unchanged.

Verification:

- `tests/test_real_data_staging.py` confirms blocked reports cannot be staged, warning reports can be staged, and artifact paths stay outside `backend/seeds/`.
- No pilot command or DB write path exists in this phase; staging writes only to the caller-provided isolated directory.
- `tests/test_real_data_staging.py` confirms quality report, snapshot, candidates, and citation metadata reference the same snapshot id.
- `tests/test_real_data_staging.py` confirms staged artifacts can be loaded through a shared typed reader, default overwrite is rejected, and tampered blocked/citation payloads are rejected.
- `tests/test_real_data_pilot.py` confirms reviewed raw rows can run to staging/citation and schema-blocked rows do not write artifacts.
- `tests/test_real_data_pilot.py` confirms reviewed raw rows artifacts load back through a typed validator and reject tampered schema reports or row lineage mismatches.
- `tests/test_real_data_pilot.py` confirms reviewed raw rows artifacts reject duplicate raw row numbers before normalization or staging.
- `tests/test_real_data_pilot.py` confirms reviewed raw rows artifacts can launch the pilot and tampered raw artifacts are rejected before staging writes.
- `tests/test_real_data_pilot.py` confirms reviewed-row quality reports preserve raw, parsed, and passed record counts across pass and schema-blocked paths.

Rollback:

- Delete isolated staging artifacts.

## Phase 5: Agent Citation Contract

- [x] Define an Agent-facing citation payload shape.
- [x] Demonstrate citation metadata from staged candidate records without changing current Agent tools.
- [x] Add an isolated read-only projection from validated staging artifacts to Agent-facing citation records.
- [x] Add an isolated read-only adapter that queries validated staging artifacts in memory without extending existing database tools or Agent tools.
- [x] Add an isolated staging manifest so multiple validated artifacts can be discovered and queried without trusting caller-provided loose paths.
- [x] Include quality report ids in staging manifest entries so approvals bind to a concrete quality gate report.
- [x] Add an isolated pilot bundle runner that turns one reviewed raw rows artifact into staging + manifest + queryable citation records without touching production paths.
- [x] Add an isolated dry-run CLI for reviewed artifact pilot bundles so manual pilots produce structured audit summaries without production writes.
- [x] Add a documented 河南 reviewed-row dry-run fixture so manual pilots can be repeated with stable audit evidence.
- [x] Extend the dry-run CLI summary with coverage, freshness, confidence, and issue categories for manual quality review.
- [x] Include source, snapshot, and quality report id in dry-run summaries even when quality blocks downstream writes.
- [x] Add a manual approval artifact contract so a reviewed staging manifest can record reviewer, reviewed time, checklist, decision, and citation count before any future consumption.
- [x] Add isolated CLI commands to write and verify manual approval artifacts for validated staging manifests.
- [x] Add approval-gated read-only querying so future consumers can require verified manual approval before reading citation records.
- [x] Add an isolated approval-gated CLI query so operators can inspect cited records only after manual approval is verified.
- [x] Add an isolated approval-gated audit CLI so operators can inspect approval, manifest, quality, and citation evidence in one reviewed summary.
- [x] Include structured warning issues in approval-gated audit summaries.
- [x] Include snapshot hash, capture time, and operator in approval-gated audit summaries.
- [x] Require reviewer notes when approving manifests that contain warning-quality artifacts.
- [x] Prove warning approval audits expose both reviewer notes and structured warning issues.
- [x] Add optional reference manifest support so dry-runs can block cross-source/cross-snapshot conflicts against already validated staging data.
- [x] Decide that the next production integration step should be a separately approved Agent-tool adapter task.

Verification:

- Unit test or fixture output includes `source`, `source_url`, `snapshot_url`, `year`, `snapshot`, `confidence`, and `source_batch_id`.
- `tests/test_real_data_staging.py` confirms projected records include admission fields, official source metadata, snapshot id, confidence, and raw row lineage without touching current Agent tools.
- `tests/test_real_data_staging.py` confirms citation readback rejects tampered snapshot URLs, so future Agent projections keep the official page URL and exact reviewed snapshot/data-view URL distinct.
- `tests/test_real_data_adapter.py` confirms the read-only adapter filters validated staging records by province, year, school, major keyword, batch, subject type, and score range while preserving citation metadata.
- `tests/test_real_data_adapter.py` confirms the adapter reuses typed staging readback and rejects tampered artifacts before returning records.
- `tests/test_real_data_manifest.py` confirms manifest write/read revalidates each staging artifact, rejects duplicate or tampered entries, and exposes trusted artifact paths for read-only querying.
- `tests/test_real_data_manifest.py` confirms manifest entries include quality report ids and reject tampered report ids.
- `tests/test_real_data_adapter.py` confirms the adapter can query multiple trusted artifacts via a manifest while preserving citation metadata.
- `tests/test_real_data_bundle.py` confirms a reviewed raw rows artifact can run through quality, staging, manifest registration, and manifest-backed citation query as one isolated bundle.
- `tests/test_real_data_bundle.py` confirms schema-blocked or tampered reviewed raw artifacts stop before staging/manifest writes.
- `tests/test_real_data_cli.py` confirms the dry-run CLI emits structured pass/blocked summaries and rejects tampered reviewed raw artifacts without downstream writes.
- `tests/test_real_data_cli.py` confirms the documented fixture in `tests/fixtures/real_data/henan_reviewed_rows_sample.json` runs through the CLI and returns stable citation metadata.
- `tests/test_real_data_cli.py` confirms the dry-run CLI exposes coverage, freshness, confidence summary, and categorized quality issues for both pass and blocked cases.
- `tests/test_real_data_cli.py` confirms dry-run summaries expose source, snapshot, and quality report id for both pass and blocked results.
- `tests/test_real_data_approval.py` confirms manual approval artifacts require timezone-aware review time, require all checklist items for approved decisions, revalidate referenced manifests, and reject stale/tampered approval records.
- `tests/test_real_data_cli.py` confirms approval CLI commands can write and verify manual approval artifacts, and reject approved decisions with incomplete checklist.
- `tests/test_real_data_adapter.py` confirms approval-gated querying returns records only for verified `approved` artifacts and blocks rejected/tampered approvals.
- `tests/test_real_data_cli.py` confirms the approval-gated query CLI returns citation records only for verified approved artifacts and blocks rejected approvals.
- `tests/test_real_data_cli.py` confirms the approval-gated audit CLI summarizes approval, manifest, quality, and citation evidence, and blocks rejected approvals.
- `tests/test_real_data_cli.py` confirms approval-gated audit summaries include quality report ids for each artifact.
- `tests/test_real_data_cli.py` confirms approval-gated audit summaries include structured warning issue fields.
- `tests/test_real_data_cli.py` confirms approval-gated audit summaries expose snapshot hash, capture time, and operator for each artifact.
- `tests/test_real_data_approval.py` and `tests/test_real_data_cli.py` confirm approved warning manifests require reviewer notes before approval artifacts are written.
- `tests/test_real_data_cli.py` confirms warning approval audit summaries expose reviewer notes next to structured warning issue evidence.
- `tests/test_real_data_bundle.py` and `tests/test_real_data_cli.py` confirm reference manifests are revalidated and cross-source conflicts block downstream staging/manifest writes.
- `.trellis/tasks/05-31-real-data-todo/dry-run.md` documents the manual dry-run command, success checks, failure checks, and isolation boundary.

Rollback:

- Remove citation fixture or adapter-only prototype.

## Quality Commands To Reuse Later

Existing relevant commands:

- `python -m backend.seeds.import_cli --dataset basic --dry-run`
- `pytest tests/test_seed_import_cli.py`
- `pytest tests/test_tool_definitions.py`

Future pilot implementation should add focused tests for the real-data modules instead of relying only on existing seed import tests.

Current focused checks:

- `./.venv/bin/pytest tests/test_real_data_source_registry.py tests/test_real_data_quality_gate.py tests/test_real_data_parser.py`
- `./.venv/bin/ruff check backend/real_data tests/test_real_data_source_registry.py tests/test_real_data_quality_gate.py tests/test_real_data_parser.py`
- `./.venv/bin/mypy backend/real_data`

Real snapshot check:

- `/tmp/sdzk_2025_regular_batch_1.xls` SHA-256:
  `9fdc37c96d3ddceec0f62da7021f8ae01f3cbc6eac7d3698c2efcd202f0c87f1`
- The 山东 official `.xls` has columns `专业代号及名称`, `院校代号及名称`, `投档计划数`, and `最低位次`.
- It does not contain `最低分`/`min_score`, so the current canonical admission-score contract correctly blocks canonical candidate creation for real rows instead of inventing score data.
- The 河南 official source page links score-bearing physical/history本科批 views, but direct datacenter requests return an anti-automation challenge in this environment. Next parser work should start from an approved browser/manual snapshot, not a blind scraper.

## Risk Notes

- The current worktree has many unrelated uncommitted changes. Future implementation must avoid broad formatting or repository-wide commands that could blur ownership.
- Official data files may use legacy Excel formats; parser choice should be proven on the actual snapshot before broad implementation.
- The first implementation should keep artifacts isolated until DB schema changes and Agent tool changes are separately approved.
