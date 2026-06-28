# Codex Worktree 合并后修复计划

## 背景

将 Codex worktree（数据溯源系统 + 数据流水线）合并到 main 分支后，测试结果为 **41 failed, 454 passed**。

### 合并的新功能

| 模块 | 说明 |
|------|------|
| `backend/data_pipeline/` | 完整的 real-data 数据流水线（sources → intake → parsers → loaders → pilots → lineage） |
| `backend/models/data_lineage.py` | 3 个 ORM 模型：DataSourceRecord、DataSnapshot、DataLineageRecord |
| `backend/agent/source_policy.py` | Agent 来源策略审查（汇总工具调用的数据来源可信度） |
| `backend/tools/definitions.py` | 工具定义扩展（5→7 个工具），新增源追踪 source_summary |
| `backend/routes/chat.py` | SSE 流式响应中集成 source_policy_review |

### 已完成的冲突解决

- 15 个冲突文件已全部解决
- `core.py` 已集成 source_policy 导入和返回值
- `definitions.py` 修复了 `search_employment` 未定义 `source_summary` 的 bug
- `chat.py` 补回了缺失的 `_summarize_tool_calls` / `_log_tool_call_summary` 函数
- Codex worktree 已清理删除

---

## 测试失败分类（41 个）

| 类别 | 数量 | 原因 | 难度 |
|------|------|------|------|
| test_integration.py | 22 | 路由前缀 `/api` 不匹配（历史遗留） | 中 |
| test_data_pipeline_* | 14 | Codex 流水线代码有 bug | 高 |
| test_data_lineage_sources.py | 3 | summarize_sources 实现与测试期望不匹配 | 中 |
| test_tool_definitions.py | 2 | 测试用旧格式，代码已改为新格式 | 低 |

---

## Task 1: 修复 test_tool_definitions.py（2 个，最快）

**文件**: `tests/test_tool_definitions.py`

**问题**: 测试断言旧的 `source`/`confidence` 顶层字段格式，代码已改为 `source_summary`/`answer_source_policy` 新格式。

**修复方式**: 更新测试断言，匹配新的返回结构。

---

## Task 2: 修复 test_data_lineage_sources.py（3 个）

**文件**: `tests/test_data_lineage_sources.py`

**问题**: `summarize_sources` 函数的实现返回格式与测试期望不一致。

**修复方式**: 对比实现和测试期望，统一接口契约（优先修测试以匹配实现）。

---

## Task 3: 修复 test_integration.py 路由前缀（22 个）

**文件**: `tests/test_integration.py`, `backend/main.py`

**问题**: `main.py` 中路由注册为 `prefix="/api"`，但集成测试直接调用 `/chat`、`/sessions` 等（不带 `/api` 前缀），导致全部 404。

**修复方式（二选一）**:
- 方案 A: 更新测试，所有路径加 `/api` 前缀
- 方案 B: 在 main.py 添加无前缀的兼容路由重定向

---

## Task 4: 修复 test_data_pipeline_* 流水线 bug（14 个）

**涉及文件**:
- `tests/test_data_pipeline_bundle.py` (4)
- `tests/test_data_pipeline_manifest.py` (1)
- `tests/test_data_pipeline_pilot.py` (5)
- `tests/test_data_pipeline_quality_gate.py` (2)
- `tests/test_data_pipeline_staging.py` (2)

**问题**: Codex worktree 中的数据流水线代码存在多处 bug，需要逐个排查。

**修复方式**: 逐个分析错误原因，修复 pipeline 代码或测试。

---

## 当前待提交

`backend/routes/chat.py` 有未暂存的修改（补回 `_summarize_tool_calls` 等函数），需要先提交。

```bash
git add backend/routes/chat.py
git commit --amend --no-edit
```

---

## 建议执行顺序

1. **先提交** chat.py 未暂存修改
2. **Task 1** — 最快见效（2 个测试）
3. **Task 2** — 中等难度（3 个测试）
4. **Task 3** — 批量修复（22 个测试）
5. **Task 4** — 最复杂（14 个测试，需要深入分析流水线代码）
