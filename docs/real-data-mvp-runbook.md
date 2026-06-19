# 真实数据 MVP Runbook

本文档串联真实数据 MVP 的端到端执行顺序。当前目标是跑通可追踪、
可校验、可审批的闭环，而不是扩大数据量。

当前阶段禁止：

- 大规模爬虫
- 写入真实应用数据库
- 修改 seed 数据
- 刷新 RAG 或 Agent 可见数据
- 在未审批时执行 canonical loader

---

## 1. 检查运行环境

先运行 no-write 环境检查，确认 Python 版本、dry-run、artifact CLI 和测试依赖
是否可用：

```bash
python -m backend.data_pipeline.env_check
```

如果只检查运行时依赖，不检查 `pytest` 等开发依赖：

```bash
python -m backend.data_pipeline.env_check --runtime-only
```

报告里的 `python_version_ok=true` 且 `ready_for_cli_runtime=true` 后，再继续
执行后续 CLI。只准备运行真实数据 CLI 时，可按 runtime-only 报告提示安装：

```bash
pip install -e "."
```

如果还要运行测试，按默认报告提示安装开发依赖：

```bash
pip install -e ".[dev]"
```

如果当前环境暂时缺少 `pydantic`，正式 source audit 会不可用；此时仍可先
运行 stdlib-only source registry smoke review，检查 registry JSON 的基础
结构、重复 source id 和覆盖摘要：

```bash
python -m backend.data_pipeline.sources.smoke_cli \
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
```

该 smoke review 不替代正式 source audit，不复核具体 dataset URL、年份、
授权或 reviewed 状态。

如果缺依赖时还需要先生成一个 source-audit-shaped 预检证据，可以运行
stdlib-only scope smoke audit。它输出 `scope`、`passed`、`issues`，用于
人工预检和 CI 降级检查；依赖恢复后仍必须补跑正式
`backend.data_pipeline.sources.cli`。

```bash
python -m backend.data_pipeline.sources.scope_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  --data-category admission_scores \
  --province 山东 \
  --year 2025 \
  --require-reviewed \
  --audit-output artifacts/real_data/sd_source_scope_smoke_audit.json
```

---

## 2. 准备数据源

先按 `docs/real-data-pilot-review-checklist.md` 复核 source：

- 来源必须是官方或授权渠道。
- `source_id` 必须稳定。
- `data_categories` 必须覆盖本次 dataset。
- `coverage.provinces` 和 `coverage.years` 必须覆盖试点范围。
- `license_note` 必须写明引用、转载、授权或待复核要求。

先用 source registry scope audit 做只读复核：

```bash
python -m backend.data_pipeline.sources.cli \
  backend/data_pipeline/sources/sources.json \
  --data-category admission_scores \
  --province 山东 \
  --year 2025 \
  --require-reviewed \
  --audit-output artifacts/real_data/sd_source_audit.json
```

如果第 1 步只跑了 smoke review，必须在安装运行时依赖后补跑上面的正式
source audit，不能把 smoke result 当作 loader 前置证据。

`missing_*` issue 是硬缺口；`source_not_reviewed`、
`source_years_not_registered` 等 warning 需要人工复核后再进入 sample
整理。需要在 CI 或发布前收紧 warning 时，加 `--fail-on-warning`。
source audit JSON 会记录本次审计的 `scope`，包括 dataset、省份、年份和是否
要求 reviewed；后续 artifact manifest 必须能对上这个 scope。

如果 source scope audit 出现 `source_not_reviewed`，先填写单独的 source
usage/citation review。该 review 只判断来源使用、引用和再分发条款是否允许
真实数据摄入，不会修改 registry、下载附件或创建 snapshot：

```bash
python -m backend.data_pipeline.sources.usage_review_cli \
  examples/real_data/source_usage_review_template.json
```

模板默认应返回 blocked。只有 reviewer 填写官方 URL、使用/引用说明、
`license_reviewed=true`、`allow_real_data_ingestion=true`、reviewer 和
review time 后，才可以把通过的 usage review 摘要放进 source approval
packet。

然后再填写单独的 source review approval，并运行 no-write review。该 review
只生成“是否可以更新 registry 元数据”的证据，不会修改 `sources.json`：

```bash
python -m backend.data_pipeline.sources.review_approval_cli \
  examples/real_data/source_review_approval_template.json
```

