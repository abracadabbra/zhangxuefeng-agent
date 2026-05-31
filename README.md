# 张雪峰 AI 咨询 Agent

> 张雪峰的认知操作系统，可运行的高考/考研/职业规划顾问

基于 OpenAI Function Calling 构建的智能教育咨询 Agent，模拟张雪峰的思维方式，为考生和家长提供个性化的升学规划建议。系统通过"灵魂追问"机制自动收集用户画像，结合院校数据库和政策库，给出精准的选校选专业建议。

## 功能特性

### 核心能力

- **高考志愿咨询** — 根据分数、省份、家庭背景，给出选校选专业建议
- **考研规划** — 择校、择专业、备考策略
- **职业规划** — 应届生就业方向、行业选择
- **灵魂追问** — 多轮对话自动收集用户画像（分数、省份、科类、家庭条件等），画像完整后才进入正式咨询
- **AI 驱动** — 基于张雪峰心智模型（SKILL.md）+ 实时数据查询

### 工具系统（Function Calling）

系统注册了 6 个工具，Agent 可根据对话上下文自动调用：

| 工具 | 功能 |
|------|------|
| `search_admission` | 搜索高校录取分数线 |
| `search_employment` | 搜索专业就业数据（就业率、薪资、方向） |
| `compare_schools` | 多院校综合对比 |
| `search_policy` | 搜索招生政策（强基计划、提前批、专项计划等） |
| `calculate_match` | 根据分数匹配院校推荐（冲/稳/保策略） |
| `semantic_search` | 语义搜索学校和专业（基于向量相似度） |

### 其他特性

- SSE 流式输出，实时展示思考和工具调用过程
- 会话持久化（Redis），支持多轮上下文
- 对话记录导出（Markdown / PDF 报纸风格排版）
- 用户反馈系统（评分 + 评论）
- 速率限制 + 安全校验中间件
- Sentry 错误监控集成

## 界面预览

<img src="docs/index.png" width="800">

<img src="docs/chat.png" width="800">

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Redis（本地开发或 Upstash）

### 本地开发

```bash
# 1. 克隆项目
git clone <repo-url>
cd zhangxuefeng-agent

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -e ".[dev]"

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填入 OPENAI_API_KEY

# 5. 启动 Redis（如本地未运行）
redis-server

# 6. 初始化数据库
alembic upgrade head

# 7. 导入种子数据（可选）
python -m backend.seeds.seed_all

# 8. 启动后端
uvicorn backend.main:app --reload --port 8000

# 9. 启动前端（新终端）
cd frontend && npm install && npm run dev
```

启动后访问：
- 前端：http://localhost:3000
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### Docker Compose

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY

# 2. 启动所有服务
docker compose up -d

# 3. 查看日志
docker compose logs -f api

# 4. 停止服务
docker compose down
```

Docker Compose 会自动启动：
- `api` — FastAPI 后端（端口 8000）
- `redis` — Redis 7（端口 6379）
- SQLite 数据通过 Docker Volume 持久化

## API 文档

### 通用说明

- 基础路径：`http://localhost:8000`
- 数据格式：JSON
- 会话机制：通过 `session_id` 维护多轮对话上下文
- 认证方式：无（开发环境），生产环境建议添加 API Key 认证

### 对话接口

#### POST `/chat` — 核心对话

支持普通模式和 SSE 流式模式。

**请求体：**

```json
{
  "session_id": "可选，空则自动创建新会话",
  "message": "我考了580分，山东考生，理科，想学计算机",
  "user_context": {
    "分数": 580,
    "省份": "山东",
    "科类": "理科"
  },
  "stream": false
}
```

**响应（非流式）：**

```json
{
  "session_id": "uuid",
  "reply": "580分山东理科考生，想学计算机...",
  "model": "gpt-4o-mini",
  "tool_calls": [
    {"name": "calculate_match", "arguments": {"score": 580, "province": "山东", "category": "理科"}}
  ],
  "usage": {"prompt_tokens": 1200, "completion_tokens": 800, "total_tokens": 2000}
}
```

**SSE 流式请求：**

```bash
curl -N http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "580分山东理科，推荐学校", "stream": true}'
```

流式事件类型：
- `text` — 文本片段
- `tool_call` — Agent 调用工具
- `tool_result` — 工具返回结果
- `done` — 流结束（含 token 用量）

### 画像管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/profile/{session_id}` | 获取用户画像 |
| PUT | `/profile/{session_id}` | 更新画像字段 |
| GET | `/profile/{session_id}/next-question` | 获取下一个追问问题 |

