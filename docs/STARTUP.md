# 项目启动指南

本文档提供张雪峰 AI 咨询 Agent 的完整启动说明，涵盖本地开发、Docker Compose 和 Fly.io 部署三种方式。

---

## 环境要求

| 依赖 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.11+ | 后端运行时 |
| Node.js | 18+ | 前端构建 |
| npm / pnpm | 任意 | 前端包管理 |
| Redis | 7+ | 用户画像缓存（可选，本地开发可跳过） |
| Docker | 24+ | Docker Compose 方式启动（可选） |

---

## 一、本地开发启动

### 1. 克隆项目

```bash
git clone <repo-url>
cd zhangxuefeng-agent
```

### 2. Python 环境配置

#### 2.1 验证 Python 版本

本项目要求 **Python 3.11+**，请先确认已安装正确版本：

```bash
# 查看 Python 版本
python3 --version
# 或
python --version

# 应输出类似：Python 3.11.x 或更高版本
```

如果未安装或版本过低，可通过以下方式安装：

```bash
# macOS（使用 Homebrew）
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Windows
# 从 https://www.python.org/downloads/ 下载安装包
```

#### 2.2 创建虚拟环境（venv）

**推荐使用 venv**（Python 内置，无需额外安装）：

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat

# 验证虚拟环境已激活（命令行前应显示 (.venv)）
which python  # 应指向 .venv/bin/python
```

退出虚拟环境：

```bash
deactivate
```

#### 2.3 使用 Conda（可选）

如果偏好 Conda：

```bash
# 创建 Conda 环境
conda create -n zhangxuefeng python=3.11 -y

# 激活环境
conda activate zhangxuefeng

# 验证
python --version
```

#### 2.4 安装 Python 依赖

激活虚拟环境后，安装项目依赖：

```bash
# 方式一：使用 pyproject.toml（推荐，安装项目及所有依赖）
pip install -e ".[dev]"

# 方式二：使用 requirements.txt
pip install -r backend/requirements.txt
```

依赖说明：

| 包名 | 用途 |
|------|------|
| fastapi | Web 框架 |
| uvicorn | ASGI 服务器 |
| openai | OpenAI API 客户端 |
| sqlalchemy | ORM 数据库操作 |
| alembic | 数据库迁移 |
| redis | Redis 客户端（用户画像缓存） |
| sse-starlette | SSE 流式输出 |
| pydantic | 数据验证 |
| pytest | 测试框架（dev） |
| ruff | 代码检查/格式化（dev） |

验证依赖安装：

```bash
# 检查关键包是否安装
python -c "import fastapi; import uvicorn; import sqlalchemy; print('依赖安装成功')"
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置说明：

```env
# ===== 必填 =====
OPENAI_API_KEY=sk-xxx           # OpenAI API 密钥

# ===== 可选 =====
OPENAI_BASE_URL=https://api.openai.com/v1  # 自定义 API 地址（如使用代理）
MODEL=gpt-4o-mini               # 使用的模型，默认 gpt-4o-mini
REDIS_URL=redis://localhost:6379/0  # Redis 地址，不配置则降级为内存模式
DATABASE_URL=sqlite:///./data/zhangxuefeng.db  # 数据库地址，有默认值
DEBUG=false                     # 调试模式
SKILL_PATH=SKILL.md             # 技能定义文件路径
SENTRY_DSN=                     # Sentry 错误追踪（可选）
COST_ALERT_THRESHOLD_USD=50.0   # 成本预警阈值
CORS_ORIGINS=*                  # CORS 允许的来源
```

> **安全提示**：`.env` 文件包含敏感信息，已加入 `.gitignore`，切勿提交到版本控制。

### 4. 启动后端

```bash
# 确保虚拟环境已激活
source .venv/bin/activate  # 如果尚未激活

# 创建数据目录（SQLite 数据库存放位置）
mkdir -p data

# 启动后端服务（开发模式，代码修改自动重载）
uvicorn backend.main:app --reload --port 8000
```

启动成功后会看到类似输出：

```
INFO:     Will watch for changes in these directories: ['/path/to/zhangxuefeng-agent']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx]
[2026-05-27 ...] 张雪峰 Agent 启动 | Model: gpt-4o-mini
[2026-05-27 ...] 数据库初始化完成
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

可用的 API 端点：
- API 服务：http://localhost:8000
- Swagger 文档：http://localhost:8000/docs
- ReDoc 文档：http://localhost:8000/redoc
- 健康检查：http://localhost:8000/health
- 数据库状态：http://localhost:8000/db/status

#### 常用 uvicorn 参数

```bash
# 基本启动
uvicorn backend.main:app --port 8000

# 开发模式（自动重载）
uvicorn backend.main:app --reload --port 8000

# 指定绑定地址
uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 多 worker 生产模式
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

# 调试级别日志
uvicorn backend.main:app --reload --port 8000 --log-level debug
```

或者直接运行 main.py：

```bash
cd backend
python main.py
```

启动成功后：
- API 服务：http://localhost:8000
- Swagger 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- 数据库状态：http://localhost:8000/db/status

### 4. 启动前端

新开一个终端窗口：

```bash
cd frontend

# 安装依赖
npm install    # 或 pnpm install

