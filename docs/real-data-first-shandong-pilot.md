# 首个山东真实小样本 Pilot

本文档用于准备第一批山东 `admission_scores` 真实小样本。目标不是扩大
数据量，而是验证 no-write 证据链能否处理一批人工复核的官方/授权样本。

当前仍然禁止：

- 大规模爬虫。
- 自动下载远程数据。
- 写入真实应用数据库。
- 修改 seed 数据。
- 刷新 RAG 或 Agent 可见数据。
- 执行 canonical loader run command。

## Pilot 范围

建议第一批只做：

- 省份：山东。
- 数据集：`admission_scores`。
- 年份：先选一个发布年份，例如 2025。
- 学校数量：5 到 20 所高关注院校。
- 行数：5 到 20 行，人工能逐行复核。
- 数据形态：优先官方公告、PDF、Excel、网页表格中的分数线数据。

不在首批做：

- 全国覆盖。
- 多省合并。
- 自动解析复杂 PDF。
- 就业、排名、政策等增强数据。
- canonical DB 写入。

## 已核对的官方入口候选

以下入口只用于人工复核和样本准备，不代表已经采集、下载或允许写库。
真正进入 snapshot 前，仍需逐项确认页面、附件、引用说明和
`source_record_ref`。

- 来源主页：
  `https://www.sdzk.cn/default.aspx`
  - 用途：登记 `sd_exam_authority` 的主页。
  - 复核状态：候选。
- 投档情况：
  `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996`
  - 用途：可作为 2025 普通类常规批第 1 次志愿
    `admission_scores` 小样本候选来源。
  - 建议：优先人工抽取 5 到 20 行。
  - 复核状态：候选。
- 投档情况：
  `https://cdn.sdzk.cn/NewsInfo.aspx?NewsID=7010`
  - 用途：可作为 2025 普通类常规批第 2 次志愿补充候选来源。
  - 建议：首批不混入多个志愿批次，除非 source review 明确批准。
  - 复核状态：候选。
- 分数线：
  `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6941`
  - 用途：只用于控制线或背景复核。
  - 限制：不直接混入院校投档行。
  - 复核状态：候选。
- 招考热点列表：
  `https://www.sdzk.cn/NewsListM.aspx?BCID=12&CID=1198`
  - 用途：查找院校计划、分数线、分段表等官方列表页。
  - 复核状态：候选。
- 普通招考列表：
  `https://cdn.sdzk.cn/NewsList.aspx?BCID=20&CID=1204`
  - 用途：查找后续第 2 次、第 3 次等投档情况表。
  - 复核状态：候选。
- 录取工作意见：
  `https://cdn.sdzk.cn/NewsInfo.aspx?NewsID=6928`
  - 用途：作为 `policies` 背景材料。
  - 限制：不作为分数线候选行。
  - 复核状态：候选。
- 招生实施办法：
  `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6866`
  - 用途：作为 `policies` 背景材料。
  - 限制：不作为分数线候选行。
  - 复核状态：候选。

如果要使用“普通类常规批第 1 次志愿投档情况表”，必须先拿到
山东省教育招生考试院官方 `NewsInfo` 或附件 URL；第三方转载、镜像或
搜索摘要不能作为 snapshot 的 `source_url`。

## 2026-06-08 网页核对记录

本次只做官方入口核对，不下载附件、不采集数据、不创建 raw snapshot。

- `https://www.sdzk.cn/default.aspx`
  - 状态：可访问山东省教育招生考试院官网首页。
  - 用途：继续作为 `sd_exam_authority.homepage_url`。
- `https://www.sdzk.cn/NewsList.aspx?BCID=1198&CID=47`
  - 状态：院校投档情况列表页可访问。
  - 页面列出 2025 年普通类常规批第 1、2、3 次志愿投档情况表。
  - 用途：定位官方 `NewsInfo` 页面，不直接作为 snapshot 文件来源。
- `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996`
  - 状态：页面标题为 2025 年普通类常规批第 1 次志愿投档情况表。
  - 页面显示发布时间为 2025-07-19，并提供 `.xls` 附件链接。
  - 用途：建议作为首批 `admission_scores` 人工 intake 候选。
