from datetime import datetime, timezone

from app.models.db_models import Competitor, Platform
from app.services.review_service import analyze_review_payload, list_reviews, save_analyzed_reviews

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _competitor():
    return Competitor(
        platform=Platform.APP_STORE,
        store_app_id="123",
        name="Competitor App",
    )


def test_analyze_review_payload_extracts_sentiment_and_signals():
    analyzed = analyze_review_payload({
        "platform": Platform.APP_STORE,
        "author": "Reviewer",
        "rating": 1,
        "review_text": "The app crashes and is slow. Please add dark mode.",
    })

    assert analyzed["sentiment"] == "negative"
    assert analyzed["sentiment_score"] < 0
    assert analyzed["mentions_bug"] is True
    assert analyzed["mentions_feature_request"] is True
    assert "performance" in analyzed["extracted_topics"]["topics"]


def test_save_analyzed_reviews_dedupes_existing_review(db_session):
    competitor = _competitor()
    db_session.add(competitor)
    db_session.commit()

    review = analyze_review_payload({
        "platform": Platform.APP_STORE,
        "author": "Reviewer",
        "rating": 5,
        "review_text": "Great and useful app",
        "posted_at": T0,
    })
    first = save_analyzed_reviews(db_session, competitor, [review], captured_at=T0)
    second = save_analyzed_reviews(db_session, competitor, [review], captured_at=T0)

    saved = list_reviews(db_session, competitor_id=competitor.id)
    assert first[0].id == second[0].id
    assert len(saved) == 1
    assert saved[0].sentiment == "positive"


def test_list_reviews_filters_by_bug_and_sentiment(db_session):
    competitor = _competitor()
    db_session.add(competitor)
    db_session.commit()

    reviews = [
        analyze_review_payload({
            "platform": Platform.APP_STORE,
            "author": "A",
            "rating": 1,
            "review_text": "Crashes every time",
        }),
        analyze_review_payload({
            "platform": Platform.APP_STORE,
            "author": "B",
            "rating": 5,
            "review_text": "Love it, great app",
        }),
    ]
    save_analyzed_reviews(db_session, competitor, reviews, captured_at=T0)

    bugs = list_reviews(db_session, mentions_bug=True)
    positive = list_reviews(db_session, sentiment="positive")
    assert len(bugs) == 1
    assert bugs[0].author == "A"
    assert len(positive) == 1
    assert positive[0].author == "B"
