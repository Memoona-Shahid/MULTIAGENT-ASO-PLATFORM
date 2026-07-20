# AI ASO (App Store Optimization) Multi-Agent Platform

An AI-powered platform that researches trending apps, keywords, competitors,
and market opportunities, and produces daily/weekly intelligence reports —
replacing a manual ASO specialist.

## Module Roadmap

| # | Module | Status |
|---|--------|--------|
| 1 | Project Foundation | ✅ Done |
| 2 | App Store Research Agent | ✅ Done |
| 3 | Google Play Research Agent | ✅ Done |
| 4 | Keyword Research Agent | ✅ Done |
| 5 | Competitor Analysis Agent | ✅ Done |
| 6 | Reviews Intelligence Agent | ✅ Done |
| 7 | Market Opportunity Agent | ✅ Done |
| 8 | AI Idea Generator Agent | ✅ Done |
| 9 | Report Generator Agent | ✅ Done |
| 10 | Memory Agent | ✅ Done |
| 11 | Coordinator Agent + Agent Runtime (ZeroClaw) | ✅ Done |
| 12 | CrewAI Orchestration | ✅ Done |
| 13 | Dashboard | ✅ Done |
| 14 | Testing / Docker / Docs polish | ✅ Done |

### Module 11 — ZeroClaw runtime

`OpenFangZeroClawRuntime` talks to a running [ZeroClaw](https://zeroclaw.net)
HTTP gateway (OpenClaw-compatible lineage):

```bash
# On a machine with ZeroClaw installed:
zeroclaw gateway   # default http://127.0.0.1:42617
# Pair once, save the bearer token into .env
```

```env
AGENT_RUNTIME=openfang_zeroclaw
OPENFANG_ZEROCLAW_BASE_URL=http://127.0.0.1:42617
OPENFANG_ZEROCLAW_API_KEY=zcl_live_...
```

Endpoints used: `GET /health`, `POST /api/chat` (fallback `POST /webhook`).
Default remains `AGENT_RUNTIME=mock` for offline/dev.

### Module 12 — CrewAI orchestration

Existing agents stay plain Python. CrewAI wraps them as tools under
`app/agents/crew/`. Choose orchestration mode:

```env
ORCHESTRATION_MODE=direct   # CoordinatorAgent (default, no LLM required)
ORCHESTRATION_MODE=crewai   # sequential Crew (needs OPENAI_API_KEY or ANTHROPIC_API_KEY)
```

Dashboard override: `POST /api/dashboard/run-daily?use_crewai=true`.
If CrewAI mode is selected but no LLM key is set, the pipeline falls back to
the direct coordinator automatically.

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
# Edit .env: add OPENAI_API_KEY (needed for ORCHESTRATION_MODE=crewai)

# 4. Run tests
pytest -v

# 5. Run the API
uvicorn app.main:app --reload
# Visit http://localhost:8000/          (dashboard)
#       http://localhost:8000/health
#       http://localhost:8000/docs
```

## Docker

```bash
docker compose up --build
```

## Orchestration quick test (PowerShell)

```powershell
# Direct coordinator (default)
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/dashboard/run-daily?opportunity_limit=5"

# Force CrewAI path (falls back to direct if no LLM key)
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/dashboard/run-daily?use_crewai=true&opportunity_limit=5"
```

## Architecture notes

- **Agents** (`app/agents/*`) are plain Python — unit-testable without an LLM.
- **CrewAI** (`app/agents/crew/`) wraps those agents as tools for multi-agent runs.
- **ZeroClaw** (`OpenFangZeroClawRuntime`) is an optional remote runtime for
  telemetry / task dispatch via HTTP gateway.
- **Dashboard** at `/` aggregates ideas, opportunities, trends, and reports.