**更新画像示例：**

```bash
curl -X PUT http://localhost:8000/profile/{session_id} \
  -H "Content-Type: application/json" \
  -d '{"field": "score", "value": "580"}'
```

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/sessions` | 列出最近会话（支持 `?limit=20`） |
| GET | `/session/{session_id}` | 获取会话详情及完整消息历史 |
| DELETE | `/session/{session_id}` | 删除会话 |
| GET | `/session/{session_id}/export` | 导出为 Markdown |
| GET | `/session/{session_id}/export/pdf` | 导出为 PDF（报纸风格） |

### 数据查询 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/schools/{school_id}` | 根据 ID 查询院校 |
| GET | `/schools/by-name/{name}` | 根据名称查询院校 |
| GET | `/majors/{major_id}` | 查询专业详情 |
| GET | `/scores/` | 查询录取分数线（支持筛选） |
| GET | `/plans/` | 查询招生计划 |
| GET | `/subject-rankings/` | 查询学科排名 |

### 其他接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 服务信息 |
| GET | `/health` | 健康检查 |
| GET | `/db/status` | 数据库状态 |
| GET | `/tools` | 列出所有已注册工具定义 |
| POST | `/cache/flush` | 清除应用缓存 |
| POST | `/recommend` | 结构化推荐（需 LangChain 模式） |
| POST | `/api/v1/feedback` | 提交用户反馈 |
| GET | `/api/v1/feedback/stats` | 反馈统计 |

## 配置说明

### 环境变量

所有配置通过 `.env` 文件或环境变量注入，参见 `.env.example`：

```bash
# ===== 必填 =====
OPENAI_API_KEY=sk-xxx              # OpenAI API 密钥

# ===== LLM 配置 =====
OPENAI_BASE_URL=https://api.openai.com/v1  # API 地址（支持代理）
MODEL=gpt-4o-mini                          # 模型名称

# ===== Redis =====
REDIS_URL=redis://localhost:6379/0  # 本地开发
# REDIS_URL=rediss://default:<password>@<host>:<port>  # Upstash 生产

# ===== 数据库 =====
DATABASE_URL=sqlite:///./data/zhangxuefeng.db

# ===== 应用 =====
DEBUG=false
SKILL_PATH=SKILL.md                 # 张雪峰人设 Prompt 文件路径
CORS_ORIGINS=*                      # CORS 允许的源（逗号分隔）

# ===== 监控 =====
SENTRY_DSN=                         # Sentry DSN（可选）
COST_ALERT_THRESHOLD_USD=50.0       # LLM 调用成本预警阈值

# ===== LangChain 模式（可选） =====
USE_LANGCHAIN=false                 # 设为 true 启用 LangChain Agent
LLM_PROVIDER=openai                 # openai / anthropic
LLM_MODEL=gpt-4o-mini
ANTHROPIC_API_KEY=                  # 使用 Anthropic 模型时填写
```

### 人设 Prompt（SKILL.md）

`SKILL.md` 是张雪峰 AI 的核心人设定义文件，作为 LLM 的 System Prompt 加载。包含：
- 角色设定和说话风格
- 咨询流程和决策规则
- 工具使用策略
- 禁忌和边界

修改此文件可自定义 Agent 的行为方式。

## 部署指南

### Fly.io 部署

```bash
# 1. 安装 Fly CLI
curl -L https://fly.io/install.sh | sh

# 2. 登录
fly auth login

# 3. 创建应用（首次）
fly launch --no-deploy

# 4. 设置密钥
fly secrets set OPENAI_API_KEY=sk-xxx
fly secrets set REDIS_URL="rediss://default:<password>@<host>:<port>"

# 5. 部署
fly deploy

# 6. 查看状态
fly status
fly logs
```

**Upstash Redis 配置：**