只有 `ready_for_registry_update=true` 后，才讨论单独审批更新 registry 的
`review_status`、`coverage.years`、`data_categories` 或 `coverage.provinces`。
仓库里的 `sd_source_review_approval_candidate.json` 只是山东 2025 候选来源草稿；
对应 checked-in artifact
`examples/real_data/artifacts/sd_source_review_approval_candidate_review.json`
应保持 blocked，直到人工确认 dataset 类别、发布年份、授权/引用、reviewer 和
review time。该 artifact 只进入 inventory/readiness summary，不批准 registry
更新。
`examples/real_data/artifacts/sd_source_review_human_checklist_blocked.json`
把这些剩余动作拆成 reviewer checklist；它仍是 blocked artifact，不访问外网、
不下载附件，也不批准 source review。
`examples/real_data/artifacts/sd_source_review_handoff_blocked.json`
把当前阻断状态整理成 reviewer handoff：候选 URL、上游 blocked artifact、
下一步人工动作和 no-write 边界。它仍不访问外网、不下载附件、不批准 source
review，也不进入 registry patch。
`examples/real_data/source_review_approval_reviewed_example.json` 是 synthetic
正向样例，只展示完整 approval packet 如何通过 packet review。它使用 synthetic
source id，不匹配真实 registry source，不批准山东来源，也不授权 registry
patch。
对应的 checked-in update plan blocked artifact 证明：即使 packet review
通过，只要 source id 不在 `sources.json`，registry update plan 仍会被
`source_not_found` 阻断。
更新前先生成 no-write registry update plan，确认将要改哪些字段：

```bash
python -m backend.data_pipeline.sources.update_plan_cli \
  backend/data_pipeline/sources/sources.json \
  artifacts/real_data/source_review_approval_review.json
```

只有 `ready_for_registry_patch=true` 后，才可以提交单独审批的 registry
patch；该命令本身不会修改 `sources.json`。
当前 candidate review 对应的 checked-in update plan 是
`examples/real_data/artifacts/sd_source_registry_update_plan_blocked.json`。
它会显示当前可能的 `review_status` 变更方向，但因为 source review 尚未 ready，
应保持 `ready_for_registry_patch=false`。

registry update plan ready 后，还必须经过单独的 registry patch approval
review，不能直接修改 `sources.json`：

```bash
python -m backend.data_pipeline.sources.patch_approval_cli \
  artifacts/real_data/source_registry_update_plan.json \
  examples/real_data/source_registry_patch_approval_template.json
```

当前 checked-in template review 是
`examples/real_data/artifacts/sd_source_registry_patch_approval_blocked.json`。
它应保持 `ready_for_registry_patch_execution=false`，并且不修改
`sources.json`。

patch approval review 通过后，还要先生成 no-write patch preview，再讨论实际
编辑 registry：

```bash
python -m backend.data_pipeline.sources.patch_preview_cli \
  backend/data_pipeline/sources/sources.json \
  artifacts/real_data/source_registry_update_plan.json \
  artifacts/real_data/source_registry_patch_approval_review.json
```

当前 checked-in preview 是
`examples/real_data/artifacts/sd_source_registry_patch_preview_blocked.json`。
它应保持 `ready_for_registry_patch_preview=false`、`changes_applied=[]`、
`patched_source={}`，直到 update plan 和 patch approval review 都通过。

也可以用 patch chain smoke 一次性检查 patch approval 和 patch preview：

```bash
python -m backend.data_pipeline.sources.patch_chain_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  artifacts/real_data/source_registry_update_plan.json \
  artifacts/real_data/source_registry_patch_approval_review.json
```

当前 checked-in patch chain 是
`examples/real_data/artifacts/sd_source_registry_patch_chain_smoke_blocked.json`。
它应保持 `patch_approval_ready=false`、`patch_preview_ready=false`，同时
`registry_not_modified=true`。

也可以用聚合 smoke 一次性检查“source scope audit → approval review →
registry update plan”这条更早的前置链：

```bash
python -m backend.data_pipeline.sources.review_chain_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  examples/real_data/source_review_approval_template.json
```

空模板应返回非零退出码；这是为了确认没有真实 reviewer 和证据时不会进入
registry patch 讨论。

进入官方样本 intake 前，还要运行 source snapshot planning review。当前
checked-in 山东 2025 来源仍是 `candidate`，所以该命令应保持 blocked：

