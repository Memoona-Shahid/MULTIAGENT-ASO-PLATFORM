from datetime import datetime, timedelta, timezone

from app.models.db_models import Platform
from app.services.competitor_service import (
    list_competitor_reviews,
    list_competitors,
    save_competitor_analysis,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = T0 + timedelta(days=1)


def _competitor(name="Competitor App", rating=4.5):
    return {
        "platform": Platform.APP_STORE,
        "store_app_id": "123",
        "name": name,
        "developer": "Example Dev",
        "category": "Productivity",
        "estimated_downloads": None,
        "rating": rating,
        "rating_count": 1000,
        "pricing_model": "freemium",
        "monetization_details": {"offers_in_app_purchases": True},
        "screenshots": ["https://example.com/screen.png"],
        "features": ["Habit tracking"],
    }


def test_save_competitor_analysis_creates_competitor_and_reviews(db_session):
    competitor, reviews = save_competitor_analysis(
        db_session,
        _competitor(),
        [{"platform": Platform.APP_STORE, "author": "A", "rating": 5, "review_text": "Great"}],
        analyzed_at=T0,
    )

    assert competitor.id is not None
    assert competitor.pricing_model == "freemium"
    assert competitor.screenshots == ["https://example.com/screen.png"]
    assert len(reviews) == 1
    assert reviews[0].competitor_id == competitor.id


def test_save_competitor_analysis_upserts_existing_competitor(db_session):
    first, _ = save_competitor_analysis(db_session, _competitor(), [], analyzed_at=T0)
    second, _ = save_competitor_analysis(
        db_session,
        _competitor(name="Renamed App", rating=4.8),
        [],
        analyzed_at=T1,
    )

    competitors = list_competitors(db_session, platform=Platform.APP_STORE)
    assert first.id == second.id
    assert len(competitors) == 1
    assert competitors[0].name == "Renamed App"
    assert competitors[0].rating == 4.8


def test_list_competitor_reviews_filters_by_competitor(db_session):
    competitor, _ = save_competitor_analysis(
        db_session,
        _competitor(),
        [
            {"platform": Platform.APP_STORE, "author": "A", "rating": 5, "review_text": "Great"},
            {"platform": Platform.APP_STORE, "author": "B", "rating": 2, "review_text": "Buggy"},
        ],
        analyzed_at=T0,
    )

    reviews = list_competitor_reviews(db_session, competitor.id)
    assert len(reviews) == 2
    assert {review.author for review in reviews} == {"A", "B"}
