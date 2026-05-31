# 实现计划

## 执行顺序

### Step 1: 灵魂追问修复
- [ ] `backend/soul_query.py`: MAX_QUERY_ROUNDS 3 → 5
- [ ] 验证：运行 soul_query 相关测试，确认 4 个必问 + 1 个选问都能触发

### Step 2: 上下文裁剪
- [ ] `backend/agent/core.py`: 添加 `_trim_messages` 函数
- [ ] `backend/agent/core.py`: 在 `chat` 和 `chat_stream` 中调用裁剪
- [ ] 验证：构造 50+ 轮消息，确认不报错且保留最近对话

### Step 3: 会话持久化
- [ ] `backend/models/`: 新增 ChatSession、ChatMessage ORM 模型
- [ ] `backend/session_store.py`: 实现 SessionStore 类
- [ ] `backend/database.py`: 注册新表到 metadata
- [ ] `backend/main.py`: 替换 `sessions: dict` 为 SessionStore
- [ ] 验证：重启后历史会话可恢复

### Step 4: 测试
- [ ] `tests/test_soul_query.py`: 修复/新增灵魂追问测试
- [ ] `tests/test_context_trimming.py`: 新增上下文裁剪测试
- [ ] `tests/test_session_store.py`: 新增会话持久化测试
- [ ] 运行全量测试确认无回归

## 验证命令

```bash
cd backend && python -m pytest tests/ -v
```
