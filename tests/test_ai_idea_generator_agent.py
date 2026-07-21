from datetime import datetime, timezone

from app.agents.ai_idea_generator_agent import AiIdeaGeneratorAgent
from app.models.db_models import MarketOpportunity
from app.services.product_idea_service import list_product_ideas

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeOpportunityClient:
    def __init__(self, opportunities=None):
        self.opportunities = opportunities or []

    def fetch_opportunities(self, db, opportunity_ids=None, min_opportunity_score=None, limit=50, **kwargs):
        if opportunity_ids:
            return [row for row in self.opportunities if row.id in opportunity_ids]
        return self.opportunities[:limit]


def _opportunity(opp_id=1, score=72.0, category="Finance"):
    return MarketOpportunity(
        id=opp_id,
        title=f"{category} opportunity",
        category=category,
        description="Rising demand with user pain",
        opportunity_score=score,
        supporting_evidence={"signal_breakdown": {"pain_score": 12, "keyword_score": 15}},
        identified_at=T0,
    )


def test_agent_generates_and_saves_ideas(db_session):
    agent = AiIdeaGeneratorAgent(client=FakeOpportunityClient([_opportunity()]))

    summary = agent.run(db_session, opportunity_ids=[1], ideas_per_opportunity=1)

    ideas = list_product_ideas(db_session)
    assert summary["total_ideas"] == 1
    assert ideas[0].source_opportunity_id == 1
    assert ideas[0].idea_type in {"mobile_app", "saas", "ai_product"}
    assert "trend signals" not in (ideas[0].problem_statement or "").lower()
    assert len(ideas[0].proposed_solution or "") > 80


def test_agent_generates_ideas_for_explicit_id_even_if_below_min_score(db_session):
    low_score_opp = _opportunity(opp_id=5, score=20.0)
    agent = AiIdeaGeneratorAgent(client=FakeOpportunityClient([low_score_opp]))

    summary = agent.run(
        db_session,
        opportunity_ids=[5],
        min_opportunity_score=45,
        ideas_per_opportunity=1,
    )

    ideas = list_product_ideas(db_session)
    assert summary["total_ideas"] == 1
    assert ideas[0].source_opportunity_id == 5


def test_agent_skips_missing_opportunity(db_session):
    agent = AiIdeaGeneratorAgent(client=FakeOpportunityClient([]))

    summary = agent.run(db_session, opportunity_ids=[999])

    assert summary["total_ideas"] == 0
    assert "opportunity_id::999" in summary["skipped"]


def test_agent_generates_multiple_idea_types(db_session):
    agent = AiIdeaGeneratorAgent(client=FakeOpportunityClient([_opportunity(score=80)]))

    summary = agent.run(db_session, opportunity_ids=[1], ideas_per_opportunity=3)

    ideas = list_product_ideas(db_session)
    assert summary["total_ideas"] == 3
    assert {idea.idea_type for idea in ideas} == {"mobile_app", "saas", "ai_product"}
