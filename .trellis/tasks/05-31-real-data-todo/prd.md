# Real Data MVP for Admission Consulting

## Goal

Build the first auditable real-data foundation for the Zhang Xuefeng AI education
consulting agent. The MVP must make education data traceable from an official or
authorized source through raw snapshots, parsed canonical rows, quality gates,
and Agent/tool responses that can cite source, year, and confidence.

This phase is planning and foundation work. It must avoid large-scale crawlers
until source contracts, snapshot contracts, lineage, and quality checks are in
place.

## Confirmed Facts

- The current canonical database uses SQLite + SQLAlchemy models for schools,
  majors, admission scores, enrollment plans, and subject rankings.
- Current seed data lives under `backend/seeds/` as JSON files, with import
  scripts for basic, extended, and full seed loads.
- Current Agent tools in `backend/tools/definitions.py` return structured facts
  but do not provide uniform source metadata, snapshot identifiers, or confidence.
- Current quality checks in `backend/seeds/data_quality.py` validate basic
  required fields, enums, and ranges, but do not validate provenance, freshness,
  coverage, or cross-source conflicts.
- Existing docs already identify the need for source labeling, confidence, and
  freshness warnings.
- The existing Trellis task is in planning status.

## Requirements

### R1. Data Source Registry

Define a source registry contract for official or authorized education data
sources. Each source entry must include:

- stable `source_id`
- source name
- source type, such as ministry, provincial exam authority, university, ranking
  provider, employment report, or licensed provider
- homepage or dataset URL
- data categories covered
- years and provinces covered when known
- trust score
- update frequency
- collection method
- license or usage notes
- owner/reviewer notes

### R2. Raw Snapshot Contract

Define a raw snapshot storage contract that allows manually downloaded official
files to be tracked before any crawler exists.

Each snapshot must include a manifest with:

- `snapshot_id`
- `source_id`
- dataset name
- source URL
- published year
- collected timestamp
- checksum
- file list
- collector or manual-ingest version
- license note

### R3. Canonical Row and Lineage Contract

Define how parsed records connect back to their raw snapshot and source. The MVP
must support lineage for at least admission scores and enrollment plans without
requiring an immediate rewrite of existing business tables.

### R4. Quality Gate

Define quality checks that must pass before data is allowed into Agent-facing
queries:

- required canonical fields
- stable uniqueness keys
- score, rank, plan count, year, and tuition ranges
- source metadata completeness
- source freshness and published year checks
- duplicate and conflict detection for the same school/province/year/batch
- coverage report by data category, province, year, and source
- confidence calculation or assignment

### R5. Collector Directory Design

Design a backend data pipeline module structure that supports future collectors,
but MVP implementation must start with manual snapshot ingestion or stubs. It
must not start large-scale crawling.

### R6. First Data Source Scope

Recommend the first data sources and a pilot scope. The pilot must be small
enough to verify manually and large enough to test the full pipeline contract.

Recommended pilot:

- 1 province, such as Shandong or Henan
- 2 recent years
- 10 to 20 high-interest universities
- first datasets: admission scores and enrollment plans

### R7. Agent Source Metadata

Plan for Agent tools to return source metadata in a consistent shape so final
answers can include source, year, confidence, and freshness warnings.

### R8. No Uncontrolled Crawling

The MVP must not start real crawlers, install scraping dependencies, or collect
large datasets until the registry, snapshot, lineage, and quality contracts are
reviewed.

## Acceptance Criteria

- [ ] `prd.md` documents goals, requirements, non-goals, and acceptance criteria.
- [ ] `design.md` defines the source registry, snapshot manifest, lineage model,
      quality gate, data flow, and module boundaries.
- [ ] `implement.md` provides an ordered implementation checklist with validation
      commands and rollback points.
- [ ] The plan identifies first pilot data sources and a bounded pilot scope.
- [ ] The plan explicitly keeps large-scale crawler implementation out of MVP.
- [ ] The plan describes how Agent tool results will eventually include source,
      year, confidence, and freshness metadata.
- [ ] The plan is compatible with the existing SQLAlchemy/Alembic/SQLite stack.

## Out of Scope

- Building or running large-scale crawlers.
- Installing new dependencies.
- Importing new real datasets into the database.
- Replacing SQLite with PostgreSQL.
- Rewriting existing Agent tools.
- Modifying frontend source panels or UI components.
- Purchasing or integrating licensed data-provider APIs.

## Open Questions

- Which pilot province should be first: Shandong, Henan, or another province?
- Should source confidence be stored as a manually reviewed score first, or
  calculated from source type plus freshness?
- Should lineage be represented through side tables only, or should high-value
  canonical tables also get direct nullable source columns later?

## Notes

- This is a complex task. It needs `design.md` and `implement.md` before moving
  from planning to implementation.
- The first implementation should prioritize auditability over data volume.
