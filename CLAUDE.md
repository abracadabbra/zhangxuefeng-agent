# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered educational consulting agent modeled after Zhang Xuefeng (张雪峰). Provides college admissions (高考), graduate school (考研), and career planning advice using an agentic workflow that queries real data before responding. The persona definition lives in `SKILL.md` and is injected as the LLM system prompt.

## Dual Backend Architecture

Two parallel FastAPI backends coexist:

- **`app/`** — Primary. Used by Docker and Fly.io. Redis-backed sessions, SSE streaming, Soul Query engine, LLM tool calling. Lighter, production-focused.
- **`backend/`** — Secondary/legacy. SQLAlchemy ORM with SQLite, seed data, data query routers (schools/majors/scores/plans), web search module. More features, uses in-memory sessions.

When modifying backend code, be clear which backend you're targeting. The Dockerfile and `docker-compose.yml` run `app/`.

## Commands

### Backend (project root)

```bash
pip install -e ".[dev]"                    # Install deps (includes dev tools)
uvicorn app.main:app --reload --port 8000  # Dev server (app/ backend)
uvicorn backend.main:app --reload --port 8000  # Dev server (backend/ backend)
pytest tests/                              # Run all tests
pytest tests/test_soul_query.py -k test_name  # Run single test
ruff check app/ backend/                   # Lint
ruff format app/ backend/                  # Format
alembic upgrade head                       # Run migrations
alembic revision --autogenerate -m "desc"  # Generate migration
```

### Frontend (from `frontend/`)

```bash
npm install         # Install deps
npm run dev         # Dev server on port 3000 (proxies /api → localhost:8000)
npm run build       # Production build (tsc -b && vite build)
npm run test        # Run tests (vitest run)
npm run lint        # ESLint
```

### Docker

```bash
docker compose up -d       # Start API + Redis
docker compose logs -f api # View logs
```

## Key Architecture

### Chat Flow

User message → `app/services/soul_query.py` checks if user profile is complete → if incomplete, asks follow-up questions (max 3 rounds) → once complete, builds context with SKILL.md system prompt + user profile + history → calls LLM via `app/services/llm.py` (optionally with Function Calling tools from `app/agent/tools.py`) → streams response via SSE through `app/api/chat.py`.

### Core Modules (app/)

- `app/services/soul_query.py` — "灵魂追问" engine, collects required user profile fields (score, province, subject, family_background)
- `app/services/context.py` — Entity extraction from messages, context window management
- `app/services/llm.py` — OpenAI-compatible LLM client (httpx-based)
- `app/services/streaming.py` — SSE streaming for LLM responses
- `app/services/session.py` — Redis session storage (24h TTL)
- `app/services/skill.py` — Loads SKILL.md as system prompt
- `app/agent/tools.py` — 5 function-calling tools (web_search, search_admission, search_employment, compare_schools, calculate_match)
- `app/models/user_profile.py` — UserProfile model (4 required + 3 optional fields)

### Backend Data Layer (backend/)

- `backend/models/` — SQLAlchemy ORM: School, Major, AdmissionScore, EnrollmentPlan
- `backend/routers/` — REST endpoints for querying schools, majors, scores, plans
- `backend/seeds/` — JSON seed data + import scripts
- `backend/crud/` — CRUD operations per model

### Frontend (frontend/)

- `frontend/src/App.tsx` — 3 views: Portal (newspaper-style homepage), SoulQuestionForm, Chat
- `frontend/src/components/ChatInterface.tsx` — SSE streaming chat UI
- `frontend/src/components/SoulQuestionForm.tsx` — Multi-step profile collection form
- Design: Tailwind CSS with custom "newspaper" theme (ink, gold, paper colors, serif fonts)

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, httpx, Pydantic v2, Redis, SQLAlchemy + Alembic (backend/ only)
- **Frontend**: React 18, TypeScript, Vite 6, Tailwind CSS 3.4
- **Testing**: pytest + pytest-asyncio (backend), Vitest + @testing-library/react (frontend)
- **Linting**: Ruff (line-length 100, py311), ESLint 9 (frontend)
- **Deploy**: Docker, Fly.io (Hong Kong region)

## Configuration

Environment variables (see `.env.example`):
- `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `MODEL` — LLM configuration
- `REDIS_URL` — Session storage
- `DATABASE_URL` — SQLite path (backend/ only)
- `SKILL_PATH` — Path to persona definition (default: `SKILL.md`)
- `SENTRY_DSN` — Error tracking
- `COST_ALERT_THRESHOLD_USD` — LLM cost alert (default: $50)

## Conventions

- Ruff config: `select = ["E", "F", "I", "UP", "B"]`, line-length 100, py311
- pytest: `asyncio_mode = "auto"`, test paths in `tests/`
- Frontend Vite proxy: `/api` → `http://localhost:8000`
- The root `App.jsx` is an early prototype artifact — not part of the Vite frontend
