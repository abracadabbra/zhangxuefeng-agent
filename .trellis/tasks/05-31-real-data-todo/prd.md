# 待办：接入真实高考数据（分数线、就业、院校）

## Goal

建立“真实数据建设”MVP 的第一段闭环：用山东省少量官方投档数据跑通“来源 → 快照 → 解析 → 校验 → 入库候选 → Agent 可引用字段”的流程设计，让未来真实高考数据具备可追踪、可校验、可引用的基础能力。

当前阶段不追求多抓数据，也不直接替换现有 seed 数据；目标是先定义数据标准、质量门槛和山东 pilot 的最小验收范围。

## Confirmed Facts

- 现有结构化数据主要来自 `backend/seeds/` 下 JSON seed 文件，并通过 `backend/seeds/import_cli.py` 导入。
- 现有导入 CLI 已支持 `dry-run`、重复策略、导入报告，以及分数/招生计划的基础范围校验。
- 现有 `AdmissionScore`、`EnrollmentPlan`、`School`、`Major`、`SubjectRanking` ORM 模型没有官方来源、快照、血缘、置信度字段。
- 现有 Agent 工具返回已包含轻量 `source`、`source_type`、`confidence` 元数据，但 `source` 仍是逻辑表名或索引名，不是具体官方来源、年份、快照。
- 山东省教育招生考试院公开发布了“山东省2025年普通类常规批第1次志愿投档情况表”，页面带 `.xls` 附件，适合作为小样本 pilot 的官方来源。
- 河南省教育考试院也有 2025 本科批平行投档分数线入口，可作为后续对照或第二省份扩展候选。

## Requirements

- 数据来源必须可追踪：
  - 每个数据批次必须记录官方/授权来源名称、来源 URL、发布机构、省份、年份、快照标识、采集时间、文件哈希。
  - 每条 canonical 候选记录必须能追溯到来源批次和原始行号或原始定位信息。
- 数据进入系统前必须可校验：
  - quality gate 必须覆盖字段完整性、字段类型、分数/位次/年份范围、重复键冲突、跨来源冲突、覆盖率、新鲜度、置信度。
  - quality gate 必须输出结构化报告，能区分 pass、warning、blocked。
  - blocked 状态不得写入生产查询路径。
- Agent 未来回答必须可引用：
  - 面向 Agent 的数据结果必须能携带 `source`、`year`、`snapshot`、`confidence`，并保留可读来源名称或 URL。
  - 第一阶段只定义合同和 pilot 验收，不要求立刻改现有 Agent 工具。
- Pilot 必须小样本、可审计：
  - 默认 pilot 省份为山东。
  - 默认 pilot 数据源为山东省教育招生考试院 2025 普通类常规批第 1 次志愿投档情况表。
  - 默认只抽取少量院校、少量专业或专业类记录验证闭环，不做大规模爬取。
- 不破坏现有系统：
  - 不修改现有 seed JSON。
  - 不直接改变当前主查询表结构或 Agent 工具，除非后续单独审批。
  - 不让未通过 quality gate 的真实数据进入现有生产查询路径。

## Acceptance Criteria

- [ ] `design.md` 定义真实数据来源、快照、原始记录、canonical 候选记录、quality report、Agent citation metadata 的合同。
- [ ] `design.md` 明确山东 pilot 的数据流边界和不改现有系统的隔离策略。
- [ ] `implement.md` 给出小步执行清单，每一步都有验证命令或人工检查证据。
- [ ] Pilot 范围明确到省份、年份、来源类型、样本规模上限和成功/失败判定。
- [ ] Quality gate 标准明确包括字段、范围、重复冲突、覆盖率、新鲜度、置信度。
- [ ] Agent 引用输出标准明确至少包含 `source`、`year`、`snapshot`、`confidence`。
- [ ] 后续实现前必须再次提交代码操作审批包，尤其是涉及 DB、seed、Agent tool、网络下载或真实文件写入时。

## Out of Scope

- 不建设全国数据爬虫。
- 不批量抓取多个省份或多个年份。
- 不替换、删除、重写现有 seed 数据。
- 不直接迁移数据库表结构。
- 不直接修改 Agent 工具返回结构。
- 不引入未经官方或授权确认的数据源。

## Open Questions

- 山东 pilot 样本院校是否优先选择用户高频院校、985/211 院校，还是选择能覆盖不同分数段的院校。
- 第一版真实数据是否先落为隔离目录中的 snapshot/canonical/report 文件，还是在通过 quality gate 后进入独立 staging 表。
