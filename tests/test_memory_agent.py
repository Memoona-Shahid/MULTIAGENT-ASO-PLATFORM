from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.agents.memory_agent import MemoryAgent
from app.models.db_models import MemoryEntry, ProductIdea
from app.services.memory_service import list_memory_entries

T0 = datetime(2026, 1, 10, tzinfo=timezone.utc)


class FakeMemorySourceClient:
    def __init__(self, data=None):
        self.data = data or {}

    def fetch_recent_trends(self, db, since, limit=200):
        return self.data.get("trends", [])

    def fetch_recent_keywords(self, db, since, limit=200):
        return self.data.get("keywords", [])

    def fetch_recent_competitors(self, db, since, limit=100):
        return self.data.get("competitors", [])

    def fetch_recent_reviews(self, db, since, limit=300):
        return self.data.get("reviews", [])

    def fetch_recent_opportunities(self, db, since, limit=100):
        return self.data.get("opportunities", [])

    def fetch_recent_product_ideas(self, db, since, limit=100):
        return self.data.get("product_ideas", [])

    def fetch_recent_reports(self, db, since, limit=50):
        return self.data.get("reports", [])


def test_agent_consolidates_product_ideas(db_session):
    idea = ProductIdea(
        id=1,
        title="Finance SaaS dashboard",
        idea_type="saas",
        problem_statement="Demand rising",
        proposed_solution="Build SaaS",
        confidence_score=72.0,
        generated_at=T0,
    )
    client = FakeMemorySourceClient({"product_ideas": [idea]})
    agent = MemoryAgent(client=client)

    summary = agent.run(db_session, lookback_days=7, min_importance=0.5)

    rows = list_memory_entries(db_session, entry_type="idea")
    assert summary["total_entries"] >= 1
    assert summary["consolidated"]["idea"] == 1
    assert rows[0].key == "idea:1"
    assert rows[0].value["title"] == "Finance SaaS dashboard"


def test_agent_write_entry(db_session):
    agent = MemoryAgent(client=FakeMemorySourceClient())
    result = agent.write_entry(
        db_session,
        {
            "entry_type": "note",
            "key": "manual:1",
            "value": {"text": "Remember to track Finance category"},
            "importance": 1.0,
        },
    )

    row = list_memory_entries(db_session, entry_type="note")[0]
    assert result["key"] == "manual:1"
    assert row.value["text"] == "Remember to track Finance category"
