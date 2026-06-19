# Real Data Pilot Examples

This directory contains synthetic examples for the real-data MVP pipeline.

They are only flow samples. They are not reviewed official data, and they must
not be treated as production admissions data.

Each example row includes synthetic `review` metadata and enables
`quality_config.require_review_metadata=true`. For a real pilot, replace those
fields with the actual extractor, reviewer, review date, and evidence notes.

## Files

| Path | Purpose |
|------|---------|
| `sd_official_sample_intake_template.json` | Template for reviewed official intake |
| `sd_official_sample_intake_reviewed_example.json` | Synthetic intake packet that passes review |
| `synthetic_official_sample_intake_reviewed_example.json` | Synthetic intake after approved planning |
| `synthetic_snapshot_pilot_rows.json` | Synthetic parser rows for approved source/snapshot chain |
| `sd_pilot_bundle.json` | Full bundle example for admission scores |
| `sd_plan_pilot_bundle.json` | Full bundle example for enrollment plans |
| `sd_snapshot_pilot_rows.json` | Rows-only bundle for `--snapshot-dir` mode |
| `sd_tool_response_with_sources.json` | Synthetic sourced tool response for answer policy review |
| `source_review_approval_template.json` | Template for separate source review approval |
| `source_review_approval_reviewed_example.json` | Synthetic source approval example |
| `synthetic_reviewed_sources_registry.json` | Synthetic temporary registry for passing source chain smoke |
| `synthetic_approved_sources_registry.json` | Synthetic temporary registry for passing snapshot planning |
| `source_registry_patch_approval_reviewed_example.json` | Synthetic registry patch approval example |
| `sd_source_review_approval_candidate.json` | Candidate source review draft for Shandong |
| `source_usage_review_template.json` | Template for usage/citation review before source approval |
| `source_year_review_template.json` | Template for official dataset year review before registry year updates |
| `ha_source_year_review_blocked.json` | Blocked Henan dataset-year review input |
| `sd_source_usage_review_blocked.json` | Blocked source usage/citation review input |
| `source_usage_review_reviewed_example.json` | Synthetic passing source usage review input |
| `source_registry_patch_approval_template.json` | Template for registry patch approval |
| `canonical_loader_run_record_template.json` | Template for post-loader run evidence |
| `agent_visibility_approval_template.json` | Template for separate Agent visibility approval |
| `snapshots/sd_pilot_2025_001/manifest.json` | Local raw snapshot manifest |
| `snapshots/sd_pilot_2025_001/files/manual-sample.csv` | Synthetic raw file |
| `snapshots/synthetic_snapshot_2025_001/manifest.json` | Synthetic snapshot manifest for no-write parser smoke |
| `artifacts/sd_source_audit.json` | Synthetic source audit artifact |
| `artifacts/sd_source_snapshot_planning_blocked.json` | Snapshot planning blocked |
| `artifacts/source_snapshot_planning_approved_example.json` | Synthetic snapshot planning ready review |
| `artifacts/priority_source_coverage_report.json` | Priority province source coverage report |
| `artifacts/priority_source_coverage_action_queue.json` | Human action queue for priority source coverage gaps |
| `artifacts/priority_source_year_review_coverage_report.json` | Coverage report for priority dataset-year review packets |
| `artifacts/ha_source_year_review_blocked.json` | Blocked Henan dataset-year review |
| `artifacts/sd_source_usage_review_blocked.json` | Blocked source usage/citation review |
| `artifacts/source_usage_review_reviewed_example.json` | Synthetic passing source usage review |
| `artifacts/source_usage_to_approval_chain_smoke_reviewed_example.json` | Synthetic usage-to-approval chain smoke |
| `artifacts/sd_source_review_human_checklist_blocked.json` | Blocked human source checklist |
| `artifacts/sd_source_review_handoff_blocked.json` | Blocked source review handoff |
| `artifacts/sd_source_review_chain_smoke_blocked.json` | Blocked source review chain smoke |
| `artifacts/sd_source_review_approval_candidate_review.json` | Blocked source review |
| `artifacts/source_review_chain_smoke_reviewed_example.json` | Synthetic passing source review chain smoke |
| `artifacts/source_review_chain_smoke_reviewed_example_update_plan.json` | Synthetic passing update plan |
| `artifacts/source_registry_patch_approval_reviewed_example_review.json` | Synthetic passing patch approval review |
| `artifacts/source_registry_patch_preview_reviewed_example.json` | Synthetic passing patch preview |
| `artifacts/source_registry_patch_chain_smoke_reviewed_example.json` | Synthetic passing patch chain |
| `artifacts/source_review_approval_reviewed_example_review.json` | Synthetic approval review |
| `artifacts/source_review_approval_reviewed_example_update_plan_blocked.json` | Synthetic update block |
| `artifacts/sd_source_registry_update_plan_blocked.json` | Blocked registry update plan |
| `artifacts/sd_source_registry_patch_approval_blocked.json` | Blocked patch approval |
| `artifacts/sd_source_registry_patch_preview_blocked.json` | Blocked patch preview |
| `artifacts/sd_source_registry_patch_chain_smoke_blocked.json` | Blocked patch chain |
| `artifacts/source_to_intake_chain_smoke_approved_example.json` | Synthetic source-to-intake chain smoke |
| `artifacts/source_intake_review_approved_example.json` | Synthetic intake review ready after snapshot planning |
| `artifacts/sd_intake_review.json` | Synthetic intake review artifact |
| `artifacts/source_parser_rows_bundle_smoke_approved_example.json` | Synthetic parser smoke for approved source |
| `artifacts/source_quality_smoke_approved_example.json` | Synthetic quality smoke for approved source/snapshot |
| `artifacts/source_to_quality_chain_smoke_approved_example.json` | Synthetic source-to-quality chain smoke |
| `artifacts/sd_parser_rows_bundle_smoke.json` | Parser rows bundle smoke |
| `artifacts/sd_quality_smoke.json` | Quality smoke review |
| `artifacts/sd_snapshot_pilot_audit.json` | Synthetic dry-run audit artifact |
| `artifacts/sd_snapshot_pilot_approval.json` | Synthetic loader approval packet |
| `artifacts/sd_pilot_artifact_manifest.json` | Synthetic evidence manifest |
| `artifacts/sd_answer_source_policy.json` | Synthetic answer source policy review |
| `artifacts/sd_agent_visibility_activation_review.json` | Blocked Agent visibility review |
| `artifacts/sd_loader_run_evidence_templates_blocked.json` | Blocked loader template review |
| `artifacts/sd_example_chain_smoke.json` | Aggregate no-write chain smoke |
| `artifacts/sd_example_chain_smoke_templates_blocked.json` | Template-input blocked smoke |
| `artifacts/sd_mvp_readiness_summary.json` | Current MVP readiness summary |
| `artifacts/sd_mvp_action_queue.json` | Current MVP manual action queue |

