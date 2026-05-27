# 张雪峰 AI 咨询 Agent — API 文档

> 版本：0.2.0 | 更新时间：2026-05-26

## 目录

1. [概述](#概述)
2. [基础信息](#基础信息)
3. [CORS 配置](#cors-配置)
4. [核心对话接口](#核心对话接口)
5. [SSE 流式输出](#sse-流式输出)
6. [用户画像接口](#用户画像接口)
7. [数据查询接口](#数据查询接口)
8. [工具定义接口](#工具定义接口)
9. [错误处理](#错误处理)
10. [调用示例](#调用示例)

---

## 概述

张雪峰 AI 咨询 Agent 提供以下核心能力：

- **对话接口**：支持非流式和 SSE 流式输出
- **Function Calling**：5 个内置工具（录取查询、就业查询、院校对比、政策搜索、分数匹配）
- **灵魂追问**：自动识别用户画像完整性，追问关键信息
- **数据查询**：院校、专业、分数线、招生计划的 RESTful API

---

## 基础信息

| 项目 | 值 |
|------|-----|
| Base URL | `http://localhost:8000` |
| 协议 | HTTP/HTTPS |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |
| 认证方式 | 无（MVP 阶段） |

### 健康检查

```http
GET /health
```

**响应**：
```json
{
  "status": "healthy",
  "timestamp": "2026-05-26T12:00:00.000000"
}
```

### 数据库状态

```http
GET /db/status
```

**响应**：
```json
{
  "status": "connected",
  "tables": {
    "schools": 154,
    "majors": 25,
    "admission_scores": 63,
    "enrollment_plans": 30
  }
}
```

---

## CORS 配置

当前配置（开发环境）：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 允许所有来源
    allow_credentials=True,     # 允许携带凭证
    allow_methods=["*"],        # 允许所有 HTTP 方法
    allow_headers=["*"],        # 允许所有请求头
)
```

**生产环境建议**：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-domain.com",
        "https://www.your-domain.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**前端对接注意事项**：

1. SSE 请求需要设置 `Accept: text/event-stream`
2. 跨域请求需确保 `withCredentials: true`（如需携带 Cookie）
3. 预检请求（OPTIONS）会自动处理，无需额外配置

---

## 核心对话接口

### POST /chat

核心对话接口，支持非流式和 SSE 流式输出。

**请求体**：

```json
{
  "session_id": "可选，空则创建新会话",
  "message": "用户消息（必填）",
  "user_context": {
    "分数": 560,
    "省份": "河南",
    "科类": "理科",
    "家庭条件": "普通工薪家庭"
  },
  "stream": false
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 否 | 会话 ID，为空则自动创建 |
| message | string | 是 | 用户消息内容 |
| user_context | object | 否 | 用户背景信息（分数、省份、科类等） |
| stream | boolean | 否 | 是否使用 SSE 流式输出，默认 false |

**非流式响应**：

```json
{
  "session_id": "uuid-xxx",
  "reply": "我跟你说，560分河南理科...",
  "model": "gpt-4o-mini",
  "tool_calls": [
    {
      "id": "call_xxx",
      "name": "search_admission",
      "arguments": {"school_name": "郑州大学"},
      "result": "{...}"
    }
  ],
  "usage": {
    "prompt_tokens": 1200,
    "completion_tokens": 800,
    "total_tokens": 2000
  }
}
```

---

## SSE 流式输出

当 `stream: true` 时，接口返回 SSE（Server-Sent Events）流。

**请求**：

```http
POST /chat
Content-Type: application/json
Accept: text/event-stream

{
  "message": "我想学金融",
  "stream": true
}
```

**响应格式**：

```
event: message
data: {"type": "text", "content": "让我"}

event: message
data: {"type": "text", "content": "查查"}

event: message
data: {"type": "text", "content": "金融专业..."}

event: message
data: {"type": "tool_call", "name": "search_employment", "arguments": {"major_name": "金融学"}}

event: message
data: {"type": "tool_result", "name": "search_employment", "result": "{...}"}

event: message
data: {"type": "text", "content": "我跟你说，金融这个行业..."}

event: message
data: {"type": "done", "usage": {"prompt_tokens": 1200, "completion_tokens": 800, "total_tokens": 2000}}
```

**事件类型**：

| type | 说明 | 数据字段 |
|------|------|----------|
| `text` | 文本片段 | `content`: 文本内容 |
| `tool_call` | 工具调用 | `name`: 工具名, `arguments`: 参数 |
| `tool_result` | 工具结果 | `name`: 工具名, `result`: 结果 JSON |
| `done` | 完成 | `usage`: Token 用量 |

**前端 SSE 接收示例（JavaScript）**：

```javascript
const response = await fetch('/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
  },
  body: JSON.stringify({
    message: '我想学金融',
    stream: true,
  }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const lines = text.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      switch (data.type) {
        case 'text':
          // 追加文本到 UI
          appendText(data.content);
          break;
        case 'tool_call':
          // 显示工具调用状态
          showToolCall(data.name);
          break;
        case 'done':
          // 对话完成
          handleComplete(data.usage);
          break;
      }
    }
  }
}
```

---

## 用户画像接口

### GET /profile/{session_id}

获取用户画像信息。

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话 ID |

**响应**：

```json
{
  "session_id": "uuid-xxx",
  "profile": {
    "score": 560,
    "province": "河南",
    "subject": "理科",
    "family_background": null,
    "target_city": null,
    "risk_tolerance": null,
    "career_goal": null
  },
  "is_complete": false,
  "missing_fields": ["family_background"]
}
```

### PUT /profile/{session_id}

更新用户画像字段。

**请求体**：

```json
{
  "field": "family_background",
  "value": "普通工薪家庭"
}
```

**响应**：同 GET /profile/{session_id}

### GET /profile/{session_id}/next-question

获取下一个追问问题（灵魂追问机制）。

**响应**：

```json
{
  "session_id": "uuid-xxx",
  "question": "家里什么条件？做生意的还是工薪阶层？这个决定了完全不同的策略。",
  "round_count": 1,
  "is_complete": false
}
```

---

## 数据查询接口

### 院校查询

#### GET /schools/{school_id}

根据 ID 查询院校。

**响应**：

```json
{
  "id": 1,
  "name": "北京大学",
  "province": "北京",
  "city": "北京",
  "level": "985",
  "school_type": "综合",
  "ranking": 1,
  "is_985": 1,
  "is_211": 1,
  "is_double_first_class": 1,
  "website": "https://www.pku.edu.cn",
  "description": "中国顶尖学府..."
}
```

#### GET /schools/by-name/{name}

根据名称查询院校。

#### POST /schools/search

多条件查询院校列表。

**请求体**：

```json
{
  "name": "北京",
  "province": "北京",
  "level": "985",
  "is_985": 1,
  "page": 1,
  "page_size": 20
}
```

**响应**：

```json
{
  "total": 8,
  "page": 1,
  "page_size": 20,
  "items": [...]
}
```

---

### 专业查询

#### GET /majors/{major_id}

根据 ID 查询专业。

#### GET /majors/by-name/{name}

根据名称查询专业。

#### GET /majors/hot/list

获取热门专业。

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 20 | 返回数量 |

#### POST /majors/search

多条件查询专业列表。

**请求体**：

```json
{
  "category": "工学",
  "is_hot": 1,
  "min_employment_rate": 0.8,
  "page": 1,
  "page_size": 20
}
```

---

### 分数线查询

#### POST /scores/search

多条件查询分数线。

**请求体**：

```json
{
  "school_name": "北京大学",
  "province": "河南",
  "year": 2025,
  "subject_type": "理科",
  "page": 1,
  "page_size": 20
}
```

**响应**：

```json
{
  "total": 5,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "school_id": 1,
      "major_id": 10,
      "province": "河南",
      "year": 2025,
      "batch": "本科一批",
      "subject_type": "理科",
      "min_score": 680,
      "avg_score": 692.5,
      "max_score": 710,
      "min_rank": 150,
      "plan_count": 30,
      "school_name": "北京大学",
      "major_name": "计算机科学与技术"
    }
  ]
}
```

#### GET /scores/school/{school_id}

查询某院校分数线。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| province | string | 省份（可选） |
| year | int | 年份（可选） |

#### GET /scores/major/{major_id}

查询某专业分数线（跨院校）。

#### GET /scores/stats

获取分数统计信息。

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| school_id | int | 是 | 院校 ID |
| province | string | 是 | 省份 |
| year | int | 是 | 年份 |
| major_id | int | 否 | 专业 ID |

---

### 招生计划查询

#### POST /plans/search

多条件查询招生计划。

**请求体**：

```json
{
  "school_name": "清华大学",
  "province": "河南",
  "year": 2025,
  "page": 1,
  "page_size": 20
}
```

#### GET /plans/school/{school_id}

查询某院校招生计划。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| province | string | 省份（可选） |
| year | int | 年份（可选） |

#### GET /plans/major/{major_id}

查询某专业招生计划（跨院校）。

---

## 工具定义接口

### GET /tools

返回所有已注册工具的定义（Function Calling 格式）。

**响应**：

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_admission",
        "description": "搜索高校录取分数线...",
        "parameters": {
          "type": "object",
          "properties": {
            "school_name": {"type": "string", "description": "学校名称"},
            "province": {"type": "string", "description": "考生所在省份"},
            "year": {"type": "integer", "description": "查询年份"},
            "category": {"type": "string", "enum": ["理科", "文科", "综合"]}
          },
          "required": ["school_name"]
        }
      }
    }
  ]
}
```

**内置工具列表**：

| 工具名 | 功能 | 触发场景 |
|--------|------|----------|
| search_admission | 搜索录取分数线 | "XX大学录取分多少" |
| search_employment | 搜索就业数据 | "XX专业好就业吗" |
| compare_schools | 院校对比 | "A和B哪个好" |
| search_policy | 搜索招生政策 | "强基计划怎么报" |
| calculate_match | 分数匹配推荐 | "580分能上什么" |

---

## 错误处理

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误示例

**400 - 消息为空**：
```json
{
  "detail": "消息不能为空"
}
```

**404 - 会话不存在**：
```json
{
  "detail": "会话不存在"
}
```

**404 - 院校不存在**：
```json
{
  "detail": "院校不存在"
}
```

---

## 调用示例

### 1. 基础对话（非流式）

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我是河南考生，560分，理科，能上什么学校？",
    "user_context": {
      "分数": 560,
      "省份": "河南",
      "科类": "理科"
    }
  }'
```

### 2. 流式对话（SSE）

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "金融专业就业怎么样？",
    "stream": true
  }'
```

### 3. 查询院校

```bash
# 按 ID 查询
curl http://localhost:8000/schools/1

# 按名称查询
curl http://localhost:8000/schools/by-name/北京大学

# 多条件查询
curl -X POST http://localhost:8000/schools/search \
  -H "Content-Type: application/json" \
  -d '{
    "province": "北京",
    "level": "985",
    "page": 1,
    "page_size": 10
  }'
```

### 4. 查询分数线

```bash
curl -X POST http://localhost:8000/scores/search \
  -H "Content-Type: application/json" \
  -d '{
    "school_name": "清华大学",
    "province": "河南",
    "year": 2025
  }'
```

### 5. 查询专业就业数据

```bash
curl http://localhost:8000/majors/by-name/计算机科学与技术
```

### 6. 获取热门专业

```bash
curl http://localhost:8000/majors/hot/list?limit=10
```

### 7. 会话管理

```bash
# 获取会话信息
curl http://localhost:8000/session/{session_id}

# 删除会话
curl -X DELETE http://localhost:8000/session/{session_id}
```

### 8. 用户画像

```bash
# 获取画像
curl http://localhost:8000/profile/{session_id}

# 更新画像
curl -X PUT http://localhost:8000/profile/{session_id} \
  -H "Content-Type: application/json" \
  -d '{
    "field": "family_background",
    "value": "普通工薪家庭"
  }'

# 获取追问问题
curl http://localhost:8000/profile/{session_id}/next-question
```

---

## 会话管理

### 会话生命周期

1. **创建**：首次调用 `/chat` 时不传 `session_id`，系统自动创建
2. **使用**：后续调用传入 `session_id` 复用会话
3. **过期**：内存存储，服务重启后丢失（MVP 阶段）
4. **删除**：调用 `DELETE /session/{session_id}`

### 会话数据结构

```json
{
  "session_id": "uuid-xxx",
  "created_at": "2026-05-26T12:00:00",
  "message_count": 6,
  "user_context": {
    "分数": 560,
    "省份": "河南",
    "科类": "理科"
  }
}
```

---

## 附录

### A. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| OPENAI_API_KEY | - | OpenAI API 密钥 |
| OPENAI_BASE_URL | https://api.openai.com/v1 | API 基础 URL |
| MODEL | gpt-4o-mini | 使用的模型 |

### B. 数据模型

详见 `backend/schemas/` 目录下的 Pydantic 模型定义。

### C. 技术架构

详见 `docs/technical-plan.md`。