- `https://cdn.sdzk.cn/NewsInfo.aspx?NewsID=7010`
  - 状态：页面标题为 2025 年普通类常规批第 2 次志愿投档情况表。
  - 页面显示发布时间为 2025-07-28，并提供 `.xls` 附件链接。
  - 用途：可作为后续补充候选；首批建议先固定第 1 次志愿。
- `https://www.sdzk.cn/NewsInfo.aspx?NewsID=7019`
  - 状态：页面标题为 2025 年普通类常规批第 3 次志愿投档情况表。
  - 页面显示发布时间为 2025-08-01，并提供 `.xls` 附件链接。
  - 用途：可作为后续补充批次候选，不建议首批同时混入多个批次。
- `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6941`
  - 状态：页面标题为 2025 年夏季高考各类别分数线。
  - 页面显示发布时间为 2025-06-25，并提供 `.pdf` 附件链接。
  - 用途：只做控制线或背景复核，不混入院校投档行。

注意：官网页脚包含“未经授权不得复制、转载、建立镜像”提示。每个
snapshot 的 `license_note` 必须记录引用、内部使用和再分发限制的人工复核
结论。

Registry 对齐：`sd_exam_authority.coverage.years` 已登记 `[2025]`，表示
2025 官方页面候选已在 2026-06-08 做过网页入口核对。这不表示来源已
`reviewed`，也不跳过 snapshot 级 license、附件和逐行复核。

## Step 0. 环境检查

先跑 no-write 环境检查：

```bash
python -m backend.data_pipeline.env_check
```

进入后续 CLI 前必须满足：

- `python_version_ok=true`
- `ready_for_cli_runtime=true`

如果只准备运行真实数据 CLI，可先用：

```bash
python -m backend.data_pipeline.env_check --runtime-only
```

## Step 1. Source 复核

优先使用已登记的 `sd_exam_authority`，但必须复核本次具体数据页：

- 是否为山东官方或授权来源。
- 页面或文件是否可追溯。
- 是否允许公开引用或内部使用。
- 本次数据类别是否为 `admission_scores`。
- 本次样本年份是否能解释清楚。

生成 source audit：

```bash
python -m backend.data_pipeline.sources.cli \
  backend/data_pipeline/sources/sources.json \
  --data-category admission_scores \
  --province 山东 \
  --year 2025 \
  --require-reviewed \
  --audit-output artifacts/real_data/sd_source_audit.json
```

进入下一步前，source audit 必须无 error。warning 必须人工处理，不能带到
`ready_for_loader_execution=true`。同时检查 JSON 里的 `scope` 是否准确记录
`admission_scores`、山东、2025 和 `require_reviewed=true`。

## Step 2. Snapshot 准备

本地保存原始文件，不覆盖、不改写原件：

```text
data/raw/sd_exam_authority/admission_scores/2025/<snapshot_id>/
  manifest.json
  files/
    original.*
```

`manifest.json` 必须包含：

- `snapshot_id`
- `source_id=sd_exam_authority`
- `dataset=admission_scores`
- `source_url`
- `published_year`
- `collected_at`
- `collector=manual`
- `collector_version`
- `files[].path`
- `files[].sha256`
- `license_note`

`files[].sha256` 必须来自原始文件内容。

## Step 2.5 Intake 模板

准备真实 rows bundle 前，先复制并填写：

```text
examples/real_data/sd_official_sample_intake_template.json
```

该模板只用于人工 intake，不是 dry-run bundle。它记录本次官方页面或附件、
本地 snapshot、逐行复核字段、`quality_config` 和 stop gates。所有空字段
补齐并完成人工复核后，才把样本行整理成 rows bundle。

进入 snapshot 准备前，先运行 no-write intake review：

```bash
python -m backend.data_pipeline.intake.cli \
  path/to/sd_official_sample_intake.json \
  --review-output artifacts/real_data/sd_intake_review.json
```

必须满足：

- `passed=true`
- `ready_for_snapshot=true`
- `issue_counts.error=0`

