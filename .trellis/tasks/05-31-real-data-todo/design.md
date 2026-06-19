# Real Data MVP Design

## Purpose

The MVP introduces an auditable data pipeline foundation before adding crawlers
or large datasets. It keeps existing query APIs and Agent tools stable while
adding the contracts needed to answer: where did this fact come from, when was
it collected, how fresh is it, and how confident should the Agent be?

## Current Architecture Summary

Current data flow:

```text
backend/seeds/*.json
  -> backend/seeds/import_*.py
  -> SQLAlchemy canonical tables
  -> CRUD query functions
  -> FastAPI routers and Agent tools
  -> RAG/Agent answer
```

Current limitations:

- Seed JSON records do not have uniform source metadata.
- Import scripts load directly into canonical tables.
- Quality checks validate shape and ranges, but not provenance or coverage.
- Agent tools return facts without a consistent source envelope.

## Target MVP Architecture

```text
Official or authorized source
  -> source registry
  -> raw snapshot + manifest
  -> parser
  -> canonical row candidates
  -> quality gate
  -> canonical DB + lineage records
  -> RAG index refresh
  -> Agent tool responses with sources
```

## Module Boundaries

Recommended package:

```text
backend/data_pipeline/
  __init__.py
  sources/
    registry.py
    sources.yaml or sources.json
  raw_store/
    manifest.py
    checksums.py
  collectors/
    manual.py
    base.py
  parsers/
    base.py
    admission_scores.py
    enrollment_plans.py
  quality/
    checks.py
    report.py
  lineage/
    models.py
    service.py
  loaders/
    admission_scores.py
    enrollment_plans.py
```

MVP implementation should start with manual snapshot ingestion. Collector
classes can exist as interfaces or stubs, but should not fetch remote pages.

## Source Registry Contract

Each source entry should use a stable `source_id` and explicit review metadata.

```json
{
  "source_id": "moe_school_list",
  "name": "Ministry of Education Higher Education Institution List",
  "source_type": "ministry",
  "homepage_url": "https://example.edu.cn",
  "data_categories": ["schools"],
  "coverage": {
    "provinces": ["全国"],
    "years": [2026]
  },
  "trust_score": 1.0,
  "update_frequency": "annual",
  "collection_method": "manual_download",
  "license_note": "Official public data; verify citation requirements.",
  "review_status": "candidate",
  "notes": ""
}
```

Recommended first source types:

- Ministry-level official data for school identity.
- Provincial exam authority data for admission scores and enrollment plans.
- University admission office pages for school-specific plans.
- University employment quality reports for later employment data.
- Ranking providers only after usage/citation rules are confirmed.

## Raw Snapshot Contract

Suggested path:

```text
data/raw/<source_id>/<dataset>/<year>/<snapshot_id>/
  manifest.json
  files/
    original.*
```

Manifest fields:

```json
{
  "snapshot_id": "sd_exam_2025_scores_20260606_001",
  "source_id": "sd_exam_authority",
  "dataset": "admission_scores",
  "source_url": "https://example.gov.cn/file.pdf",
  "published_year": 2025,
  "collected_at": "2026-06-06T00:00:00+08:00",
  "collector": "manual",
  "collector_version": "0.1.0",
  "files": [
    {
      "path": "files/original.pdf",
      "sha256": "<checksum>",
      "content_type": "application/pdf"
    }
  ],
  "license_note": "Manual review required before production use."
}
```

## Canonical Candidate Contract

Parsers should output candidate rows before loading. Candidate rows should avoid
database sessions and remain easy to unit test.

Admission score candidate:

```json
{
  "entity_type": "admission_score",
  "natural_key": {
    "school_name": "Example University",
    "major_name": null,
    "province": "山东",
    "year": 2025,
    "batch": "本科批",
    "subject_type": "综合"
  },
  "values": {
    "min_score": 620,
    "avg_score": null,
    "max_score": null,
    "min_rank": 12000,
    "plan_count": null
  },
  "source": {
    "snapshot_id": "sd_exam_2025_scores_20260606_001",
    "source_record_ref": "page=12,row=8",
    "confidence": 0.95
  }
}
```

