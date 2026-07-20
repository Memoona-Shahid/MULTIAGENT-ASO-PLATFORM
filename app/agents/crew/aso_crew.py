"""
CrewAI orchestration for the daily ASO intelligence pipeline (Module 12).

Builds a sequential Crew whose agents each own one domain tool. The LLM
decides phrasing/confirmation; the heavy lifting stays in the plain-Python
agents behind the tools (Modules 2–10).

When no LLM API key is configured, `run_daily_crew` falls back to
CoordinatorAgent so local/dev still works without OpenAI/Anthropic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.crew.tools import build_aso_tools
from app.core.agent_runtime import agent_runtime
from app.core.config import settings
from app.core.logging import logger
from app.models.db_models import ReportFormat


def _llm_configured() -> bool:
    return bool(settings.openai_api_key or settings.anthropic_api_key)


def _build_llm():
    """Construct a CrewAI LLM from settings. Prefer OpenAI, else Anthropic."""
    from crewai import LLM

    if settings.openai_api_key:
        return LLM(model=settings.llm_model, api_key=settings.openai_api_key)
    if settings.anthropic_api_key:
        model = settings.llm_model
        if not model.startswith("anthropic/") and "claude" in model:
            model = f"anthropic/{model}"
        elif not model.startswith("anthropic/"):
            model = "anthropic/claude-3-5-haiku-latest"
        return LLM(model=model, api_key=settings.anthropic_api_key)
    raise RuntimeError("No LLM API key configured for CrewAI")


def build_daily_crew(
    db: Session,
    *,
    research_trends: bool = True,
    research_keywords: bool = True,
    analyze_competitors: bool = True,
    synthesize_opportunities: bool = True,
    consolidate_memory: bool = False,
    opportunity_limit: int = 10,
    ideas_per_opportunity: int = 1,
    report_format: str = "markdown",
):
    """Assemble (but do not run) the daily intelligence Crew."""
    from crewai import Agent, Crew, Process, Task

    tools = {t.name: t for t in build_aso_tools(db)}
    llm = _build_llm()

    def agent(role: str, goal: str, tool_name: str, backstory: str) -> Agent:
        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=[tools[tool_name]],
            llm=llm,
            verbose=settings.debug,
            allow_delegation=False,
        )

    tasks: list = []
    agents: list = []

    if research_trends:
        apple = agent(
            "App Store Research Analyst",
            "Capture current Apple App Store chart movers.",
            "research_app_store_trends",
            "You specialize in Apple App Store chart intelligence for ASO.",
        )
        play = agent(
            "Google Play Research Analyst",
            "Capture current Google Play chart movers.",
            "research_google_play_trends",
            "You specialize in Google Play chart intelligence for ASO.",
        )
        agents.extend([apple, play])
        tasks.append(
            Task(
                description="Call research_app_store_trends exactly once and return its JSON result.",
                expected_output="JSON summary of App Store trending snapshot.",
                agent=apple,
            )
        )
        tasks.append(
            Task(
                description="Call research_google_play_trends exactly once and return its JSON result.",
                expected_output="JSON summary of Google Play trending snapshot.",
                agent=play,
            )
        )

    if research_keywords:
        kw = agent(
            "Keyword Research Specialist",
            "Expand trend-derived seeds into high-opportunity keywords.",
            "research_keywords",
            "You find high-volume, lower-competition app store keywords.",
        )
        agents.append(kw)
        tasks.append(
            Task(
                description=(
                    "Call research_keywords with suggestions_per_seed=6 and seed_limit=10. "
                    "Return the tool JSON."
                ),
                expected_output="JSON keyword research summary including seeds.",
                agent=kw,
            )
        )

    if analyze_competitors:
        comp = agent(
            "Competitor Intelligence Analyst",
            "Profile top competitors from trending charts.",
            "analyze_competitors",
            "You analyze competitor apps, monetization, and review themes.",
        )
        agents.append(comp)
        tasks.append(
            Task(
                description=(
                    "Call analyze_competitors with competitor_limit=6 and reviews_per_app=8. "
                    "Return the tool JSON."
                ),
                expected_output="JSON competitor analysis summary.",
                agent=comp,
            )
        )

    if synthesize_opportunities:
        opp = agent(
            "Market Opportunity Strategist",
            "Synthesize market gaps from store signals.",
            "synthesize_market_opportunities",
            "You turn ASO signals into ranked market opportunities.",
        )
        agents.append(opp)
        tasks.append(
            Task(
                description=(
                    "Call synthesize_market_opportunities with min_score=10 and "
                    "min_keyword_opportunity=40. Return the tool JSON."
                ),
                expected_output="JSON opportunity synthesis summary.",
                agent=opp,
            )
        )

    report = agent(
        "ASO Report Writer",
        "Produce today's product ideas and daily intelligence report.",
        "generate_daily_report",
        "You turn opportunities into concrete product ideas and a readable daily report.",
    )
    agents.append(report)
    tasks.append(
        Task(
            description=(
                f"Call generate_daily_report with opportunity_limit={opportunity_limit}, "
                f"ideas_per_opportunity={ideas_per_opportunity}, report_format='{report_format}'. "
                "Return the tool JSON."
            ),
            expected_output="JSON report generation summary with report_id and file_path.",
            agent=report,
        )
    )

    if consolidate_memory:
        mem = agent(
            "Memory Curator",
            "Consolidate today's intelligence into long-term memory.",
            "consolidate_memory",
            "You store durable ASO insights for future recall.",
        )
        agents.append(mem)
        tasks.append(
            Task(
                description="Call consolidate_memory with lookback_days=1. Return the tool JSON.",
                expected_output="JSON memory consolidation summary.",
                agent=mem,
            )
        )

    return Crew(agents=agents, tasks=tasks, process=Process.sequential, verbose=settings.debug)


def run_daily_crew(
    db: Session,
    *,
    research_trends: bool = False,
    research_keywords: bool = True,
    analyze_competitors: bool = True,
    synthesize_opportunities: bool = True,
    consolidate_memory: bool = False,
    opportunity_limit: int = 10,
    ideas_per_opportunity: int = 1,
    report_format: ReportFormat | str = ReportFormat.MARKDOWN,
) -> dict:
    """
    Run the CrewAI daily pipeline, or fall back to CoordinatorAgent when no LLM
    key is available (so CI/local still work).
    """
    fmt = report_format.value if isinstance(report_format, ReportFormat) else str(report_format)

    if not _llm_configured():
        logger.info("No LLM key — falling back to CoordinatorAgent (direct orchestration)")
        from app.agents.coordinator_agent import CoordinatorAgent

        return CoordinatorAgent().run_daily_pipeline(
            db,
            synthesize_opportunities=synthesize_opportunities,
            research_keywords=research_keywords,
            analyze_competitors=analyze_competitors,
            opportunity_limit=opportunity_limit,
            ideas_per_opportunity=ideas_per_opportunity,
            report_format=ReportFormat(fmt) if fmt in {e.value for e in ReportFormat} else ReportFormat.MARKDOWN,
            consolidate_memory=consolidate_memory,
            use_crewai=False,
        )

    started_at = datetime.now(timezone.utc)
    agent_runtime.run_task(
        "aso_crew",
        "daily_pipeline_start",
        {"started_at": started_at.isoformat(), "mode": "crewai"},
    )

    crew = build_daily_crew(
        db,
        research_trends=research_trends,
        research_keywords=research_keywords,
        analyze_competitors=analyze_competitors,
        synthesize_opportunities=synthesize_opportunities,
        consolidate_memory=consolidate_memory,
        opportunity_limit=opportunity_limit,
        ideas_per_opportunity=ideas_per_opportunity,
        report_format=fmt,
    )
    raw = crew.kickoff()
    finished_at = datetime.now(timezone.utc)

    summary: dict[str, Any] = {
        "pipeline": "daily_intelligence_crewai",
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "success": True,
        "crew_output": str(raw),
        "report_id": None,
        "file_path": None,
        "ideas_in_report": 0,
        "total_ideas_generated": 0,
    }

    # Best-effort parse of the final task JSON if the report tool returned it.
    try:
        import json

        text = str(raw)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                summary["report_id"] = parsed.get("report_id")
                summary["file_path"] = parsed.get("file_path")
                summary["ideas_in_report"] = parsed.get("ideas_in_report", 0)
                idea_gen = parsed.get("idea_generation") or {}
                summary["total_ideas_generated"] = idea_gen.get("total_ideas", 0)
                summary["steps"] = {"report": parsed}
    except Exception:  # noqa: BLE001
        pass

    agent_runtime.run_task(
        "aso_crew",
        "daily_pipeline_finish",
        {"success": summary["success"], "report_id": summary["report_id"]},
    )
    logger.info("CrewAI daily pipeline complete: report_id={}", summary.get("report_id"))
    return summary
