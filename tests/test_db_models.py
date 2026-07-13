from app.models.db_models import (
    ChartType,
    Competitor,
    Keyword,
    Platform,
    Review,
    TrendingApp,
)


def test_create_trending_app(db_session):
    app = TrendingApp(
        platform=Platform.APP_STORE,
        store_app_id="com.example.app",
        name="Example App",
        chart_type=ChartType.TOP_FREE,
        rank=1,
        rating=4.5,
    )
    db_session.add(app)
    db_session.commit()

    fetched = db_session.query(TrendingApp).first()
    assert fetched.name == "Example App"
    assert fetched.chart_type == ChartType.TOP_FREE
    assert fetched.platform == Platform.APP_STORE


def test_create_keyword(db_session):
    kw = Keyword(term="fitness tracker", platform=Platform.GOOGLE_PLAY, search_volume=10000, difficulty_score=42.5)
    db_session.add(kw)
    db_session.commit()

    fetched = db_session.query(Keyword).filter_by(term="fitness tracker").first()
    assert fetched is not None
    assert fetched.search_volume == 10000


def test_competitor_review_relationship(db_session):
    competitor = Competitor(
        platform=Platform.GOOGLE_PLAY,
        store_app_id="com.example.competitor",
        name="Competitor App",
    )
    db_session.add(competitor)
    db_session.commit()

    review = Review(
        competitor_id=competitor.id,
        platform=Platform.GOOGLE_PLAY,
        rating=2,
        review_text="App crashes on startup",
        sentiment="negative",
        mentions_bug=True,
    )
    db_session.add(review)
    db_session.commit()

    fetched_competitor = db_session.query(Competitor).first()
    assert len(fetched_competitor.reviews) == 1
    assert fetched_competitor.reviews[0].mentions_bug is True
