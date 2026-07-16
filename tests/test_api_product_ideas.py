from unittest.mock import patch


def test_product_ideas_endpoint_empty_when_no_data(client):
    response = client.get("/api/product-ideas")
    assert response.status_code == 200
    assert response.json() == []


def test_generate_ideas_endpoint_triggers_agent(client):
    fake_summary = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "opportunities": {"1": 1},
        "skipped": {},
        "total_ideas": 1,
    }

    with patch("app.api.product_ideas.AiIdeaGeneratorAgent") as MockAgent:
        MockAgent.return_value.run.return_value = fake_summary
        response = client.post(
            "/api/product-ideas/generate",
            json={
                "opportunity_ids": [1],
                "min_opportunity_score": 45,
                "ideas_per_opportunity": 1,
                "opportunity_limit": 50,
            },
        )

    assert response.status_code == 200
    assert response.json() == fake_summary


def test_product_ideas_endpoint_accepts_filters(client):
    response = client.get(
        "/api/product-ideas",
        params={"idea_type": "mobile_app", "min_confidence_score": 50, "limit": 10},
    )
    assert response.status_code == 200
    assert response.json() == []
