from unittest.mock import patch

from app.models.db_models import ChartType


def test_trending_endpoint_empty_when_no_data(client):
    response = client.get("/api/app-store/trending")
    assert response.status_code == 200
    assert response.json() == []


def test_research_endpoint_triggers_agent(client):
    fake_summary = {"captured_at": "2026-01-01T00:00:00+00:00", "charts": {"top_free": 2}, "fast_growing": 0}

    with patch("app.api.app_store.AppStoreResearchAgent") as MockAgent:
        MockAgent.return_value.run.return_value = fake_summary
        response = client.post("/api/app-store/research", params={"limit": 10})

    assert response.status_code == 200
    assert response.json() == fake_summary


def test_trending_endpoint_filters_by_chart_type(client):
    response = client.get("/api/app-store/trending", params={"chart_type": ChartType.TOP_PAID.value})
    assert response.status_code == 200
    assert response.json() == []
