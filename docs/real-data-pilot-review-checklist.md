# 真实数据 Pilot 人工复核清单

本文档用于山东/河南等单省小样本进入 dry-run 前的人工复核。目标是保证
每一批样本都能回答：来源是谁、发布年份是什么、原始快照在哪里、
字段如何映射、是否可以进入 loader 审批，以及后续是否允许进入
Agent/RAG 可见性审批。

当前阶段仍然不做爬虫、不写真实 DB、不修改 seed 数据。

---

## 1. 数据源复核

每个 pilot bundle 必须优先登记 `source`：

| 项 | 要求 |
|----|------|
| `source_id` | 使用稳定 slug，如 `sd_exam_authority` |
| `name` | 写官方/授权来源全称 |
| `source_type` | 优先使用 `provincial_exam_authority`、`ministry`、`university` |
| `homepage_url` | 指向官方主页或授权来源主页 |
| `data_categories` | 必须覆盖本次 `dataset` |
| `coverage.provinces` | 必须包含试点省份，如 `山东` |
| `coverage.years` | 必须包含本次 `published_year` |
| `trust_score` | 官方/授权来源建议为 `0.95` 到 `1.0` |
| `collection_method` | MVP 优先 `manual_download` |
| `license_note` | 写明公开引用、转载、授权或待复核要求 |
| `review_status` | 未复核用 `candidate`，复核后再升为 `reviewed` |

阻断条件：

- 来源不是官方/授权渠道，且无法确认引用或使用许可。
- `source_id` 与 manifest 的 `source_id` 不一致。
- source 的 `data_categories` 不包含 manifest 的 `dataset`。
- source 的覆盖年份不包含 manifest 的 `published_year`。

### 使用/引用复核

source approval 前必须先完成 usage/citation review。填写
`examples/real_data/source_usage_review_template.json` 时至少确认：

- 官方页面或附件 URL。
- 页面版权、转载、镜像、引用或授权说明。
- 是否检测到再分发限制。
- `usage_status` 是否允许真实数据摄入。
- `license_reviewed=true`。
- `allow_real_data_ingestion=true`。
- reviewer 和 review time。

如果 `usage_status` 仍是 `blocked_pending_authorization`，或 reviewer/time
为空，不得准备 source approval。

---

## 2. 快照复核

每个样本批次必须有 `manifest`：

| 项 | 要求 |
|----|------|
| `snapshot_id` | 稳定且可追溯，建议包含省份、数据集、年份、批次号 |
| `source_id` | 与 source 完全一致 |
| `dataset` | `admission_scores` 或 `enrollment_plans` |
| `source_url` | 指向原始公告、PDF、Excel 或下载页 |
| `published_year` | 取官方数据发布年份，不是整理年份 |
| `collected_at` | 记录人工整理时间 |
| `collector` | MVP 使用 `manual` |
| `collector_version` | 当前人工整理规范版本，如 `0.1.0` |
| `files[].path` | 相对路径，不允许绝对路径或 `..` |
| `files[].sha256` | 原始文件 checksum，64 位十六进制 |
| `license_note` | 与 source 许可说明保持一致或更具体 |

阻断条件：

- 没有原始文件 checksum。
- `source_url` 不是可追溯的官方/授权页面。
- `published_year` 与样本行年份含义冲突且无法解释。
- 原始文件经过人工改写后覆盖了原件。

---

## 3. 样本行复核

### 分数线 `admission_scores`

必填 natural key：

- `school_name`
- `province`
- `year`
- `batch`
- `subject_type`

推荐字段：

- `major_name`
- `min_score`
- `avg_score`
- `max_score`
- `min_rank`
- `source_record_ref`

### 招生计划 `enrollment_plans`

必填 natural key：

- `school_name`
- `major_name`
- `province`
- `year`

推荐字段：

- `plan_count`
- `subject_requirement`
- `batch`
- `duration`
- `tuition`
- `source_record_ref`

