# 张雪峰 AI 咨询 Agent — 技术方案 v1.0

> 更新时间：2026-05-26
> 状态：已确认（team-lead + echo 架构师审核通过）

## 一、项目定位

**一句话**：基于张雪峰心智模型的 AI 高考/考研/职业规划咨询 Agent，核心差异化是「先查数据再回答」的 Agentic 工作流。

**目标用户**：高考考生及家长、考研学生、职业规划咨询者

**核心价值**：用张雪峰的思维框架 + 实时数据，给出明确、有数据支撑的建议

---

## 二、系统架构

```
┌─────────────────────────────────────────────────┐
│                    前端层                         │
│   微信小程序 / Web Chat UI / H5                   │
└──────────────────────┬──────────────────────────┘
                       │ HTTPS / SSE
┌──────────────────────▼──────────────────────────┐
│                  API Gateway                     │
│   FastAPI + CORS + Rate Limiting                 │
└───┬──────────┬──────────┬──────────┬────────────┘
    │          │          │          │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼────┐
│ 对话   │ │ 用户   │ │ Agent │ │ 会话    │
│ 管理   │ │ 画像   │ │ 核心  │ │ 存储    │
│ 模块   │ │ 模块   │ │ 模块  │ │ 模块    │
└───┬───┘ └───┬───┘ └───┬───┘ └───┬────┘
    │         │         │         │
┌───▼─────────▼─────────▼─────────▼──────────────┐
│              LLM Provider (OpenAI/Claude)        │
│              Function Calling / Tool Use          │
└───┬──────────┬──────────┬───────────────────────┘
    │          │          │
┌───▼───┐ ┌───▼────┐ ┌───▼──────┐
│ Web   │ │ 录取   │ │ 就业     │
│ Search│ │ 数据库 │ │ 数据库   │
│ Tool  │ │ Tool   │ │ Tool     │
└───────┘ └────────┘ └──────────┘
```

---

## 三、模块详细设计

### 3.1 Agent 核心模块

**职责**：接收用户消息 → 问题分类 → 调用工具获取数据 → 用张雪峰框架生成回答

**实现方案**：基于 LLM Function Calling 的 ReAct Agent（不用 LangChain）

**关键设计决策**：

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Agent 框架 | **原生 Function Calling**，不用 LangChain | 轻量、可控、调试简单、延迟低 |
| LLM | GPT-4o-mini（默认）/ GPT-4o（复杂问题） | 中文能力强、Function Calling 成熟 |
| 工具调用策略 | auto（LLM 自主决定） | 符合 SKILL.md 的「先判断是否需要数据」 |
| 最大工具轮次 | 3 轮 | 避免无限循环，控制延迟和成本 |

**Agent 核心流程伪代码**：

```python
async def agent_respond(session, user_message):
    # 1. 构建 system prompt（精简版 SKILL.md）
    system_prompt = build_system_prompt(session.user_context)

    # 2. 定义 tools
    tools = [
        web_search_tool,      # 搜索实时信息
        score_lookup_tool,    # 查询录取分数线
        career_data_tool,     # 查询就业数据
        university_info_tool, # 查询院校信息
        calculate_match_tool, # 分数匹配院校
    ]

    # 3. LLM 决定是否需要调用工具
    response = await llm.chat(
        messages=session.history + [user_message],
        tools=tools,
        tool_choice="auto"
    )

    # 4. 如果需要工具，执行后把结果喂回 LLM
    while response.tool_calls:
        tool_results = await execute_tools(response.tool_calls)
        response = await llm.chat(
            messages=... + tool_results,
            tools=tools
        )

    return response.content
```

### 3.2 工具层设计（5 个 Tool）

| Tool | 输入 | 输出 | 触发场景 |
|------|------|------|----------|
| `web_search` | query, search_type | 搜索结果摘要 | 行业报告、政策、实时信息 |
| `search_admission` | school, province, year | 分数线/位次/招生计划 | "XX大学录取分多少" |
| `search_employment` | major, region | 就业率/薪资/去向 | "XX专业好就业吗" |
| `compare_schools` | school_list, metrics | 多维对比表 | "A和B哪个好" |
| `calculate_match` | score, province, preference | 匹配院校列表 | "580分能上什么" |

**数据来源**：
- MVP：Tavily 搜索 API + 手动整理 50 所热门院校数据
- V2：阳光高考网/掌上高考 API + 麦可思报告
- V3：与数据供应商合作

### 3.3 用户画像模块（灵魂追问机制）

**核心理念**：张雪峰的「灵魂追问」必须在系统层面实现，不能靠 LLM 自己记得问。

