# CLAUDE.md

## Project Overview

AI-powered educational consulting agent modeled after Zhang Xuefeng (张雪峰). Provides college admissions (高考), graduate school (考研), and career planning advice. The persona definition lives in `SKILL.md` and is loaded as the LLM system prompt.

## Commands

### Backend

```bash
pip install -e ".[dev]"                          # Install deps
uvicorn backend.main:app --reload --port 8000    # Dev server
ruff check backend/                              # Lint
ruff format backend/                             # Format
alembic upgrade head                             # Run migrations
```

### Frontend (from `frontend/`)

```bash
npm install
npm run dev        # Dev server on port 3000 (proxies /api → localhost:8000)
npm run build      # Production build
npm run test       # Vitest
npm run lint       # ESLint
```

### Docker

```bash
docker compose up -d
docker compose logs -f api
```

## Architecture

### Chat Flow

User message → `backend/main.py` receives POST /chat → `backend/soul_query.py` checks if user profile is complete → if incomplete, asks follow-up questions (max 3 rounds) → once complete, injects profile as context → calls LLM via `backend/agent/core.py` (AgentCore) with SKILL.md as system prompt → SSE streamed response.

### Core Modules

- `backend/main.py` — FastAPI app, routes (chat, profile, session, health, db)
- `backend/agent/core.py` — OpenAI API + Function Calling + multi-round tool loop
- `backend/agent/prompt.py` — Built-in system prompt (fallback if SKILL.md not found)
- `backend/tools/definitions.py` — 5 registered tools (search_admission, search_employment, compare_schools, search_policy, calculate_match)
- `backend/tools/registry.py` — Decorator-based tool registry + dispatch
- `backend/soul_query.py` — "灵魂追问" engine (score, province, subject, family_background)
- `backend/user_profile.py` — UserProfile model + Redis persistence
- `backend/models/` — SQLAlchemy ORM: School, Major, AdmissionScore, EnrollmentPlan, SubjectRanking
- `backend/routers/` — REST endpoints for data queries
- `backend/crud/` — CRUD operations per model
- `backend/seeds/` — JSON seed data + import scripts
- `backend/database.py` — SQLAlchemy engine + session factory

### Frontend

- React 18 + TypeScript + Vite 6 + Tailwind CSS 3.4
- 3 views: Portal (homepage), SoulQuestionForm (profile collection), Chat (SSE streaming)

## Conventions

- Ruff: `select = ["E", "F", "I", "UP", "B"]`, line-length 100, py311
- Vite proxy: `/api` → `http://localhost:8000`
