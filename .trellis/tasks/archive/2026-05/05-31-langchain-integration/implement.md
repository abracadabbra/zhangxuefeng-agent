# 实现计划

## 执行顺序

### Step 1: 依赖安装
- [ ] pyproject.toml 添加 langchain 可选依赖
- [ ] 安装依赖：`pip install -e ".[langchain]"`

### Step 2: LLM 工厂 (`backend/agent/llm_factory.py`)
- [ ] 创建 LLM 工厂函数，支持 openai/anthropic 切换
- [ ] 环境变量配置：`LLM_PROVIDER`, `LLM_MODEL`
- [ ] 单元测试

### Step 3: 工具适配层 (`backend/agent/tools_adapter.py`)
- [ ] 将 ToolRegistry 转换为 LangChain Tool 列表
- [ ] 处理异步工具函数
- [ ] 单元测试

### Step 4: LangChain Agent (`backend/agent/langchain_agent.py`)
- [ ] 创建 Agent 核心类
- [ ] 集成 ConversationSummaryBufferMemory
- [ ] 对话历史加载/保存
- [ ] 集成测试

### Step 5: API 集成 (`backend/main.py`)
- [ ] 添加环境变量 `USE_LANGCHAIN` 切换
- [ ] 修改 `/chat` 端点支持双轨运行
- [ ] 集成测试

### Step 6: 测试验证
- [ ] 运行全量测试：`python -m pytest tests/ -v`
- [ ] 手动测试：验证多步推理、对话记忆
- [ ] 性能对比：新旧实现响应时间

## 验证命令

```bash
# 安装依赖
pip install -e ".[langchain]"

# 运行测试
python -m pytest tests/ -v

# 启动服务测试
USE_LANGCHAIN=true uvicorn backend.main:app --reload --port 8000
```