The checked-in `artifacts/*.json` files are static review examples. They are not
generated from official data, do not prove a real source was reviewed, and do
not authorize loader execution.

`artifacts/priority_source_coverage_report.json` summarizes the priority
province registry state for Shandong, Henan, Guangdong, Jiangsu, Zhejiang,
Hebei, Sichuan, and Hubei. It only reports registered homepage candidates,
missing years, and missing approved sources; it does not approve any source or
collect data.

`artifacts/priority_source_coverage_action_queue.json` turns those priority
province gaps into no-write human review actions. It keeps snapshot planning
blocked until missing dataset years are reviewed and source approval is
completed for every priority province.

`source_year_review_template.json` and
`artifacts/ha_source_year_review_blocked.json` define the next no-write gate for
missing dataset years. The checked-in Henan example has no reviewed candidate
years or official evidence yet, so it cannot update `sources.json`.

`artifacts/priority_source_year_review_coverage_report.json` summarizes whether
all priority provinces with missing dataset years have year review packets. The
current report remains blocked because only Henan has a blocked packet and
Guangdong, Jiangsu, Zhejiang, Hebei, Sichuan, and Hubei still need review
packets before any source registry year update plan can be prepared.

To inventory these evidence artifacts without importing pydantic contracts or
running any data pipeline step:

```bash
python -m backend.data_pipeline.pilots.evidence_inventory_cli \
  examples/real_data/artifacts
```

The inventory summarizes each artifact's `action`, `passed` value, ready fields,
required-review count, and no-write evidence. Warnings such as missing `action`
fields are review prompts; they do not authorize real data collection or loader
execution.

To summarize current MVP readiness across source planning, aggregate smoke, and
the evidence inventory:

```bash
python -m backend.data_pipeline.pilots.readiness_summary_cli
```

