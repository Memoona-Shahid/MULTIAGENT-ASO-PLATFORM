"""
Google Play Research Agent (Requirement 1 & 2, Google Play side).

Mirrors AppStoreResearchAgent's shape (fetch -> enrich -> save -> compute
fast-growing), but for Google Play via GooglePlayClient. Two differences
from the App Store agent worth knowing:

  1. Google Play still has all three charts (Free/Paid/Grossing) -- Apple
     discontinued Grossing from its free feed, Google hasn't.
  2. Detail enrichment (rating count) is opt-in here (`fetch_details`) since
     it's one HTTP request per app with no batch option, unlike Apple's
     iTunes Lookup API. Off by default to keep runs fast; the chart listing
     itself already includes a rating value, just not the rating count.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import ChartType, Platform
from app.services.google_play_client import ChartUnavailableError, GooglePlayClient
from app.services.trending_app_service import (
    get_latest_snapshot,
    get_previous_snapshot,
    save_trending_apps,
)

DEFAULT_CHARTS = (ChartType.TOP_FREE, ChartType.TOP_PAID, ChartType.TOP_GROSSING)
DEFAULT_FAST_GROWING_RANK_DELTA = 10


class GooglePlayResearchAgent:
    def __init__(self, client: GooglePlayClient | None = None):
        self.client = client or GooglePlayClient()

    def run(
        self,
        db: Session,
        chart_types: list[ChartType] | None = None,
        limit: int = 100,
        fetch_details: bool = False,
        fast_growing_threshold: int = DEFAULT_FAST_GROWING_RANK_DELTA,
    ) -> dict:
        """Fetch + persist all requested charts, then compute fast-growing apps.

        `fetch_details=True` additionally does one detail lookup per app to
        get rating counts -- slower (no batch API on Google's side), off by
        default. Returns a summary dict, same shape as AppStoreResearchAgent.
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
                saved = self._fetch_and_save_chart(db, chart_type, limit, captured_at, fetch_details)
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

        logger.info("GooglePlayResearchAgent run complete: {}", summary)
        return summary

    def _fetch_and_save_chart(
        self,
        db: Session,
        chart_type: ChartType,
        limit: int,
        captured_at: datetime,
        fetch_details: bool,
    ) -> list:
        entries = self.client.fetch_chart(chart_type, limit=limit)
        if not entries:
            logger.warning("No entries returned for chart {}", chart_type)
            return []

        if fetch_details:
            app_ids = [e["store_app_id"] for e in entries if e.get("store_app_id")]
            details = self.client.fetch_app_details(app_ids)
            for entry in entries:
                detail = details.get(str(entry.get("store_app_id")), {})
                if detail.get("rating_count") is not None:
                    entry["rating_count"] = detail["rating_count"]
                # Chart listing's own rating/price/category win if present;
                # detail lookup only fills gaps.
                entry["rating"] = entry.get("rating") or detail.get("rating")
                entry["price"] = entry.get("price") if entry.get("price") is not None else detail.get("price")
                if not entry.get("category"):
                    entry["category"] = detail.get("category")

        for entry in entries:
            entry["platform"] = Platform.GOOGLE_PLAY
            entry["chart_type"] = chart_type
            entry.setdefault("rating_count", None)

        return save_trending_apps(db, entries, captured_at)

    def _compute_fast_growing(
        self, db: Session, chart_type: ChartType, captured_at: datetime, threshold: int
    ) -> list:
        """Same climb/new-entrant logic as AppStoreResearchAgent, scoped to Google Play."""
        current = get_latest_snapshot(db, Platform.GOOGLE_PLAY, chart_type)
        previous = get_previous_snapshot(db, Platform.GOOGLE_PLAY, chart_type, before=captured_at)

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
            delta = threshold if prev_rank is None else prev_rank - row.rank

            if delta >= threshold:
                climbers.append({
                    "platform": Platform.GOOGLE_PLAY,
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
