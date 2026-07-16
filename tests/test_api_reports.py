from unittest.mock import patch


def test_reports_endpoint_empty_when_no_data(client):
    response = client.get("/api/reports")
    assert response.status_code == 200
    assert response.json() == []


def test_generate_report_endpoint_triggers_agent(client):
    fake_summary = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "report_type": "daily",
        "report_format": "markdown",
        "period_start": "2025-12-31T00:00:00+00:00",
        "period_end": "2026-01-01T00:00:00+00:00",
        "signals": {"trends": 0, "keywords": 0, "competitors": 0, "reviews": 0, "opportunities": 0, "product_ideas": 3},
        "skipped": {},
        "idea_generation": {"total_ideas": 3, "opportunities": {"1": 1, "2": 1, "3": 1}, "skipped": {}},
        "ideas_in_report": 3,
        "file_path": "./data/reports/daily_2026-01-01.md",
        "report_id": 1,
    }

    with patch("app.api.reports.ReportGeneratorAgent") as MockAgent:
        MockAgent.return_value.run.return_value = fake_summary
        response = client.post(
            "/api/reports/generate",
            json={
                "report_type": "daily",
                "report_format": "markdown",
                "generate_ideas": True,
                "min_opportunity_score": 0,
                "ideas_per_opportunity": 1,
                "opportunity_limit": 10,
            },
        )

    assert response.status_code == 200
    assert response.json() == fake_summary
    MockAgent.return_value.run.assert_called_once()


def test_reports_endpoint_accepts_filters(client):
    response = client.get(
        "/api/reports",
        params={"report_type": "weekly", "report_format": "html", "limit": 10},
    )
    assert response.status_code == 200
    assert response.json() == []
