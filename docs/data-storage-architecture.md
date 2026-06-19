# 数据存储架构

本文档描述张雪峰 AI 咨询 Agent 项目的数据存储架构，涵盖数据库选型、数据模型、种子数据导入、会话存储。

---

## 1. 数据库选型与 ORM 层

### 数据层

- **数据库**: SQLite（文件路径 `backend/zhangxuefeng.db`）
- **ORM**: SQLAlchemy + Alembic 迁移
- **连接配置**: `backend/database.py`

```python
DATABASE_URL = "sqlite:///backend/zhangxuefeng.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
```

- **依赖注入**: 通过 `get_db()` 函数注入到 FastAPI 路由

---



## 2. 数据模型定义

### School（院校表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String(100) | 院校名称（唯一） |
| province | String(20) | 所在省份 |
| city | String(30) | 所在城市 |
| level | String(20) | 层次：985/211/双一流/普通 |
| school_type | String(20) | 类型：综合/理工/医药等 |
| ranking | Integer | 软科排名 |
| is_985 | Integer | 是否 985 |
| is_211 | Integer | 是否 211 |
| is_double_first_class | Integer | 是否双一流 |

### Major（专业表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String(100) | 专业名称（唯一） |
| category | String(50) | 学科门类 |
| sub_category | String(50) | 专业类 |
| employment_rate | Float | 就业率 |
| avg_salary | Float | 平均月薪 |
| is_hot | Integer | 是否热门 |

### AdmissionScore（分数线表）

| 字段 | 类型 | 说明 |
|------|------|------|
| school_id | Integer | 院校ID（FK） |
| major_id | Integer | 专业ID（可为空） |
| province | String(20) | 招生省份 |
| year | Integer | 年份 |
| batch | String(20) | 批次 |
| subject_type | String(10) | 科类 |
| min_score | Integer | 最低分 |
| avg_score | Float | 平均分 |
| max_score | Integer | 最高分 |
| min_rank | Integer | 最低位次 |

### EnrollmentPlan（招生计划表）

| 字段 | 类型 | 说明 |
|------|------|------|
| school_id | Integer | 院校ID（FK） |
| major_id | Integer | 专业ID（FK） |
| province | String(20) | 招生省份 |
| year | Integer | 年份 |
| plan_count | Integer | 计划人数 |
| subject_requirement | String(100) | 选科要求 |
| duration | Integer | 学制 |
| tuition | Integer | 学费 |

---

## 3. 种子数据导入

### 存储格式

JSON 文件，位于 `backend/seeds/` 目录，按数据类型和区域拆分：

- **院校**: `seed_schools.json`, `seed_schools_v2.json`, `seed_schools_extended.json`, `seed_schools_{区域}.json`
- **专业**: `seed_majors.json`, `seed_majors_extended.json`, `seed_majors_expanded.json`
- **分数线**: `seed_scores.json`, `seed_scores_v2.json`, `seed_scores_extended.json`, `seed_scores_province.json`
- **招生计划**: `seed_plans.json`, `seed_plans_v2.json`, `seed_plans_extended.json`

### 导入方式

| 命令 | 说明 |
|------|------|
| `python -m backend.seeds.import_cli --dataset basic --dry-run` | 基础数据预检，不写入数据库 |
| `python -m backend.seeds.import_cli --dataset extended --duplicate-policy update --report-path data/import-report.json` | 扩展数据增量导入，重复数据更新并输出导入报告 |
| `python -m backend.seeds.import_cli --dataset full --duplicate-policy skip` | 全量院校/专业/分数线导入，重复数据跳过 |
| `python -m backend.seeds.data_quality` | 数据质量检查，检查必填字段、唯一性、范围等 |

---

## 4. 会话数据存储

- **存储位置**: Python 字典（进程内存），重启丢失
- **结构**: `sessions: dict[str, dict]`
- **用户画像**: Redis（`user:{session_id}:profile`，TTL 24 小时），Redis 不可用时降级为内存
- **API 路径**: `POST /chat`

---

## 5. 数据查询路径

```
用户请求 → POST /chat
  ↓
获取/创建会话（内存字典）
  ↓
提取实体（分数、省份、科类等）
  ↓
构建 UserProfile
  ↓
灵魂追问检查（不完整则返回追问问题）
  ↓
画像完整 → 加载 SKILL.md 系统提示
  ↓
构建上下文消息（skill + history + message + user_context）
  ↓
调用 LLM（支持流式/非流式）
  ↓
保存消息到 Redis
  ↓
返回响应
```

### 数据查询

```
用户请求 → /schools/{id} 或 /schools/search
  ↓
FastAPI 路由
  ↓
get_db() 依赖注入（SQLAlchemy Session）
  ↓
CRUD 操作（backend/crud/school.py）
  ↓
SQLAlchemy ORM 查询 SQLite
  ↓
返回 Pydantic Schema
```

---

## 6. 真实数据流水线 MVP