该命令只检查本地 intake JSON，不下载附件、不创建 snapshot、不解析 rows，
也不执行 loader。

## Step 3. Rows Bundle

人工整理 5 到 20 行 normalized rows。每行必填：

- `school_name`
- `province=山东`
- `year`
- `batch`
- `subject_type`

推荐填写：

- `major_name`
- `min_score`
- `avg_score`
- `max_score`
- `min_rank`
- `source_record_ref`
- `confidence`

`source_record_ref` 必须能定位回原始文件，例如页码、sheet、表格行号
或网页位置。

### 人工抽样 worksheet

整理 rows bundle 前，建议先用本地表格或纸面清单逐行复核。每条样本行
至少记录以下内容：

- 来源定位：
  - `source_url`
  - `snapshot_id`
  - 原始文件名
  - 页码、sheet 名、表格行号或网页位置
- canonical natural key：
  - 学校名称
  - 专业名称，没有专业维度时留空并说明
  - 省份
  - 年份
  - 批次
  - 科类或选科类型
- 分数字段：
  - 最低分
  - 平均分，如官方未给出则留空
  - 最高分，如官方未给出则留空
  - 最低位次，如官方未给出则留空
- 复核信息：
  - 摘录人
  - 复核人
  - 复核日期
  - 是否逐字核对学校名、专业名、批次和分数
  - 是否确认该行不是第三方转载或二次加工数据
- rows bundle 映射：
  - `school_name`
  - `major_name`
  - `province`
  - `year`
  - `batch`
  - `subject_type`
  - `min_score`
  - `min_rank`
  - `source_record_ref`
  - `confidence`
  - `review.extracted_by`
  - `review.reviewed_by`
  - `review.reviewed_at`
  - `review.notes`

阻断条件：

- `source_record_ref` 不能定位回原始记录。
- 官方文件或页面缺少可解释的发布年份。
- 学校名、专业名、批次或科类无法和原文对应。
- 分数或位次来自人工计算，而不是官方原始字段。
- 该行来自第三方转载、截图或摘要。
- 复核人未完成逐行核对。

如果人工复核表已经导出为 CSV，可先生成 rows bundle：

```bash
python -m backend.data_pipeline.parsers.tabular_cli \
  path/to/reviewed_rows.csv \
  --dataset admission_scores \
  --output path/to/sd_pilot_rows.json
```

该 CLI 只读取本地 CSV 并规范化空值、数值和 `review.*` 字段，不下载附件、
不创建 snapshot，也不执行 loader。

`quality_config` 建议：

```json
{
  "current_year": 2026,
  "expected_provinces": ["山东"],
  "expected_years": [2025],
  "require_review_metadata": true
}
```

## Step 4. Dry-run

只做 no-write dry-run：

```bash
python -m backend.data_pipeline.pilots.cli \
  --snapshot-dir data/raw/sd_exam_authority/admission_scores/2025/<snapshot_id> \
  --audit-output artifacts/real_data/sd_pilot_audit.json \
  --approval-output artifacts/real_data/sd_pilot_loader_approval.json \
  path/to/sd_pilot_rows.json
```

必须检查：

- `load_ready=true`
- `blockers=[]`
- `snapshot_file_issues=[]`
- `source_validation_issues=[]`
- `coverage.missing_expected_provinces=[]`
- `coverage.missing_expected_years=[]`
- `review_status=ready_for_loader_review`

如果出现 `needs_warning_review` 或 `blocked`，停止并修复样本或范围。

## Step 5. Artifact Manifest

汇总证据包：

```bash
python -m backend.data_pipeline.pilots.artifacts_cli \
  --source-audit artifacts/real_data/sd_source_audit.json \
  --intake-review artifacts/real_data/sd_intake_review.json \
  --dry-run-audit artifacts/real_data/sd_pilot_audit.json \
  --loader-approval artifacts/real_data/sd_pilot_loader_approval.json \
  --rows-bundle path/to/sd_pilot_rows.json \
  --snapshot-dir data/raw/sd_exam_authority/admission_scores/2025/<snapshot_id> \
  --manifest-output artifacts/real_data/sd_pilot_artifact_manifest.json
```

