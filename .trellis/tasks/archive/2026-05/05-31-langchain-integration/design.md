# 技术设计

## 架构变更

### 当前架构
```
main.py → AgentCore → openai.AsyncOpenAI → LLM
                ↓
         ToolRegistry → 工具执行
```

### 目标架构
```
main.py → LangChainAgent → ChatOpenAI/ChatAnthropic → LLM
                ↓
         ToolExecutor → 工具执行
                ↓
         ConversationMemory → 对话历史管理
```

## 模块设计

### 1. LLM 层 (`backend/agent/llm_factory.py`)

```python
def create_llm(provider: str = "openai", **kwargs):
    """根据 provider 创建 LLM 实例"""
    if provider == "openai":
        return ChatOpenAI(model=kwargs.get("model", "gpt-4o-mini"))
    elif provider == "anthropic":
        return ChatAnthropic(model=kwargs.get("model", "claude-3-5-sonnet"))
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

### 2. 工具适配层 (`backend/agent/tools_adapter.py`)

将现有 ToolRegistry 中的工具转换为 LangChain Tool 格式：

```python
def convert_tools(registry: ToolRegistry) -> list[Tool]:
    """将 ToolRegistry 转换为 LangChain Tool 列表"""
    tools = []
    for name, tool_def in registry._tools.items():
        tools.append(Tool(
            name=name,
            description=tool_def.description,
            func=tool_def.fn,
        ))
    return tools
```

### 3. Agent 核心 (`backend/agent/langchain_agent.py`)

```python
class LangChainAgent:
    def __init__(self, llm, tools, system_prompt):
        self.memory = ConversationSummaryBufferMemory(
            llm=llm,
            max_token_limit=2000,
            return_messages=True,
        )
        self.agent = create_openai_tools_agent(llm, tools, prompt)
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=tools,
            memory=self.memory,
            verbose=True,
        )

    async def chat(self, message: str, session_id: str) -> dict:
        """处理用户消息"""
        result = await self.executor.ainvoke({"input": message})
        return {"reply": result["output"]}
```

### 4. 会话记忆集成

```python
# 从 session_store 加载历史
history = session_store.get_history(session_id)
memory.chat_memory.add_messages(history)

# 对话结束后保存
session_store.add_message(session_id, "user", message)
session_store.add_message(session_id, "assistant", reply)
```

## 兼容性设计

1. **API 接口不变** — `/chat` 端点签名保持一致
2. **双轨运行** — 通过环境变量 `USE_LANGCHAIN=true` 切换新旧实现
3. **渐进迁移** — Phase 1 完成后可独立部署，不影响现有功能

## 依赖管理

```toml
# pyproject.toml
[project.optional-dependencies]
langchain = [
    "langchain>=0.2",
    "langchain-openai>=0.1",
    "langchain-anthropic>=0.1",
    "langchain-chroma>=0.1",
]
```

## 风险控制

1. **测试覆盖** — 每个 Phase 完成后跑全量测试
2. **回滚方案** — 保留旧实现，通过配置切换
3. **性能监控** — 对比新旧实现的响应时间和 token 消耗
