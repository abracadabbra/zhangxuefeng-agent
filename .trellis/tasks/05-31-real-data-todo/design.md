# 真实高考数据 MVP 设计

## Objective

用山东省官方小样本数据建立真实数据进入系统的最小闭环。设计目标是让数据在进入查询路径前先具备可追踪、可校验、可引用能力，同时避免破坏现有 seed 数据、数据库结构和 Agent 工具。

## Boundaries

本阶段只定义合同和 pilot 实施边界。后续实现应优先写入隔离的真实数据工作区，例如 `data/real_data/` 或等价 staging 目录；未通过审批前不修改 `backend/seeds/`、ORM 模型、生产数据库和 Agent 工具。

## Pilot Source

默认 pilot 选择山东，因为山东省教育招生考试院 2025 年普通类常规批第 1 次志愿投档情况表具有明确官方页面和 `.xls` 附件，适合做“官方来源 → 文件快照 → 原始行 → canonical 候选”的链路验证。

候选来源信息：

- source_name: 山东省教育招生考试院
- province: 山东
- year: 2025
- source_type: official_exam_authority
- document_title: 山东省2025年普通类常规批第1次志愿投档情况表
- source_url: https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996
- raw_format: xls

河南省教育考试院 2025 本科批平行投档分数线可作为下一省份候选。

河南候选来源信息：

- source_name: 河南省教育考试院
- province: 河南
- year: 2025
- source_type: official_exam_authority
- document_title: 河南省2025年普通高招本科院校平行投档分数线
- source_url: https://gaokao.haedu.cn/517/518/519/2025/1207/150720.html
- linked_data_views:
  - https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?yearTip=2025&pc=1&kl=5
  - https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?yearTip=2025&pc=1&kl=1
- access_note: datacenter direct requests return an anti-automation challenge in this environment; capture must be handled as a reviewed manual/browser snapshot before parser integration.
- snapshot_note: because the score-bearing data view is dynamic and has no static attachment in the source page, a reviewed manual/browser snapshot must record `raw_file_url`, `raw_file_name`, `raw_file_sha256`, `captured_at`, and `operator` before any rows are parsed.

实际快照验证结论：

- 该山东 `.xls` 是 legacy OLE2 Excel 文件，适合验证真实官方文件的 snapshot、hash、sheet/header 读取和 raw row lineage。
- 该表实际列为 `专业代号及名称`、`院校代号及名称`、`投档计划数`、`最低位次`，不包含 `最低分`。
- 因此它不能单独产出当前 admission-score canonical 合同要求的 `min_score`；真实行应在解析阶段被标记为缺少 `min_score`，不得伪造分数进入 quality gate 或 staging。
- Parser 边界应先输出 header/schema fit report，记录 observed columns、matched canonical fields、missing required fields；对于该山东快照，schema report 应为 `blocked` 且 `missing_required_fields = ("min_score",)`。
- 后续若要跑通真实行的 pass → staging 闭环，需要补一个含最低分的官方来源，或单独审批扩展 canonical 合同以支持“位次/计划”类投档记录。
- 河南 2025 本科批平行投档分数线是下一步 pass → staging 的更合适候选，但必须先取得可审计快照和字段表头，不能仅凭入口链接写入 canonical 数据。

## Data Contracts

### Source Batch

`SourceBatch` 描述一个官方或授权数据发布批次。

Required fields:

- `source_batch_id`: stable id, e.g. `sd-2025-regular-batch-1投档`
- `source_name`: official or authorized publisher
- `source_url`: official page URL
- `province`: province covered by the data
- `year`: admission year
- `published_at`: source publish time when available
- `captured_at`: snapshot capture time
- `snapshot_id`: stable snapshot version
- `raw_file_name`: downloaded or manually attached file name
- `raw_file_sha256`: raw file hash
- `license_or_authority`: why the source is acceptable
- `operator`: person or process that captured the snapshot

### Raw Record

`RawRecord` preserves row-level lineage from the source snapshot.

Required fields:

- `source_batch_id`
- `snapshot_id`
- `raw_row_number`
- `raw_columns`
- `raw_values`
- `parse_status`: `parsed`, `warning`, or `blocked`
- `parse_notes`

### Source Schema Report

`SourceSchemaReport` checks whether extracted raw rows fit the selected canonical contract before row normalization.

Required fields:

- `status`: `pass` or `blocked`
- `observed_columns`: headers extracted from the official snapshot
- `required_fields`: canonical fields required for this pilot contract
- `matched_fields`: mapping from canonical field to observed source column
- `missing_required_fields`: required canonical fields not present in the source headers

For the 山东 2025 official `.xls`, this report is expected to block the current admission-score contract because the source has rank and plan columns but no score column.

