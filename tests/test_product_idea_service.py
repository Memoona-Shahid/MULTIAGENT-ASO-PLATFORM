from datetime import datetime, timezone

from app.services.product_idea_service import list_product_ideas, save_product_ideas

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _idea(title="Finance mobile app", confidence=72.0):
    return {
        "title": title,
        "idea_type": "mobile_app",
        "problem_statement": "Users are frustrated with incumbents",
        "proposed_solution": "Ship a simpler mobile workflow",
        "target_audience": "Mobile users in finance",
        "monetization_strategy": "Freemium subscription",
        "confidence_score": confidence,
        "source_opportunity_id": 1,
    }


def test_save_product_ideas(db_session):
    rows = save_product_ideas(db_session, [_idea()], generated_at=T0)

    assert len(rows) == 1
    assert rows[0].title == "Finance mobile app"
    assert rows[0].idea_type == "mobile_app"
    assert rows[0].source_opportunity_id == 1


def test_list_product_ideas_filters(db_session):
    save_product_ideas(
        db_session,
        [
            _idea(title="Mobile", confidence=80),
            {**_idea(title="SaaS"), "idea_type": "saas", "confidence_score": 40},
        ],
        generated_at=T0,
    )

    mobile = list_product_ideas(db_session, idea_type="mobile_app")
    high_conf = list_product_ideas(db_session, min_confidence_score=60)
    assert len(mobile) == 1
    assert mobile[0].title == "Mobile"
    assert len(high_conf) == 1
    assert high_conf[0].confidence_score == 80