1. 在 [Upstash Console](https://console.upstash.com) 创建 Redis 数据库
2. 选择区域 `Hong Kong (ap-east)` 与 Fly.io 同区域
3. 复制 `REDIS_URL`（带 `rediss://` 前缀）
4. 通过 `fly secrets set REDIS_URL=...` 注入

### Docker 部署

```bash
# 构建镜像
docker build -t zhangxuefeng-agent .

# 运行（配合外部 Redis）
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-xxx \
  -e REDIS_URL=redis://your-redis:6379/0 \
  -v ./data:/app/data \
  zhangxuefeng-agent
```

### 生产环境建议

- 使用 `redis://` 以外部 Redis 替代容器内 Redis
- 设置 `CORS_ORIGINS` 为具体域名，不要使用 `*`
- 配置 `SENTRY_DSN` 开启错误监控
- 使用反向代理（Nginx / Caddy）处理 HTTPS
- 设置 `DEBUG=false`

## 开发指南

### 项目结构

```
zhangxuefeng-agent/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 应用入口 + 核心 API
│   ├── agent/                  # Agent 核心
│   │   ├── core.py             # OpenAI Function Calling 主循环
│   │   └── prompt.py           # 内置 System Prompt（SKILL.md 的 fallback）
│   ├── tools/                  # 工具系统
│   │   ├── definitions.py      # 6 个工具的实现
│   │   └── registry.py         # 装饰器注册表 + 分发
│   ├── models/                 # SQLAlchemy ORM 模型
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── crud/                   # 数据库 CRUD 操作
│   ├── routers/                # 数据查询 API 路由
│   ├── seeds/                  # 种子数据 + 导入脚本
│   ├── search/                 # 语义搜索（ChromaDB 向量检索）
│   ├── database.py             # 数据库连接配置
│   ├── soul_query.py           # 灵魂追问引擎
│   ├── user_profile.py         # 用户画像模型 + Redis 持久化
│   ├── session_store.py        # 会话存储
│   ├── cache.py                # 应用缓存层
│   ├── security.py             # 安全校验中间件
│   ├── export.py               # PDF 导出
│   └── middleware/             # 速率限制等中间件
├── frontend/                   # React + Vite + Tailwind CSS 前端
├── alembic/                    # 数据库迁移脚本
├── tests/                      # 测试套件
├── docs/                       # 文档和截图
├── data/                       # SQLite 数据库文件
├── SKILL.md                    # 张雪峰 AI 技能定义（系统 Prompt）
├── pyproject.toml              # Python 依赖管理
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

### 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| 前端框架 | React 18 + TypeScript + Vite 6 |
| 样式 | Tailwind CSS 3.4（报纸风主题） |
| LLM | OpenAI GPT-4o-mini / GPT-4o（支持代理） |
| 工具框架 | OpenAI Function Calling（原生） |
| 向量搜索 | ChromaDB + Sentence Transformers |
| 会话存储 | Redis |
| 数据库 | SQLite + SQLAlchemy + Alembic |
| 测试 | pytest（后端）+ Vitest（前端） |
| 监控 | Sentry + 自定义 MetricsCollector |

### 核心流程

```
用户消息
  ↓
POST /chat 接收请求
  ↓
soul_query.py 检查画像是否完整
  ├─ 不完整 → 返回追问问题（最多 3 轮）
  └─ 完整 ↓
注入画像为上下文
  ↓
AgentCore.chat() — OpenAI Function Calling 主循环
  ├─ LLM 返回文本 → 流式输出给用户
  └─ LLM 调用工具 → 执行工具 → 结果回传 LLM → 继续生成
  ↓
SSE 流式响应返回前端
```

### 添加新工具

在 `backend/tools/definitions.py` 中使用 `@register_tool` 装饰器：

```python
from .registry import register_tool

@register_tool(
    name="my_new_tool",
    description="工具描述，LLM 会根据此描述决定何时调用",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数说明"},
        },
        "required": ["param1"],
    },
)
async def my_new_tool(param1: str) -> str:
    """工具实现"""
    # 业务逻辑...
    return json.dumps({"status": "success", "data": result}, ensure_ascii=False)
```

工具会自动注册到 Agent，无需额外配置。

### 常用开发命令

```bash
# ===== 后端 =====
pip install -e ".[dev]"                          # 安装依赖
uvicorn backend.main:app --reload --port 8000    # 启动开发服务器
ruff check backend/                              # Lint
ruff format backend/                             # 格式化
pytest                                           # 运行测试

# ===== 前端 =====
cd frontend
npm install                                      # 安装依赖
npm run dev                                      # 启动开发服务器（端口 3000）
npm run build                                    # 生产构建
npm run test                                     # 运行测试
npm run lint                                     # Lint

# ===== 数据库 =====
alembic upgrade head                             # 执行迁移
alembic revision --autogenerate -m "desc"        # 生成迁移脚本

# ===== 语义搜索 =====
python -m backend.seeds.embed_data               # 生成向量嵌入数据
```

### 代码规范

- **Python**：Ruff，规则 `["E", "F", "I", "UP", "B"]`，行宽 100，Python 3.11+
- **TypeScript**：ESLint + React Hooks 规则
- **代理**：Vite 开发服务器将 `/api` 代理到 `http://localhost:8000`

## License

MIT
