# 实现计划

## 执行顺序

### Step 1: search_policy stub 清理
- [ ] `backend/tools/definitions.py`: 移除 `search_policy` 注册或改为友好提示
- [ ] 验证：工具列表中不再包含 search_policy（或返回友好提示）

### Step 2: LLM 调用重试 + 降级
- [ ] `backend/agent/core.py`: 添加重试装饰器或重试逻辑
- [ ] 验证：mock 429 响应时自动重试

### Step 3: 前端历史会话
- [ ] `backend/main.py`: 新增 `GET /sessions` 列表接口
- [ ] `frontend/src/App.tsx`: 添加历史会话入口
- [ ] `frontend/src/components/ChatInterface.tsx`: 加载历史消息
- [ ] 验证：重启后可看到并恢复历史会话

### Step 4: 工具结果缓存
- [ ] `backend/tools/registry.py`: 添加 TTL 缓存层
- [ ] 验证：相同参数连续调用第二次命中缓存

### Step 5: 对话导出
- [ ] `backend/main.py`: 新增 `GET /session/{id}/export` 接口
- [ ] 前端添加导出按钮
- [ ] 验证：下载的 .md 文件包含完整对话

### Step 6: 反馈机制
- [ ] `backend/models/`: 新增 Feedback ORM 模型
- [ ] `backend/main.py`: 新增 `POST /api/v1/feedback` 和 `GET /api/v1/feedback/stats`
- [ ] 验证：前端点赞/点踩能提交

## 验证命令

```bash
backend/.venv/bin/python -m pytest tests/ -v
```
