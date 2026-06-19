# 真实数据 MVP 状态

本文档记录当前真实数据建设 MVP 的阶段性状态。当前重点是 no-write
闭环：先把来源、快照、解析、校验、审批和证据包跑通，再进入真实
小样本。

## 当前已成型

```text
source registry audit
  -> raw snapshot manifest + checksum
  -> manual rows bundle
  -> parser candidates
  -> parser rows bundle smoke
  -> quality smoke review
  -> quality gate + coverage blockers
  -> dry-run audit
  -> loader approval packet
  -> pilot artifact manifest
  -> answer source policy review
  -> Agent visibility activation review
```

已具备的门禁：

- 数据源登记：校验来源类别、省份、年份、review 状态和 warning。
  Registry 已包含山东、河南和广东、江苏、浙江、河北、四川、湖北等
  重点省份的官方考试院 homepage candidate；除山东 2025 候选外，其余
  不登记具体年份，进入 snapshot 前仍需逐页复核 dataset URL、授权和年份。
- Source review approval：`source_not_reviewed` 需要单独 approval packet
  复核 source URL、年份、引用/授权、reviewer 和 review 时间。approval review
  输出会附带 `evidence_summary` 展示已填证据和缺失确认项，并用
  `required_reviews` 给出剩余人工复核动作。approval review 通过后，只生成
  registry update hint；不会自动修改 `sources.json`。approval packet 现在必须
  携带 `source_usage_review` 摘要，且
  `ready_for_source_approval_license_review=true` 后才能通过 source approval。
  当前山东 2025 candidate review 已固化为 blocked artifact：它记录候选官方
  页面和 `.xls` 附件已定位，dataset category 与 published year 已确认；
  但页面版权/使用限制仍需授权或引用复核，reviewer/time 与 allow flag
  仍未确认，因此 `ready_for_registry_update=false`。
  `source_usage_review` blocked artifact 单独记录官网版权/使用限制和
  `allow_real_data_ingestion=false`，作为 source approval 前置的授权 gate。
  synthetic source usage positive artifact 展示 reviewer、review time、
  license review 和 allow flag 都具备时 usage gate 可通过，但只使用 synthetic
  source id，不批准山东或任何真实来源。
  synthetic usage-to-approval chain smoke 把该 positive usage artifact 与
  synthetic source approval review 串联，检查 source id、category、province、
  years、ready usage evidence 和 registry update hint 连续一致；它仍不修改
  registry，也不批准山东或任何真实来源。
  另有 human checklist blocked artifact，把已核验项和剩余的授权/引用、
  reviewer/time、allow flag 待办拆开，避免把候选来源误当成已审批来源。
  source review handoff blocked artifact 进一步汇总候选 URL、上游 blocked
  artifact、人工下一步和 no-write 边界，方便 reviewer 接手，但不批准 source。
  source review chain smoke blocked artifact 串联 source scope audit、source
  approval review 和 registry update plan，显示山东 scope 存在，但 approval
  和 update plan 仍因 usage/source approval 未通过而 blocked。
  synthetic reviewed source approval example 只展示 packet review 的正向输出，
  使用 synthetic source id，不代表山东或任何真实来源已通过审批。
  synthetic source review chain positive artifact 使用临时 synthetic registry
  输入，展示 usage review、source approval 和 update plan 都 ready 时的
  no-write 正向链路；它不修改当前 `sources.json`，也不批准任何真实来源。
  synthetic registry patch positive artifacts 继续展示 ready update plan 到
  patch approval、patch preview 和 patch chain 的 no-write 正向链路；预览中
  只显示 synthetic source 的 `reviewed -> approved` 计划变更，不执行 patch。
  synthetic snapshot planning positive artifact 展示 source 已 approved 且覆盖
  category/province/year 后，`ready_for_snapshot_planning=true`；它仍不下载
  文件，也不创建 raw snapshot。
  synthetic intake positive artifact 继续把该 planning 摘要带入官方样本
  intake review，展示 `ready_for_snapshot=true` 的 no-write 入口；它仍不
  创建 raw snapshot，也不解析行。
  synthetic source-to-intake chain smoke 聚合 source review chain、registry
  patch chain、snapshot planning 和 intake review，检查 source id 和
  category/province/year scope 连续一致，但仍不执行任何真实写入。
  synthetic parser and quality positive artifacts 继续使用同一个
  synthetic source/snapshot，展示 candidate source metadata、confidence、
  coverage 和 review metadata 可进入 parser/quality smoke。
  synthetic source-to-quality chain smoke 继续把 source-to-intake、parser
  rows bundle smoke 和 quality smoke 聚合，检查 source id、snapshot id、
  dataset、candidate count 和 source year 连续一致；它仍不执行正式 parser、
  正式 quality gate、loader、DB/seed/RAG/Agent 写入。
  该 synthetic approval 对应的 update plan blocked artifact 显示它无法进入
  registry patch：source id 不在当前 `sources.json`，因此 `source_not_found`。
