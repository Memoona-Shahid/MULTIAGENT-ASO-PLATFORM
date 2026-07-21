def test_dashboard_page_loads(client):
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "ASO Intelligence" in response.text
    assert "Generate today" in response.text
    assert "/api/dashboard/overview" in response.text


def test_root_page_loads_dashboard(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Product ideas" in response.text
    assert "Market opportunities" in response.text
    assert "Reports" in response.text
    assert "openIdea" in response.text


def test_dashboard_overview_endpoint(client):
    response = client.get("/api/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert "counts" in data
    assert "ideas" in data
    assert "reports" in data
    assert "trends" in data
    assert "opportunities" in data


def test_dashboard_idea_detail_not_found(client):
    response = client.get("/api/dashboard/ideas/99999")
    assert response.status_code == 200
    assert response.json()["error"] == "Idea not found"


def test_dashboard_idea_detail_returns_sections(db_session):
    from datetime import datetime, timezone

    from app.api.dashboard_data import get_idea_detail
    from app.models.db_models import MarketOpportunity, ProductIdea

    opp = MarketOpportunity(
        id=1,
        title="Finance gap",
        category="Finance",
        description="Users want simpler budgeting tools.",
        opportunity_score=78.0,
        identified_at=datetime.now(timezone.utc),
    )
    idea = ProductIdea(
        id=1,
        title="CashClear",
        idea_type="mobile_app",
        problem_statement="Young adults struggle with complex finance apps.",
        proposed_solution="A simple budgeting app with guided savings goals.",
        target_audience="First-time savers",
        monetization_strategy="Freemium + premium insights",
        confidence_score=82.0,
        source_opportunity_id=1,
        generated_at=datetime.now(timezone.utc),
    )
    db_session.add_all([opp, idea])
    db_session.commit()

    data = get_idea_detail(1, db_session)

    assert data["idea"]["title"] == "CashClear"
    assert data["opportunity"]["title"] == "Finance gap"
    section_keys = [row["key"] for row in data["detail_sections"]]
    assert "pitch" in section_keys
    assert "how_it_works" in section_keys
    assert "market_context" in section_keys
    combined = " ".join(row["body"] for row in data["detail_sections"]).lower()
    assert "trend signals" not in combined