真实数据建设采用“先可追踪、可校验、可引用，再扩大数据量”的策略。
MVP 不直接大规模爬取，也不修改现有 seed 数据，而是在现有
canonical 表之外增加来源、快照和血缘侧表。

### 目标链路

```text
官方/授权数据源
  ↓
source registry（数据源登记）
  ↓
raw snapshot manifest（原始快照元数据）
  ↓
manual parser（手工审核样本解析）
  ↓
canonical candidates（候选行）
  ↓
quality gate（入库前质量门禁）
  ↓
canonical loader（受控写入）
  ↓
lineage records（血缘记录）
  ↓
Agent tools（返回 source/year/confidence）
  ↓
answer source policy review（回答引用门禁）
  ↓
Agent visibility activation review（Agent/RAG 可见性门禁）
```

### MVP 模块

| 模块 | 路径 | 说明 |
|------|------|------|
| 数据源登记 | `backend/data_pipeline/sources/` | 保存来源、覆盖范围、可信度 |
| 原始快照 | `backend/data_pipeline/raw_store/` | 定义 snapshot manifest 和文件 checksum |
| 解析器 | `backend/data_pipeline/parsers/` | 手工样本转候选行，不爬远程数据 |
| 质量门禁 | `backend/data_pipeline/quality/` | 校验字段、范围、重复、新鲜度 |
| 血缘服务 | `backend/data_pipeline/lineage/` | 读写 source、snapshot、entity 来源关系 |
| 受控加载 | `backend/data_pipeline/loaders/` | audit 通过后写 canonical 与 lineage |
| Pilot dry-run | `backend/data_pipeline/pilots/` | 本地 bundle 转 audit report，不写 DB |
| 可见性复核 | `backend/data_pipeline/activation/` | Agent/RAG 可见性门禁 |

source registry 提供 `audit_scope(...)` 做只读范围审计。它用于检查计划中的
dataset、省份、年份是否已有登记来源，并把 candidate/reviewed 状态和年份覆盖
缺口显式暴露给人工复核；它不采集远程数据，也不写入 DB。

命令行入口是 `python -m backend.data_pipeline.sources.cli`，输出 JSON audit
report，可用于人工审批包或 CI 预检查。

---

## 7. 真实数据血缘表

Alembic 迁移 `004_data_lineage` 新增 3 张侧表，不改变现有院校、专业、
分数线、招生计划表结构。

### data_sources（数据源登记表）

| 字段 | 说明 |
|------|------|
| source_id | 稳定来源 ID，如 `sd_exam_authority` |
| name | 来源名称 |
| source_type | 来源类型，如省考试院、教育部、高校招生办 |
| homepage_url | 来源主页 |
| data_categories | 覆盖的数据类别 JSON |
| coverage_json | 覆盖省份、年份等范围 JSON |
| trust_score | 来源可信度 |
| update_frequency | 更新频率 |
| collection_method | 采集方式，MVP 优先 manual download |
| license_note | 使用和引用说明 |
| review_status | candidate / reviewed 等复核状态 |

### data_snapshots（数据快照表）

| 字段 | 说明 |
|------|------|
| snapshot_id | 稳定快照 ID |
| source_id | 关联 `data_sources.source_id` |
| dataset | 数据集类型，如 `admission_scores` |
| source_url | 原始数据 URL 或下载页 |
| published_year | 官方发布年份 |
| collected_at | 采集/整理时间 |
| collector | 采集器名称，MVP 可为 `manual` |
| collector_version | 采集器版本 |
| files_json | 原始文件路径、checksum、content type |
| status | 快照状态 |

### data_lineage_records（数据血缘表）

| 字段 | 说明 |
|------|------|
| entity_type | canonical 实体类型，如 `admission_score` |
| entity_id | canonical 表主键；允许为空以支持先按 natural key 记录 |
| natural_key_json | 学校、专业、省份、年份、批次等自然键 |
| snapshot_id | 来源快照 |
| source_record_ref | 原文件定位，如页码、行号、sheet 行 |
| parser_name | 解析器名称 |
| parser_version | 解析器版本 |
| quality_status | quality gate 结果 |
| confidence | 单条数据置信度 |

血缘记录是追加式审计历史。重复 load 可以产生新的 lineage record，
用于保留不同快照、不同解析器版本或不同复核状态的来源证据。

---

## 8. Pilot Dry-run 与入库门禁

真实数据试点先使用本地 bundle 干跑：

```bash
python -m backend.data_pipeline.pilots.cli examples/real_data/sd_pilot_bundle.json
```

dry-run 只输出 audit report：

- 不爬取远程网站
- 不写入 SQLite
- 不修改 seed JSON
- 不刷新 RAG
- 不调用 canonical loader

只有当 audit report 满足 `load_ready=true` 且 `blockers=[]`，才允许进入
下一步 loader 审批。真实 DB 写入必须单独确认，并优先使用受控入口
`load_candidates_after_artifact_manifest(...)`，该入口会检查完整 artifact
manifest 的 loader-ready 状态。`load_candidates_after_audit(...)` 保留为低层
dry-run guard。

