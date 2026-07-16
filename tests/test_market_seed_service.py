from datetime import datetime, timezone

from app.models.db_models import ChartType, Platform, TrendingApp
from app.services.market_seed_service import (
    build_competitor_targets_from_trends,
    build_keyword_seeds_from_trends,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_build_keyword_seeds_from_trends(db_session):
    rows = [
        TrendingApp(
            platform=Platform.GOOGLE_PLAY,
            store_app_id="com.a",
            name="ChatGPT Assistant",
            category="Productivity",
            chart_type=ChartType.TOP_FREE,
            rank=1,
            captured_at=T0,
        ),
        TrendingApp(
            platform=Platform.GOOGLE_PLAY,
            store_app_id="com.b",
            name="TikTok Social Videos",
            category="Social",
            chart_type=ChartType.TOP_FREE,
            rank=2,
            captured_at=T0,
        ),
        TrendingApp(
            platform=Platform.GOOGLE_PLAY,
            store_app_id="com.c",
            name="Amazon Shopping Deals",
            category="Shopping",
            chart_type=ChartType.TOP_FREE,
            rank=3,
            captured_at=T0,
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()

    seeds = build_keyword_seeds_from_trends(db_session, limit=6)
    assert "productivity" in seeds
    assert "social" in seeds
    assert "shopping" in seeds
    assert "fitness" not in seeds or len(seeds) >= 3


def test_build_competitor_targets_from_trends(db_session):
    rows = [
        TrendingApp(
            platform=Platform.GOOGLE_PLAY,
            store_app_id="com.social",
            name="Social App",
            category="Social",
            chart_type=ChartType.TOP_FREE,
            rank=1,
            captured_at=T0,
        ),
        TrendingApp(
            platform=Platform.GOOGLE_PLAY,
            store_app_id="com.shop",
            name="Shop App",
            category="Shopping",
            chart_type=ChartType.TOP_FREE,
            rank=2,
            captured_at=T0,
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()

    targets = build_competitor_targets_from_trends(db_session, limit=5)
    assert len(targets) == 2
    assert {t["store_app_id"] for t in targets} == {"com.social", "com.shop"}
