# 张雪峰 AI 咨询 Agent

> 张雪峰的认知操作系统，可运行的高考/考研/职业规划顾问

## 功能

- 🎯 **高考志愿咨询**：根据分数/省份/家庭背景，给出选校选专业建议
- 📚 **考研规划**：择校、择专业、备考策略
- 💼 **职业规划**：应届生就业方向、行业选择
- 🔍 **AI 驱动**：基于张雪峰心智模型 + 实时数据查询

## 快速开始

### 作为 Hermes Skill 运行

```bash
# 克隆到 Hermes skills 目录
git clone https://github.com/abracadabbra/zhangxuefeng-agent.git
cp -r zhangxuefeng-agent ~/.hermes/skills/zhangxuefeng-agent
```

### 作为独立服务运行

```bash
# 后端
cd backend && pip install -r requirements.txt && python main.py

# 前端
cd frontend && npm install && npm run dev
```

## 项目结构

```
zhangxuefeng-agent/
├── SKILL.md              # 核心技能定义
├── README.md
├── backend/
│   ├── main.py           # FastAPI 主入口
│   ├── skills/          # 技能模块
│   └── services/        # 业务逻辑
├── frontend/             # 未来：Web/小程序前端
└── docs/                 # 设计文档
```

## 商业模式

- **C 端**：微信小程序咨询，按次收费
- **B 端**：考研/志愿填报机构 SaaS
- **会员订阅**：高级功能（模拟面试、定制方案）

## License

MIT
