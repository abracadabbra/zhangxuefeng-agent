---
schemaVersion: 1
scope: workspace
updatedAt: "2026-05-27T13:58:13.228Z"
workspaceName: zhangxuefeng-agent
---

# Project Memory

## Project Overview
- 项目：张雪峰 AI 咨询 Agent 前端界面。
- 目标：构建一个基于张雪峰心智模型的 AI 教育咨询产品前端，核心交互为对话式，支持高考志愿、考研规划、职业规划三大场景。
- 目标用户：考生、家长、考研学生，移动端优先（微信小程序方向）。

## Current State
- 前端项目已存在于 `frontend/`，基于 React 19 + TypeScript + Tailwind CSS + Vite。
- **已实现**：ChatInterface（SSE 流式对话）、MessageBubble、SourcePanel（数据来源卡片+详情弹窗）、UserProfilePanel（用户画像表单）、FeedbackRating + FeedbackDashboard（反馈系统）、类型定义（types/index.ts）。
- **缺失**：门户首页（三大场景入口）、深靛蓝+琥珀金配色（当前用 Tailwind 默认蓝 #3b82f6）、分步表单（灵魂追问交互）、移动端优先布局。
- **无** `DESIGN.md` 设计规范文件。
- 技术栈：组件直接 fetch 后端 API（`/api/v1/chat`, `/api/profile/` 等），Vitest 测试。
- **状态更新**：已将尝试修改的 `tailwind.config.js` 和 `index.css` 回退至原始状态（默认蓝配色）。

## Artifacts
- **README.md**: 项目描述、功能列表和快速开始指南。
- **SKILL.md**: 张雪峰完整角色定义、思维框架、回答风格和核心原则，含 5 个核心心智模型、8 条决策启发式、表达 DNA。
- **docs/technical-plan.md**: 技术架构方案 v1.0，前后端分离、Agentic 工作流。
- **frontend/src/App.tsx**: 主组件，Header + ChatInterface 切换，缺少门户首页路由。
- **frontend/src/components/**: ChatInterface、MessageBubble、SourcePanel、UserProfilePanel、FeedbackRating、FeedbackDashboard。
- **frontend/tailwind.config.js**: 当前配色为 Tailwind 默认蓝（#3b82f6），已恢复原状。

## Design Direction
- **风格**: 门户引导型 + 专业学术风，建立可信赖感，避免冷冰冰科技感。
- **配色**: 深靛蓝 (#1a237e, #283593) + 暖琥珀金 (#ffb300, #ffa000)，专业稳重且不失温度。（**计划中，尚未实施**）
- **布局**: 首页门户式引导，三大场景卡片分流；场景内分步表单（"灵魂追问"）+ 对话聊天双模式。
- **核心气质**: "数据驱动" + "说真话"，像一个"咨询室"入口。

## User Feedback
- 用户确认"门户引导型 + 专业学术风"设计方向。
- 用户要求设计需基于 README.md 和 SKILL.md。
- 用户倾向先做简单版本，逐步迭代。

## Decisions
- 产品形态为**门户引导型**首页，非直接进入聊天框。
- 三大场景入口：高考志愿、考研规划、职业规划，卡片式分流。
- 核心交互为**分步表单**（收集关键信息）与**对话式聊天**双模式。
- 配色：深靛蓝 + 暖琥珀金。
- 布局响应式优先，适配移动端。

## Open Questions
- UI 组件（卡片、输入框、按钮）的详细样式规范。
- 用户登录/认证流程设计。
- 历史会话列表和会话管理 UI。
- "数据驱动"特质在界面上的可视化呈现。

## Next Steps
- 改造配色：将 tailwind.config.js 和全局样式从默认蓝换成深靛蓝+琥珀金。
- 加门户首页：App.tsx 增加三大场景卡片入口路由。
- 加分步表单：实现“灵魂追问”多步交互组件。
- 移动端适配：响应式布局优化。

## Promotion Candidates For DESIGN.md
- 主色调（深靛蓝 + 暖琥珀金）及使用场景。
- 门户引导型布局规范。
- 分步表单与对话聊天双模式交互规范。
- 卡片组件、按钮组件基础样式（待细化）。

## Recent History
- **2026-05-26**: 用户提供项目上下文，确认“门户引导型+专业学术风”方向，开始设计。
- **2026-05-27**: 完整检查前端项目源码，发现已有完整聊天+反馈系统但缺少门户首页、正确配色、分步表单和移动端适配，向用户汇报现状并提出四项改造建议。随后尝试修改配色，但根据用户要求，已将 `tailwind.config.js` 和 `index.css` 的修改回退。