- Registry update plan：读取 source approval review 和当前 registry，
  生成 no-write patch plan，列出将更新的 `review_status`、`coverage.years`、
  `data_categories` 和 `coverage.provinces`。只有
  `ready_for_registry_patch=true` 后，才讨论单独审批 registry patch。
  当前山东 candidate review 对应的 update plan 已固化为 blocked artifact：
  它显示潜在 `review_status` 变更方向，但因为 source review 未 ready，
  `ready_for_registry_patch=false`。
- Registry patch approval：读取 update plan 和单独 approval packet，只有
  `ready_for_registry_patch_execution=true` 后，才允许讨论实际编辑
  `sources.json`。该 review 仍不修改 registry。
  当前 template review 已固化为 blocked artifact：因为 update plan 未 ready、
  patch approval 未授权、未确认 planned updates、缺 reviewer/time，
  `ready_for_registry_patch_execution=false`。
- Registry patch preview：读取 registry、update plan 和 patch approval review，
  输出 no-write `patched_source` 预览，供实际编辑前复核。
  当前 checked-in preview 已保持 blocked：`changes_applied=[]` 且
  `patched_source={}`，因为 update plan 和 patch approval review 都未 ready。
- Registry patch chain smoke：聚合 patch approval review 和 patch preview，
  确认 registry 仍未被修改，并输出剩余 required reviews。
  当前 checked-in chain smoke 保持 blocked：patch approval 和 patch preview
  都不 ready，但 `registry_not_modified=true`。
- Source snapshot planning review：对指定 data category/province/year 执行
  scoped source audit，并把 source warning 也作为 snapshot planning blocker。
  输出 `source_summary` 汇总匹配 source id、review 状态和覆盖年份。
- Official intake review：官方样本 intake packet 必须携带通过的
  `source_snapshot_planning_review`，且 scope/source id 需要和 pilot scope
  一致；blocked intake 会输出 `required_reviews` 说明需补的人工动作。
- 原始快照：校验 `manifest.json` 与文件 checksum。
- Parser：把人工复核 rows 转成 canonical candidates。
- Parser rows bundle smoke：在缺少 pydantic 运行依赖时，用 stdlib-only
  smoke 从 rows bundle 和 snapshot manifest 生成 candidate preview，并检查
  source/snapshot/dataset、自然键和 review metadata。该 smoke 不替代正式
  parser contract。candidate source envelope 会显式携带 `source_id`、
  `snapshot_id`、`dataset`、`year`、`source_record_ref`、`confidence` 和
  `has_review_metadata`，用于后续 quality、loader 和 Agent 引用证据。
- Quality gate：校验字段、范围、重复冲突、新鲜度、置信度和覆盖率。
- Quality smoke：在缺少 pydantic 运行依赖时，用 stdlib-only smoke 从 parser
  candidate preview 生成质量证据摘要，覆盖必填自然键、值域、重复冲突、
  source metadata、覆盖率、新鲜度、置信度和 review metadata。该 smoke 不
  替代正式 quality gate。当前输出也包含 `source_metadata` 汇总，便于检查
  source/year/snapshot/confidence 覆盖；缺少 candidate source id、snapshot
  id、dataset 或 year 会阻断 quality smoke；candidate source id、snapshot
  id、dataset 和 year 与 parser scope / natural key 不一致也会阻断。
