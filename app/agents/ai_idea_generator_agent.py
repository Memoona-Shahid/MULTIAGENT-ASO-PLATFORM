"""
AI Idea Generator Agent (Module 8).

Transforms scored MarketOpportunity rows into concrete product ideas
(mobile app / SaaS / AI product). Uses category-specific templates so
outputs are actionable and distinct — not the same SaaS dashboard title
for every category.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import MarketOpportunity
from app.services.product_idea_client import ProductIdeaSourceClient
from app.services.product_idea_service import save_product_ideas
from app.utils.category_normalize import normalize_category

DEFAULT_MIN_OPPORTUNITY_SCORE = 45.0
DEFAULT_IDEAS_PER_OPPORTUNITY = 1
IDEA_TYPES = ("mobile_app", "saas", "ai_product")

# Concrete product concepts per category — used to avoid generic "X SaaS dashboard" spam.
CATEGORY_CONCEPTS: dict[str, dict[str, dict[str, str]]] = {
    "Social": {
        "mobile_app": {
            "title": "PulseCircle — private interest groups with low-noise feeds",
            "solution": "A mobile social app for niche communities with topic rooms, creator tools, and spam-resistant discovery instead of endless open feeds.",
            "audience": "Users burned out by noisy mainstream social apps",
            "monetization": "Freemium + creator subscriptions and tip jars",
        },
        "saas": {
            "title": "SocialGap Atlas — competitor gap tracker for social apps",
            "solution": "A SaaS console that maps social-app review complaints, feature gaps, and chart movers into weekly product bets.",
            "audience": "Social product managers and indie founders",
            "monetization": "Seat-based SaaS with competitor tracking tiers",
        },
        "ai_product": {
            "title": "ThreadSense AI — social retention opportunity scout",
            "solution": "An AI analyst that reads social app reviews and chart shifts, then recommends retention features to ship next.",
            "audience": "Growth and ASO teams in social products",
            "monetization": "Usage-based AI analysis credits",
        },
    },
    "Productivity": {
        "mobile_app": {
            "title": "FocusLane — habit + task app with one-screen planning",
            "solution": "A productivity mobile app that merges habit tracking and daily tasks into a 30-second morning plan with offline-first sync.",
            "audience": "Busy professionals who abandon complex productivity suites",
            "monetization": "Freemium with Pro calendar/integrations pack",
        },
        "saas": {
            "title": "OpsBrief — lightweight ops dashboard for solo operators",
            "solution": "A SaaS workspace that turns productivity keyword demand and competitor gaps into a simple weekly operating checklist.",
            "audience": "Freelancers and micro-teams",
            "monetization": "Flat monthly SaaS plans",
        },
        "ai_product": {
            "title": "PlanPilot AI — daily plan generator from goals and reviews",
            "solution": "An AI coach that converts user goals and competitor feature gaps into a prioritized daily plan.",
            "audience": "Knowledge workers seeking lighter productivity tools",
            "monetization": "Subscription with AI planning credits",
        },
    },
    "Entertainment": {
        "mobile_app": {
            "title": "ClipNest — short-form discovery without algorithm fatigue",
            "solution": "A short-drama / clip mobile app with human-curated shelves and creator playlists instead of opaque algorithmic loops.",
            "audience": "Entertainment viewers seeking fresher short content",
            "monetization": "Ads + premium ad-free and early access",
        },
        "saas": {
            "title": "ShowRadar — entertainment chart and gap monitor",
            "solution": "Track entertainment chart movers, keyword demand, and review themes to spot format opportunities early.",
            "audience": "Content studios and indie entertainment founders",
            "monetization": "Monthly market-intel SaaS",
        },
        "ai_product": {
            "title": "PlotSpark AI — entertainment concept generator",
            "solution": "Generate short-form show/app concepts from trending entertainment signals and audience complaints.",
            "audience": "Creators and entertainment product teams",
            "monetization": "Per-concept generation fees + Pro plan",
        },
    },
    "Shopping": {
        "mobile_app": {
            "title": "DealPath — personal shopping assistant for deal hunting",
            "solution": "A shopping app that watches price drops, wishlist gaps, and review trust signals for categories users actually buy.",
            "audience": "Value-focused mobile shoppers",
            "monetization": "Affiliate commissions + premium alerts",
        },
        "saas": {
            "title": "ShelfGap — ecommerce ASO and listing opportunity desk",
            "solution": "A SaaS desk that surfaces shopping-app keyword gaps, rating risks, and monetization patterns from store data.",
            "audience": "DTC brands and marketplace sellers",
            "monetization": "Monthly SaaS by tracked SKUs/apps",
        },
        "ai_product": {
            "title": "BuySignal AI — shopping trend to product brief",
            "solution": "Turn shopping chart and review signals into product briefs with positioning and monetization options.",
            "audience": "Ecommerce product managers",
            "monetization": "Report packs + AI credit wallet",
        },
    },
    "Health & Fitness": {
        "mobile_app": {
            "title": "FormLoop — fitness habit app with form cues and streaks",
            "solution": "A fitness mobile app focused on short guided sessions, form reminders, and habit streaks without gym-app bloat.",
            "audience": "Casual fitness users quitting complex trackers",
            "monetization": "Freemium + coach/program subscriptions",
        },
        "saas": {
            "title": "FitGap Studio — fitness competitor opportunity board",
            "solution": "Monitor fitness keyword demand and competitor review pain to prioritize features for new fitness apps.",
            "audience": "Fitness founders and studio operators",
            "monetization": "Monthly SaaS + white-label reports",
        },
        "ai_product": {
            "title": "CoachDraft AI — workout plan from market gaps",
            "solution": "Generate fitness program concepts from high-opportunity keywords and common user complaints.",
            "audience": "Fitness coaches and app builders",
            "monetization": "Subscription with generation limits",
        },
    },
    "Finance": {
        "mobile_app": {
            "title": "CashClear — simple personal finance for first-time savers",
            "solution": "A finance app with guided budgets, bill reminders, and plain-language insights instead of complex investing suites.",
            "audience": "Young adults starting personal finance",
            "monetization": "Freemium + premium insights and banking partners",
        },
        "saas": {
            "title": "FinGap Desk — finance app opportunity tracker",
            "solution": "Track finance category chart moves, keyword demand, and review friction to find underserved money workflows.",
            "audience": "Fintech founders and ASO specialists",
            "monetization": "Team SaaS seats",
        },
        "ai_product": {
            "title": "MoneyBrief AI — fintech idea briefs from store signals",
            "solution": "Produce finance product briefs from keyword opportunity and competitor rating gaps.",
            "audience": "Fintech PMs and indie builders",
            "monetization": "Per-brief pricing + Pro plan",
        },
    },
    "Communication": {
        "mobile_app": {
            "title": "ReplyKit — focused messaging for work circles",
            "solution": "A communication app for small teams with scheduled send, priority inboxes, and fewer notification traps.",
            "audience": "Remote teams tired of noisy chat apps",
            "monetization": "Per-workspace subscription",
        },
        "saas": {
            "title": "MsgGap Monitor — messaging competitor intel",
            "solution": "Watch communication-app ratings, feature requests, and chart ranks to spot messaging niches.",
            "audience": "Comms startups and product teams",
            "monetization": "Monthly SaaS",
        },
        "ai_product": {
            "title": "InboxPilot AI — messaging UX opportunity finder",
            "solution": "Analyze communication reviews to recommend UX fixes and new messaging product angles.",
            "audience": "Communication product managers",
            "monetization": "AI analysis subscription",
        },
    },
    "Photo & Video": {
        "mobile_app": {
            "title": "CutQuick — one-tap short video editor for creators",
            "solution": "A photo/video app optimized for fast cuts, captions, and templates based on rising creator demand.",
            "audience": "Short-form creators on mobile",
            "monetization": "Freemium + pro export packs",
        },
        "saas": {
            "title": "CreateGap Lab — creator-tool opportunity board",
            "solution": "Benchmark photo/video apps on features, ratings, and keyword demand for white-space tools.",
            "audience": "Creator-tool founders",
            "monetization": "SaaS tiers by tracked competitors",
        },
        "ai_product": {
            "title": "FrameForge AI — video feature concept generator",
            "solution": "Propose photo/video features from review themes and keyword gaps.",
            "audience": "Creator-app product teams",
            "monetization": "Credits + Pro plan",
        },
    },
    "Music & Audio": {
        "mobile_app": {
            "title": "LoopRoom — social listening rooms for niche genres",
            "solution": "A music app for niche genre rooms, shared queues, and discovery without mega-catalog overwhelm.",
            "audience": "Music fans of niche genres",
            "monetization": "Ads + premium rooms and offline packs",
        },
        "saas": {
            "title": "AudioGap Desk — music app market monitor",
            "solution": "Track music/audio chart and keyword opportunities to find underserved listening experiences.",
            "audience": "Audio startups and label digital teams",
            "monetization": "Monthly market SaaS",
        },
        "ai_product": {
            "title": "SoundBrief AI — audio product idea briefs",
            "solution": "Convert music/audio store signals into product briefs with audience and monetization options.",
            "audience": "Audio product managers",
            "monetization": "Per-brief + subscription",
        },
    },
    "Dating": {
        "mobile_app": {
            "title": "MatchLite — intent-first dating with fewer swipes",
            "solution": "A dating app that prioritizes shared goals and conversation starters over endless swipe volume.",
            "audience": "Daters frustrated by low-quality matches",
            "monetization": "Freemium + boosts and verified profiles",
        },
        "saas": {
            "title": "DateGap Intel — dating competitor opportunity board",
            "solution": "Monitor dating-app review pain and keyword demand to find underserved matching niches.",
            "audience": "Dating founders and growth teams",
            "monetization": "Monthly SaaS",
        },
        "ai_product": {
            "title": "SparkBrief AI — dating concept generator",
            "solution": "Generate dating product concepts from competitor complaints and demand keywords.",
            "audience": "Dating product teams",
            "monetization": "AI credits + Pro",
        },
    },
}


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
                diversify_by_category=True,
            )

        ideas = []
        seen_idea_keys: set[str] = set()
        for opportunity in opportunities:
            generated = self._generate_for_opportunity(opportunity, ideas_per_opportunity)
            unique_for_opp = []
            for idea in generated:
                key = f"{idea['title'].lower()}::{idea['idea_type']}"
                if key in seen_idea_keys:
                    continue
                seen_idea_keys.add(key)
                unique_for_opp.append(idea)
            ideas.extend(unique_for_opp)
            summary["opportunities"][str(opportunity.id)] = len(unique_for_opp)

        saved = save_product_ideas(db, ideas, generated_at) if ideas else []
        summary["total_ideas"] = len(saved)

        logger.info("AiIdeaGeneratorAgent run complete: {}", summary)
        return summary

    def _generate_for_opportunity(
        self, opportunity: MarketOpportunity, ideas_per_opportunity: int
    ) -> list[dict]:
        category = normalize_category(opportunity.category) or "General"
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
        concept = (CATEGORY_CONCEPTS.get(category) or {}).get(idea_type)

        if concept:
            title = concept["title"]
            solution = f"{concept['solution']} Market signal focus: {pain_hint}."
            audience = concept["audience"]
            monetization = concept["monetization"]
        else:
            title = f"{category} opportunity product ({idea_type.replace('_', ' ')})"
            solution = (
                f"Build a {idea_type.replace('_', ' ')} for {category.lower()} that addresses "
                f"{pain_hint}, using a sharper workflow than incumbents."
            )
            audience = f"Users and operators underserved in {category.lower()}"
            monetization = "Freemium core with premium subscription for advanced features"

        problem = opportunity.description or opportunity.title
        return {
            "title": title,
            "idea_type": idea_type,
            "problem_statement": problem,
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
