from unittest.mock import patch

from app.models.db_models import Platform


def test_reviews_endpoint_empty_when_no_data(client):
    response = client.get("/api/reviews")
    assert response.status_code == 200
    assert response.json() == []


def test_reviews_analyze_endpoint_triggers_agent(client):
    fake_summary = {
        "captured_at": "2026-01-01T00:00:00+00:00",
        "competitors": {},
        "skipped": {},
        "total_competitors": 0,
        "total_reviews": 0,
        "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
        "bugs": 0,
        "feature_requests": 0,
    }

    with patch("app.api.reviews.ReviewsIntelligenceAgent") as MockAgent:
        MockAgent.return_value.run.return_value = fake_summary
        response = client.post(
            "/api/reviews/analyze",
            json={
                "competitor_ids": [1],
                "platform": Platform.APP_STORE.value,
                "reviews_per_competitor": 5,
            },
        )

    assert response.status_code == 200
    assert response.json() == fake_summary


def test_reviews_endpoint_accepts_filters(client):
    response = client.get(
        "/api/reviews",
        params={"sentiment": "negative", "mentions_bug": True, "limit": 10},
    )
    assert response.status_code == 200
    assert response.json() == []