- Coverage gate：缺失 `expected_provinces` 或 `expected_years` 会阻断 loader。
- Loader approval：只生成审批包，不写 DB。
- Artifact manifest：汇总 source audit、dry-run audit、approval 和输入路径。
- Loader handoff：manifest 输出推荐 loader 入口和单独 run command 要求。
- Static evidence artifacts：`examples/real_data/artifacts/` 已包含
  priority source coverage report、
  source review human checklist blocked review、source review handoff blocked
  review、source review candidate blocked review、synthetic source approval
  positive review、synthetic source usage positive review、synthetic
  usage-to-approval chain smoke、synthetic source review chain positive smoke、
  synthetic
  registry update plan positive review、synthetic registry patch approval
  positive review、synthetic registry patch preview positive review、
  synthetic registry patch chain positive smoke、synthetic snapshot planning
  positive review、synthetic intake positive review、synthetic source-to-intake
  chain smoke、synthetic parser rows bundle smoke、synthetic quality smoke、
  synthetic source-to-quality chain smoke、synthetic update plan blocked review、
  registry update plan blocked review、
  registry patch approval blocked review、registry patch preview blocked review、
  registry patch chain smoke blocked review、parser rows bundle smoke、quality
  smoke、no-write aggregate smoke、模板输入 blocked smoke、loader evidence 模板
  blocked review、当前山东 snapshot planning blocked review、MVP readiness
  summary 等静态证据。
  这些 artifact 只证明链路形状、正向示例和当前阻断状态，不代表真实 source
  已审批。
  priority source coverage report 显示山东、河南、广东、江苏、浙江、河北、
  四川、湖北均已有 homepage candidate；除山东 2025 外，其他重点省份仍缺
  登记年份，且全部重点省份都没有 approved source，因此不能进入 snapshot
  planning。
- Agent source metadata：分数线和招生计划工具已有 additive `sources` envelope，
  包含来源、年份、快照、置信度、freshness、trust score、复核状态和
  授权说明，并提供 `source_summary` 标记 citation-ready 和 caution 状态；
  缺少 confidence、trust score 或 review status 的来源默认需要谨慎回答。
  `reviewed` 和 `approved` 均视为已复核状态；`candidate`、缺失状态或低置信度
  仍会触发 caution。`source_summary.source_metadata_complete=false` 会使
  answer policy 降级为 unsupported，避免缺少 source/snapshot/year/confidence
  的结果被当作可引用真实数据。
  工具响应顶层也会汇总本批结果的来源覆盖和 caution 状态，并提供
  `answer_source_policy` 指明 `citeable`、`citeable_with_caution` 或
  `unsupported`。当前覆盖 `search_admission`、`search_enrollment_plan`
  和 `calculate_match`。就业、院校对比、政策和语义搜索工具只提供保守
  unsupported answer policy，不作为真实数据引用入口。该策略 helper 可在
  缺少 DB 运行依赖时独立导入，用于 no-write
  smoke 验证；`backend.data_pipeline.lineage.policy_cli` 可对本地工具响应或
  `source_summary` artifact 生成 answer policy review。`SKILL.md` 已加入
  prompt-level 回答规则，要求 Agent 按 `answer_source_policy` 降低确定性、
  引用来源或拒绝把未溯源工具结果当作真实数据证据。非流式
  `AgentCore.chat()` 还会把本轮 tool results 汇总为 additive
  `answer_source_policy_review`，方便调用方识别 citeable、cautious 或
  unsupported 回答状态。`/chat` 非流式响应会透传该字段；SSE 流式响应在
  tool result 后追加 `answer_source_policy_review` message，不改变旧事件。
- Agent visibility activation：`backend.data_pipeline.activation.cli` 会检查
  artifact manifest、answer policy review 和单独 Agent visibility approval；
  未确认 loader run 或未给可见性审批时，默认阻断 Agent/RAG 可见性。
- Aggregate example chain smoke：`backend.data_pipeline.pilots.example_chain_smoke_cli`
  会把 intake、parser smoke、quality smoke、artifact manifest、answer policy
  和 activation review 串成 stdlib-only no-write 检查，并在顶层聚合
  `required_reviews`，方便 reviewer 直接看到还缺 loader run command、Agent
  visibility approval 或模板补全项。如果提供 loader-run record，还会暴露
  `reviews.loader_run_evidence` 并独立检查
  `loader_run_evidence_ready_when_provided`。
- MVP readiness summary：`backend.data_pipeline.pilots.readiness_summary_cli`
  汇总当前 source snapshot planning、aggregate smoke、usage-to-approval chain
  smoke、source-to-quality chain smoke 和 evidence inventory，明确区分
  synthetic no-write 链路 ready 与真实 source/snapshot 仍 blocked。
  当前 checked-in summary 应保持 `passed=false`，阻断项包括山东 source 仍未
  通过 snapshot planning、缺少单独 loader run command、缺少单独 Agent
  visibility approval。
