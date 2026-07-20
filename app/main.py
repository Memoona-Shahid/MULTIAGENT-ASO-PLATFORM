"""
FastAPI application entrypoint.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Modules 2-10 will each register their own routers under app/api/ and
include them here. For now this exposes just a health check so you can
verify the foundation is wired correctly end-to-end.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.agent_runtime import agent_runtime
from app.core.config import settings
from app.core.database import db_session, init_db
from app.core.logging import logger
from app.core.scheduler import (
    register_daily_job,
    register_weekly_job,
    shutdown_scheduler,
    start_scheduler,
)
from app.models.db_models import ReportFormat, ReportType
from app.models.schemas import HealthOut


def _run_scheduled_daily_report() -> None:
    from app.agents.coordinator_agent import CoordinatorAgent

    with db_session() as db:
        CoordinatorAgent().run_daily_pipeline(
            db,
            synthesize_opportunities=True,
            research_keywords=True,
            analyze_competitors=True,
            report_format=ReportFormat.MARKDOWN,
        )


def _run_scheduled_weekly_report() -> None:
    from app.agents.report_generator_agent import ReportGeneratorAgent

    with db_session() as db:
        ReportGeneratorAgent().run(
            db,
            report_type=ReportType.WEEKLY,
            report_format=ReportFormat.MARKDOWN,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting {} [{}]", settings.app_name, settings.app_env)
    init_db()
    logger.info("Agent runtime backend: {}", settings.agent_runtime)
    register_daily_job(_run_scheduled_daily_report)
    register_weekly_job(_run_scheduled_weekly_report)
    start_scheduler()
    yield
    shutdown_scheduler()
    logger.info("Shutting down {}", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="AI-powered ASO Multi-Agent Platform — automated app store intelligence.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthOut, tags=["system"])
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        app_env=settings.app_env,
        agent_runtime=settings.agent_runtime,
    )


@app.get("/health/runtime", tags=["system"])
def health_runtime() -> dict:
    return {"agent_runtime": settings.agent_runtime, "healthy": agent_runtime.health_check()}


# --- Routers ---
from app.api import app_store, competitors, dashboard, dashboard_data, google_play, keywords, memory, opportunities, product_ideas, reports, reviews  # noqa: E402

app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(dashboard_data.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(app_store.router, prefix="/api/app-store", tags=["app-store"])
app.include_router(google_play.router, prefix="/api/google-play", tags=["google-play"])
app.include_router(keywords.router, prefix="/api/keywords", tags=["keywords"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["competitors"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])
app.include_router(product_ideas.router, prefix="/api/product-ideas", tags=["product-ideas"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
