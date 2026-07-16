from unittest.mock import MagicMock

from app.agents.coordinator_agent import CoordinatorAgent
from app.models.db_models import ReportFormat


def test_coordinator_runs_daily_pipeline(db_session):
    keyword_agent = MagicMock()
    keyword_agent.run.return_value = {"total_keywords": 12, "seeds": {}}

    competitor_agent = MagicMock()
    competitor_agent.run.return_value = {"total_competitors": 3, "total_reviews": 10}

    opportunity_agent = MagicMock()
    opportunity_agent.run.return_value = {"opportunities": 2}

    report_agent = MagicMock()
    report_agent.run.return_value = {
        "report_id": 9,
        "file_path": "data/reports/daily_2026-07-16.md",
        "ideas_in_report": 5,
        "idea_generation": {"total_ideas": 5, "opportunities": {"1": 1}, "skipped": {}},
    }

    memory_agent = MagicMock()
    memory_agent.run.return_value = {"total_entries": 10}

    agent = CoordinatorAgent(
        opportunity_agent=opportunity_agent,
        report_agent=report_agent,
        memory_agent=memory_agent,
        keyword_agent=keyword_agent,
        competitor_agent=competitor_agent,
    )

    summary = agent.run_daily_pipeline(
        db_session,
        opportunity_limit=5,
        ideas_per_opportunity=1,
        report_format=ReportFormat.MARKDOWN,
        research_keywords=True,
        analyze_competitors=True,
    )

    assert summary["success"] is True
    assert summary["report_id"] == 9
    assert summary["ideas_in_report"] == 5
    assert summary["total_ideas_generated"] == 5
    keyword_agent.run.assert_called_once()
    opportunity_agent.run.assert_called_once()
    report_agent.run.assert_called_once()
    memory_agent.run.assert_not_called()
