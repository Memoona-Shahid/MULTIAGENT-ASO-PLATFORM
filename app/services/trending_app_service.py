"""
Persistence layer for TrendingApp snapshots.

Kept separate from the agent so the agent only orchestrates fetch -> enrich
-> save -> compute-fast-growing, while all the SQL lives here and is unit
testable against a plain DB session with no HTTP involved.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import ChartType, Platform, TrendingApp


def save_trending_apps(db: Session, apps: list[dict], captured_at: datetime) -> list[TrendingApp]:
    """Bulk-insert a chart snapshot. `apps` items must contain at minimum:
    platform, store_app_id, name, chart_type, rank. Other TrendingApp fields optional.
    """
    rows = []
    for app in apps:
        rows.append(TrendingApp(
            platform=app["platform"],
            store_app_id=str(app["store_app_id"]),
            name=app["name"],
            developer=app.get("developer"),
            category=app.get("category"),
            chart_type=app["chart_type"],
            rank=app.get("rank"),
            rating=app.get("rating"),
            rating_count=app.get("rating_count"),
            price=app.get("price"),
            icon_url=app.get("icon_url"),
            store_url=app.get("store_url"),
            raw_metadata=app.get("raw_metadata"),
            captured_at=captured_at,
        ))
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)

    logger.info("Saved {} trending app rows at {}", len(rows), captured_at)
    return rows


def get_latest_snapshot(
    db: Session, platform: Platform, chart_type: ChartType
) -> list[TrendingApp]:
    """Return all rows from the most recent captured_at for this platform+chart."""
    latest_ts = db.scalar(
        select(TrendingApp.captured_at)
        .where(TrendingApp.platform == platform, TrendingApp.chart_type == chart_type)
        .order_by(TrendingApp.captured_at.desc())
        .limit(1)
    )
    if latest_ts is None:
        return []

    return list(db.scalars(
        select(TrendingApp)
        .where(
            TrendingApp.platform == platform,
            TrendingApp.chart_type == chart_type,
            TrendingApp.captured_at == latest_ts,
        )
        .order_by(TrendingApp.rank)
    ))


def get_previous_snapshot(
    db: Session, platform: Platform, chart_type: ChartType, before: datetime
) -> list[TrendingApp]:
    """Return all rows from the most recent captured_at strictly before `before`."""
    previous_ts = db.scalar(
        select(TrendingApp.captured_at)
        .where(
            TrendingApp.platform == platform,
            TrendingApp.chart_type == chart_type,
            TrendingApp.captured_at < before,
        )
        .order_by(TrendingApp.captured_at.desc())
        .limit(1)
    )
    if previous_ts is None:
        return []

    return list(db.scalars(
        select(TrendingApp)
        .where(
            TrendingApp.platform == platform,
            TrendingApp.chart_type == chart_type,
            TrendingApp.captured_at == previous_ts,
        )
        .order_by(TrendingApp.rank)
    ))


def list_trending_apps(
    db: Session,
    platform: Platform | None = None,
    chart_type: ChartType | None = None,
    category: str | None = None,
    limit: int = 100,
) -> list[TrendingApp]:
    """Query the most recent snapshot(s) matching optional filters, for the API layer."""
    stmt = select(TrendingApp)
    if platform is not None:
        stmt = stmt.where(TrendingApp.platform == platform)
    if chart_type is not None:
        stmt = stmt.where(TrendingApp.chart_type == chart_type)
    if category is not None:
        stmt = stmt.where(TrendingApp.category == category)
    stmt = stmt.order_by(TrendingApp.captured_at.desc(), TrendingApp.rank).limit(limit)

    return list(db.scalars(stmt))
