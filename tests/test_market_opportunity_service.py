from datetime import datetime, timezone

from app.services.market_opportunity_service import (
    list_market_opportunities,
    save_market_opportunities,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _opportunity(title="Finance opportunity", score=72.5, category="Finance"):
    return {
        "title": title,
        "category": category,
        "description": "Demand rising with unresolved complaints",
        "opportunity_score": score,
        "supporting_evidence": {"keyword_ids": [1, 2], "review_ids": [9]},
    }


def test_save_market_opportunities(db_session):
    rows = save_market_opportunities(db_session, [_opportunity()], identified_at=T0)

    assert len(rows) == 1
    assert rows[0].title == "Finance opportunity"
    assert rows[0].opportunity_score == 72.5


def test_list_market_opportunities_filters(db_session):
    save_market_opportunities(
        db_session,
        [_opportunity(title="Finance", score=80, category="Finance"), _opportunity(title="Games", score=40, category="Games")],
        identified_at=T0,
    )

    high_score = list_market_opportunities(db_session, min_opportunity_score=60)
    finance = list_market_opportunities(db_session, category="Finance")
    assert len(high_score) == 1
    assert high_score[0].title == "Finance"
    assert len(finance) == 1
    assert finance[0].category == "Finance"
