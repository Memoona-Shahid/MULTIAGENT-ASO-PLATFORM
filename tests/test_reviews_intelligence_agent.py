from app.agents.reviews_intelligence_agent import ReviewsIntelligenceAgent
from app.models.db_models import Competitor, Platform
from app.services.review_client import ReviewSourceUnavailableError
from app.services.review_service import list_reviews


class FakeReviewClient:
    def __init__(self, reviews=None, error=None):
        self.reviews = reviews or []
        self.error = error

    def fetch_reviews(self, app_id, limit=50):
        if self.error:
            raise self.error
        return self.reviews[:limit]


def _save_competitor(db_session, platform=Platform.APP_STORE, store_app_id="123"):
    competitor = Competitor(
        platform=platform,
        store_app_id=store_app_id,
        name="Competitor App",
    )
    db_session.add(competitor)
    db_session.commit()
    db_session.refresh(competitor)
    return competitor


def test_run_analyzes_reviews_for_tracked_competitor(db_session):
    competitor = _save_competitor(db_session)
    agent = ReviewsIntelligenceAgent(
        apple_client=FakeReviewClient([
            {
                "platform": Platform.APP_STORE,
                "author": "A",
                "rating": 1,
                "review_text": "Crashes and slow",
            },
            {
                "platform": Platform.APP_STORE,
                "author": "B",
                "rating": 5,
                "review_text": "Great useful app",
            },
        ])
    )

    summary = agent.run(db_session, competitor_ids=[competitor.id], reviews_per_competitor=10)

    reviews = list_reviews(db_session, competitor_id=competitor.id)
    assert summary["total_competitors"] == 1
    assert summary["total_reviews"] == 2
    assert summary["sentiment"]["negative"] == 1
    assert summary["sentiment"]["positive"] == 1
    assert summary["bugs"] == 1
    assert len(reviews) == 2


def test_run_skips_missing_competitor_id(db_session):
    agent = ReviewsIntelligenceAgent(apple_client=FakeReviewClient())

    summary = agent.run(db_session, competitor_ids=[999])

    assert summary["total_competitors"] == 0
    assert summary["skipped"]["competitor_id::999"] == "Competitor not found"


def test_run_skips_source_failure_without_crashing(db_session):
    competitor = _save_competitor(db_session)
    agent = ReviewsIntelligenceAgent(
        apple_client=FakeReviewClient(error=ReviewSourceUnavailableError("reviews down"))
    )

    summary = agent.run(db_session, competitor_ids=[competitor.id])

    assert summary["total_competitors"] == 0
    assert "app_store::123" in summary["skipped"]
    assert list_reviews(db_session, competitor_id=competitor.id) == []


def test_run_routes_google_play_to_google_client(db_session):
    competitor = _save_competitor(
        db_session,
        platform=Platform.GOOGLE_PLAY,
        store_app_id="com.example.app",
    )
    agent = ReviewsIntelligenceAgent(
        apple_client=FakeReviewClient(),
        google_play_client=FakeReviewClient([
            {
                "platform": Platform.GOOGLE_PLAY,
                "author": "G",
                "rating": 4,
                "review_text": "Useful app",
            }
        ]),
    )

    summary = agent.run(db_session, competitor_ids=[competitor.id])

    reviews = list_reviews(db_session, competitor_id=competitor.id)
    assert summary["total_reviews"] == 1
    assert reviews[0].platform == Platform.GOOGLE_PLAY