---

## 9. Agent 数据引用

Agent 工具查询分数线、招生计划时，结果项可附带 `sources` 数组，包含：

| 字段 | 说明 |
|------|------|
| source_id | 来源 ID |
| name | 来源名称 |
| source_type | 来源类型，如省考试院、教育部、高校招生办 |
| source_url | 快照原始 URL |
| published_year | 官方发布年份 |
| snapshot_id | 快照 ID |
| source_record_ref | 原始记录定位 |
| confidence | 置信度 |
| freshness | current / stale / expired / unknown |
| quality_status | 质量门禁状态 |
| trust_score | 来源登记可信度 |
| review_status | 来源登记复核状态 |
| license_note | 引用、转载、授权或待复核说明 |

结果项还可附带 `source_summary`：

| 字段 | 说明 |
|------|------|
| source_count | 来源数量 |
| citation_ready | 是否已有可引用来源 |
| needs_caution | 是否需要降低回答确定性或提示谨慎 |
| best_confidence | 最高单条来源置信度 |
| best_trust_score | 最高来源登记可信度 |
| freshness | 当前结果来源中的最弱 freshness 状态 |
| review_statuses | 涉及的来源复核状态列表 |

该结构是附加字段，不改变现有查询结果的核心字段。后续 RAG/Agent
回答应优先使用带来源、年份和置信度的数据，并在缺少来源、缺少
confidence / trust score / review status、来源过期、低置信或未复核时
降低回答确定性。

工具响应顶层还可附带聚合后的 `source_summary`，用于描述本次返回结果的
整体引用状态：

| 字段 | 说明 |
|------|------|
| item_count | 返回结果项数量 |
| items_with_sources | 带可引用来源的结果项数量 |
| items_needing_caution | 需要谨慎回答的结果项数量 |
| source_count | 本次结果涉及的来源总数 |
| citation_ready | 是否所有返回项都有可引用来源 |
| needs_caution | 是否任一返回项需要谨慎回答 |

工具响应顶层还可附带 `answer_source_policy`，这是由 `source_summary`
投影出的回答层门禁：

| 字段 | 说明 |
|------|------|
| answer_mode | `citeable` / `citeable_with_caution` / `unsupported` |
| citation_ready | 是否可以引用来源 |
| requires_citation | 回答是否必须带来源 |
| requires_caution | 回答是否必须提示谨慎或降低确定性 |
| allowed_default_answer | 是否允许不加谨慎提示地默认回答 |
| reasons | 触发该策略的原因列表 |

当前工具层覆盖 `search_admission`、`search_enrollment_plan` 和
`calculate_match`。其他仍使用预置库或语义搜索的工具暂不声明为真实数据
引用入口。

回答来源策略可通过 no-write CLI 复核：

```bash
python -m backend.data_pipeline.lineage.policy_cli path/to/tool_response.json
```

非流式 `AgentCore.chat()` 会把本轮 tool results 的 `answer_source_policy`
汇总成 additive `answer_source_policy_review` 返回给调用方。该汇总采用保守
规则：任一工具 unsupported、缺少 policy 或返回未知 answer mode 时，整体
按 unsupported/caution 处理。当前该字段不改变 stream 事件、不刷新 RAG，
也不授权 Agent 默认可见数据。

`/chat` 非流式响应会透传该 review。SSE 流式响应会在每个 `tool_result`
后追加一条 message：

```json
{
  "type": "answer_source_policy_review",
  "review": {
    "overall_answer_mode": "citeable_with_caution",
    "requires_citation": true,
    "requires_caution": true
  }
}
```

前端或调用方可以忽略该 additive 事件；忽略时旧的 text/tool_call/tool_result
/done 流程保持不变。

即使工具结果可引用，也不能直接进入 Agent/RAG 默认可见数据。需要单独的
Agent visibility activation review：

```bash
python -m backend.data_pipeline.activation.cli \
  --artifact-manifest path/to/pilot_artifact_manifest.json \
  --answer-policy-review path/to/answer_source_policy.json \
  --activation-approval path/to/agent_visibility_approval.json
```

该 review 要求 artifact manifest、answer policy、loader run 确认和
activation approval 的 scope 对齐；它只生成复核 JSON，不执行 RAG refresh，
也不修改 Agent 可见数据。

---

## 总结

- **结构化数据**（院校/专业/分数线/招生计划）: SQLite + SQLAlchemy ORM，通过 JSON 种子文件导入
- **会话数据**: 内存字典（开发阶段），重启丢失
- **用户画像**: Redis（`user:{session_id}:profile`，TTL 24 小时），不可用时降级为内存
- **真实数据 MVP**: 通过 source registry、snapshot manifest、quality gate、
  lineage tables、Agent `sources` envelope 和 activation review 建立可追踪、
  可校验、可引用、可控可见的数据闭环
