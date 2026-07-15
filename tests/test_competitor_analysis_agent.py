from app.agents.competitor_analysis_agent import CompetitorAnalysisAgent
from app.models.db_models import Platform
from app.services.competitor_client import CompetitorSourceUnavailableError
from app.services.competitor_service import list_competitor_reviews, list_competitors


class FakeCompetitorClient:
    def __init__(self, details=None, reviews=None, details_error=None, reviews_error=None):
        self.details = details or {}
        self.reviews = reviews or []
        self.details_error = details_error
        self.reviews_error = reviews_error

    def fetch_details(self, app_id):
        if self.details_error:
            raise self.details_error
        return {**self.details, "store_app_id": app_id}

    def fetch_reviews(self, app_id, limit=20):
        if self.reviews_error:
            raise self.reviews_error
        return self.reviews[:limit]


def _details(platform=Platform.APP_STORE):
    return {
        "platform": platform,
        "store_app_id": "123",
        "name": "Competitor App",
        "developer": "Example Dev",
        "category": "Productivity",
        "estimated_downloads": "1,000+",
        "rating": 4.7,
        "rating_count": 2500,
        "pricing_model": "freemium",
        "monetization_details": {"offers_in_app_purchases": True},
        "screenshots": ["screen1"],
        "features": ["Planning"],
    }


def test_run_saves_competitor_and_reviews(db_session):
    client = FakeCompetitorClient(
        details=_details(),
        reviews=[{"platform": Platform.APP_STORE, "author": "A", "rating": 5, "review_text": "Great"}],
    )
    agent = CompetitorAnalysisAgent(apple_client=client)

    summary = agent.run(
        db_session,
        targets=[{"platform": Platform.APP_STORE, "store_app_id": "123"}],
        reviews_per_app=10,
    )

    competitors = list_competitors(db_session, platform=Platform.APP_STORE)
    reviews = list_competitor_reviews(db_session, competitors[0].id)
    assert summary["total_competitors"] == 1
    assert summary["total_reviews"] == 1
    assert competitors[0].name == "Competitor App"
    assert reviews[0].review_text == "Great"


def test_run_skips_bad_competitor_without_crashing(db_session):
    client = FakeCompetitorClient(
        details_error=CompetitorSourceUnavailableError("missing app")
    )
    agent = CompetitorAnalysisAgent(apple_client=client)

    summary = agent.run(
        db_session,
        targets=[{"platform": Platform.APP_STORE, "store_app_id": "missing"}],
    )

    assert summary["total_competitors"] == 0
    assert "app_store::missing" in summary["skipped"]
    assert list_competitors(db_session) == []


def test_run_saves_competitor_when_reviews_are_unavailable(db_session):
    client = FakeCompetitorClient(
        details=_details(),
        reviews_error=CompetitorSourceUnavailableError("reviews down"),
    )
    agent = CompetitorAnalysisAgent(apple_client=client)

    summary = agent.run(
        db_session,
        targets=[{"platform": Platform.APP_STORE, "store_app_id": "123"}],
    )

    competitors = list_competitors(db_session, platform=Platform.APP_STORE)
    assert summary["total_competitors"] == 1
    assert summary["total_reviews"] == 0
    assert "app_store::123::reviews" in summary["skipped"]
    assert len(competitors) == 1


def test_run_routes_google_play_targets_to_google_client(db_session):
    google_client = FakeCompetitorClient(details=_details(platform=Platform.GOOGLE_PLAY))
    agent = CompetitorAnalysisAgent(
        apple_client=FakeCompetitorClient(details=_details()),
        google_play_client=google_client,
    )

    summary = agent.run(
        db_session,
        targets=[{"platform": Platform.GOOGLE_PLAY, "store_app_id": "com.example.app"}],
        reviews_per_app=0,
    )

    competitors = list_competitors(db_session, platform=Platform.GOOGLE_PLAY)
    assert summary["total_competitors"] == 1
    assert competitors[0].store_app_id == "com.example.app"
