"""
Plain-language narratives for product ideas.

Turns template/technical idea records into explanations a non-technical reader
can understand: what problem exists, what to build, and how people would use it.
"""

from __future__ import annotations

import re
from typing import Any


_TECHNICAL_MARKERS = (
    "trend signals",
    "fast-growing",
    "keyword upside",
    "bug mentions",
    "feature requests",
    "avg opportunity",
)


def product_name(title: str) -> str:
    """Extract the product name before an em dash, else the full title."""
    text = (title or "").strip()
    if " — " in text:
        return text.split(" — ", 1)[0].strip()
    if " - " in text:
        return text.split(" - ", 1)[0].strip()
    return text


def strip_technical_jargon(text: str) -> str:
    """Remove parenthetical ASO/stat dumps from opportunity descriptions."""
    cleaned = re.sub(r"\([^)]*trend signals[^)]*\)", "", text or "", flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned


def is_technical_description(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _TECHNICAL_MARKERS)


def _idea_type_label(idea_type: str | None) -> str:
    return {
        "mobile_app": "phone app",
        "saas": "online business tool",
        "ai_product": "AI-powered tool",
    }.get(idea_type or "", "digital product")


def _product_format(idea_type: str | None) -> str:
    return {
        "mobile_app": "a mobile app people download on their phone",
        "saas": "a website (online dashboard) that teams use in a browser",
        "ai_product": "an AI-powered online tool",
    }.get(idea_type or "", "a digital product")


def _clean_solution_text(text: str) -> str:
    core = (text or "").strip()
    core = re.sub(r"\s*Market signal focus:.*$", "", core, flags=re.IGNORECASE).strip()
    return core.rstrip(".")


def plain_problem_statement(
    *,
    category: str,
    pain_hint: str,
    opportunity_title: str | None = None,
    raw_description: str | None = None,
) -> str:
    if raw_description and not is_technical_description(raw_description):
        return strip_technical_jargon(raw_description)

    cat = (category or "this").lower()
    hints = {
        "bugs, negative reviews, and unmet feature requests": (
            f"People using {cat} apps are frustrated. Reviews mention bugs, missing features, "
            "and experiences that feel worse than they should for how popular the category is."
        ),
        "high keyword demand with weak incumbent execution": (
            f"Lots of people search for better {cat} solutions, but the apps available today "
            "still feel confusing, incomplete, or built for power users instead of everyday people."
        ),
        "rising category demand with room for differentiation": (
            f"The {cat} category is active on app stores, but many products still look and feel "
            "the same — there is room for something clearer and more focused."
        ),
    }
    base = hints.get(pain_hint, hints["rising category demand with room for differentiation"])

    if opportunity_title and ":" in opportunity_title:
        focus = opportunity_title.split(":", 1)[1].strip().rstrip(".")
        if focus and not is_technical_description(focus):
            base += f" The clearest opening right now: {focus.lower()}."

    return base


def plain_solution(
    *,
    title: str,
    idea_type: str | None,
    category: str,
    short_solution: str,
    audience: str | None = None,
) -> str:
    name = product_name(title)
    cat = (category or "this space").lower()
    fmt = _product_format(idea_type)
    core = _clean_solution_text(short_solution) or f"solve an important {cat} problem in a simpler way"
    who = (audience or f"people underserved in {cat}").strip()

    parts = [
        (
            f"{name} is {fmt} aimed at {who.lower()}. "
            f"In simple terms, it is meant to {core.lower()}."
        ),
    ]

    if idea_type == "mobile_app":
        parts.append(
            f"Someone downloads {name} when they want a straightforward way to handle a {cat}-related task "
            "without learning a complicated app. The first version should do one job really well."
        )
        parts.append(
            "What to include in version 1:\n"
            f"• A simple sign-up screen\n"
            f"• A home screen that shows the user's main goal or next step\n"
            f"• The core action screen — the reason they opened the app\n"
            "• Gentle reminders or progress tracking (if relevant)\n"
            "• An optional paid upgrade for advanced features"
        )
    elif idea_type == "saas":
        parts.append(
            f"A small team opens {name} in their browser each week to understand where {cat} "
            "opportunities are and what to build next — without manually digging through app stores and spreadsheets."
        )
        parts.append(
            "What to include in version 1:\n"
            "• Team sign-up and a shared workspace\n"
            "• A dashboard that ranks opportunities in plain language (not raw data tables)\n"
            "• A detail page per opportunity explaining the problem and a suggested product angle\n"
            "• Share or export so founders can discuss ideas together\n"
            "• Email or weekly digest summarizing what changed"
        )
    elif idea_type == "ai_product":
        parts.append(
            f"{name} helps {who.lower()} go from a rough market signal to a clear product brief in minutes, "
            f"using AI to explain opportunities in everyday language."
        )
        parts.append(
            "What to include in version 1:\n"
            "• A simple prompt or form: category, audience, or problem area\n"
            "• AI-generated brief with problem, solution sketch, and target user\n"
            "• Editable output the user can copy into Notion, slides, or a pitch\n"
            "• History of past briefs so teams can compare ideas"
        )
    else:
        parts.append(
            f"The product should feel approachable on day one and clearly explain value to {who.lower()}."
        )

    return "\n\n".join(parts)


def usage_steps(
    *,
    title: str,
    idea_type: str | None,
    category: str,
    short_solution: str,
) -> str:
    name = product_name(title)
    cat = (category or "this").lower()
    core = _clean_solution_text(short_solution).lower()

    if idea_type == "mobile_app":
        return (
            f"1. A person realizes they need help with a {cat} task and searches the app store.\n"
            f"2. They download {name}, create an account in under a minute, and see a simple starting screen.\n"
            f"3. They complete the main task the app promises — for example: {core or 'solving their daily problem'}.\n"
            "4. They come back because the app saves time, reduces stress, or gives clear progress.\n"
            "5. If they love it, they upgrade or tell friends."
        )
    if idea_type == "saas":
        return (
            f"1. A founder or product lead signs up for {name} and invites their team.\n"
            f"2. They open the dashboard and see the top {cat} opportunities explained in plain English.\n"
            "3. They click one opportunity and read who has the problem and what a new product could look like.\n"
            "4. They shortlist ideas, discuss with co-founders, and decide what to prototype next.\n"
            "5. They return weekly as new market signals appear."
        )
    if idea_type == "ai_product":
        return (
            f"1. A builder opens {name} and describes the {cat} space they care about.\n"
            "2. The tool generates a readable product brief — problem, idea, audience, and monetization angle.\n"
            "3. They edit the brief, save it, and share it with teammates or investors.\n"
            "4. They generate variations to compare different product directions.\n"
            "5. They upgrade when they need more briefs or deeper analysis."
        )
    return (
        f"1. A user discovers {name}.\n"
        "2. They understand the value within the first minute.\n"
        "3. They complete the core action and return when it helps them again."
    )


def plain_monetization(text: str | None, idea_type: str | None) -> str:
    base = (text or "").strip()
    if not base:
        base = "Freemium with a paid plan for advanced features"

    expansions = {
        "Team SaaS seats": (
            "Charge a monthly fee per team member. Offer a free trial, then paid plans for teams "
            "that want weekly updates, more tracked categories, and shared workspaces."
        ),
        "Monthly SaaS": (
            "Charge a flat monthly subscription. Start with a low tier for solo founders and a higher "
            "tier for teams that need collaboration and exports."
        ),
        "Freemium + premium insights": (
            "Free basic version for individuals; paid plan unlocks deeper insights, alerts, and history."
        ),
        "Freemium + Pro integrations": (
            "Free for personal use; paid plan adds integrations, sync, and power features."
        ),
        "Per-brief + Pro plan": (
            "Sell individual AI briefs, plus a monthly Pro plan for unlimited briefs and saved history."
        ),
    }
    for key, expansion in expansions.items():
        if key.lower() in base.lower():
            return f"{base}. {expansion}"
    if idea_type == "mobile_app":
        return f"{base}. Typical model: free download, optional subscription for premium features."
    if idea_type == "saas":
        return f"{base}. Typical model: monthly subscription with a free trial."
    return base


def plain_market_context(opportunity: dict[str, Any] | None) -> str:
    if not opportunity:
        return "This idea was generated from app store trends, search demand, and competitor signals."

    category = opportunity.get("category") or "this category"
    score = opportunity.get("opportunity_score")
    title = opportunity.get("title") or ""
    desc = opportunity.get("description") or ""

    parts = [
        f"We spotted potential in {category} because demand looks active and current apps do not fully satisfy users."
    ]
    if title and ":" in title and not is_technical_description(title):
        parts.append(f"Focus area: {title.split(':', 1)[1].strip().rstrip('.')}.")
    if score is not None:
        parts.append(
            f"Opportunity strength: {score}/100 — higher means more reason to explore this space now."
        )
    if desc and not is_technical_description(desc):
        parts.append(strip_technical_jargon(desc))
    return " ".join(parts)


def _looks_enriched_solution(solution: str) -> bool:
    lowered = (solution or "").lower()
    return any(
        marker in lowered
        for marker in ("version 1", "what to include", "key screens", "key parts to build")
    )


def _article(phrase: str) -> str:
    first = (phrase or " ").strip().lower()[:1]
    return "an" if first in "aeiou" else "a"


def elevator_pitch(
    *,
    title: str,
    idea_type: str | None,
    category: str,
    short_solution: str,
    audience: str | None,
) -> str:
    name = product_name(title)
    label = _idea_type_label(idea_type)
    core = _clean_solution_text(short_solution) or f"improve how people experience {category.lower()}"
    who = (audience or "everyday users").strip()
    return (
        f"{name} is {_article(label)} {label} built for {who.lower()}. "
        f"Put simply, it is meant to {core.lower()}. "
        f"You would build it for the {category.lower()} market where people are actively looking for better options."
    )


def enrich_idea_dict(idea: dict[str, Any], opportunity: Any | None = None) -> dict[str, Any]:
    """Return a copy of idea fields with plain-language problem/solution text."""
    category = getattr(opportunity, "category", None) or "General"
    opp_title = getattr(opportunity, "title", None)
    raw_desc = getattr(opportunity, "description", None)
    pain_hint = idea.pop("_pain_hint", None) or "rising category demand with room for differentiation"

    short_solution = _clean_solution_text(idea.get("proposed_solution") or idea.get("solution") or "")
    audience = idea.get("target_audience")

    enriched = dict(idea)
    enriched["problem_statement"] = plain_problem_statement(
        category=category,
        pain_hint=pain_hint,
        opportunity_title=opp_title,
        raw_description=raw_desc,
    )
    enriched["proposed_solution"] = plain_solution(
        title=idea.get("title", "Product"),
        idea_type=idea.get("idea_type"),
        category=category,
        short_solution=short_solution,
        audience=audience,
    )
    enriched["monetization_strategy"] = plain_monetization(
        idea.get("monetization_strategy"),
        idea.get("idea_type"),
    )
    return enriched


def build_detail_sections(
    idea: dict[str, Any],
    opportunity: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Structured sections for the dashboard idea detail panel."""
    title = idea.get("title") or "Untitled idea"
    idea_type = idea.get("idea_type")
    category = (opportunity or {}).get("category") or "General"
    short_solution = _clean_solution_text(idea.get("proposed_solution") or "")
    pitch_source = short_solution
    if len(short_solution) > 200 and ". " in short_solution:
        pitch_source = short_solution.split(". ", 1)[0]

    audience = idea.get("target_audience")
    problem = idea.get("problem_statement") or ""
    if is_technical_description(problem):
        problem = plain_problem_statement(
            category=category,
            pain_hint="rising category demand with room for differentiation",
            opportunity_title=(opportunity or {}).get("title"),
            raw_description=problem,
        )

    stored_solution = (idea.get("proposed_solution") or "").strip()
    if _looks_enriched_solution(stored_solution):
        solution = stored_solution
    else:
        solution = plain_solution(
            title=title,
            idea_type=idea_type,
            category=category,
            short_solution=short_solution or stored_solution,
            audience=audience,
        )

    return [
        {
            "key": "pitch",
            "title": "In simple terms",
            "body": elevator_pitch(
                title=title,
                idea_type=idea_type,
                category=category,
                short_solution=pitch_source,
                audience=audience,
            ),
        },
        {
            "key": "problem",
            "title": "The everyday problem",
            "body": problem,
        },
        {
            "key": "what_to_build",
            "title": "What you would build",
            "body": solution,
        },
        {
            "key": "how_it_works",
            "title": "How people would use it",
            "body": usage_steps(
                title=title,
                idea_type=idea_type,
                category=category,
                short_solution=pitch_source,
            ),
        },
        {
            "key": "audience",
            "title": "Who this is for",
            "body": (
                f"{audience}. They are the people most likely to pay for or adopt this product first."
                if audience
                else "People who are underserved by current apps in this category."
            ),
        },
        {
            "key": "monetization",
            "title": "How it makes money",
            "body": plain_monetization(idea.get("monetization_strategy"), idea_type),
        },
        {
            "key": "market_context",
            "title": "Why this opportunity exists now",
            "body": plain_market_context(opportunity),
        },
    ]