The checked-in summary should stay blocked until the source is reviewed,
snapshot planning is ready, and separate loader / Agent visibility approvals
exist. It reports the synthetic usage-to-approval and source-to-quality chain
signals explicitly, but those signals do not authorize source approval, raw
snapshot creation, loader execution, database writes, or Agent/RAG refresh.

To view the current ordered human action queue:

```bash
python -m backend.data_pipeline.pilots.action_queue_cli
```

The checked-in queue keeps source usage/citation review, reviewer/timestamp,
separate source approval, and source snapshot planning ahead of loader or
Agent visibility approval. Its current state reports synthetic
usage-to-approval and source-to-quality readiness separately from the blocked
real Shandong source review. It also carries `source_review_context` so the
reviewer can see the candidate official page, attachment, upstream artifact
refs, and pending manual action ids in one place. It does not approve the source
or execute any data movement.

The checked-in parser smoke candidate preview carries additive source metadata:
`source_id`, `snapshot_id`, `dataset`, `year`, `source_record_ref`, `confidence`,
and `has_review_metadata`. The checked-in quality smoke also summarizes
`source_metadata` so reviewers can verify source/year/confidence coverage before
loader or Agent visibility discussion.

`sd_official_sample_intake_template.json` is not a dry-run bundle. Use it as a
preparation checklist before turning reviewed official rows into a real bundle.
`sd_official_sample_intake_reviewed_example.json` is a synthetic filled example
that can regenerate the checked-in intake review shape. It is not official data.

## Source Review Precheck

Before preparing rows or snapshots, resolve source review blockers separately.
First review source usage, citation, and redistribution terms:

```bash
python -m backend.data_pipeline.sources.usage_review_cli \
  examples/real_data/source_usage_review_template.json
```

The template is intentionally blocked. A reviewer must fill source id, scope,
official URLs, usage terms, reviewer identity, review time, and an explicit
decision before source approval can proceed.

The source review approval template is disabled by default and should fail until
a human reviewer fills real evidence, including a ready usage/citation review
summary:

```bash
python -m backend.data_pipeline.sources.review_approval_cli \
  examples/real_data/source_review_approval_template.json
```

After a filled approval review passes, generate a no-write registry update plan
to inspect the exact metadata patch before touching `sources.json`:

```bash
python -m backend.data_pipeline.sources.update_plan_cli \
  backend/data_pipeline/sources/sources.json \
  artifacts/real_data/source_review_approval_review.json
```

Before editing `sources.json`, review a separate registry patch approval packet:

```bash
python -m backend.data_pipeline.sources.patch_approval_cli \
  artifacts/real_data/source_registry_update_plan.json \
  examples/real_data/source_registry_patch_approval_template.json
```

The registry patch approval template is also disabled by default. It should
return blocked until a reviewer confirms the planned updates and sets
`allow_source_registry_patch=true`.

After registry patch approval passes, generate a no-write patch preview before
editing `sources.json`:

```bash
python -m backend.data_pipeline.sources.patch_preview_cli \
  backend/data_pipeline/sources/sources.json \
  artifacts/real_data/source_registry_update_plan.json \
  artifacts/real_data/source_registry_patch_approval_review.json
```

The preview prints the patched source entry and does not write the registry.

Run the registry patch chain smoke to check approval and preview together:

```bash
python -m backend.data_pipeline.sources.patch_chain_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  artifacts/real_data/source_registry_update_plan.json \
  artifacts/real_data/source_registry_patch_approval_review.json
```

After the registry source is approved, run snapshot planning review before
preparing any local raw snapshot files:

```bash
python -m backend.data_pipeline.sources.snapshot_planning_cli \
  backend/data_pipeline/sources/sources.json \
  --data-category admission_scores \
  --province 山东 \
  --year 2025
```

The checked-in current-registry output is
`artifacts/sd_source_snapshot_planning_blocked.json`. It intentionally stays
blocked because `sd_exam_authority` is still `candidate`, not approved.

Official intake packets must include the resulting `snapshot_planning_review`.
Intake review is blocked when that review is missing, scope-mismatched, or not
ready.

Run the aggregate smoke to check the whole source precheck chain:

```bash
python -m backend.data_pipeline.sources.review_chain_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  examples/real_data/source_review_approval_template.json
```

