s# 张雪峰 AI 咨询 Agent

> 张雪峰的认知操作系统，可运行的高考/考研/职业规划顾问

## 功能

- 🎯 **高考志愿咨询**：根据分数/省份/家庭背景，给出选校选专业建议
- 📚 **考研规划**：择校、择专业、备考策略
- 💼 **职业规划**：应届生就业方向、行业选择
- 🔍 **AI 驱动**：基于张雪峰心智模型 + 实时数据查询

## 快速开始

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
# 编辑 .env，填入 OPENAI_API_KEY

# 5. 启动服务
uvicorn app.main:app --reload --port 8000
```

### Docker Compose

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY

# 2. 启动所有服务
docker compose up -d

# 3. 访问
# API: http://localhost:8000
# 文档: http://localhost:8000/docs
# 健康检查: http://localhost:8000/health
```

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

**Upstash Redis 配置**：
1. 在 [Upstash Console](https://console.upstash.com) 创建 Redis 数据库
2. 选择区域 `Hong Kong (ap-east)` 与 Fly.io 同区域
3. 复制 `REDIS_URL`（带 `rediss://` 前缀）
4. 通过 `fly secrets set REDIS_URL=...` 注入

## 项目结构

```
zhangxuefeng-agent/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── api/                 # API 路由层
│   │   ├── chat.py          # 对话接口
│   │   └── health.py        # 健康检查
│   ├── core/                # 配置管理、中间件
│   │   ├── config.py        # pydantic-settings 配置
│   │   └── middleware.py    # CORS、日志、异常处理
│   ├── models/              # Pydantic 数据模型
│   │   └── schemas.py
│   ├── services/            # 业务逻辑层
│   │   ├── llm.py           # LLM 调用封装
│   │   └── skill.py         # SKILL.md 加载
│   ├── agent/               # Agent 核心（预留）
│   └── utils/               # 工具函数
├── SKILL.md                 # 张雪峰 AI 技能定义
├── pyproject.toml           # 依赖管理
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/chat` | 对话接口 |
| GET | `/api/v1/session/{id}` | 获取会话信息 |
| DELETE | `/api/v1/session/{id}` | 删除会话 |

## 技术栈

| 层 | 技术 |
|---|---|
| 框架 | FastAPI + Uvicorn |
| LLM | OpenAI GPT-4o-mini / GPT-4o |
| 工具框架 | OpenAI Function Calling（原生） |
| 缓存 | Redis |
| 数据库 | SQLite（MVP）→ PostgreSQL（生产） |
| 配置管理 | pydantic-settings |

## License

MIT