# 启动开发服务器
npm run dev    # 或 pnpm dev
```

启动成功后访问：http://localhost:3000

前端已配置代理，`/api/*` 请求会自动转发到后端 `http://localhost:8000`。

### 5. （可选）导入种子数据

```bash
# 确保在项目根目录，且已激活虚拟环境
cd backend
python -m seeds.import_data
```

### 6. （可选）启动 Redis

如果需要用户画像持久化功能：

```bash
# macOS
brew install redis
brew services start redis

# Linux
sudo systemctl start redis

# 或使用 Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

---

## 二、Docker Compose 启动

适合快速启动后端 + Redis，无需手动安装依赖。

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

### 2. 启动服务

```bash
# 构建并启动（后台运行）
docker compose up -d

# 查看日志
docker compose logs -f api

# 停止服务
docker compose down
```

启动后：
- API 服务：http://localhost:8000
- Swagger 文档：http://localhost:8000/docs
- Redis：localhost:6379

> **注意**：Docker Compose 方式只启动后端和 Redis。前端仍需按「本地开发」方式单独启动。

---

## 三、Fly.io 部署

### 1. 安装 Fly CLI

```bash
curl -L https://fly.io/install.sh | sh
```

### 2. 登录并部署

```bash
fly auth login

# 首次部署
fly launch --no-deploy

# 设置密钥
fly secrets set OPENAI_API_KEY=sk-xxx
fly secrets set REDIS_URL="rediss://default:<password>@<host>:<port>"

# 部署
fly deploy
```

### 3. Upstash Redis 配置

1. 在 [Upstash Console](https://console.upstash.com) 创建 Redis 数据库
2. 选择区域 `Hong Kong (ap-east)` 与 Fly.io 同区域
3. 复制 `REDIS_URL`（带 `rediss://` 前缀）
4. 通过 `fly secrets set REDIS_URL=...` 注入

### 4. 查看状态

```bash
fly status
fly logs
fly ssh console
```

---

## 项目结构概览

```
zhangxuefeng-agent/
├── app/                        # Docker 构建入口（打包用）
│   └── main.py
├── backend/                    # 后端源码
│   ├── main.py                 # FastAPI 应用主入口
│   ├── agent/                  # Agent 核心逻辑
│   ├── routers/                # API 路由（schools/majors/scores/plans）
│   ├── models/                 # SQLAlchemy ORM 模型
│   ├── schemas/                # Pydantic 数据模型
│   ├── crud/                   # 数据库 CRUD 操作
│   ├── seeds/                  # 种子数据导入脚本
│   ├── tools/                  # Function Calling 工具定义
│   ├── websearch/              # 网络搜索模块
│   ├── database.py             # 数据库连接配置
│   ├── soul_query.py           # 灵魂追问引擎
│   └── user_profile.py         # 用户画像管理
├── frontend/                   # 前端源码（React + Vite + Tailwind）
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── alembic/                    # 数据库迁移
├── docs/                       # 项目文档
├── tests/                      # 测试代码
├── SKILL.md                    # 张雪峰 AI 技能定义
├── pyproject.toml              # Python 依赖管理
├── Dockerfile                  # Docker 镜像定义
├── docker-compose.yml          # Docker Compose 编排
├── fly.toml                    # Fly.io 部署配置
├── alembic.ini                 # Alembic 迁移配置
├── .env.example                # 环境变量模板
└── .gitignore
```

---

## 常见问题排查

### 1. 后端启动报错 `ModuleNotFoundError`

```
ModuleNotFoundError: No module named 'backend'
```

**解决**：确保在项目根目录执行 `pip install -e ".[dev]"`，或使用 `uvicorn backend.main:app` 而非 `uvicorn app.main:app`。

### 2. 前端请求后端 404

**原因**：Vite 代理配置将 `/api/*` 转发到后端，但路径会去掉 `/api` 前缀。

**解决**：前端请求应使用 `/api/chat` 而非 `/chat`。

### 3. Redis 连接失败

```
redis.exceptions.ConnectionError
```

**解决**：
- 本地开发：确保 Redis 已启动，或不设置 `REDIS_URL`（会自动降级为内存模式）
- Docker Compose：`REDIS_URL` 已自动配置为 `redis://redis:6379/0`

### 4. 数据库相关错误

```
sqlalchemy.exc.OperationalError: no such table
```

**解决**：
```bash
# 方式一：应用启动时自动建表（默认行为）
# 重启后端即可

# 方式二：使用 Alembic 迁移
alembic upgrade head
```

### 5. OpenAI API 调用失败

```
openai.AuthenticationError
```

**解决**：
- 检查 `.env` 中 `OPENAI_API_KEY` 是否正确
- 如果使用自定义 API 地址，确认 `OPENAI_BASE_URL` 配置正确
- 检查网络是否能访问 OpenAI API

### 6. 端口被占用

```
OSError: [Errno 48] Address already in use
```

**解决**：
```bash
# 查找占用端口的进程
lsof -i :8000   # 后端
lsof -i :3000   # 前端

# 杀掉进程
kill -9 <PID>
```

### 7. 前端依赖安装失败

```bash
# 清除缓存重试
rm -rf node_modules package-lock.json
npm install
```

---

## API 快速验证

启动后可用以下命令验证服务是否正常：

```bash
# 健康检查
curl http://localhost:8000/health

# 数据库状态
curl http://localhost:8000/db/status

# 发送对话请求
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，我是山东考生，考了580分，能上什么学校？"}'
```

---

## 开发命令速查

```bash
# 后端
uvicorn backend.main:app --reload --port 8000   # 启动开发服务器
pytest tests/                                     # 运行测试
ruff check backend/                               # 代码检查
ruff format backend/                              # 代码格式化
alembic revision --autogenerate -m "description"  # 生成迁移
alembic upgrade head                              # 执行迁移

# 前端
cd frontend
npm run dev        # 启动开发服务器
npm run build      # 构建生产版本
npm run test       # 运行测试
npm run lint       # 代码检查
npm run preview    # 预览构建产物
```
