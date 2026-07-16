"""
AI Idea Generator Agent (Module 8).

Builds concrete product ideas from market opportunities.
Uses multiple concept variants per category and rotates them across runs
so each Generate action produces different ideas when possible.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import MarketOpportunity, ProductIdea
from app.services.product_idea_client import ProductIdeaSourceClient
from app.services.product_idea_service import save_product_ideas
from app.utils.category_normalize import normalize_category

DEFAULT_MIN_OPPORTUNITY_SCORE = 45.0
DEFAULT_IDEAS_PER_OPPORTUNITY = 1
IDEA_TYPES = ("mobile_app", "saas", "ai_product")

# Multiple variants per category so runs don't always emit the same titles.
CATEGORY_VARIANTS: dict[str, list[dict[str, str]]] = {
    "Social": [
        {
            "idea_type": "mobile_app",
            "title": "PulseCircle — private interest groups with low-noise feeds",
            "solution": "A social app for niche communities with topic rooms and spam-resistant discovery.",
            "audience": "Users burned out by noisy mainstream social apps",
            "monetization": "Freemium + creator subscriptions",
        },
        {
            "idea_type": "ai_product",
            "title": "ThreadSense AI — retention opportunity scout for social apps",
            "solution": "An AI analyst that turns social reviews and chart shifts into retention feature bets.",
            "audience": "Growth teams in social products",
            "monetization": "Usage-based AI analysis credits",
        },
        {
            "idea_type": "saas",
            "title": "ClanMap — community health dashboard for social startups",
            "solution": "Track community churn signals, moderation load, and competitor feature gaps weekly.",
            "audience": "Social founders and community leads",
            "monetization": "Seat-based SaaS",
        },
        {
            "idea_type": "mobile_app",
            "title": "NearbyNotes — local-only social feed for real-world hangouts",
            "solution": "A location-limited social app for events, meetups, and neighborhood posts without global noise.",
            "audience": "People seeking local social connection",
            "monetization": "Ads + premium event boosts",
        },
    ],
    "Productivity": [
        {
            "idea_type": "mobile_app",
            "title": "FocusLane — habit + task app with one-screen planning",
            "solution": "Merge habits and daily tasks into a 30-second morning plan with offline sync.",
            "audience": "Busy professionals quitting complex productivity suites",
            "monetization": "Freemium + Pro integrations",
        },
        {
            "idea_type": "ai_product",
            "title": "PlanPilot AI — daily plan generator from goals",
            "solution": "Convert goals and competitor feature gaps into a prioritized daily plan.",
            "audience": "Knowledge workers wanting lighter planning tools",
            "monetization": "Subscription with AI credits",
        },
        {
            "idea_type": "saas",
            "title": "OpsBrief — weekly operating checklist for solo operators",
            "solution": "Turn productivity demand signals into a simple weekly ops checklist.",
            "audience": "Freelancers and micro-teams",
            "monetization": "Flat monthly SaaS",
        },
        {
            "idea_type": "mobile_app",
            "title": "DeepBlock — distraction firewall with timed deep-work sessions",
            "solution": "A focus app that blocks distracting apps during timed deep-work blocks and tracks streak quality.",
            "audience": "Students and remote workers",
            "monetization": "Freemium + team seats",
        },
    ],
    "Entertainment": [
        {
            "idea_type": "saas",
            "title": "ShowRadar — entertainment chart and gap monitor",
            "solution": "Track chart movers and review themes to spot format opportunities early.",
            "audience": "Content studios and indie entertainment founders",
            "monetization": "Monthly market-intel SaaS",
        },
        {
            "idea_type": "mobile_app",
            "title": "ClipNest — short-form discovery without algorithm fatigue",
            "solution": "Human-curated shelves and creator playlists instead of opaque algorithmic loops.",
            "audience": "Viewers seeking fresher short content",
            "monetization": "Ads + premium early access",
        },
        {
            "idea_type": "ai_product",
            "title": "PlotSpark AI — short-drama concept generator",
            "solution": "Generate short-form concepts from entertainment demand and audience complaints.",
            "audience": "Creators and entertainment PMs",
            "monetization": "Per-concept fees + Pro plan",
        },
        {
            "idea_type": "mobile_app",
            "title": "BingeBuddy — co-watching rooms for niche shows",
            "solution": "Watch parties and discussion rooms for niche series fans.",
            "audience": "Fans who want social binge experiences",
            "monetization": "Freemium + premium rooms",
        },
    ],
    "Shopping": [
        {
            "idea_type": "saas",
            "title": "ShelfGap — ecommerce ASO and listing opportunity desk",
            "solution": "Surface shopping keyword gaps, rating risks, and monetization patterns.",
            "audience": "DTC brands and marketplace sellers",
            "monetization": "Monthly SaaS by tracked apps/SKUs",
        },
        {
            "idea_type": "mobile_app",
            "title": "DealPath — personal shopping assistant for deal hunting",
            "solution": "Watch price drops and wishlist gaps for categories users actually buy.",
            "audience": "Value-focused mobile shoppers",
            "monetization": "Affiliate + premium alerts",
        },
        {
            "idea_type": "ai_product",
            "title": "BuySignal AI — shopping trend to product brief",
            "solution": "Turn shopping chart and review signals into product briefs.",
            "audience": "Ecommerce product managers",
            "monetization": "Report packs + AI credits",
        },
        {
            "idea_type": "mobile_app",
            "title": "TrustCart — review-quality shopping companion",
            "solution": "Filter fake-looking reviews and highlight trustworthy product signals before purchase.",
            "audience": "Online shoppers wary of review spam",
            "monetization": "Freemium + affiliate",
        },
    ],
    "Health & Fitness": [
        {
            "idea_type": "saas",
            "title": "FitGap Studio — fitness competitor opportunity board",
            "solution": "Monitor fitness keyword demand and review pain to prioritize features.",
            "audience": "Fitness founders and studio operators",
            "monetization": "Monthly SaaS + white-label reports",
        },
        {
            "idea_type": "mobile_app",
            "title": "FormLoop — short guided fitness sessions with streaks",
            "solution": "Short guided sessions and form cues without gym-app bloat.",
            "audience": "Casual fitness users",
            "monetization": "Freemium + coach programs",
        },
        {
            "idea_type": "ai_product",
            "title": "CoachDraft AI — workout concepts from market gaps",
            "solution": "Generate fitness program concepts from high-opportunity keywords and complaints.",
            "audience": "Fitness coaches and app builders",
            "monetization": "Subscription with generation limits",
        },
        {
            "idea_type": "mobile_app",
            "title": "RecoverDay — rest-day and mobility planner",
            "solution": "A recovery-first fitness app for mobility, sleep, and deload planning.",
            "audience": "Active users who overtrain and burn out",
            "monetization": "Freemium + premium recovery plans",
        },
    ],
    "Finance": [
        {
            "idea_type": "mobile_app",
            "title": "CashClear — simple finance for first-time savers",
            "solution": "Guided budgets and plain-language insights instead of complex investing suites.",
            "audience": "Young adults starting personal finance",
            "monetization": "Freemium + partner banking offers",
        },
        {
            "idea_type": "saas",
            "title": "FinGap Desk — finance app opportunity tracker",
            "solution": "Find underserved money workflows from chart and keyword demand.",
            "audience": "Fintech founders",
            "monetization": "Team SaaS seats",
        },
        {
            "idea_type": "ai_product",
            "title": "MoneyBrief AI — fintech idea briefs from store signals",
            "solution": "Produce finance product briefs from keyword opportunity and rating gaps.",
            "audience": "Fintech PMs and indie builders",
            "monetization": "Per-brief + Pro plan",
        },
        {
            "idea_type": "mobile_app",
            "title": "BillShield — bill calendar with late-fee warnings",
            "solution": "A bill-tracking app focused on due dates, reminders, and late-fee avoidance.",
            "audience": "Households managing multiple bills",
            "monetization": "Freemium + premium household seats",
        },
    ],
    "Communication": [
        {
            "idea_type": "saas",
            "title": "MsgGap Monitor — messaging competitor intel",
            "solution": "Watch ratings and chart ranks to spot messaging niches.",
            "audience": "Comms startups and product teams",
            "monetization": "Monthly SaaS",
        },
        {
            "idea_type": "mobile_app",
            "title": "ReplyKit — focused messaging for work circles",
            "solution": "Priority inboxes and scheduled send for small teams.",
            "audience": "Remote teams tired of noisy chat apps",
            "monetization": "Per-workspace subscription",
        },
        {
            "idea_type": "ai_product",
            "title": "InboxPilot AI — messaging UX opportunity finder",
            "solution": "Recommend messaging UX fixes from review themes.",
            "audience": "Communication product managers",
            "monetization": "AI analysis subscription",
        },
        {
            "idea_type": "mobile_app",
            "title": "QuietThread — async chat with digest mode only",
            "solution": "An async messaging app that delivers digests instead of constant pings.",
            "audience": "Professionals protecting focus time",
            "monetization": "Freemium + team plans",
        },
    ],
    "Photo & Video": [
        {
            "idea_type": "saas",
            "title": "CreateGap Lab — creator-tool opportunity board",
            "solution": "Benchmark photo/video apps for white-space tools.",
            "audience": "Creator-tool founders",
            "monetization": "SaaS by tracked competitors",
        },
        {
            "idea_type": "mobile_app",
            "title": "CutQuick — one-tap short video editor",
            "solution": "Fast cuts, captions, and templates for short-form creators.",
            "audience": "Short-form creators on mobile",
            "monetization": "Freemium + pro export packs",
        },
        {
            "idea_type": "ai_product",
            "title": "FrameForge AI — video feature concept generator",
            "solution": "Propose photo/video features from review themes and keyword gaps.",
            "audience": "Creator-app product teams",
            "monetization": "Credits + Pro plan",
        },
        {
            "idea_type": "mobile_app",
            "title": "ShotList — mobile storyboard and shoot checklist",
            "solution": "A creator app for shot lists, lighting notes, and on-set checklists.",
            "audience": "Indie creators and small video teams",
            "monetization": "Freemium + pro templates",
        },
    ],
    "Music & Audio": [
        {
            "idea_type": "saas",
            "title": "AudioGap Desk — music app market monitor",
            "solution": "Find underserved listening experiences from chart and keyword signals.",
            "audience": "Audio startups and label digital teams",
            "monetization": "Monthly market SaaS",
        },
        {
            "idea_type": "mobile_app",
            "title": "LoopRoom — social listening rooms for niche genres",
            "solution": "Genre rooms and shared queues without mega-catalog overwhelm.",
            "audience": "Niche music fans",
            "monetization": "Ads + premium rooms",
        },
        {
            "idea_type": "ai_product",
            "title": "SoundBrief AI — audio product idea briefs",
            "solution": "Convert music/audio store signals into product briefs.",
            "audience": "Audio product managers",
            "monetization": "Per-brief + subscription",
        },
        {
            "idea_type": "mobile_app",
            "title": "PracticePad — music practice tracker with streaks",
            "solution": "A practice journal app with timed sessions and teacher feedback loops.",
            "audience": "Music students and teachers",
            "monetization": "Freemium + teacher seats",
        },
    ],
    "Dating": [
        {
            "idea_type": "mobile_app",
            "title": "MatchLite — intent-first dating with fewer swipes",
            "solution": "Prioritize shared goals and conversation starters over swipe volume.",
            "audience": "Daters frustrated by low-quality matches",
            "monetization": "Freemium + boosts",
        },
        {
            "idea_type": "saas",
            "title": "DateGap Intel — dating competitor opportunity board",
            "solution": "Find underserved matching niches from review pain and demand keywords.",
            "audience": "Dating founders",
            "monetization": "Monthly SaaS",
        },
        {
            "idea_type": "ai_product",
            "title": "SparkBrief AI — dating concept generator",
            "solution": "Generate dating concepts from competitor complaints and demand keywords.",
            "audience": "Dating product teams",
            "monetization": "AI credits + Pro",
        },
        {
            "idea_type": "mobile_app",
            "title": "CoffeeFirst — local meetup dating without endless chat",
            "solution": "A dating app that pushes users toward short local meetups instead of infinite messaging.",
            "audience": "People who want faster real-world dates",
            "monetization": "Freemium + verified meetup boosts",
        },
    ],
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

        existing_titles = {
            (title or "").strip().lower()
            for title in db.scalars(select(ProductIdea.title)).all()
        }
        run_seed = int(generated_at.timestamp())

        ideas = []
        seen_idea_keys: set[str] = set()
        for index, opportunity in enumerate(opportunities):
            generated = self._generate_for_opportunity(
                opportunity,
                ideas_per_opportunity=ideas_per_opportunity,
                run_seed=run_seed,
                slot=index,
                used_titles=existing_titles | {k.split("::", 1)[0] for k in seen_idea_keys},
            )
            unique_for_opp = []
            for idea in generated:
                key = f"{idea['title'].lower()}::{idea['idea_type']}"
                if key in seen_idea_keys or idea["title"].lower() in existing_titles:
                    continue
                seen_idea_keys.add(key)
                existing_titles.add(idea["title"].lower())
                unique_for_opp.append(idea)
            ideas.extend(unique_for_opp)
            summary["opportunities"][str(opportunity.id)] = len(unique_for_opp)

        saved = save_product_ideas(db, ideas, generated_at) if ideas else []
        summary["total_ideas"] = len(saved)

        logger.info("AiIdeaGeneratorAgent run complete: {}", summary)
        return summary

    def _generate_for_opportunity(
        self,
        opportunity: MarketOpportunity,
        *,
        ideas_per_opportunity: int,
        run_seed: int,
        slot: int,
        used_titles: set[str],
    ) -> list[dict]:
        category = normalize_category(opportunity.category) or "General"
        score = float(opportunity.opportunity_score or 50.0)
        selected_types = self._select_idea_types(score, ideas_per_opportunity, run_seed + slot)

        ideas = []
        for type_offset, idea_type in enumerate(selected_types):
            ideas.append(
                self._build_idea(
                    opportunity,
                    category,
                    score,
                    idea_type,
                    run_seed=run_seed + slot + type_offset,
                    used_titles=used_titles,
                )
            )
        return ideas

    def _select_idea_types(self, score: float, count: int, seed: int) -> list[str]:
        if count >= 3:
            return list(IDEA_TYPES)
        if count == 2:
            pairs = [
                ["mobile_app", "ai_product"],
                ["mobile_app", "saas"],
                ["saas", "ai_product"],
            ]
            return pairs[seed % len(pairs)]
        # Rotate type each run so the same category is not always SaaS/mobile.
        ordered = ["mobile_app", "saas", "ai_product"]
        if score >= 70:
            ordered = ["ai_product", "mobile_app", "saas"]
        elif score >= 55:
            ordered = ["mobile_app", "ai_product", "saas"]
        else:
            ordered = ["saas", "mobile_app", "ai_product"]
        start = seed % len(ordered)
        return [ordered[start]]

    def _build_idea(
        self,
        opportunity: MarketOpportunity,
        category: str,
        score: float,
        idea_type: str,
        *,
        run_seed: int,
        used_titles: set[str],
    ) -> dict:
        pain_hint = self._pain_hint(opportunity)
        confidence = round(min(100.0, max(35.0, score * 0.9)), 2)
        concept = self._pick_concept(category, idea_type, run_seed, used_titles)

        if concept:
            title = concept["title"]
            solution = f"{concept['solution']} Market signal focus: {pain_hint}."
            audience = concept["audience"]
            monetization = concept["monetization"]
            idea_type = concept.get("idea_type", idea_type)
        else:
            stamp = datetime.now(timezone.utc).strftime("%H%M")
            title = f"{category} {idea_type.replace('_', ' ')} concept {stamp}"
            solution = (
                f"Build a {idea_type.replace('_', ' ')} for {category.lower()} that addresses "
                f"{pain_hint}, using a sharper workflow than incumbents."
            )
            audience = f"Users and operators underserved in {category.lower()}"
            monetization = "Freemium core with premium subscription for advanced features"

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

    def _pick_concept(
        self,
        category: str,
        idea_type: str,
        run_seed: int,
        used_titles: set[str],
    ) -> dict[str, str] | None:
        variants = list(CATEGORY_VARIANTS.get(category) or [])
        if not variants:
            return None

        # Prefer unused titles first, then matching idea_type, then any variant.
        unused = [v for v in variants if v["title"].lower() not in used_titles]
        pool = unused or variants
        typed = [v for v in pool if v.get("idea_type") == idea_type]
        pool = typed or pool
        return pool[run_seed % len(pool)]

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
