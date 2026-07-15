from unittest.mock import patch

from app.models.db_models import Platform


def test_competitors_endpoint_empty_when_no_data(client):
    response = client.get("/api/competitors")
    assert response.status_code == 200
    assert response.json() == []


def test_analyze_endpoint_triggers_agent(client):
    fake_summary = {
        "captured_at": "2026-01-01T00:00:00+00:00",
        "competitors": {"app_store::123": {"competitor_id": 1, "reviews": 2}},
        "skipped": {},
        "total_competitors": 1,
        "total_reviews": 2,
    }

    with patch("app.api.competitors.CompetitorAnalysisAgent") as MockAgent:
        MockAgent.return_value.run.return_value = fake_summary
        response = client.post(
            "/api/competitors/analyze",
            json={
                "targets": [{"platform": Platform.APP_STORE.value, "store_app_id": "123"}],
                "reviews_per_app": 2,
            },
        )

    assert response.status_code == 200
    assert response.json() == fake_summary


def test_competitor_reviews_endpoint_returns_404_for_missing_competitor(client):
    response = client.get("/api/competitors/999/reviews")
    assert response.status_code == 404