- MVP action queue：`backend.data_pipeline.pilots.action_queue_cli`
  汇总 readiness summary 和 source review handoff，把当前山东试点的下一步
  人工动作排成队列。当前首要动作仍是 usage/citation review、reviewer/time
  和 separate source approval；source snapshot planning 会作为显式 blocker
  排在其后，loader run command 与 Agent visibility approval 被保留为
  deferred，不会被误当成当前可执行动作。current state 会显式区分
  synthetic usage-to-approval/source-to-quality 链路 ready 与山东真实 source
  review 未 ready。`source_review_context` 会把候选官方页、附件、上游
  artifact refs 和 pending manual action ids 带到队列里，方便人工 reviewer
  直接接手。
- Priority source coverage action queue：
  `backend.data_pipeline.sources.coverage_action_queue_cli` 会把重点省份覆盖
  报告中的缺口转成人工复核队列。当前 8 个重点省份都有 homepage candidate，
  但 7 个省份缺少 dataset year review，8 个省份都缺少 approved source；
  因此该队列保持 `passed=false`，只提示人工动作，不授权采集、快照或入库。
- Source year review：`backend.data_pipeline.sources.year_review_cli`
  提供 official dataset year 的人工复核门禁。当前
  `ha_source_year_review_blocked.json` 只登记河南 homepage candidate，没有
  reviewed candidate years、year evidence、reviewer 或允许更新决定，因此
  `ready_for_source_year_registration=false`，不会改 `sources.json`。
- Source year review coverage：
  `backend.data_pipeline.sources.year_review_coverage_cli` 会把重点省份缺
  dataset year 的清单和已有 year review artifact 对齐。当前 7 个重点省份
  需要年份复核，只有河南有 blocked packet，广东、江苏、浙江、河北、四川、
  湖北仍缺 review packet，因此保持
  `ready_for_priority_source_year_registration=false`，不会改 `sources.json`。

## 当前禁止动作

- 不启动大规模爬虫。
- 不下载或采集真实远程数据。
- 不写入真实应用数据库。
- 不修改 seed 数据。
- 不刷新 RAG 或 Agent 可见数据。
- 不执行 canonical loader run command。

## 当前验证状态

已能在当前环境完成：

- `python3 -m py_compile` 静态编译检查。
- `python3 -m json.tool` JSON 格式检查。
- 相关 Markdown / Python 长行扫描。

当前环境未完成：

- `pytest`：当前 Python 环境缺少 `pytest`。
- CLI runtime smoke：当前 Python 环境缺少运行依赖，如 `sqlalchemy`、
  `pydantic`。
- Alembic migration run：未对真实 DB 执行迁移。
- canonical loader run：未执行，需单独审批。

当前缺少 `pydantic` 时，仍可用 stdlib-only smoke review 检查 registry
结构、重复 source id 和基础字段：

```bash
python -m backend.data_pipeline.sources.smoke_cli \
  backend/data_pipeline/sources/sources.json
```

也可以用 stdlib-only coverage report 查看重点省份登记、候选年份和审批
状态缺口：

```bash
python -m backend.data_pipeline.sources.coverage_cli \
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
```

当前该 report 只表示“来源登记/候选覆盖”状态：重点省份均有官方 homepage
candidate，但除山东 2025 候选外，大多数省份仍没有登记 dataset 年份，
且没有任何 source 被标记为 approved。`passed=true` 只表示 registry
结构无 error；是否能进入 snapshot、loader 或 Agent/RAG 可见性讨论，
以 report 里的 `readiness` 区块为准。

source review 前置链也有 stdlib-only aggregate smoke。当前 checked-in
approval 模板为空，命令应返回 blocked：

```bash
python -m backend.data_pipeline.sources.review_chain_smoke_cli \
  backend/data_pipeline/sources/sources.json \
  examples/real_data/source_review_approval_template.json
```

当前结果应体现：source scope audit 可定位 `source_not_reviewed`，但
approval review 未通过，registry update plan 也不 ready。chain smoke 顶层
会汇总 `required_reviews`，方便 reviewer 直接看到下一步人工动作。