The checked-in template should keep returning a blocked review until reviewer,
source URL, citation, category, year, and license evidence are filled. None of
these commands modifies `sources.json`.

`sd_source_review_approval_candidate.json` pre-fills the official candidate
page for the Shandong 2025 first-choice filing table, but it is still blocked:
the official page, attachment, data category, and published year are identified,
but the allow flag, usage/citation review, reviewer, and review time remain
missing. The review output includes `evidence_summary` so reviewers can see
which evidence fields are present without treating the candidate as approved.
It also includes `required_reviews` to list the remaining human-review actions
before registry update planning can proceed.
`sd_source_usage_review_blocked.json` and
`artifacts/sd_source_usage_review_blocked.json` separate the usage/citation
decision from the broader source approval packet. They record the official
copyright notice and keep real-data ingestion blocked until a reviewer
explicitly approves usage and citation terms.
`source_usage_review_reviewed_example.json` and its checked-in artifact show
the positive usage review shape using only a synthetic source id. They do not
approve Shandong or any real source.
`artifacts/source_usage_to_approval_chain_smoke_reviewed_example.json`
connects that synthetic usage review to the synthetic source approval review,
checking source id, category, province, years, ready usage evidence, and
registry update hint continuity. It is still no-write evidence only and does
not approve Shandong or any real source.
`artifacts/sd_source_review_human_checklist_blocked.json` turns those remaining
actions into an explicit manual checklist for the reviewer.
`artifacts/sd_source_review_handoff_blocked.json` summarizes the current
blocked source-review handoff: what a human reviewer must verify next, which
upstream artifacts prove the block, and which no-write actions remain out of
scope.
`artifacts/sd_source_review_chain_smoke_blocked.json` aggregates source scope
audit, source approval review, and registry update planning. It shows the
registry scope is present while approval and update planning remain blocked.
The checked-in
`artifacts/sd_source_review_approval_candidate_review.json` captures that
blocked review state for inventory and readiness summary checks.
`source_review_approval_reviewed_example.json` and its checked-in review
artifact show the positive packet shape using a synthetic source id only. They
do not approve Shandong, do not match a real registry source, and do not
authorize a registry patch.
`synthetic_reviewed_sources_registry.json` and
`artifacts/source_review_chain_smoke_reviewed_example.json` demonstrate the
passing no-write chain when a synthetic source already exists in a temporary
registry input and usage/source approval are ready. They do not modify
`backend/data_pipeline/sources/sources.json` and do not approve any real
source.
`source_registry_patch_approval_reviewed_example.json` and its checked-in
patch approval, preview, and chain smoke artifacts demonstrate the next
synthetic no-write path from ready update plan to patch preview. They show the
planned `reviewed -> approved` status change for the synthetic source, but they
do not execute a registry patch and do not modify `sources.json`.
`synthetic_approved_sources_registry.json` and
`artifacts/source_snapshot_planning_approved_example.json` demonstrate the
next no-write gate after source approval: snapshot planning becomes ready only
when a synthetic approved source covers the requested category, province, and
year. The artifact still does not create raw snapshots or download files.
`synthetic_official_sample_intake_reviewed_example.json` and
`artifacts/source_intake_review_approved_example.json` continue that synthetic
chain into official intake review: the packet carries the approved snapshot
planning summary and becomes `ready_for_snapshot=true`, while still not
creating a raw snapshot or downloading files.
`artifacts/source_to_intake_chain_smoke_approved_example.json` aggregates the
synthetic source review chain, registry patch preview chain, snapshot planning
review, and intake review. It checks source id and scope consistency across
those no-write gates, but still does not execute registry edits, create raw
snapshots, parse rows, or run loaders.
`synthetic_snapshot_pilot_rows.json`,
`artifacts/source_parser_rows_bundle_smoke_approved_example.json`, and
`artifacts/source_quality_smoke_approved_example.json` continue the same
synthetic source/snapshot into parser and quality smoke. They verify candidate
source metadata, confidence, coverage, and review metadata without running the
formal parser contract, formal quality gate, or loader.
`artifacts/source_to_quality_chain_smoke_approved_example.json` aggregates that
same synthetic source-to-intake chain with parser and quality smoke. It checks
source id, snapshot id, dataset, candidate count, and source year continuity
before loader discussion, while still not executing parser, quality, loader,
registry edits, DB writes, seed writes, RAG refresh, or Agent-visible data.
`artifacts/source_review_approval_reviewed_example_update_plan_blocked.json`
proves that the same synthetic source approval remains blocked at registry
update planning because the synthetic source id is not in `sources.json`.
The checked-in
`artifacts/sd_source_registry_update_plan_blocked.json` shows the next registry
update plan also remains blocked while the source review is not ready. It does
not modify `sources.json`.
`artifacts/sd_source_registry_patch_approval_blocked.json` shows the default
registry patch approval template also remains blocked. It does not modify
`sources.json`.
`artifacts/sd_source_registry_patch_preview_blocked.json` shows no patched source
is produced while the update plan and patch approval review remain blocked.
`artifacts/sd_source_registry_patch_chain_smoke_blocked.json` aggregates the
blocked patch approval and preview checks while keeping registry modification
out of scope.

