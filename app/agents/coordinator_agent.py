"""
Coordinator Agent (Module 11 core orchestration).

Daily pipeline:
  trends → keyword seeds → keyword research
  trends → competitor targets → competitor analysis
  opportunities → product ideas → daily report
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.ai_idea_generator_agent import AiIdeaGeneratorAgent
from app.agents.competitor_analysis_agent import CompetitorAnalysisAgent
from app.agents.keyword_research_agent import KeywordResearchAgent
from app.agents.market_opportunity_agent import MarketOpportunityAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.report_generator_agent import ReportGeneratorAgent
from app.core.agent_runtime import agent_runtime
from app.core.config import settings
from app.core.logging import logger
from app.models.db_models import Platform, ReportFormat, ReportType
from app.services.market_seed_service import (
    build_competitor_targets_from_trends,
    build_keyword_seeds_from_trends,
)


class CoordinatorAgent:
    """Orchestrates the full ASO intelligence workflow."""

    def __init__(
        self,
        opportunity_agent: MarketOpportunityAgent | None = None,
        idea_agent: AiIdeaGeneratorAgent | None = None,
        report_agent: ReportGeneratorAgent | None = None,
        memory_agent: MemoryAgent | None = None,
        keyword_agent: KeywordResearchAgent | None = None,
        competitor_agent: CompetitorAnalysisAgent | None = None,
    ):
        self.opportunity_agent = opportunity_agent or MarketOpportunityAgent()
        self.idea_agent = idea_agent or AiIdeaGeneratorAgent()
        self.report_agent = report_agent or ReportGeneratorAgent()
        self.memory_agent = memory_agent or MemoryAgent()
        self.keyword_agent = keyword_agent or KeywordResearchAgent()
        self.competitor_agent = competitor_agent or CompetitorAnalysisAgent()

    def run_daily_pipeline(
        self,
        db: Session,
        *,
        synthesize_opportunities: bool = True,
        research_keywords: bool = True,
        analyze_competitors: bool = True,
        opportunity_limit: int = 10,
        ideas_per_opportunity: int = 1,
        report_format: ReportFormat = ReportFormat.MARKDOWN,
        consolidate_memory: bool = False,
        keyword_seed_limit: int = 10,
        competitor_limit: int = 6,
        use_crewai: bool | None = None,
        research_trends: bool = False,
    ) -> dict:
        # Module 12: optional CrewAI path (same pipeline, tools wrap these agents).
        crew_mode = settings.orchestration_mode == "crewai" if use_crewai is None else use_crewai
        if crew_mode:
            from app.agents.crew import run_daily_crew

            return run_daily_crew(
                db,
                research_trends=research_trends,
                research_keywords=research_keywords,
                analyze_competitors=analyze_competitors,
                synthesize_opportunities=synthesize_opportunities,
                consolidate_memory=consolidate_memory,
                opportunity_limit=opportunity_limit,
                ideas_per_opportunity=ideas_per_opportunity,
                report_format=report_format,
            )

        started_at = datetime.now(timezone.utc)
        summary: dict = {
            "pipeline": "daily_intelligence",
            "started_at": started_at.isoformat(),
            "steps": {},
            "skipped": {},
            "report_id": None,
            "file_path": None,
            "ideas_in_report": 0,
            "total_ideas_generated": 0,
            "keyword_seeds": [],
            "competitor_targets": 0,
        }

        agent_runtime.run_task(
            "coordinator",
            "daily_pipeline_start",
            {"started_at": started_at.isoformat()},
        )

        if research_keywords:
            seeds = build_keyword_seeds_from_trends(db, limit=keyword_seed_limit)
            summary["keyword_seeds"] = seeds
            summary["steps"]["keywords"] = self._safe_step(
                "keywords",
                summary,
                lambda: self.keyword_agent.run(
                    db,
                    seed_terms=seeds,
                    platforms=[Platform.GOOGLE_PLAY],
                    suggestions_per_seed=6,
                ),
            )

        if analyze_competitors:
            targets = build_competitor_targets_from_trends(db, limit=competitor_limit)
            summary["competitor_targets"] = len(targets)
            if targets:
                summary["steps"]["competitors"] = self._safe_step(
                    "competitors",
                    summary,
                    lambda: self.competitor_agent.run(
                        db,
                        targets=targets,
                        reviews_per_app=8,
                    ),
                )
            else:
                summary["skipped"]["competitors"] = "No trending apps available to analyze"

        if synthesize_opportunities:
            summary["steps"]["opportunities"] = self._safe_step(
                "opportunities",
                summary,
                lambda: self.opportunity_agent.run(
                    db,
                    min_score=10.0,
                    min_keyword_opportunity=40.0,
                ),
            )

        report_result = self._safe_step(
            "report",
            summary,
            lambda: self.report_agent.run(
                db,
                report_type=ReportType.DAILY,
                report_format=report_format,
                generate_ideas=True,
                min_opportunity_score=0.0,
                ideas_per_opportunity=ideas_per_opportunity,
                opportunity_limit=opportunity_limit,
            ),
        )
        summary["steps"]["report"] = report_result
        if isinstance(report_result, dict):
            summary["report_id"] = report_result.get("report_id")
            summary["file_path"] = report_result.get("file_path")
            summary["ideas_in_report"] = report_result.get("ideas_in_report", 0)
            idea_gen = report_result.get("idea_generation") or {}
            summary["total_ideas_generated"] = idea_gen.get("total_ideas", 0)
            summary["steps"]["ideas"] = idea_gen

        if consolidate_memory:
            summary["steps"]["memory"] = self._safe_step(
                "memory",
                summary,
                lambda: self.memory_agent.run(
                    db,
                    lookback_days=1,
                    per_source_limit=50,
                    min_importance=0.5,
                ),
            )

        finished_at = datetime.now(timezone.utc)
        summary["finished_at"] = finished_at.isoformat()
        summary["success"] = "report" not in summary["skipped"]

        agent_runtime.run_task(
            "coordinator",
            "daily_pipeline_finish",
            {"success": summary["success"], "report_id": summary["report_id"]},
        )
        logger.info("CoordinatorAgent daily pipeline complete: {}", summary)
        return summary

    def _safe_step(self, name: str, summary: dict, fn):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Coordinator step {} failed: {}", name, exc)
            summary["skipped"][name] = str(exc)
            return None