```python
SOUL_QUERY_SCHEMA = {
    "score": None,              # 分数（必问）
    "province": None,           # 省份（必问）
    "subject": None,            # 文理/选科（必问）
    "family_background": None,  # 家庭条件（必问）
    "target_city": None,        # 目标城市（选问）
    "risk_tolerance": None,     # 风险偏好（选问）
    "career_goal": None,        # 职业方向（选问）
}

class SoulQueryEngine:
    required_fields = ["score", "province", "subject", "family_background"]

    def get_next_question(self, context: dict) -> Optional[str]:
        """返回下一个追问，如果所有必填信息已齐则返回None"""
        for field in self.required_fields:
            if not context.get(field):
                return self._generate_question(field, context)
        return None

    def _generate_question(self, field: str, context: dict) -> str:
        """用张雪峰语气生成追问"""
        questions = {
            "score": "你孩子考了多少分？先把这个告诉我。",
            "province": "哪个省的？这个很重要，不同省差别太大了。",
            "subject": "文科还是理科？新高考的话选的什么科？",
            "family_background": "家里什么条件？做生意的还是工薪阶层？这个决定了完全不同的策略。",
        }
        return questions.get(field, f"把{field}告诉我。")
```

**集成到对话流程**：
1. 用户提问 → 检查 soul_query 是否完整
2. 不完整 → 先追问（最多 3 轮，避免烦人）
3. 完整 → 基于画像推荐
4. 对话中途获取的新信息 → 实时更新画像

**关键设计**：
- 追问语气要像张雪峰，不能像表单
- 已回答的信息不再重复问
- 用户跳过某个问题时，给出默认策略（如"家里条件一般"）
- 画像信息持久化到 Redis，下次对话直接加载

### 3.4 流程式方案（分步表单 + 一次性生成）

除了对话式追问，还支持**流程式分步表单**，适合家长用户：

```
用户进入 → 选择高考/考研 → 输入省份 → 输入分数 → 输入文理科
→ 输入家庭条件 → 选择意向方向 → 系统生成个性化方案
```

**MVP 实现**：前端分步表单（wizard），后端一次性组装 prompt + 调用 LLM 生成方案。

```python
@app.post("/api/v1/generate-plan")
async def generate_plan(request: PlanRequest):
    # request 包含：分数、省份、文理科、家庭条件、意向方向等
    prompt = build_zhangxuefeng_prompt(request)

    # 可选：搜索实时数据补充
    if request.needs_realtime_data:
        search_results = await tavily_search(f"{request意向专业} 就业率 2025")
        prompt += f"\n\n## 实时数据\n{search_results}"

    # 一次性生成完整方案
    response = await openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": SKILL_PROMPT},
                  {"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=3000
    )

    return {"plan": response.choices[0].message.content}
```

**关于 LangChain/LangGraph**：
- MVP 阶段不需要，原生 Function Calling 足够
- LangGraph 适合未来多 Agent 协作场景（Phase 4+）
- 线性流程不需要 DAG 编排，状态机即可

### 3.5 数据可信度与新鲜度

**可信度评分**：

| 数据来源 | 可信度 |
|----------|--------|
| 阳光高考网/教育部 | 1.0 |
| 政府统计报告 | 0.95 |
| 麦可思/智联 | 0.85 |
| 主流媒体报道 | 0.70 |
| 用户评论/论坛 | 0.30 |

**时效性衰减**：每年衰减 0.1，最低 0.1

**新鲜度警告 UI**：
- ✅ 正常（<6个月）：直接引用
- ⚠️ 注意（6-12个月）：括号标注来源，如"（据麦可思2025年报告）"
- 🔴 警告（>12个月）：明确提示 + 提供「查看最新数据」按钮

---

## 四、API 设计

### 4.1 核心接口

```
POST   /api/v1/chat              # 对话（SSE 流式返回）
POST   /api/v1/chat/sync         # 对话（同步返回，兼容性）
POST   /api/v1/generate-plan     # 流程式一次性生成方案
GET    /api/v1/session/{id}      # 获取会话信息
DELETE /api/v1/session/{id}      # 删除会话
POST   /api/v1/profile           # 更新用户画像
GET    /api/v1/health            # 健康检查
```

### 4.2 对话接口

**请求**：
```json
{
  "session_id": "xxx-xxx",
  "message": "我想学金融",
  "user_context": {
    "score": 560,
    "province": "河南",
    "subject": "理科"
  }
}
```

**响应（SSE 流式）**：
```
data: {"type": "thinking", "content": "让我查查金融专业的就业数据..."}
data: {"type": "tool_call", "tool": "web_search", "query": "金融专业 就业率 2025"}
data: {"type": "tool_result", "content": "...搜索结果..."}
data: {"type": "content", "content": "我跟你说，金融这个行业..."}
data: {"type": "content", "content": "千万别碰。你去看看..."}
data: {"type": "done", "usage": {"prompt_tokens": 1200, "completion_tokens": 800}}
```

### 4.3 流程式方案生成接口

**请求**：
```json
{
  "exam_type": "高考",
  "score": 560,
  "province": "河南",
  "subject": "理科",
  "family_background": "普通工薪家庭",
  "target_city": "不限",
  "interests": ["计算机", "金融"],
  "needs_realtime_data": true
}
```

**响应**：
```json
{
  "plan": "我跟你说，560分河南理科...",
  "data_sources": ["麦可思2025年报告", "阳光高考网2025年数据"],
  "freshness_warnings": []
}
```

---

## 五、前端方案

### MVP：Web 分步表单 + Chat UI