```bash
python -m backend.data_pipeline.sources.snapshot_planning_cli \
  backend/data_pipeline/sources/sources.json \
  --data-category admission_scores \
  --province 山东 \
  --year 2025 \
  --review-output artifacts/real_data/sd_source_snapshot_planning_blocked.json
```

该输出必须达到 `ready_for_snapshot_planning=true` 后，才允许准备 raw snapshot。
当前 checked-in blocked artifact 只证明来源仍需人工 review，不会修改
`sources.json`、下载附件或创建 snapshot。

试点推荐：

- 省份：山东优先，河南可作为第二候选。
- 年份：先做 2025；后续扩到 2024-2025。
- 数据集：先 admission scores，再 enrollment plans。
- 范围：少量学校、少量行，人工能逐行复核。

---

## 2.5 Intake 前置复核

真实样本进入 snapshot 前，先填写官方样本 intake JSON，并运行 no-write
review：

```bash
python -m backend.data_pipeline.intake.cli \
  path/to/official_sample_intake.json \
  --review-output artifacts/real_data/intake_review.json
```

仓库内的合成 reviewed 示例可用于检查 intake review 形状：

```bash
python -m backend.data_pipeline.intake.cli \
  examples/real_data/sd_official_sample_intake_reviewed_example.json
```

该示例不是官方数据；真实 pilot 必须从空白模板重新填写，并人工复核
来源、授权、快照路径和 checksum。

必须满足：

- `passed=true`
- `ready_for_snapshot=true`
- `issue_counts.error=0`
- `scope.source_id`、`scope.dataset`、`scope.province` 和
  `scope.published_year` 与本次 pilot 一致

该步骤只检查本地 intake JSON，不下载附件、不创建 raw snapshot、不解析 rows、
不写 DB，也不授权 loader。

---

## 3. 准备本地快照

推荐使用 raw snapshot 目录形态：

```text
data/raw/<source_id>/<dataset>/<year>/<snapshot_id>/
  manifest.json
  files/
    original.*
```

manifest 必须记录：

- `snapshot_id`
- `source_id`
- `dataset`
- `source_url`
- `published_year`
- `collected_at`
- `collector=manual`
- `collector_version`
- `files[].path`
- `files[].sha256`
- `license_note`

MVP 只接受人工审核后的本地文件。不要覆盖原始文件；如果需要清洗，
另存为 normalized rows。

---

## 4. 准备 rows bundle

rows bundle 保存人工整理后的 normalized rows：

```json
{
  "source": {},
  "quality_config": {},
  "rows": []
}
```

如果不用 `--snapshot-dir`，bundle 还必须包含 `manifest`。如果使用
`--snapshot-dir`，manifest 从本地快照目录读取。

示例见：

- `examples/real_data/sd_pilot_bundle.json`
- `examples/real_data/sd_plan_pilot_bundle.json`
- `examples/real_data/sd_snapshot_pilot_rows.json`

缺少 `pydantic` 运行依赖时，可以先用 stdlib-only parser rows bundle smoke
检查 normalized rows 是否具备 parser handoff 的最小证据：

```bash
python -m backend.data_pipeline.parsers.rows_bundle_smoke_cli \
  examples/real_data/sd_snapshot_pilot_rows.json \
  --snapshot-manifest examples/real_data/snapshots/sd_pilot_2025_001/manifest.json \
  --expect-source-id sd_exam_authority \
  --expect-snapshot-id sd_pilot_2025_001 \
  --expect-dataset admission_scores
```

该 smoke 只生成 candidate preview 和 review issues，不执行正式 parser contract、
quality gate、loader、DB 写入或 Agent/RAG refresh。依赖恢复后仍必须跑正式
dry-run 和 quality gate。

Parser smoke candidate previews 必须在每条 candidate source envelope 中携带
`source_id`、`snapshot_id`、`dataset`、`year`、`source_record_ref`、
`confidence` 和 `has_review_metadata`。这些字段是后续 quality gate、loader
handoff 和 Agent 引用的最小可追踪证据。

可以继续用 stdlib-only quality smoke 从 parser candidate preview 生成质量
证据摘要：

```bash
python -m backend.data_pipeline.quality.smoke_cli \
  examples/real_data/artifacts/sd_parser_rows_bundle_smoke.json \
  --rows-bundle examples/real_data/sd_snapshot_pilot_rows.json
```