阻断条件：

- 必填 natural key 为空。
- 分数不在 `0-750`。
- 位次不是正数。
- 招生计划人数明显异常，且无法由官方注释解释。
- 同一 snapshot 内相同 natural key 出现不同值。
- `source_record_ref` 无法定位到原始页码、sheet、行号或表格位置。

---

## 4. Quality Config 复核

pilot bundle 应显式设置本次期望覆盖：

```json
{
  "quality_config": {
    "current_year": 2026,
    "expected_provinces": ["山东"],
    "expected_years": [2025]
  }
}
```

复核要求：

- `current_year` 使用运行 dry-run 时的实际年份。
- `expected_provinces` 必须与试点省份一致。
- `expected_years` 必须覆盖本次样本年份。
- 对跨年样本，宁可拆成多个 snapshot，也不要混淆发布年份和招生年份。

---

## 5. Dry-run 审核标准

运行 dry-run 后，只有满足以下条件才可以进入 loader 审批：

- `load_ready=true`
- `blockers=[]`
- `candidate_count` 与人工整理行数一致
- `source_validation_issues=[]`
- `issue_counts.error` 为空或为 `0`
- `coverage.missing_expected_provinces=[]`
- `coverage.missing_expected_years=[]`

缺失期望覆盖会进入 `blockers`，格式为
`coverage_missing:province:<省份>` 或 `coverage_missing:year:<年份>`。出现这类
阻断时，不得进入 loader 审批。

如果存在 warning：

- `stale_data`：确认是否允许历史年份进入当前 pilot。
- `low_confidence`：补充来源复核，或降低该批次 Agent 可见级别。

---

## 6. Loader 前审批包

真实 DB 写入前必须单独审批，审批包至少包含：

- 本次 bundle 文件路径。
- dry-run audit 摘要。
- 将写入的 canonical entity 类型和数量。
- 将写入的 snapshot 和 source。
- 是否会覆盖既有 canonical 行。
- 回滚方式，包括如何删除本次 lineage records 和 canonical 变更。

未获得审批前，不得运行 canonical loader，不得写入 `backend/zhangxuefeng.db`，
不得刷新 RAG 或让 Agent 默认使用该批数据。

---

## 7. Answer Source Policy 复核

只有在单独审批并执行 canonical loader，且已经产生本地工具响应 JSON 后，
才复核回答来源策略。

必须检查：

- `action=answer_source_policy_review`
- `passed=true`
- `answer_source_policy.answer_mode` 不是 `unsupported`
- `answer_source_policy.requires_citation=true`
- `non_goals` 明确不刷新 RAG 或 Agent

阻断条件：

- 缺少工具响应或 `source_summary`。
- `answer_mode=unsupported`。
- `citation_ready=false`。
- `requires_citation=false`，但回答要使用该批真实数据。

如果 `answer_mode=citeable_with_caution`，可以进入下一步，但 Agent 回答必须
引用来源、年份、置信度，并降低确定性。

---

## 8. Agent Visibility Activation 复核

即使 loader 和 answer policy 都通过，也必须单独复核 Agent/RAG 可见性。

`activation_approval` 至少包含：

- `action=agent_visibility_approval`
- `allow_agent_visibility=true`
- `loader_run_confirmed=true`
- `reviewed_by`
- `reviewed_at`
- `scope.source_id`
- `scope.snapshot_id`
- `scope.dataset`

必须检查：

- `ready_for_agent_visibility=true`
- `issue_counts.error=0`
- `scope` 与 artifact manifest 一致
- `non_goals` 明确该 review 不执行 refresh

阻断条件：

- 未确认 canonical loader 已按单独审批执行。
- 缺少 `agent_visibility_approval`。
- approval scope 与 artifact manifest 不一致。
- answer policy review 未通过。
- 任何步骤试图把 review 命令当作 RAG/Agent refresh 命令。
