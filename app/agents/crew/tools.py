"""
CrewAI tools that wrap the existing plain-Python ASO agents.

The underlying agents stay unit-testable without an LLM. These tools are the
bridge Module 12 uses so a Crew can call them during orchestration.
"""

from __future__ import annotations

import json
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.agents.app_store_research_agent import AppStoreResearchAgent
from app.agents.competitor_analysis_agent import CompetitorAnalysisAgent
from app.agents.google_play_research_agent import GooglePlayResearchAgent
from app.agents.keyword_research_agent import KeywordResearchAgent
from app.agents.market_opportunity_agent import MarketOpportunityAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.report_generator_agent import ReportGeneratorAgent
from app.models.db_models import Platform, ReportFormat, ReportType
from app.services.market_seed_service import (
    build_competitor_targets_from_trends,
    build_keyword_seeds_from_trends,
)


def _dump(result: Any) -> str:
    try:
        return json.dumps(result, default=str, ensure_ascii=False)
    except TypeError:
        return str(result)


class EmptyArgs(BaseModel):
    pass


class KeywordResearchArgs(BaseModel):
    suggestions_per_seed: int = Field(default=6, ge=1, le=20)
    seed_limit: int = Field(default=10, ge=1, le=50)


class CompetitorArgs(BaseModel):
    competitor_limit: int = Field(default=6, ge=1, le=30)
    reviews_per_app: int = Field(default=8, ge=1, le=50)


class OpportunityArgs(BaseModel):
    min_score: float = Field(default=10.0, ge=0, le=100)
    min_keyword_opportunity: float = Field(default=40.0, ge=0, le=100)


class ReportArgs(BaseModel):
    opportunity_limit: int = Field(default=10, ge=1, le=50)
    ideas_per_opportunity: int = Field(default=1, ge=1, le=3)
    report_format: str = Field(default="markdown")


class MemoryArgs(BaseModel):
    lookback_days: int = Field(default=1, ge=1, le=30)
    per_source_limit: int = Field(default=50, ge=1, le=200)


class _DbTool(BaseTool):
    """Base for tools that close over a SQLAlchemy session."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    db: Any = None


class ResearchAppStoreTool(_DbTool):
    name: str = "research_app_store_trends"
    description: str = (
        "Fetch Apple App Store top charts, detect fast-growing apps, and persist "
        "trending_app snapshots."
    )
    args_schema: type[BaseModel] = EmptyArgs

    def _run(self) -> str:
        return _dump(AppStoreResearchAgent().run(self.db))


class ResearchGooglePlayTool(_DbTool):
    name: str = "research_google_play_trends"
    description: str = (
        "Fetch Google Play top charts and persist trending_app snapshots."
    )
    args_schema: type[BaseModel] = EmptyArgs

    def _run(self) -> str:
        return _dump(GooglePlayResearchAgent().run(self.db))


class ResearchKeywordsTool(_DbTool):
    name: str = "research_keywords"
    description: str = (
        "Derive keyword seeds from trending apps and expand them via store "
        "autocomplete into scored Keyword rows."
    )
    args_schema: type[BaseModel] = KeywordResearchArgs

    def _run(self, suggestions_per_seed: int = 6, seed_limit: int = 10) -> str:
        seeds = build_keyword_seeds_from_trends(self.db, limit=seed_limit)
        if not seeds:
            return _dump({"total_keywords": 0, "seeds": {}, "note": "No trend-derived seeds"})
        result = KeywordResearchAgent().run(
            self.db,
            seed_terms=seeds,
            platforms=[Platform.GOOGLE_PLAY, Platform.APP_STORE],
            suggestions_per_seed=suggestions_per_seed,
        )
        result = dict(result)
        result["keyword_seeds"] = seeds
        return _dump(result)


class AnalyzeCompetitorsTool(_DbTool):
    name: str = "analyze_competitors"
    description: str = (
        "Pick competitor targets from trending apps and run competitor + review analysis."
    )
    args_schema: type[BaseModel] = CompetitorArgs

    def _run(self, competitor_limit: int = 6, reviews_per_app: int = 8) -> str:
        targets = build_competitor_targets_from_trends(self.db, limit=competitor_limit)
        if not targets:
            return _dump({"total_competitors": 0, "note": "No trending apps available"})
        result = CompetitorAnalysisAgent().run(
            self.db,
            targets=targets,
            reviews_per_app=reviews_per_app,
        )
        result = dict(result)
        result["competitor_targets"] = len(targets)
        return _dump(result)


class SynthesizeOpportunitiesTool(_DbTool):
    name: str = "synthesize_market_opportunities"
    description: str = (
        "Combine trends, keywords, and competitor signals into MarketOpportunity rows."
    )
    args_schema: type[BaseModel] = OpportunityArgs

    def _run(self, min_score: float = 10.0, min_keyword_opportunity: float = 40.0) -> str:
        return _dump(
            MarketOpportunityAgent().run(
                self.db,
                min_score=min_score,
                min_keyword_opportunity=min_keyword_opportunity,
            )
        )


class GenerateDailyReportTool(_DbTool):
    name: str = "generate_daily_report"
    description: str = (
        "Generate product ideas from opportunities and render a daily intelligence report."
    )
    args_schema: type[BaseModel] = ReportArgs

    def _run(
        self,
        opportunity_limit: int = 10,
        ideas_per_opportunity: int = 1,
        report_format: str = "markdown",
    ) -> str:
        fmt = ReportFormat.MARKDOWN
        if report_format.lower() in {e.value for e in ReportFormat}:
            fmt = ReportFormat(report_format.lower())
        return _dump(
            ReportGeneratorAgent().run(
                self.db,
                report_type=ReportType.DAILY,
                report_format=fmt,
                generate_ideas=True,
                min_opportunity_score=0.0,
                ideas_per_opportunity=ideas_per_opportunity,
                opportunity_limit=opportunity_limit,
            )
        )


class ConsolidateMemoryTool(_DbTool):
    name: str = "consolidate_memory"
    description: str = (
        "Consolidate recent intelligence into MemoryEntry rows for long-term recall."
    )
    args_schema: type[BaseModel] = MemoryArgs

    def _run(self, lookback_days: int = 1, per_source_limit: int = 50) -> str:
        return _dump(
            MemoryAgent().run(
                self.db,
                lookback_days=lookback_days,
                per_source_limit=per_source_limit,
                min_importance=0.5,
            )
        )


def build_aso_tools(db: Session) -> list[BaseTool]:
    """Create the full tool set bound to a DB session."""
    return [
        ResearchAppStoreTool(db=db),
        ResearchGooglePlayTool(db=db),
        ResearchKeywordsTool(db=db),
        AnalyzeCompetitorsTool(db=db),
        SynthesizeOpportunitiesTool(db=db),
        GenerateDailyReportTool(db=db),
        ConsolidateMemoryTool(db=db),
    ]