## No-write Dry Run

Run a full bundle dry-run:

```bash
python -m backend.data_pipeline.pilots.cli \
  examples/real_data/sd_pilot_bundle.json
```

Review the synthetic filled intake packet:

```bash
python -m backend.data_pipeline.intake.cli \
  examples/real_data/sd_official_sample_intake_reviewed_example.json
```

Run a local snapshot dry-run and generate review artifacts:

```bash
python -m backend.data_pipeline.pilots.cli \
  --snapshot-dir examples/real_data/snapshots/sd_pilot_2025_001 \
  --audit-output artifacts/real_data/sd_snapshot_pilot_audit.json \
  --approval-output artifacts/real_data/sd_snapshot_pilot_approval.json \
  examples/real_data/sd_snapshot_pilot_rows.json
```

After source audit and dry-run artifacts exist, generate a manifest that ties
the review evidence together:

```bash
python -m backend.data_pipeline.pilots.artifacts_cli \
  --source-audit artifacts/real_data/sd_source_audit.json \
  --intake-review artifacts/real_data/sd_intake_review.json \
  --dry-run-audit artifacts/real_data/sd_snapshot_pilot_audit.json \
  --loader-approval artifacts/real_data/sd_snapshot_pilot_approval.json \
  --rows-bundle examples/real_data/sd_snapshot_pilot_rows.json \
  --snapshot-dir examples/real_data/snapshots/sd_pilot_2025_001 \
  --manifest-output artifacts/real_data/sd_pilot_artifact_manifest.json
```

Both commands are dry-run only:

- no crawler
- no database writes
- no seed data changes
- no RAG or Agent refresh
- no canonical loader execution

The `artifacts/` outputs are review artifacts. The manifest also does not
approve loader execution; it only indexes the evidence that a reviewer should
inspect. Its `artifact_path_issues`, `intake_review_issues`,
`artifact_scope_issues`, and `loader_approval_issues` must all be empty before
loader execution is discussed.
These files should normally stay local or be attached to a review process, not
committed as source data.

After a reviewed sample is available through a tool response, review the
answer-source policy from the local JSON response:

```bash
python -m backend.data_pipeline.lineage.policy_cli \
  examples/real_data/sd_tool_response_with_sources.json \
  --policy-output artifacts/real_data/answer_source_policy.json
```

This is also no-write. It only checks whether the response source summary is
citeable, caution-only, or unsupported for Agent answers.

After a separately approved canonical loader run, record the local run evidence
and review it before Agent/RAG visibility approval:

```bash
python -m backend.data_pipeline.activation.loader_evidence_cli \
  --artifact-manifest artifacts/real_data/sd_pilot_artifact_manifest.json \
  --loader-run-record path/to/canonical_loader_run_record.json \
  --review-output artifacts/real_data/loader_run_evidence_review.json
```

Start from `canonical_loader_run_record_template.json`, but do not treat the
template as evidence. The review must pass before copying its
`loader_run_evidence` object into `agent_visibility_approval`.
The checked-in template-input output is
`artifacts/sd_loader_run_evidence_templates_blocked.json`; it intentionally has
`passed=false`.

Agent/RAG visibility stays blocked until a separate activation approval exists:

```bash
python -m backend.data_pipeline.activation.cli \
  --artifact-manifest artifacts/real_data/sd_pilot_artifact_manifest.json \
  --answer-policy-review artifacts/real_data/sd_answer_source_policy.json \
  --review-output artifacts/real_data/sd_agent_visibility_activation_review.json
```