该 smoke 检查必填自然键、source metadata、值域、重复冲突、覆盖率、新鲜度、
置信度和 review metadata，但仍不替代正式 pydantic quality gate。
Quality smoke 会汇总 `source_metadata`，包括 source ids、snapshot ids、
datasets、years、confidence min/max 和缺失 source/snapshot 计数。进入 loader
讨论前，应该确认这些汇总和 pilot scope 一致。candidate source id、snapshot
id 和 dataset 必须匹配 parser smoke scope，candidate source year 必须匹配
natural key year。

---

## 5. Dry-run

先跑 no-write dry-run：

```bash
python -m backend.data_pipeline.pilots.cli \
  --snapshot-dir examples/real_data/snapshots/sd_pilot_2025_001 \
  --audit-output artifacts/real_data/sd_snapshot_pilot_audit.json \
  --approval-output artifacts/real_data/sd_snapshot_pilot_approval.json \
  examples/real_data/sd_snapshot_pilot_rows.json
```

该命令只会：

- 读取本地 bundle
- 读取本地 manifest
- 校验 checksum
- 解析 rows
- 运行 quality gate
- 输出 audit JSON
- 在 audit ready 时输出 approval packet JSON

该命令不会：

- 爬取远程网站
- 写入 DB
- 修改 seed
- 执行 loader
- 刷新 RAG 或 Agent

---

## 6. 审核 Audit

必须检查：

- `load_ready=true`
- `blockers=[]`
- `snapshot_file_issues=[]`
- `source_validation_issues=[]`
- `issue_counts.error=0`
- `coverage.missing_expected_provinces=[]`
- `coverage.missing_expected_years=[]`
- `review_status=ready_for_loader_review`

如果 `blockers` 出现 `coverage_missing:province:<省份>` 或
`coverage_missing:year:<年份>`，表示本次 `quality_config` 声明的覆盖目标尚未
达成。不要进入 loader；应补齐样本，或把本次 pilot 范围调整成真实已复核
范围后重跑 dry-run。

如果 `review_status=needs_warning_review`，必须先人工处理 warning，不得直接
进入 loader。

如果 `review_status=blocked`，必须修复数据、manifest、source 或 rows 后重跑
dry-run。

---

## 7. 审批 Loader

只有 approval packet 存在且内容通过人工复核后，才可以进入 loader 审批。

审批包至少确认：

- 本次 audit artifact 路径。
- 本次 approval packet 路径。
- 将写入的 `source_id`、`snapshot_id`、`dataset`。
- `candidate_count` 和 `entity_counts`。
- parser name/version。
- 回滚动作。
- 明确不包含 crawler、seed 修改、RAG/Agent refresh。

即使审批通过，也应单独给出实际 loader run command。不要把 dry-run 命令和
loader 写入命令合并。代码层真实进入 canonical loader 前，优先使用
`load_candidates_after_artifact_manifest(...)`，让写入入口复用 source audit、
dry-run、loader approval、路径和 scope 的完整证据包门禁。

---

## 8. 汇总 Artifact Manifest

进入任何真实 loader run 之前，建议把本次 pilot 的复核产物汇总成一个
artifact manifest：

- source audit JSON
- intake review JSON
- dry-run audit JSON
- loader approval JSON
- rows bundle 路径
- snapshot dir 路径

命令行入口：

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

只有 source audit 无 error/warning、intake review ready、dry-run ready、
loader approval 允许写入，且 `artifact_path_issues=[]`、
`intake_review_issues=[]`、`artifact_scope_issues=[]`、
`loader_approval_issues=[]`、`ready_for_loader_execution=true` 时，才可以继续
准备单独审批的 loader run command。artifact manifest 会在
`review_summary.source_audit_scope` 中摘录 source audit 的审计范围，并记录
缺失的 rows bundle、snapshot dir 等本地证据路径问题、intake review 未通过
或缺失的问题、source audit scope 与 dry-run 覆盖范围不一致的问题，以及
loader approval 与 dry-run 身份或数量不一致的问题；这些问题必须先消除。
该 manifest 本身不批准 crawler、DB 写入、seed 修改或 RAG/Agent 刷新。

manifest 的 `loader_handoff` 会显式记录推荐入口
`load_candidates_after_artifact_manifest`、是否已达到 artifact manifest ready，
以及仍需单独 loader run command。后续审批应引用该区块，避免把
artifact manifest ready 误读成自动写库授权。

