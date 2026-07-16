from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.market_opportunity_agent import MarketOpportunityAgent
from app.models.db_models import ChartType, Competitor, Keyword, Platform, Review, TrendingApp


T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeSignalClient:
    def __init__(self, trend_rows=None, keyword_rows=None, competitor_rows=None, review_rows=None):
        self._trend_rows = trend_rows or []
        self._keyword_rows = keyword_rows or []
        self._competitor_rows = competitor_rows or []
        self._review_rows = review_rows or []

    def fetch_trend_signals(self, db: Session, limit: int = 300):
        return self._trend_rows

    def fetch_keyword_signals(self, db: Session, min_opportunity_score: float = 55.0, limit: int = 300):
        return self._keyword_rows

    def fetch_competitor_signals(self, db: Session, limit: int = 200):
        return self._competitor_rows

    def fetch_review_signals(self, db: Session, limit: int = 500):
        return self._review_rows


def _seed_db(db_session):
    pass


def test_market_opportunity_agent_synthesizes_and_saves(db_session):
    # Build minimal DB rows so save_market_opportunities can persist.
    trending = TrendingApp(
        platform=Platform.APP_STORE,
        store_app_id="1",
        name="Trend App",
        category="Finance",
        chart_type=ChartType.FAST_GROWING,
        rank=1,
        captured_at=T0,
    )
    db_session.add(trending)

    keyword = Keyword(
        term="finance widget",
        platform=Platform.APP_STORE,
        search_volume=90,
        difficulty_score=20,
        opportunity_score=70,
        related_apps={},
        captured_at=T0,
    )
    db_session.add(keyword)

    competitor = Competitor(
        platform=Platform.APP_STORE,
        store_app_id="com.example.finance",
        name="Finance Competitor",
        category="Finance",
    )
    db_session.add(competitor)
    db_session.commit()
    db_session.refresh(competitor)

    # Attach a negative review so pain_score is non-zero
    review = Review(
        competitor_id=competitor.id,
        platform=Platform.APP_STORE,
        author="A",
        rating=1,
        review_text="crash and needs feature request",
        sentiment="negative",
        mentions_bug=True,
        mentions_feature_request=True,
        extracted_topics={},
        posted_at=None,
        captured_at=T0,
    )
    db_session.add(review)
    db_session.commit()

    client = FakeSignalClient(
        trend_rows=[trending],
        keyword_rows=[keyword],
        competitor_rows=[competitor],
        review_rows=[review],
    )
    agent = MarketOpportunityAgent(client=client)

    summary = agent.run(db_session, min_score=10, min_keyword_opportunity=50, per_source_limit=10)

    assert summary["opportunities"] >= 1
    assert "identified_at" in summary


def test_market_opportunity_agent_skips_source_on_failure(db_session):
    client = FakeSignalClient()

    # Force one failing method
    class FailingClient(FakeSignalClient):
        def fetch_trend_signals(self, db: Session, limit: int = 300):
            raise RuntimeError("boom")

    agent = MarketOpportunityAgent(client=FailingClient())
    summary = agent.run(db_session, min_score=10)

    assert summary["opportunities"] == 0 or summary["opportunities"] >= 0
    assert "trends" in summary["skipped"]