### Reviewed Raw Rows Artifact

`ReviewedRawRowsArtifact` stores the reviewed small-sample raw rows before canonical staging.

Required fields:

- `schema_version`: `real_data_reviewed_rows.v1`
- `source_page`
- `snapshot`
- `rows`
- `schema_report`

Readback validation must reject artifacts when the snapshot does not match the source page, any row lineage does not match the snapshot, or the stored schema report does not match a fresh schema assessment of the stored rows.

### Canonical Candidate

`CanonicalCandidate` is not production data yet. It is the normalized candidate that must pass quality gate before any DB write.

Required fields for admission score pilot:

- `province`
- `year`
- `school_name`
- `major_or_group_name`
- `batch`
- `subject_type`
- `plan_count`
- `min_score`
- `min_rank`
- `source_batch_id`
- `snapshot_id`
- `raw_row_number`
- `confidence`

Optional fields:

- `school_code`
- `major_code`
- `selection_requirement`
- `tuition`
- `duration`
- `notes`

### Quality Report

`QualityReport` is the gate output.

Required fields:

- `report_id`
- `source_batch_id`
- `snapshot_id`
- `status`: `pass`, `warning`, or `blocked`
- `record_count_raw`
- `record_count_parsed`
- `record_count_passed`
- `field_errors`
- `range_errors`
- `duplicate_conflicts`
- `cross_source_conflicts`
- `coverage_metrics`
- `freshness_result`
- `confidence_summary`
- `blocked_reasons`

For reviewed-row pilots, `record_count_raw` is the number of reviewed raw rows in the input artifact, `record_count_parsed` is the number of canonical candidates produced after schema/parse checks, and `record_count_passed` is zero when the gate blocks staging.

### Agent Citation Metadata

Any future Agent-facing query result derived from real data should carry:

- `source`: human-readable official source name
- `source_url`: official source page URL
- `snapshot_url`: exact raw file or reviewed dynamic data-view URL captured in the snapshot
- `year`
- `snapshot`
- `confidence`
- `source_batch_id`

This extends the existing tool metadata pattern, where current database tools already return logical `source`, `source_type`, and `confidence`.

## Quality Gate

The pilot quality gate should reject or warn before database writes.

Blocking checks:

- Missing required fields.
- Invalid year outside configured pilot year.
- Score outside 0-750.
- Rank less than 1 when present.
- Duplicate canonical key within the same snapshot.
- Conflicting values for the same canonical key across snapshots unless manually resolved.
- Unknown or unofficial source authority.
- Missing snapshot hash.

Warning checks:

- Coverage below pilot target.
- Missing optional code fields.
- Freshness older than expected for the selected admission year.
- Confidence below `high` but above block threshold.
- School or major name requires manual normalization.

Coverage checks for pilot:

- At least the selected sample schools are present.
- Parsed record count matches expected sampled rows.
- Each canonical record has source lineage.

Confidence rules:

- `high`: official source, exact row lineage, required fields complete, no conflicts.
- `medium`: official source with minor normalization warnings.
- `low`: incomplete source or unresolved parsing ambiguity; should not enter Agent-facing result.

## Data Flow

1. Register source batch metadata from official page.
2. Capture raw file snapshot and compute SHA-256.
   - For static attachments, snapshot metadata is built from the registered attachment.
   - For dynamic official views, snapshot metadata must be built from a reviewed manual/browser capture and retain the official data-view URL.
3. Parse a small selected subset into raw records.
4. Write and validate reviewed raw rows artifact for the audited small sample.
5. Run source schema fit before canonical normalization.
6. Normalize raw records into canonical candidates.
7. Run quality gate, including schema/parse blocking issues.
8. If report is `pass` or accepted `warning`, write only to an isolated staging artifact or staging table after separate approval.
9. Expose citation metadata contract for future Agent tool integration.

The reviewed-row pilot runner is an isolated orchestration helper for steps 3-9. It does not fetch, scrape, mutate seed data, touch production DB tables, or modify Agent tools. It accepts already reviewed `RawRecord` inputs and a validated `SourceSnapshot`; for real pilot execution, prefer starting from a validated `ReviewedRawRowsArtifact` so raw-row lineage and schema fit are rechecked before staging.

## Compatibility

The existing seed import path remains untouched. `backend/seeds/import_cli.py` may later inspire validation/report shapes, but the first implementation should not mutate seed files or overload seed import with official source semantics unless explicitly approved.

The existing Agent tool metadata is a compatible pattern, but current tools should not be changed until staging data and citation contracts are validated.

## Rollback

Planning rollback is deleting this file and restoring `prd.md`. Implementation rollback should remove only isolated snapshot/canonical/report artifacts or staging tables introduced by that implementation step.
