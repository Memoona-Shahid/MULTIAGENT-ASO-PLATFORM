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
from app.core.database import init_db
from app.core.logging import logger
from app.models.schemas import HealthOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting {} [{}]", settings.app_name, settings.app_env)
    init_db()
    logger.info("Agent runtime backend: {}", settings.agent_runtime)
    yield
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
from app.api import app_store, google_play, keywords  # noqa: E402

app.include_router(app_store.router, prefix="/api/app-store", tags=["app-store"])
app.include_router(google_play.router, prefix="/api/google-play", tags=["google-play"])
app.include_router(keywords.router, prefix="/api/keywords", tags=["keywords"])

# --- Routers from future modules get included here ---
