"""
AI Idea Generator Agent (Module 8).

Transforms scored MarketOpportunity rows into concrete product ideas
(mobile app / SaaS / AI product). Uses deterministic templates today so
the module is fully testable without an LLM; CrewAI/LLM enrichment can
replace the generator later without changing the API shape.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import MarketOpportunity
from app.services.product_idea_client import ProductIdeaSourceClient
from app.services.product_idea_service import save_product_ideas

DEFAULT_MIN_OPPORTUNITY_SCORE = 45.0
DEFAULT_IDEAS_PER_OPPORTUNITY = 1
IDEA_TYPES = ("mobile_app", "saas", "ai_product")


class AiIdeaGeneratorAgent:
    def __init__(self, client: ProductIdeaSourceClient | None = None):
        self.client = client or ProductIdeaSourceClient()

    def run(
        self,
        db: Session,
        opportunity_ids: list[int] | None = None,
        min_opportunity_score: float = DEFAULT_MIN_OPPORTUNITY_SCORE,
        ideas_per_opportunity: int = DEFAULT_IDEAS_PER_OPPORTUNITY,
        opportunity_limit: int = 50,
    ) -> dict:
        if ideas_per_opportunity < 1 or ideas_per_opportunity > len(IDEA_TYPES):
            raise ValueError(f"ideas_per_opportunity must be between 1 and {len(IDEA_TYPES)}")

        generated_at = datetime.now(timezone.utc)
        summary: dict = {
            "generated_at": generated_at.isoformat(),
            "opportunities": {},
            "skipped": {},
            "total_ideas": 0,
        }

        if opportunity_ids:
            requested = list(dict.fromkeys(opportunity_ids))
            opportunities = self.client.fetch_opportunities(db, opportunity_ids=requested)
            found_ids = {opp.id for opp in opportunities}
            for opp_id in requested:
                if opp_id not in found_ids:
                    summary["skipped"][f"opportunity_id::{opp_id}"] = "Opportunity not found"
        else:
            opportunities = self.client.fetch_opportunities(
                db,
                min_opportunity_score=min_opportunity_score,
                limit=opportunity_limit,
            )

        ideas = []
        for opportunity in opportunities:
            generated = self._generate_for_opportunity(opportunity, ideas_per_opportunity)
            ideas.extend(generated)
            summary["opportunities"][str(opportunity.id)] = len(generated)

        saved = save_product_ideas(db, ideas, generated_at) if ideas else []
        summary["total_ideas"] = len(saved)

        logger.info("AiIdeaGeneratorAgent run complete: {}", summary)
        return summary

    def _generate_for_opportunity(
        self, opportunity: MarketOpportunity, ideas_per_opportunity: int
    ) -> list[dict]:
        category = opportunity.category or "General"
        score = float(opportunity.opportunity_score or 50.0)
        selected_types = self._select_idea_types(score, ideas_per_opportunity)

        ideas = []
        for idea_type in selected_types:
            ideas.append(self._build_idea(opportunity, category, score, idea_type))
        return ideas

    def _select_idea_types(self, score: float, count: int) -> list[str]:
        if count >= 3:
            return list(IDEA_TYPES)
        if count == 2:
            return ["mobile_app", "ai_product"] if score >= 60 else ["mobile_app", "saas"]
        if score >= 70:
            return ["ai_product"]
        if score >= 55:
            return ["mobile_app"]
        return ["saas"]

    def _build_idea(
        self,
        opportunity: MarketOpportunity,
        category: str,
        score: float,
        idea_type: str,
    ) -> dict:
        pain_hint = self._pain_hint(opportunity)
        confidence = round(min(100.0, max(35.0, score * 0.9)), 2)

        if idea_type == "mobile_app":
            title = f"{category} mobile app with faster onboarding"
            solution = (
                f"Ship a focused {category.lower()} mobile app that solves the top user pain "
                f"({pain_hint}) with a simpler workflow than incumbent apps."
            )
            audience = f"Mobile users frustrated with existing {category.lower()} apps"
            monetization = "Freemium with premium subscription for advanced features"
        elif idea_type == "saas":
            title = f"{category} SaaS dashboard for indie operators"
            solution = (
                f"Build a lightweight SaaS workspace for {category.lower()} teams to track "
                f"demand signals and act on gaps like: {pain_hint}."
            )
            audience = f"Small teams and solo founders in {category.lower()}"
            monetization = "Monthly SaaS tiers based on tracked apps and report volume"
        else:
            title = f"AI copilot for {category.lower()} growth decisions"
            solution = (
                f"Launch an AI assistant that turns {category.lower()} store signals into weekly "
                f"prioritized actions, starting with: {pain_hint}."
            )
            audience = f"ASO managers and product leads in {category.lower()}"
            monetization = "Usage-based AI credits plus pro plan for automated reports"

        return {
            "title": title,
            "idea_type": idea_type,
            "problem_statement": opportunity.description or opportunity.title,
            "proposed_solution": solution,
            "target_audience": audience,
            "monetization_strategy": monetization,
            "confidence_score": confidence,
            "source_opportunity_id": opportunity.id,
        }

    def _pain_hint(self, opportunity: MarketOpportunity) -> str:
        evidence = opportunity.supporting_evidence or {}
        breakdown = evidence.get("signal_breakdown") or {}
        pain_score = breakdown.get("pain_score")
        if pain_score and pain_score >= 10:
            return "bugs, negative reviews, and unmet feature requests"
        keyword_score = breakdown.get("keyword_score")
        if keyword_score and keyword_score >= 10:
            return "high keyword demand with weak incumbent execution"
        return "rising category demand with room for differentiation"
