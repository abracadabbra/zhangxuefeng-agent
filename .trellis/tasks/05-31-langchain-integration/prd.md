# PRD: LangChain 集成

## 背景

引入 LangChain 增强 Agent 能力，解决当前架构的局限性。

## 需求

### Phase 1: LLM 层替换
- 将 `openai` SDK 直连改为 LangChain `ChatOpenAI`
- 保持现有 `/chat` API 接口不变
- 支持一行代码切换 LLM provider

### Phase 2: Agent 多步推理
- 引入 LangChain Agent，支持自主串联多个工具调用
- 复用现有 ToolRegistry 中的 6 个工具
- 保持 SKILL.md 作为 system prompt

### Phase 3: 对话记忆
- 替换手写滑动窗口裁剪为 `ConversationSummaryBufferMemory`
- 前 10 轮保留原文，超出部分自动摘要
- 保持 session_store 持久化

## 验收标准

- [ ] `/chat` 接口功能不变，现有测试全部通过
- [ ] LLM provider 可通过环境变量切换
- [ ] Agent 能自主串联多个工具调用
- [ ] 长对话自动摘要，不丢失关键信息
- [ ] 新增测试覆盖 LangChain 集成逻辑
