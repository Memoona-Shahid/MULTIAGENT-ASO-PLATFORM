"""
App Store Research Agent (Requirement 1 & 2, Apple side).

Responsibilities:
  - Pull Top Free / Top Paid / Top Grossing charts from Apple.
  - Enrich each entry with rating/price/category via the iTunes Lookup API.
  - Persist a timestamped snapshot to `trending_apps`.
  - Detect "fast growing" apps by comparing this snapshot's ranks against
    the previous snapshot for the same chart (Apple has no native
    "fast growing" chart, so this is computed, not fetched).

This agent is a plain orchestration class, not a CrewAI Agent — it's the
"tool" a CrewAI agent will call once Module 12 wires up the Coordinator.
Keeping it plain here means it's directly unit-testable without needing an
LLM or CrewAI in the loop.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import ChartType, Platform
from app.services.app_store_client import AppleAppStoreClient, ChartUnavailableError
from app.services.trending_app_service import (
    get_latest_snapshot,
    get_previous_snapshot,
    save_trending_apps,
)

# Top Grossing is intentionally excluded: Apple discontinued it from the
# public RSS feed this client uses. Pass chart_types=[ChartType.TOP_GROSSING]
# explicitly if you've wired up an alternate data source for it — the agent
# will still just skip it gracefully (see _fetch_and_save_chart) rather than
# fail the whole run if it's genuinely unavailable.
DEFAULT_CHARTS = (ChartType.TOP_FREE, ChartType.TOP_PAID)

# An app counts as "fast growing" if it climbed at least this many ranks
# since the previous snapshot, OR is newly present in the top N where it
# wasn't ranked before at all (treated as a max-value climb).
DEFAULT_FAST_GROWING_RANK_DELTA = 10


class AppStoreResearchAgent:
    def __init__(self, client: AppleAppStoreClient | None = None):
        self.client = client or AppleAppStoreClient()

    def run(
        self,
        db: Session,
        chart_types: list[ChartType] | None = None,
        limit: int = 100,
        fast_growing_threshold: int = DEFAULT_FAST_GROWING_RANK_DELTA,
    ) -> dict:
        """Fetch + persist all requested charts, then compute fast-growing apps.

        Returns a summary dict: counts per chart type + fast-growing count.
        """
        charts = chart_types or list(DEFAULT_CHARTS)
        captured_at = datetime.now(timezone.utc)
        summary: dict = {
            "captured_at": captured_at.isoformat(),
            "charts": {},
            "skipped_charts": {},
            "fast_growing": 0,
        }

        for chart_type in charts:
            try:
                saved = self._fetch_and_save_chart(db, chart_type, limit, captured_at)
                summary["charts"][chart_type.value] = len(saved)
            except ChartUnavailableError as exc:
                logger.warning("Skipping chart {}: {}", chart_type, exc)
                summary["skipped_charts"][chart_type.value] = str(exc)

        fast_growing = []
        for chart_type in charts:
            if chart_type.value in summary["skipped_charts"]:
                continue
            fast_growing.extend(
                self._compute_fast_growing(db, chart_type, captured_at, fast_growing_threshold)
            )
        summary["fast_growing"] = len(fast_growing)

        logger.info("AppStoreResearchAgent run complete: {}", summary)
        return summary

    def _fetch_and_save_chart(
        self, db: Session, chart_type: ChartType, limit: int, captured_at: datetime
    ) -> list:
        entries = self.client.fetch_chart(chart_type, limit=limit)
        if not entries:
            logger.warning("No entries returned for chart {}", chart_type)
            return []

        app_ids = [e["store_app_id"] for e in entries if e.get("store_app_id")]
        details = self.client.fetch_app_details(app_ids)

        for entry in entries:
            detail = details.get(str(entry.get("store_app_id")), {})
            # Chart feed wins for rank/name/basic identity; lookup API fills in
            # the richer fields the RSS feed doesn't provide.
            entry["rating"] = detail.get("rating")
            entry["rating_count"] = detail.get("rating_count")
            entry["price"] = detail.get("price")
            if not entry.get("category"):
                entry["category"] = detail.get("category")
            entry["platform"] = Platform.APP_STORE
            entry["chart_type"] = chart_type

        return save_trending_apps(db, entries, captured_at)

    def _compute_fast_growing(
        self, db: Session, chart_type: ChartType, captured_at: datetime, threshold: int
    ) -> list:
        """Compare latest vs previous snapshot for one chart; persist climbers
        as separate TrendingApp rows under ChartType.FAST_GROWING."""
        current = get_latest_snapshot(db, Platform.APP_STORE, chart_type)
        previous = get_previous_snapshot(db, Platform.APP_STORE, chart_type, before=captured_at)

        if not previous:
            logger.info(
                "No previous snapshot for chart {} yet — skipping fast-growing calc "
                "(need at least 2 snapshots).", chart_type,
            )
            return []

        previous_ranks = {row.store_app_id: row.rank for row in previous}

        climbers = []
        for row in current:
            prev_rank = previous_ranks.get(row.store_app_id)
            if prev_rank is None:
                # New entrant to the chart — treat as a strong climb.
                delta = threshold
            else:
                delta = prev_rank - row.rank  # positive = moved up (toward rank 1)

            if delta >= threshold:
                climbers.append({
                    "platform": Platform.APP_STORE,
                    "store_app_id": row.store_app_id,
                    "name": row.name,
                    "developer": row.developer,
                    "category": row.category,
                    "chart_type": ChartType.FAST_GROWING,
                    "rank": row.rank,
                    "rating": row.rating,
                    "rating_count": row.rating_count,
                    "price": row.price,
                    "icon_url": row.icon_url,
                    "store_url": row.store_url,
                    "raw_metadata": {
                        "source_chart": chart_type.value,
                        "previous_rank": prev_rank,
                        "rank_delta": delta,
                    },
                })

        if climbers:
            save_trending_apps(db, climbers, captured_at)
            logger.info("Detected {} fast-growing apps on chart {}", len(climbers), chart_type)

        return climbers
