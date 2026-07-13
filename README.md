# AI ASO (App Store Optimization) Multi-Agent Platform

An AI-powered platform that researches trending apps, keywords, competitors,
and market opportunities, and produces daily/weekly intelligence reports —
replacing a manual ASO specialist.

## Module Roadmap

| # | Module | Status |
|---|--------|--------|
| 1 | Project Foundation (this delivery) | ✅ Done |
| 2 | App Store Research Agent | ⏳ Next |
| 3 | Google Play Research Agent | ⏳ |
| 4 | Keyword Research Agent | ⏳ |
| 5 | Competitor Analysis Agent | ⏳ |
| 6 | Reviews Intelligence Agent | ⏳ |
| 7 | Market Opportunity Agent | ⏳ |
| 8 | AI Idea Generator Agent | ⏳ |
| 9 | Report Generator Agent | ⏳ |
| 10 | Memory Agent | ⏳ |
| 11 | Coordinator Agent + Agent Runtime (OpenFang/ZeroClaw) | ⚠️ Blocked — see below |
| 12 | CrewAI Orchestration | ⏳ (depends on 11) |
| 13 | Dashboard | ⏳ |
| 14 | Testing / Docker / Docs polish | ⏳ |

### A note on Module 11 (OpenFang/ZeroClaw)

"OpenFang/ZeroClaw" is not a runtime with public documentation available.
Every agent in this codebase is built against an `AgentRuntime` abstract
interface (`app/core/agent_runtime.py`) instead of any concrete SDK, so:

- **Modules 2–10 and 12–14 work fully today** using `MockAgentRuntime`
  (set `AGENT_RUNTIME=mock` in `.env`, the default).
- When you're ready for Module 11, get the real OpenFang/ZeroClaw
  SDK/API docs (ask ChatGPT — see prompt below), then implement
  `OpenFangZeroClawRuntime.run_task()` / `.health_check()` to match. Flip
  `AGENT_RUNTIME=openfang_zeroclaw` in `.env` — nothing else in the
  codebase needs to change.

**Suggested ChatGPT prompt for Module 11**, once you're ready:

> I'm integrating an agent runtime called "OpenFang/ZeroClaw" into a Python
> FastAPI + CrewAI project. Explain what OpenFang/ZeroClaw is, how to
> install/authenticate it, and show a minimal Python example of submitting
> a task to an agent and retrieving the result (sync and async if
> supported). I need to implement it against this interface:
>
> ```python
> class AgentRuntime(ABC):
>     def run_task(self, agent_name: str, task_name: str, inputs: dict) -> AgentTaskResult: ...
>     def health_check(self) -> bool: ...
> ```
>
> Give me the concrete implementation of both methods.

## Project Structure

```
ai_aso_platform/
├── app/
│   ├── core/
│   │   ├── config.py          # centralized settings (pydantic-settings)
│   │   ├── logging.py         # loguru setup (console + rotating file logs)
│   │   ├── database.py        # SQLAlchemy engine/session
│   │   ├── agent_runtime.py   # AgentRuntime interface + Mock/OpenFang backends
│   │   └── scheduler.py       # APScheduler shell for daily/weekly jobs
│   ├── models/
│   │   ├── db_models.py       # ORM models (TrendingApp, Keyword, Competitor, etc.)
│   │   └── schemas.py         # Pydantic API schemas
│   ├── agents/                # Module 2-10 agents land here
│   ├── services/               # business logic shared across agents
│   ├── api/                   # FastAPI routers per module
│   ├── utils/
│   │   └── retry.py           # exponential-backoff retry decorator
│   └── main.py                # FastAPI app entrypoint
├── tests/                     # pytest suite (12 tests, all passing)
├── data/
│   ├── db/                    # SQLite file lives here by default
│   └── reports/               # generated PDF/MD/HTML reports land here
├── logs/                      # rotating app.log / errors.log
├── docker/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env: add your OPENAI_API_KEY or ANTHROPIC_API_KEY (needed from Module 2+)

# 4. Run tests
pytest -v

# 5. Run the API
uvicorn app.main:app --reload
# Visit http://localhost:8000/health
```

## Docker

```bash
docker compose up --build
```

## What's included in Module 1

- **Folder structure** for the full project (agents, services, api, utils, models)
- **Config system** (`app/core/config.py`) — single source of truth for all env vars
- **Logging** (`app/core/logging.py`) — console + rotating file logs, error-only log
- **Database layer** (`app/core/database.py`) — SQLAlchemy engine/session, SQLite by
  default, one-line swap to Postgres for production
- **Full ORM schema** (`app/models/db_models.py`) covering every entity in the brief:
  `TrendingApp`, `Keyword`, `Competitor`, `Review`, `MarketOpportunity`,
  `ProductIdea`, `Report`, `MemoryEntry`
- **Pydantic API schemas** (`app/models/schemas.py`)
- **Retry utility** (`app/utils/retry.py`) — exponential backoff for flaky
  scraping/API calls, used by every research agent from Module 2 onward
- **AgentRuntime abstraction** (`app/core/agent_runtime.py`) — the key
  architectural piece that lets us build everything now and swap in
  OpenFang/ZeroClaw later
- **Scheduler shell** (`app/core/scheduler.py`) — APScheduler wired up,
  ready for Module 9 to register the daily/weekly report jobs
- **FastAPI app** (`app/main.py`) with `/health` and `/health/runtime` endpoints
- **Docker + docker-compose** — production-ready container setup
- **12 passing pytest tests** covering config, DB models, agent runtime, and API

## Next: Module 2 — App Store Research Agent

Discovers trending apps from Apple's App Store (Top Free/Paid/Grossing +
fast-growing), normalizes them into `TrendingApp` rows.
