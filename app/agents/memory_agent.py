"""
Memory Agent (Module 10).

Consolidates recent platform signals into durable MemoryEntry rows so
reports and future agents can recall trends, competitors, ideas, and
report outcomes over time.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import ChartType
from app.services.memory_client import MemorySourceClient
from app.services.memory_service import prune_memory_entries, upsert_memory_entry

DEFAULT_LOOKBACK_DAYS = 7
DEFAULT_PER_SOURCE_LIMIT = 200
DEFAULT_MIN_IMPORTANCE = 0.5


class MemoryAgent:
    def __init__(self, client: MemorySourceClient | None = None):
        self.client = client or MemorySourceClient()

    def run(
        self,
        db: Session,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        per_source_limit: int = DEFAULT_PER_SOURCE_LIMIT,
        min_importance: float = DEFAULT_MIN_IMPORTANCE,
        prune_below_importance: float | None = None,
    ) -> dict:
        consolidated_at = datetime.now(timezone.utc)
        since = consolidated_at - timedelta(days=lookback_days)
        summary: dict = {
            "consolidated_at": consolidated_at.isoformat(),
            "lookback_days": lookback_days,
            "consolidated": {},
            "skipped": {},
            "pruned": 0,
            "total_entries": 0,
        }

        trends = self._safe_fetch("trends", summary, lambda: self.client.fetch_recent_trends(db, since, per_source_limit))
        keywords = self._safe_fetch(
            "keywords", summary, lambda: self.client.fetch_recent_keywords(db, since, per_source_limit)
        )
        competitors = self._safe_fetch(
            "competitors", summary, lambda: self.client.fetch_recent_competitors(db, since, per_source_limit)
        )
        reviews = self._safe_fetch(
            "reviews", summary, lambda: self.client.fetch_recent_reviews(db, since, per_source_limit * 2)
        )
        opportunities = self._safe_fetch(
            "opportunities",
            summary,
            lambda: self.client.fetch_recent_opportunities(db, since, per_source_limit),
        )
        product_ideas = self._safe_fetch(
            "product_ideas",
            summary,
            lambda: self.client.fetch_recent_product_ideas(db, since, per_source_limit),
        )
        reports = self._safe_fetch(
            "reports", summary, lambda: self.client.fetch_recent_reports(db, since, min(per_source_limit, 50))
        )

        saved = 0
        saved += self._consolidate_rows(
            db,
            summary,
            "trend",
            [self._entry_from_trend(row) for row in trends],
            min_importance,
            consolidated_at,
        )
        saved += self._consolidate_rows(
            db,
            summary,
            "keyword",
            [self._entry_from_keyword(row) for row in keywords],
            min_importance,
            consolidated_at,
        )
        saved += self._consolidate_rows(
            db,
            summary,
            "competitor",
            [self._entry_from_competitor(row) for row in competitors],
            min_importance,
            consolidated_at,
        )
        saved += self._consolidate_rows(
            db,
            summary,
            "review",
            [self._entry_from_review(row) for row in reviews],
            min_importance,
            consolidated_at,
        )
        saved += self._consolidate_rows(
            db,
            summary,
            "opportunity",
            [self._entry_from_opportunity(row) for row in opportunities],
            min_importance,
            consolidated_at,
        )
        saved += self._consolidate_rows(
            db,
            summary,
            "idea",
            [self._entry_from_idea(row) for row in product_ideas],
            min_importance,
            consolidated_at,
        )
        saved += self._consolidate_rows(
            db,
            summary,
            "report",
            [self._entry_from_report(row) for row in reports],
            min_importance,
            consolidated_at,
        )

        if prune_below_importance is not None:
            summary["pruned"] = prune_memory_entries(db, prune_below_importance)

        summary["total_entries"] = saved
        logger.info("MemoryAgent run complete: {}", summary)
        return summary

    def write_entry(self, db: Session, entry: dict) -> dict:
        saved = upsert_memory_entry(db, entry)
        return {
            "entry_type": saved.entry_type,
            "key": saved.key,
            "importance": saved.importance,
            "created_at": saved.created_at.isoformat(),
        }

    def _consolidate_rows(
        self,
        db: Session,
        summary: dict,
        entry_type: str,
        entries: list[dict],
        min_importance: float,
        consolidated_at: datetime,
    ) -> int:
        saved = 0
        for entry in entries:
            if entry["importance"] < min_importance:
                continue
            upsert_memory_entry(db, entry, created_at=consolidated_at)
            saved += 1
        summary["consolidated"][entry_type] = saved
        return saved

    def _entry_from_trend(self, row) -> dict:
        platform = row.platform.value if hasattr(row.platform, "value") else row.platform
        importance = 0.6
        if row.chart_type == ChartType.FAST_GROWING:
            importance = 0.85
        if row.rank is not None and row.rank <= 10:
            importance = max(importance, 0.9)
        return {
            "entry_type": "trend",
            "key": f"{platform}:{row.store_app_id}",
            "value": {
                "name": row.name,
                "category": row.category,
                "chart_type": row.chart_type.value if hasattr(row.chart_type, "value") else row.chart_type,
                "rank": row.rank,
                "rating": row.rating,
            },
            "tags": {"platform": platform, "category": row.category, "source_agent": "app_store_research_agent"},
            "importance": importance,
        }

    def _entry_from_keyword(self, row) -> dict:
        platform = row.platform.value if hasattr(row.platform, "value") else row.platform
        score = float(row.opportunity_score or 0.0)
        return {
            "entry_type": "keyword",
            "key": f"{platform}:{row.term}",
            "value": {
                "term": row.term,
                "search_volume": row.search_volume,
                "difficulty_score": row.difficulty_score,
                "opportunity_score": row.opportunity_score,
            },
            "tags": {"platform": platform, "source_agent": "keyword_research_agent"},
            "importance": max(0.5, min(1.0, score / 100.0)),
        }

    def _entry_from_competitor(self, row) -> dict:
        platform = row.platform.value if hasattr(row.platform, "value") else row.platform
        rating = float(row.rating or 0.0)
        return {
            "entry_type": "competitor",
            "key": f"{platform}:{row.store_app_id}",
            "value": {
                "name": row.name,
                "category": row.category,
                "rating": row.rating,
                "pricing_model": row.pricing_model,
                "features": row.features,
            },
            "tags": {"platform": platform, "category": row.category, "source_agent": "competitor_analysis_agent"},
            "importance": max(0.5, min(1.0, rating / 5.0)),
        }

    def _entry_from_review(self, row) -> dict:
        platform = row.platform.value if hasattr(row.platform, "value") else row.platform
        importance = 0.5
        if row.sentiment == "negative":
            importance = 0.75
        if row.mentions_bug:
            importance = max(importance, 0.8)
        if row.mentions_feature_request:
            importance = max(importance, 0.7)
        return {
            "entry_type": "review",
            "key": f"competitor:{row.competitor_id}",
            "value": {
                "competitor_id": row.competitor_id,
                "sentiment": row.sentiment,
                "rating": row.rating,
                "mentions_bug": row.mentions_bug,
                "mentions_feature_request": row.mentions_feature_request,
                "topics": row.extracted_topics,
            },
            "tags": {"platform": platform, "source_agent": "reviews_intelligence_agent"},
            "importance": importance,
        }

    def _entry_from_opportunity(self, row) -> dict:
        score = float(row.opportunity_score or 0.0)
        return {
            "entry_type": "opportunity",
            "key": f"opportunity:{row.id}",
            "value": {
                "title": row.title,
                "category": row.category,
                "description": row.description,
                "opportunity_score": row.opportunity_score,
                "supporting_evidence": row.supporting_evidence,
            },
            "tags": {"category": row.category, "source_agent": "market_opportunity_agent"},
            "importance": max(0.5, min(1.0, score / 100.0)),
        }

    def _entry_from_idea(self, row) -> dict:
        confidence = float(row.confidence_score or 0.0)
        return {
            "entry_type": "idea",
            "key": f"idea:{row.id}",
            "value": {
                "title": row.title,
                "idea_type": row.idea_type,
                "problem_statement": row.problem_statement,
                "proposed_solution": row.proposed_solution,
                "confidence_score": row.confidence_score,
                "source_opportunity_id": row.source_opportunity_id,
            },
            "tags": {"source_agent": "ai_idea_generator_agent"},
            "importance": max(0.5, min(1.0, confidence / 100.0)),
        }

    def _entry_from_report(self, row) -> dict:
        report_type = row.report_type.value if hasattr(row.report_type, "value") else row.report_type
        return {
            "entry_type": "report",
            "key": f"{report_type}:{row.id}",
            "value": {
                "title": row.title,
                "summary": row.summary,
                "report_format": row.report_format.value if hasattr(row.report_format, "value") else row.report_format,
                "file_path": row.file_path,
                "period_start": row.period_start.isoformat() if row.period_start else None,
                "period_end": row.period_end.isoformat() if row.period_end else None,
            },
            "tags": {"source_agent": "report_generator_agent"},
            "importance": 0.9,
        }

    def _safe_fetch(self, source: str, summary: dict, fn):
        try:
            rows = fn()
            summary.setdefault("sources", {})[source] = len(rows)
            return rows
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping memory source {}: {}", source, exc)
            summary.setdefault("sources", {})[source] = 0
            summary["skipped"][source] = str(exc)
            return []