Enrollment plan candidate:

```json
{
  "entity_type": "enrollment_plan",
  "natural_key": {
    "school_name": "Example University",
    "major_name": "Computer Science and Technology",
    "province": "山东",
    "year": 2025
  },
  "values": {
    "plan_count": 20,
    "subject_requirement": "物理+化学",
    "batch": "本科批",
    "duration": 4,
    "tuition": 6000
  },
  "source": {
    "snapshot_id": "sd_exam_2025_plans_20260606_001",
    "source_record_ref": "sheet=plans,row=42",
    "confidence": 0.95
  }
}
```

## Lineage Model

Prefer side tables for MVP to avoid high-risk edits across all existing query
paths.

Proposed tables:

- `data_sources`: source registry rows promoted into DB.
- `data_snapshots`: raw snapshot metadata and checksum status.
- `data_lineage_records`: maps canonical records or natural keys to snapshots.

Lineage record shape:

```text
id
entity_type
entity_id nullable
natural_key_json
snapshot_id
source_record_ref
parser_name
parser_version
quality_status
confidence
created_at
```

This allows an MVP loader to first link by natural key and later backfill
`entity_id` after canonical upsert.

## Quality Gate

Quality checks should be grouped into severity levels:

- `error`: blocks load.
- `warning`: allows load but lowers confidence or requires report review.
- `info`: coverage and freshness statistics.

Blocking checks:

- Missing `source_id`, `snapshot_id`, source URL, or checksum.
- Missing canonical natural-key fields.
- Invalid year, score, rank, plan count, duration, or tuition ranges.
- Duplicate candidate rows with conflicting values inside the same snapshot.
- Unknown school or major when the loader is configured not to create reference
  entities.

Warning checks:

- Source is older than the configured freshness window.
- Cross-source conflict for the same natural key.
- Low coverage compared with expected pilot scope.
- Source trust score below the Agent default-answer threshold.

## Confidence and Freshness

Initial confidence can be deterministic:

```text
confidence = source_trust_score - freshness_penalty - conflict_penalty
```

Suggested source trust defaults:

- Ministry or provincial exam authority: 1.00
- Government statistical report: 0.95
- University official site/report: 0.90
- Licensed third-party report: 0.85
- Mainstream media: 0.70
- Forum or user-generated content: 0.30

Freshness penalty can start simple:

- Same or previous admission cycle: 0.00
- 2 years old: 0.10
- 3+ years old: 0.20 or warning

## Agent Tool Source Envelope

Future tool responses should include a consistent `sources` array:

```json
{
  "status": "success",
  "items": [],
  "sources": [
    {
      "source_id": "sd_exam_authority",
      "name": "Shandong Education Admissions Examination Institute",
      "source_url": "https://example.gov.cn/file.pdf",
      "published_year": 2025,
      "snapshot_id": "sd_exam_2025_scores_20260606_001",
      "confidence": 0.95,
      "freshness": "current"
    }
  ]
}
```

The Agent prompt already asks for data citation, so the main missing piece is
tool-level metadata.

## Compatibility

- Keep SQLite and SQLAlchemy for MVP.
- Use Alembic for any schema additions.
- Preserve existing seed import scripts until the pipeline proves itself.
- Do not change existing API response contracts in the first foundation step
  unless source metadata is behind additive fields.
- Keep RAG refresh as a later step after canonical data is quality-gated.

## Rollback Strategy

- Planning-only changes can be reverted by restoring Trellis task files.
- Pipeline code can be removed without affecting existing seed imports if it is
  added under `backend/data_pipeline/`.
- Schema additions should be isolated to source/snapshot/lineage tables.
- Agent response source metadata should be additive and removable without
  breaking existing consumers.
