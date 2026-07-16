"""
Report Generator Agent (Module 9).

Builds daily/weekly reports focused on actionable product ideas.
By default it generates fresh ideas from market opportunities, then
includes those ideas prominently in the saved report file.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.agents.ai_idea_generator_agent import AiIdeaGeneratorAgent
from app.agents.market_opportunity_agent import MarketOpportunityAgent
from app.core.logging import logger
from app.models.db_models import ReportFormat, ReportType
from app.services.report_client import ReportDataClient
from app.services.report_renderer import (
    ReportRenderError,
    build_report_context,
    render_report_file,
)
from app.services.report_service import save_report

DEFAULT_PER_SOURCE_LIMIT = 200
DEFAULT_MIN_OPPORTUNITY_SCORE = 0.0
DEFAULT_IDEAS_PER_OPPORTUNITY = 1
DEFAULT_OPPORTUNITY_LIMIT = 10


class ReportGeneratorAgent:
    def __init__(
        self,
        client: ReportDataClient | None = None,
        idea_agent: AiIdeaGeneratorAgent | None = None,
        opportunity_agent: MarketOpportunityAgent | None = None,
    ):
        self.client = client or ReportDataClient()
        self.idea_agent = idea_agent or AiIdeaGeneratorAgent()
        self.opportunity_agent = opportunity_agent or MarketOpportunityAgent()

    def run(
        self,
        db: Session,
        report_type: ReportType = ReportType.DAILY,
        report_format: ReportFormat = ReportFormat.MARKDOWN,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        per_source_limit: int = DEFAULT_PER_SOURCE_LIMIT,
        output_dir: str | None = None,
        generate_ideas: bool = True,
        min_opportunity_score: float = DEFAULT_MIN_OPPORTUNITY_SCORE,
        ideas_per_opportunity: int = DEFAULT_IDEAS_PER_OPPORTUNITY,
        opportunity_limit: int = DEFAULT_OPPORTUNITY_LIMIT,
    ) -> dict:
        generated_at = datetime.now(timezone.utc)
        if period_end is None:
            period_end = generated_at
        if period_start is None:
            period_start = self._default_period_start(report_type, period_end)

        summary: dict = {
            "generated_at": generated_at.isoformat(),
            "report_type": report_type.value,
            "report_format": report_format.value,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "signals": {},
            "skipped": {},
            "idea_generation": None,
            "file_path": None,
            "report_id": None,
            "ideas_in_report": 0,
        }

        idea_window_start = generated_at
        if generate_ideas:
            self._ensure_opportunities(db, summary)
            idea_window_start = datetime.now(timezone.utc)
            summary["idea_generation"] = self._safe_step(
                "idea_generation",
                summary,
                lambda: self.idea_agent.run(
                    db,
                    min_opportunity_score=min_opportunity_score,
                    ideas_per_opportunity=ideas_per_opportunity,
                    opportunity_limit=opportunity_limit,
                ),
            )

        trends = self._safe_fetch(
            "trends",
            summary,
            lambda: self.client.fetch_trends(db, period_start, period_end, limit=per_source_limit),
        )
        keywords = self._safe_fetch(
            "keywords",
            summary,
            lambda: self.client.fetch_keywords(db, period_start, period_end, limit=per_source_limit),
        )
        competitors = self._safe_fetch(
            "competitors",
            summary,
            lambda: self.client.fetch_competitors(db, period_start, period_end, limit=per_source_limit),
        )
        reviews = self._safe_fetch(
            "reviews",
            summary,
            lambda: self.client.fetch_reviews(db, period_start, period_end, limit=per_source_limit * 2),
        )
        opportunities = self._safe_fetch(
            "opportunities",
            summary,
            lambda: self.client.fetch_opportunities(db, period_start, period_end, limit=per_source_limit),
        )
        product_ideas = self._resolve_report_ideas(
            db,
            generate_ideas=generate_ideas,
            idea_window_start=idea_window_start,
            period_end=period_end,
            limit=per_source_limit,
        )
        summary["signals"]["product_ideas"] = len(product_ideas)
        summary["ideas_in_report"] = len(product_ideas)

        context = build_report_context(
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            generated_at=generated_at,
            trends=trends,
            keywords=keywords,
            competitors=competitors,
            reviews=reviews,
            opportunities=opportunities,
            product_ideas=product_ideas,
        )

        file_path = None
        try:
            file_path = render_report_file(
                context,
                report_type=report_type,
                report_format=report_format,
                generated_at=generated_at,
                output_dir=output_dir,
            )
        except ReportRenderError as exc:
            logger.warning("Report file render failed: {}", exc)
            summary["skipped"]["render"] = str(exc)

        saved = save_report(
            db,
            {
                "report_type": report_type,
                "report_format": report_format,
                "title": context["title"],
                "summary": context["summary"],
                "file_path": file_path,
                "period_start": period_start,
                "period_end": period_end,
            },
            generated_at=generated_at,
        )

        summary["file_path"] = file_path
        summary["report_id"] = saved.id
        logger.info("ReportGeneratorAgent run complete: {}", summary)
        return summary

    def _ensure_opportunities(self, db: Session, summary: dict) -> None:
        if self.client.count_opportunities(db) > 0:
            return
        summary["opportunity_synthesis"] = self._safe_step(
            "opportunity_synthesis",
            summary,
            lambda: self.opportunity_agent.run(db, min_score=10.0, min_keyword_opportunity=40.0),
        )

    def _resolve_report_ideas(
        self,
        db: Session,
        *,
        generate_ideas: bool,
        idea_window_start: datetime,
        period_end: datetime,
        limit: int,
    ) -> list:
        if generate_ideas:
            fresh_ideas = self.client.fetch_product_ideas(
                db,
                idea_window_start - timedelta(seconds=1),
                period_end + timedelta(seconds=1),
                limit=limit,
            )
            if fresh_ideas:
                return fresh_ideas

        period_ideas = self.client.fetch_product_ideas(db, period_end - timedelta(days=7), period_end, limit=limit)
        if period_ideas:
            return period_ideas

        return self.client.fetch_latest_product_ideas(db, limit=min(limit, 20))

    def _default_period_start(self, report_type: ReportType, period_end: datetime) -> datetime:
        days = 7 if report_type == ReportType.WEEKLY else 1
        return period_end - timedelta(days=days)

    def _safe_fetch(self, source: str, summary: dict, fn):
        try:
            rows = fn()
            summary["signals"][source] = len(rows)
            return rows
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping report source {}: {}", source, exc)
            summary["signals"][source] = 0
            summary["skipped"][source] = str(exc)
            return []

    def _safe_step(self, step: str, summary: dict, fn):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Report step {} failed: {}", step, exc)
            summary["skipped"][step] = str(exc)
            return None
