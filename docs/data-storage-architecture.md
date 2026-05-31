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
| `python -m seeds.import_data` | 基础导入，只导入基础文件 |
| `python -m seeds.import_extended` | 扩展导入，合并所有文件，支持增量更新（get_or_create） |
| `python -m seeds.data_quality` | 数据质量检查，检查必填字段、唯一性、范围等 |

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

## 总结

- **结构化数据**（院校/专业/分数线/招生计划）: SQLite + SQLAlchemy ORM，通过 JSON 种子文件导入
- **会话数据**: 内存字典（开发阶段），重启丢失
- **用户画像**: Redis（`user:{session_id}:profile`，TTL 24 小时），不可用时降级为内存
