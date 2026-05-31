# 技术设计

## 1. 灵魂追问修复

**改动文件**：`backend/soul_query.py`

**方案**：将 `MAX_QUERY_ROUNDS` 从 3 改为 5。

逻辑分析：
- 必问字段 4 个（score, province, subject, family_background）
- 选问字段最多追问 1 个
- 当前 `get_next_question` 每调用一次 `round_count += 1`
- 改为 5 后：4 轮必问 + 1 轮选问 = 正好

**不改的原因**：动态计算更复杂且无必要，常量 5 足够清晰。

## 2. 上下文裁剪

**改动文件**：`backend/agent/core.py`

**方案**：在 `chat` 和 `chat_stream` 方法中，构建 `full_messages` 后、调用 API 前，插入裁剪步骤。

裁剪策略：
- 始终保留 system prompt（第 0 条）
- 保留最近 `MAX_HISTORY_ROUNDS` 轮对话（默认 20 轮 = 40 条消息）
- 超出部分从最旧的非 system 消息开始删除
- 裁剪时如果遇到 tool 消息但对应的 assistant 消息被裁掉了，也一并删除（避免 tool_call_id 悬空）

```
MAX_HISTORY_ROUNDS = 20  # 可配置

def _trim_messages(messages: list[dict], max_rounds: int) -> list[dict]:
    if len(messages) <= 1 + max_rounds * 2:
        return messages
    return [messages[0]] + messages[-(max_rounds * 2):]
```

**为什么不用摘要**：引入复杂度和额外 API 调用，MVP 阶段滑动窗口够用。

## 3. 会话持久化

**新增文件**：`backend/session_store.py`
**改动文件**：`backend/main.py`、`backend/database.py`

**方案**：新增 `ChatSession` 和 `ChatMessage` 两张表，替换 `sessions: dict`。

表结构：
```sql
CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_context JSON DEFAULT '{}',
    query_state JSON DEFAULT '{}'
);

CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
    role TEXT NOT NULL,        -- user / assistant / tool
    content TEXT,
    tool_call_id TEXT,         -- for tool messages
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_messages_session ON chat_messages(session_id);
```

SessionStore 类接口：
```python
class SessionStore:
    async def get_or_create(self, session_id: str) -> dict
    async def add_message(self, session_id: str, role: str, content: str) -> None
    async def get_history(self, session_id: str) -> list[dict]
    async def delete(self, session_id: str) -> None
    async def update_context(self, session_id: str, context: dict) -> None
```

**兼容性**：`main.py` 中 `sessions` dict 替换为 `SessionStore` 实例，接口不变。
