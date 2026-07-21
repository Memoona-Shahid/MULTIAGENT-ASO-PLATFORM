from app.utils.idea_narrative import (
    build_detail_sections,
    enrich_idea_dict,
    is_technical_description,
    plain_solution,
)


def test_is_technical_description_detects_aso_jargon():
    text = "Finance shows momentum (13 trend signals, 0 fast-growing) with keyword upside"
    assert is_technical_description(text) is True


def test_plain_solution_expands_saas_idea_for_non_technical_readers():
    body = plain_solution(
        title="FinGap Desk — finance app opportunity tracker",
        idea_type="saas",
        category="Finance",
        short_solution="Find underserved money workflows from chart and keyword demand.",
        audience="Fintech founders",
    )
    assert "FinGap Desk" in body
    assert "website" in body.lower() or "browser" in body.lower()
    assert "dashboard" in body.lower()
    assert "trend signals" not in body.lower()


def test_build_detail_sections_avoids_duplicate_jargon_for_old_records():
    sections = build_detail_sections(
        {
            "title": "FinGap Desk — finance app opportunity tracker",
            "idea_type": "saas",
            "problem_statement": (
                "Finance shows momentum (13 trend signals, 0 fast-growing) with keyword upside "
                "(avg opportunity 88.0) and user pain from reviews."
            ),
            "proposed_solution": "Find underserved money workflows from chart and keyword demand.",
            "target_audience": "Fintech founders",
            "monetization_strategy": "Team SaaS seats",
        },
        {
            "title": "Finance: high-demand keywords with weak competition",
            "category": "Finance",
            "opportunity_score": 45.9,
            "description": "Finance shows momentum (13 trend signals, 0 fast-growing)",
        },
    )
    keys = [row["key"] for row in sections]
    assert keys == [
        "pitch",
        "problem",
        "what_to_build",
        "how_it_works",
        "audience",
        "monetization",
        "market_context",
    ]
    combined = " ".join(row["body"] for row in sections).lower()
    assert "trend signals" not in combined
    assert "in simple terms" in sections[0]["title"].lower()
    assert "how people would use it" in sections[3]["title"].lower()


def test_enrich_idea_dict_sets_plain_fields():
    class Opp:
        category = "Finance"
        title = "Finance: high-demand keywords with weak competition"
        description = "technical junk with trend signals"

    idea = enrich_idea_dict(
        {
            "title": "FinGap Desk — finance app opportunity tracker",
            "idea_type": "saas",
            "proposed_solution": "Find underserved money workflows from chart and keyword demand.",
            "target_audience": "Fintech founders",
            "monetization_strategy": "Team SaaS seats",
            "_pain_hint": "high keyword demand with weak incumbent execution",
        },
        Opp(),
    )
    assert "trend signals" not in idea["problem_statement"].lower()
    assert len(idea["proposed_solution"]) > 120
    assert "version 1" in idea["proposed_solution"].lower()
