from unittest.mock import patch

from app.models.db_models import Platform


def test_opportunities_endpoint_loads(client):
    # Avoid depending on DB state: patch the service response.
    fake_items = [
        {
            "id": 1,
            "title": "Finance opportunity",
            "category": "Finance",
            "description": "Demand rising",
            "opportunity_score": 72.5,
            "identified_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    with patch("app.api.opportunities.list_market_opportunities", return_value=fake_items):
        response = client.get("/api/opportunities", params={"limit": 1})

    assert response.status_code == 200
    assert response.json() == fake_items


def test_opportunity_synthesize_triggers_agent(client):
    fake_summary = {
        "identified_at": "2026-01-01T00:00:00+00:00",
        "signals": {"trends": 0, "keywords": 0, "competitors": 0, "reviews": 0},
        "skipped": {},
        "opportunities": 3,
    }
    with patch("app.api.opportunities.MarketOpportunityAgent") as MockAgent:
        MockAgent.return_value.run.return_value = fake_summary
        response = client.post(
            "/api/opportunities/synthesize",
            json={
                "min_score": 45,
                "min_keyword_opportunity": 55,
                "per_source_limit": 300,
            },
        )

    assert response.status_code == 200
    assert response.json() == fake_summary