**技术选型**：Next.js + Tailwind CSS + SSE

**页面 1：分步表单（wizard）**
```
┌─────────────────────────────┐
│  张雪峰 AI 咨询顾问          │
├─────────────────────────────┤
│  Step 1/5: 选择考试类型      │
│  [高考] [考研]               │
│                             │
│  Step 2/5: 输入省份          │
│  [省份选择器]                │
│                             │
│  Step 3/5: 输入分数          │
│  [分数输入框]                │
│                             │
│  Step 4/5: 文理科            │
│  [文科] [理科] [新高考选科]   │
│                             │
│  Step 5/5: 家庭条件          │
│  [工薪家庭] [经商] [体制内]   │
│                             │
│  [生成方案 →]                │
└─────────────────────────────┘
```

**页面 2：方案结果页**
```
┌─────────────────────────────┐
│  你的专属志愿方案             │
├─────────────────────────────┤
│                             │
│  [张雪峰风格的方案内容]       │
│  - 可冲院校：...             │
│  - 稳妥院校：...             │
│  - 保底院校：...             │
│  - 专业建议：...             │
│                             │
│  数据来源：麦可思2025年报告   │
│  ⚠️ 部分数据基于2025年       │
│                             │
│  [继续咨询] [重新填写]        │
└─────────────────────────────┘
```

### V2：微信小程序（Taro/Uni-app）

---

## 六、数据层设计

| 数据 | 存储 | 说明 |
|------|------|------|
| 会话数据 | Redis | TTL 2 小时，MVP 阶段 |
| 用户画像 | Redis → PostgreSQL | 持久化后支持历史回看 |
| 录取分数线 | SQLite → PostgreSQL | 年度更新，(school, major, province, year) 四元组 |
| 就业数据 | SQLite → PostgreSQL | 年度更新 |
| 搜索缓存 | Redis | TTL 24 小时，避免重复搜索 |

### 录取数据表结构

```sql
CREATE TABLE admission_scores (
    id INTEGER PRIMARY KEY,
    year INTEGER NOT NULL,
    province TEXT NOT NULL,
    university TEXT NOT NULL,
    major TEXT,
    subject_type TEXT NOT NULL,
    min_score INTEGER,
    avg_score INTEGER,
    max_score INTEGER,
    rank_min INTEGER,
    batch TEXT
);
```

### 就业数据表结构

```sql
CREATE TABLE career_data (
    id INTEGER PRIMARY KEY,
    year INTEGER NOT NULL,
    university TEXT,
    major TEXT NOT NULL,
    employment_rate REAL,
    median_salary INTEGER,
    top_industries TEXT,
    top_companies TEXT,
    further_study_rate REAL,
    source TEXT
);
```

---

## 七、部署方案

### MVP 部署

```
Fly.io VM (FastAPI + Uvicorn)
  ↓
Upstash Redis (会话存储)
  ↓
OpenAI API (LLM)
  ↓
Tavily API (Web搜索)
```

**成本估算**：

| 项目 | 月成本 |
|------|--------|
| LLM (gpt-4o-mini) | $15-30（1000 次对话） |
| Web搜索 (Tavily) | $5-10 |
| Fly.io | $0-5 |
| Redis (Upstash) | $0 |
| 域名 + SSL | $1 |
| **总计** | **$21-46/月** |

---

## 八、分阶段路线图

| 阶段 | 时间 | 目标 |
|------|------|------|
| **Phase 1: MVP** | Week 1-2 | 对话 + Function Calling + 基础数据（50 所热门院校） |
| **Phase 2: 数据增强** | Week 3-4 | WebSearch 集成 + 灵魂追问 + 会话管理 |
| **Phase 3: 前端上线** | Week 5-6 | Web 前端（分步表单 + Chat）+ 部署上线 |
| **Phase 4: 商业化** | Week 7-8 | 小程序 + 支付 + 用户反馈收集 |
| **Phase 5: 规模化** | 持续 | 多 Agent + 语音 + 视频号 |

---

## 九、风险与应对

| 风险 | 应对 |
|------|------|
| LLM 幻觉（编造数据） | 强制工具调用 + 数据来源标注 |
| 搜索结果质量差 | 多源交叉验证 + 人工审核热门数据 |
| API 成本超预期 | 缓存 + 模型降级（简单问题用 mini） |
| 张雪峰家属投诉 | 免责声明 + 非官方声明 |
| 高考季流量暴增 | 预扩容 + 限流 + 队列 |

---

## 十、技术栈总结

| 层 | 技术 |
|---|---|
| 前端 MVP | Next.js + Tailwind + SSE |
| 前端 V2 | 微信小程序（Taro） |
| 后端 | Python FastAPI + Uvicorn |
| LLM | OpenAI GPT-4o-mini / GPT-4o |
| 工具框架 | OpenAI Function Calling（原生，不用 LangChain） |
| 搜索 | Tavily API |
| 缓存 | Redis（Upstash） |
| 数据库 MVP | SQLite |
| 数据库生产 | PostgreSQL |
| 部署 | Fly.io → 阿里云 |
