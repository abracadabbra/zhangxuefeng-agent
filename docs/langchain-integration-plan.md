# LangChain 集成技术方案

## 目标

引入 LangChain 增强 Agent 能力，重点解决：多步推理、对话记忆、结构化输出、LLM 切换。

## 现状

| 组件 | 当前实现 | 问题 |
|------|----------|------|
| LLM 调用 | openai SDK 直连 | 硬编码 OpenAI，换 provider 要改代码 |
| 工具调度 | 自定义 ToolRegistry | 只支持单工具调用，无法串联 |
| 对话记忆 | 手动裁剪（滑动窗口） | 无摘要能力，长对话丢信息 |
| 输出格式 | prompt 约束 | 不稳定，LLM 可能返回非结构化 |
| 检索 | ChromaDB 直接调用 | 单次查询，无多跳检索 |

## 方案设计

### Phase 1: 基础替换（1-2天）

**替换 LLM 调用层：**

```python
# 当前
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=api_key)
response = await client.chat.completions.create(...)

# 改为
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

llm = ChatOpenAI(model="gpt-4o-mini")  # 或 ChatAnthropic(model="claude-3-5-sonnet")
response = await llm.ainvoke(messages)
```

**收益：** 一行代码切换 LLM provider，支持 OpenAI/Anthropic/Google。

### Phase 2: Agent 多步推理（2-3天）

**引入 LangChain Agent：**

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 工具定义（复用现有 ToolRegistry）
tools = [
    Tool(name="search_admission", func=search_admission_fn, description="..."),
    Tool(name="search_employment", func=search_employment_fn, description="..."),
    Tool(name="semantic_search", func=semantic_search_fn, description="..."),
    Tool(name="compare_schools", func=compare_schools_fn, description="..."),
    Tool(name="calculate_match", func=calculate_match_fn, description="..."),
]

# Agent 提示词（复用 SKILL.md）
prompt = ChatPromptTemplate.from_messages([
    ("system", load_skill_prompt()),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 创建 Agent
agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
```

**收益：** Agent 自主规划多步调用，如：
- "河南630分学计算机推荐学校" → 自动串联：查分数线 → 筛选计算机 → 排序
- "对比北大和清华的计算机专业" → 自动并行调用两次查询

### Phase 3: 对话记忆（1天）

**引入结构化记忆：**

```python
from langchain.memory import ConversationSummaryBufferMemory

memory = ConversationSummaryBufferMemory(
    llm=llm,
    max_token_limit=2000,  # 超过此阈值自动摘要
    return_messages=True,
    memory_key="chat_history",
)
```

**对比当前方案：**

| 方案 | 优点 | 缺点 |
|------|------|------|
| 当前滑动窗口 | 简单、无额外成本 | 丢失早期信息 |
| SummaryBufferMemory | 保留关键信息摘要 | 需要额外 LLM 调用 |
| 混合方案 | 前 N 轮保留原文，超出部分摘要 | 实现稍复杂 |

**建议：** 用混合方案 — 前 10 轮保留原文，超出部分自动摘要。

### Phase 4: 结构化输出（1天）

**引入 Pydantic 输出解析：**

```python
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class SchoolRecommendation(BaseModel):
    school_name: str = Field(description="学校名称")
    reason: str = Field(description="推荐理由")
    admission_probability: float = Field(description="录取概率 0-1")
    match_score: int = Field(description="匹配度 1-10")

class RecommendationResult(BaseModel):
    recommendations: list[SchoolRecommendation]
    summary: str = Field(description="总结建议")

parser = PydanticOutputParser(pydantic_object=RecommendationResult)

# 在 prompt 中注入格式要求
prompt = prompt.partial(format_instructions=parser.get_format_instructions())
```

**收益：** 输出稳定 JSON，前端直接解析，不需要正则提取。

### Phase 5: 检索链优化（可选，2天）

**引入多查询检索：**

```python
from langchain.retrievers import MultiQueryRetriever

retriever = MultiQueryRetriever.from_llm(
    retriever=vector_store.as_retriever(search_kwargs={"k": 10}),
    llm=llm,
)

# 一个问题生成多个查询角度
# "计算机专业就业怎么样" → 
#   - "计算机科学与技术就业率"
#   - "软件工程薪资水平"  
#   - "人工智能就业前景"
```

## 迁移策略

### 渐进式迁移（推荐）

```
Phase 1: 替换 LLM 层（不影响现有功能）
Phase 2: 引入 Agent（可与现有 ToolRegistry 并存）
Phase 3: 添加记忆（替换手写裁剪逻辑）
Phase 4: 结构化输出（逐步替换各工具返回格式）
Phase 5: 检索优化（可选）
```

### 风险控制

1. **保持现有 API 接口不变** — `/chat` 端点签名不动
2. **双轨运行** — 新旧实现并存，通过配置切换
3. **测试覆盖** — 每个 Phase 完成后跑全量测试

## 依赖变更

```toml
# pyproject.toml 新增
[project.optional-dependencies]
langchain = [
    "langchain>=0.2",
    "langchain-openai>=0.1",
    "langchain-anthropic>=0.1",
    "langchain-chroma>=0.1",
]
```

用户可选择安装：`pip install -e ".[langchain]"`

## 工作量估算

| Phase | 工作量 | 优先级 |
|-------|--------|--------|
| Phase 1: LLM 层替换 | 1-2天 | P0 |
| Phase 2: Agent 多步推理 | 2-3天 | P1 |
| Phase 3: 对话记忆 | 1天 | P1 |
| Phase 4: 结构化输出 | 1天 | P2 |
| Phase 5: 检索优化 | 2天 | P3 |

**总计：7-9 天**

## 决策点

- [ ] 是否引入 LangChain？（当前手写够用 vs 未来扩展性）
- [ ] 哪些 Phase 先做？（建议 Phase 1-3 先行）
- [ ] 是否保留双轨运行？（建议保留，降低风险）