如果当前环境缺少 `pydantic`，无法运行正式 artifact manifest builder，可先用
stdlib-only smoke 检查静态 manifest 的形状、scope、路径、loader handoff，
以及 referenced artifacts 的关键 scope 是否一致：

```bash
python -m backend.data_pipeline.pilots.artifact_smoke_cli \
  examples/real_data/artifacts/sd_pilot_artifact_manifest.json \
  --expect-source-id sd_exam_authority \
  --expect-snapshot-id sd_pilot_2025_001 \
  --expect-dataset admission_scores
```

该 smoke 不运行 parser、quality gate 或 pydantic manifest contract；依赖恢复
后仍需重跑正式 `backend.data_pipeline.pilots.artifacts_cli`。

也可以用 stdlib-only inventory 汇总当前 evidence artifacts 和剩余人工 review
动作：

```bash
python -m backend.data_pipeline.pilots.evidence_inventory_cli \
  examples/real_data/artifacts
```

该 inventory 只读取本地 JSON artifact，不运行 parser、quality gate、loader、
DB 写入或 Agent/RAG refresh。它是复核辅助，不证明真实官方来源已经获批。
Checked-in evidence artifacts 应包含 `action` 和 no-write `non_goals`，这样
inventory 不需要依赖文件名猜测就能解释每个 artifact。

如果 reviewer 需要一个总状态，而不是逐个读取 artifact，可运行 MVP readiness
summary：

```bash
python -m backend.data_pipeline.pilots.readiness_summary_cli \
  --summary-output examples/real_data/artifacts/sd_mvp_readiness_summary.json
```

当前 checked-in summary 应保持 `passed=false`：inventory 完整、synthetic
no-write 链路 ready，但山东真实 source 仍未通过 snapshot planning，且还需要
单独 loader run command 和 Agent visibility approval。该 summary 只做只读汇总，
不批准 source review、snapshot、loader、DB 写入或 Agent/RAG refresh。

---

## 9. Agent 回答来源策略复核

真实数据进入工具响应后，可用 answer source policy CLI 对本地工具结果或
`source_summary` artifact 做 no-write 复核：

```bash
python -m backend.data_pipeline.lineage.policy_cli \
  path/to/tool_response.json \
  --policy-output artifacts/real_data/answer_source_policy.json
```

仓库内的合成 tool response 示例可用于检查 answer policy review 形状：

```bash
python -m backend.data_pipeline.lineage.policy_cli \
  examples/real_data/sd_tool_response_with_sources.json \
  --policy-output artifacts/real_data/sd_answer_source_policy.json
```

该示例不是官方真实工具结果；真实 pilot 必须使用实际 Agent/tool response 或
真实 `source_summary` artifact。

如果手头只有 `source_summary` JSON：

```bash
python -m backend.data_pipeline.lineage.policy_cli \
  path/to/source_summary.json \
  --summary-only
```

`answer_source_policy.answer_mode=unsupported` 会返回非 0，表示该批结果不应
作为默认真实数据回答；`citeable_with_caution` 允许引用，但回答必须提示谨慎
或降低确定性。该步骤不读取 DB、不刷新 RAG，也不授权 Agent 默认使用
新数据。

Agent system prompt 也必须保留同样的回答约束。当前可用标准库测试确认
`SKILL.md` 仍包含 `answer_source_policy`、三种 `answer_mode` 和
`legacy_untraced_tool` 处理规则：

```bash
python3 tests/test_agent_prompt_source_policy.py
```

---

## 10. Agent 可见性激活复核

如果已经通过单独审批执行 canonical loader，先把执行结果记录成本地
`canonical_loader_run_record`，再生成 no-write evidence review：

```bash
python -m backend.data_pipeline.activation.loader_evidence_cli \
  --artifact-manifest artifacts/real_data/sd_pilot_artifact_manifest.json \
  --loader-run-record artifacts/real_data/canonical_loader_run_record.json \
  --review-output artifacts/real_data/loader_run_evidence_review.json
```

`loader_run_evidence_review.ready_for_activation_evidence=true` 后，再把其中
的 `loader_run_evidence` 放入 Agent visibility approval。该 review 只检查
本地 JSON 证据，不执行 loader、不写 DB、不刷新 RAG/Agent。
仓库内的模板 blocked 输出是
`examples/real_data/artifacts/sd_loader_run_evidence_templates_blocked.json`；
它证明默认 loader-run 模板不能作为真实执行证据。