当前 checked-in synthetic 山东链路还可用 stdlib-only parser/quality/aggregate
smoke 和 readiness summary 复核：

```bash
python -m backend.data_pipeline.parsers.rows_bundle_smoke_cli \
  examples/real_data/sd_snapshot_pilot_rows.json \
  --snapshot-manifest examples/real_data/snapshots/sd_pilot_2025_001/manifest.json \
  --expect-source-id sd_exam_authority \
  --expect-snapshot-id sd_pilot_2025_001 \
  --expect-dataset admission_scores

python -m backend.data_pipeline.quality.smoke_cli \
  examples/real_data/artifacts/sd_parser_rows_bundle_smoke.json \
  --rows-bundle examples/real_data/sd_snapshot_pilot_rows.json

python -m backend.data_pipeline.pilots.evidence_inventory_cli \
  examples/real_data/artifacts

python -m backend.data_pipeline.pilots.readiness_summary_cli
```

当前 inventory 应报告至少 38 个 checked-in artifact，且
`issue_counts.error=0`、`issue_counts.warning=0`。
当前 readiness summary 应报告 `passed=false`、
`synthetic_chain_ready=true`、`source_to_quality_chain_ready=true`、
`evidence_inventory_ready=true`、`ready_for_real_snapshot=false`。
它的 `required_reviews` 还会聚合 source review candidate 的剩余人工动作，
例如确认 published year、license review、reviewer 和 reviewed_at。

可用以下命令生成 no-write Python 版本和依赖报告：

```bash
python -m backend.data_pipeline.env_check
```

## 进入真实小样本前置条件

下一步建议仍选山东优先。进入真实小样本前，需要满足：

- 环境检查输出 `python_version_ok=true` 和 `ready_for_cli_runtime=true`。
- 明确官方或授权来源页面，并确认引用/使用说明。
- source review approval review 输出 `ready_for_registry_update=true`。
- registry update plan 输出 `ready_for_registry_patch=true`，并经过单独审批。
- registry patch approval review 输出
  `ready_for_registry_patch_execution=true`，再讨论实际编辑 `sources.json`。
- registry patch preview 输出 `ready_for_registry_patch_preview=true`，并人工
  确认 `patched_source` 符合 update plan。
- source snapshot planning review 输出 `ready_for_snapshot_planning=true`。
- 生成 source audit artifact，并消除 error / warning。
- 保存原始文件到本地 raw snapshot 目录，不覆盖原件。
- 生成 `manifest.json`，包含 source、dataset、published year、checksum。
- 人工整理少量 rows，保留 `source_record_ref`。
- parser rows bundle smoke 输出 `ready_for_parser=true`。
- quality smoke 输出 `ready_for_quality_gate=true`，且 coverage 无缺口。
- dry-run 输出 `load_ready=true`、`blockers=[]`。
- loader approval packet 存在并通过人工复核。
- artifact manifest 的 `artifact_path_issues=[]`。
- artifact manifest 的 `artifact_scope_issues=[]`。
- artifact manifest 的 `loader_approval_issues=[]`。
- artifact manifest 输出 `ready_for_loader_execution=true`。
- artifact manifest 的 `loader_handoff.requires_separate_loader_run_command=true`。
- answer source policy review 已生成，且 `answer_mode` 不是 `unsupported`。
- Agent prompt source policy contract 检查通过，确保 `SKILL.md` 要求回答
  遵守 `answer_source_policy`。
- Agent visibility activation review 已生成；若要让 Agent/RAG 默认使用该批数据，
  必须单独达到 `ready_for_agent_visibility=true`。

即使上述条件都满足，仍然需要单独审批 loader run command。

## 推荐下一步

1. 安装或选择已有 Python 环境，跑通 pytest 和 CLI runtime smoke。
2. 按 `docs/real-data-first-shandong-pilot.md` 选定一个官方小样本来源。
3. 填写 source review approval，生成 registry update plan，并单独审批是否
   更新 registry 元数据。
4. 手工准备 5 到 20 行样本，按 checklist 生成完整 no-write artifact。
5. 复核 artifact manifest 后，再讨论是否进入受控 loader。

相关文档：

- `docs/real-data-mvp-runbook.md`
- `docs/real-data-first-shandong-pilot.md`
- `docs/real-data-pilot-dry-run.md`
- `docs/real-data-pilot-review-checklist.md`
- `docs/data-storage-architecture.md`