进入 loader 讨论前必须满足：

- `artifact_path_issues=[]`
- `intake_review_issues=[]`
- `artifact_scope_issues=[]`
- `loader_approval_issues=[]`
- `ready_for_loader_execution=true`
- `review_summary.source_audit_scope` 与本次 pilot 范围一致

即使满足，也只表示证据包齐全。真实 DB 写入仍需单独审批 loader run
command。

## Step 6. Answer Source Policy（loader 后）

只有在后续单独审批并执行 canonical loader，且已经得到本地工具响应
JSON 后，才进入回答来源策略复核：

```bash
python -m backend.data_pipeline.lineage.policy_cli \
  path/to/tool_response.json \
  --policy-output artifacts/real_data/sd_answer_source_policy.json
```

如果只有工具响应里的 `source_summary`：

```bash
python -m backend.data_pipeline.lineage.policy_cli \
  path/to/source_summary.json \
  --summary-only \
  --policy-output artifacts/real_data/sd_answer_source_policy.json
```

必须检查：

- `action=answer_source_policy_review`
- `answer_source_policy.answer_mode` 不是 `unsupported`
- `non_goals` 明确不刷新 RAG 或 Agent

`citeable_with_caution` 可以进入后续复核，但 Agent 回答必须引用来源并降低
确定性。

## Step 7. Agent Visibility Activation（单独审批）

即使 answer policy 通过，也不能让 Agent/RAG 默认使用该批数据。必须再运行
Agent visibility activation review：

```bash
python -m backend.data_pipeline.activation.cli \
  --artifact-manifest artifacts/real_data/sd_pilot_artifact_manifest.json \
  --answer-policy-review artifacts/real_data/sd_answer_source_policy.json \
  --activation-approval artifacts/real_data/sd_agent_visibility_approval.json \
  --review-output artifacts/real_data/sd_agent_visibility_activation_review.json
```

`activation_approval` 必须来自单独人工审批，并至少包含：

- `action=agent_visibility_approval`
- `allow_agent_visibility=true`
- `loader_run_confirmed=true`
- `reviewed_by` / `reviewed_at`
- `scope.source_id=sd_exam_authority`
- `scope.snapshot_id=<snapshot_id>`
- `scope.dataset=admission_scores`

只有 `ready_for_agent_visibility=true` 才能进入单独的 Agent/RAG refresh 或部署
流程。该 review 本身仍不执行 refresh。

## 停止点

必须停止并复核的情况：

- source audit 有 error 或 warning。
- 原始文件没有 checksum。
- `source_url` 不可追溯。
- rows 缺 natural key。
- `source_record_ref` 无法定位原始记录。
- dry-run 出现 blocker。
- artifact manifest 出现 `artifact_path_issues`。
- artifact manifest 出现 `intake_review_issues`。
- artifact manifest 出现 `artifact_scope_issues`。
- artifact manifest 出现 `loader_approval_issues`。
- answer policy review 为 `unsupported`。
- Agent visibility activation review 未达到 `ready_for_agent_visibility=true`。
- 任何步骤需要写 DB、改 seed、刷新 RAG 或让 Agent 默认使用该数据。

## 完成定义

首个山东小样本 pilot 的 no-write 完成标准：

- source audit JSON 已生成且无 error/warning。
- source audit scope 与 artifact manifest review summary 一致。
- raw snapshot 目录和 manifest 已人工复核。
- rows bundle 已人工复核。
- dry-run audit 已生成且 `load_ready=true`。
- loader approval packet 已生成。
- artifact manifest 已生成且 `ready_for_loader_execution=true`。
- artifact manifest 的 `artifact_path_issues`、`intake_review_issues`、
  `artifact_scope_issues` 和 `loader_approval_issues` 为空。
- 尚未执行 canonical loader。
- 尚未刷新 RAG 或让 Agent 默认使用该批数据。
- 如果后续执行 loader，必须补 answer policy review 和 Agent visibility
  activation review。