That command reproduces the checked-in blocked review with
`missing_agent_visibility_approval`. After a separately approved canonical loader
run exists, pass the approval and loader evidence review:

```bash
python -m backend.data_pipeline.activation.cli \
  --artifact-manifest artifacts/real_data/sd_pilot_artifact_manifest.json \
  --answer-policy-review artifacts/real_data/sd_answer_source_policy.json \
  --activation-approval path/to/agent_visibility_approval.json \
  --loader-run-evidence-review artifacts/real_data/loader_run_evidence_review.json \
  --review-output artifacts/real_data/sd_agent_visibility_activation_review.json
```

The checked-in activation review intentionally has
`ready_for_agent_visibility=false` because it has no real
`agent_visibility_approval`. Start from
`agent_visibility_approval_template.json` only after a separately approved
canonical loader run is confirmed. The template defaults to
`allow_agent_visibility=false` and `loader_run_confirmed=false`; do not flip
those fields without human approval.

This repository includes synthetic checked-in artifacts under
`examples/real_data/artifacts/` only to demonstrate the expected evidence-chain
shape. Replace them with freshly generated and reviewed artifacts for a real
Shandong or Henan pilot.

Run the stdlib-only aggregate smoke for the checked-in synthetic chain:

```bash
python -m backend.data_pipeline.pilots.example_chain_smoke_cli \
  --intake examples/real_data/sd_official_sample_intake_reviewed_example.json \
  --artifact-manifest examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --tool-response examples/real_data/sd_tool_response_with_sources.json \
  --parser-smoke-review \
    examples/real_data/artifacts/sd_parser_rows_bundle_smoke.json \
  --quality-smoke-review examples/real_data/artifacts/sd_quality_smoke.json \
  --expected-activation-review \
    examples/real_data/artifacts/sd_agent_visibility_activation_review.json \
  --expect-source-id sd_exam_authority \
  --expect-snapshot-id sd_pilot_2025_001 \
  --expect-dataset admission_scores
```

The checked-in output for this synthetic no-approval path is
`artifacts/sd_example_chain_smoke.json`.
Its top-level `required_reviews` lists the remaining human actions before loader
execution or Agent visibility can be discussed.

After a separately approved canonical loader run, the same aggregate smoke can
also include Agent visibility approval evidence:

```bash
python -m backend.data_pipeline.pilots.example_chain_smoke_cli \
  --intake examples/real_data/sd_official_sample_intake_reviewed_example.json \
  --artifact-manifest examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --tool-response examples/real_data/sd_tool_response_with_sources.json \
  --parser-smoke-review \
    examples/real_data/artifacts/sd_parser_rows_bundle_smoke.json \
  --quality-smoke-review examples/real_data/artifacts/sd_quality_smoke.json \
  --expect-source-id sd_exam_authority \
  --expect-snapshot-id sd_pilot_2025_001 \
  --expect-dataset admission_scores \
  --activation-approval path/to/agent_visibility_approval.json \
  --loader-run-record path/to/canonical_loader_run_record.json
```

`--activation-approval` and `--loader-run-record` must be provided together.
This remains a no-write review; it does not execute the canonical loader or
refresh Agent/RAG visibility.

The checked-in template-input output is
`artifacts/sd_example_chain_smoke_templates_blocked.json`. It intentionally has
`passed=false`, proving the default approval and loader-run templates are not
valid activation evidence.

## Replacing With Reviewed Official Samples

For a real Shandong or Henan pilot:

1. Replace `source` metadata with the reviewed official or authorized source.
2. Replace `manifest.source_url` with the official announcement or download URL.
3. Store the original file under a snapshot `files/` directory.
4. Recompute `files[].sha256` from the original file.
5. Export reviewed worksheet rows as CSV with normalized column names.
6. Convert the CSV into a rows bundle:

```bash
python -m backend.data_pipeline.parsers.tabular_cli \
  path/to/reviewed_rows.csv \
  --dataset admission_scores \
  --output path/to/sd_snapshot_pilot_rows.json
```

7. Confirm row-level `review` metadata is present in the rows bundle.
8. Run dry-run and inspect `review_status`, `blockers`, and `review_notes`.
9. Request separate approval before any canonical loader command is run.
10. Record and review loader run evidence after the approved loader finishes.
11. Request separate Agent/RAG visibility approval before default use.

See `docs/real-data-pilot-review-checklist.md` before preparing real samples.