真实数据完成 loader 证据、answer policy 复核后，仍需单独 Agent visibility
approval，才能讨论是否让 Agent/RAG 默认使用该批数据：

如果没有单独 approval，先生成 blocked review，确认 Agent visibility 仍被阻断：

```bash
python -m backend.data_pipeline.activation.cli \
  --artifact-manifest artifacts/real_data/sd_pilot_artifact_manifest.json \
  --answer-policy-review artifacts/real_data/answer_source_policy.json \
  --review-output artifacts/real_data/agent_visibility_activation_review.json
```

该状态应包含 `missing_agent_visibility_approval`，不能刷新 RAG/Agent。
只有在 loader run evidence 和单独 approval 都存在后，才运行完整复核：

```bash
python -m backend.data_pipeline.activation.cli \
  --artifact-manifest artifacts/real_data/sd_pilot_artifact_manifest.json \
  --answer-policy-review artifacts/real_data/answer_source_policy.json \
  --activation-approval artifacts/real_data/agent_visibility_approval.json \
  --loader-run-evidence-review artifacts/real_data/loader_run_evidence_review.json \
  --review-output artifacts/real_data/agent_visibility_activation_review.json
```

`activation_approval` 至少需要：

- `action=agent_visibility_approval`
- `allow_agent_visibility=true`
- `loader_run_confirmed=true`
- `reviewed_by` / `reviewed_at`
- `loader_run_evidence.run_id`
- `loader_run_evidence.completed_at`
- `loader_run_evidence.artifact_manifest_path`
- `loader_run_evidence.result_status=succeeded`
- `loader_run_evidence.loaded_counts` 与 artifact manifest 的
  `candidate_count` 一致
- `loader_run_evidence` 必须与已通过的 `loader_run_evidence_review` 一致
- `scope.source_id`、`scope.snapshot_id`、`scope.dataset` 与 artifact manifest
  一致

该复核只生成本地 JSON，不执行 loader、不写 DB、不刷新 RAG、不修改 Agent
默认可见数据。`ready_for_agent_visibility=true` 也只表示可以进入单独审批的
Agent/RAG refresh 或部署流程。

---

## 11. 示例证据链一键 Smoke

当前环境缺少运行依赖时，可以用 stdlib-only 聚合 smoke 检查 checked-in
synthetic 山东示例链路是否仍自洽：

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
  --expect-dataset admission_scores \
  --review-output examples/real_data/artifacts/sd_example_chain_smoke.json
```

该 smoke 应同时确认：

- intake review ready。
- artifact manifest smoke 通过，且 referenced artifacts scope 一致。
- parser rows bundle smoke ready，且 source/snapshot/dataset/row_count 与
  artifact manifest 一致。
- quality smoke ready，且 source/snapshot/dataset/candidate_count 与 artifact
  manifest 一致。
- answer source policy 可引用。
- 无 activation approval 时 Agent visibility 仍被阻断。
- 顶层 `required_reviews` 会列出仍需单独 loader run command 和 Agent
  visibility approval。

也可以把默认 activation / loader 模板作为输入，确认模板不能误通过：

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
  --activation-approval examples/real_data/agent_visibility_approval_template.json \
  --loader-run-record examples/real_data/canonical_loader_run_record_template.json \
  --review-output \
    examples/real_data/artifacts/sd_example_chain_smoke_templates_blocked.json
```

该模板输入 smoke 应返回非零退出码，且顶层 `required_reviews` 指向需要补齐的
审批、loader run 和 reviewer/time。详细 loader-run 证据问题会出现在
`reviews.loader_run_evidence`。

它不运行正式 parser、quality gate、pydantic artifact builder 或 loader；依赖恢复
后仍需跑正式 dry-run / artifact / activation 命令。

---

## 12. 后续扩展顺序

单省试点通过后，按以下顺序扩展：

1. 山东 admission scores 小样本。
2. 山东 enrollment plans 小样本。
3. 山东 2024-2025 完整年份。
4. 河南复制同一流程。
5. 广东、江苏、浙江、河北、四川、湖北等重点省份。
6. 全国省级数据。
7. 就业报告、招生章程、政策公告、学科排名等增强数据。

每一步都必须保留 source、snapshot、quality、audit、approval 和 lineage。
