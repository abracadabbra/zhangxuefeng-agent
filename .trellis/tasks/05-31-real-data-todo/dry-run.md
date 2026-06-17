# 真实数据 dry-run 操作说明

## 目标

用一个已复核的小样本 reviewed raw rows artifact 跑通隔离链路：

`reviewed raw rows -> schema/quality gate -> staging artifact -> staging manifest -> citation query summary`

该命令只写调用方指定的输出目录，不写生产 DB、不改 `backend/seeds/`、不注册或调用现有 Agent tools。

## 样本输入

- Fixture: `tests/fixtures/real_data/henan_reviewed_rows_sample.json`
- Source page: 河南省教育考试院 2025 本科院校平行投档分数线入口
- Snapshot URL: 河南 datacenter 物理类本科批查询视图
- Sample rows: 1
- Sample school: 郑州大学
- Sample major/group: 计算机类

## 命令

```bash
./.venv/bin/python -m backend.real_data.cli bundle-dry-run \
  --reviewed-rows-artifact tests/fixtures/real_data/henan_reviewed_rows_sample.json \
  --output-dir /tmp/real_data_henan_dry_run \
  --province 河南 \
  --year 2025 \
  --batch 本科批 \
  --subject-type 物理类 \
  --expected-school 郑州大学 \
  --overwrite
```

## 成功判定

输出 JSON 应满足：

- `quality_status = "pass"`
- `quality_report_id` 指向本次 quality gate 报告
- `schema_status = "pass"`
- `source.source_name = "河南省教育考试院"`
- `snapshot.raw_file_sha256` 记录被复核快照哈希
- `record_count_raw = 1`
- `record_count_parsed = 1`
- `record_count_passed = 1`
- `coverage.observed_schools = ["郑州大学"]`
- `confidence_summary.high = 1`
- `freshness_result = "published_in_admission_year"`
- `issues.field_errors = []`
- `manifest_artifact_count = 1`
- `citation_record_count = 1`
- `sample_citation.source = "河南省教育考试院"`
- `sample_citation.snapshot_url` 指向被复核的数据视图 URL
- `sample_citation.confidence = "high"`

输出目录应只包含隔离 staging/manifest 产物；不得出现 seed、DB migration、Agent tool 相关改动。

## 失败判定

- reviewed artifact 被篡改：CLI 返回非 0，且不写 staging/manifest。
- schema 缺少 `min_score`：CLI 返回 0 但 `quality_status = "blocked"`，`quality_report_id`、`source`、`snapshot` 仍可用于审计，`issues.field_errors` 包含 `missing_source_schema_field`，且不写 staging/manifest。
- manifest 或 staging artifact 被篡改：后续 typed readback / manifest query 必须失败。

## 人工审批

dry-run 通过后，可以为 manifest 写入人工复核记录：

```bash
./.venv/bin/python -m backend.real_data.cli approve-manifest \
  --manifest /tmp/real_data_henan_dry_run/staging_manifest.json \
  --approval-output /tmp/real_data_henan_dry_run/manual_approval.json \
  --reviewer codex-reviewer \
  --reviewed-at 2026-06-09T18:00:00+00:00 \
  --decision approved \
  --source-verified \
  --snapshot-verified \
  --quality-reviewed \
  --citation-reviewed \
  --no-production-writes-verified
```

审批记录可回读校验：

```bash
./.venv/bin/python -m backend.real_data.cli verify-approval \
  --approval-artifact /tmp/real_data_henan_dry_run/manual_approval.json
```

`approved` 决策必须勾选全部 checklist。回读审批记录时会重新校验 referenced manifest，manifest 被篡改时审批记录必须失效。

如果 manifest 中包含 `quality_status = "warning"` 的 staging artifact，`approved` 决策还必须填写 `--notes`，说明 warning 已被人工复核并接受；否则审批命令应返回非 0 且不写 approval artifact。

审批通过后，可以通过 approval-gated 查询命令验证未来 Agent 可引用记录：

```bash
./.venv/bin/python -m backend.real_data.cli query-approved \
  --approval-artifact /tmp/real_data_henan_dry_run/manual_approval.json \
  --province 河南 \
  --year 2025 \
  --school-name 郑州大学 \
  --major-keyword 计算机
```

查询输出 JSON 应包含 `total` 和 `records`。每条 record 必须保留 `source`、`source_url`、`snapshot_url`、`year`、`snapshot`、`confidence`、`source_batch_id`，以及对应的学校、专业、分数、位次、计划数和原始行号。

也可以输出一份审批后的完整审计包：

```bash
./.venv/bin/python -m backend.real_data.cli audit-approved \
  --approval-artifact /tmp/real_data_henan_dry_run/manual_approval.json
```

审计包会重新校验 approval、manifest 和 staging artifact，然后输出：

- `approval`: 审批人、审批时间、decision、checklist。
- `artifact_summaries`: 每个 staging artifact 的 source、source_url、snapshot_url、raw_file_sha256、captured_at、operator、quality_status、quality_report_id、coverage、freshness、confidence_summary、warning_issues 和记录计数。
- `sample_citation_record`: 一条 approval-gated citation record 样例。

当审批对象包含 warning-quality artifact 时，审计包必须同时展示 `approval.notes` 和对应 artifact 的 `warning_issues`，方便复核“哪些 warning 被人工接受，以及接受理由是什么”。

`decision != "approved"`、approval 被篡改、manifest 被篡改或 staging artifact 被篡改时，该命令必须返回非 0。

## 参考 manifest 冲突检查

当已有一份复核通过的 staging manifest 时，可以把它作为新 pilot 的参考来源：

```bash
./.venv/bin/python -m backend.real_data.cli bundle-dry-run \
  --reviewed-rows-artifact tests/fixtures/real_data/henan_reviewed_rows_sample.json \
  --output-dir /tmp/real_data_henan_dry_run_next \
  --province 河南 \
  --year 2025 \
  --batch 本科批 \
  --subject-type 物理类 \
  --expected-school 郑州大学 \
  --reference-manifest /tmp/real_data_henan_dry_run/staging_manifest.json
```

该参数只读取并重新校验 reference manifest 及其 staging artifacts，不写入 reference 目录。若新样本与参考数据具有相同 canonical key，但 `min_score`、`min_rank` 或 `plan_count` 不一致，quality gate 应返回 `blocked`，`issues.cross_source_conflicts` 应包含 `cross_source_conflict`，且不得写出新的 staging/manifest。
