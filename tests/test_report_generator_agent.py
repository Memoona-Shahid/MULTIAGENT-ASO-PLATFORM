from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.agents.report_generator_agent import ReportGeneratorAgent
from app.models.db_models import ProductIdea, ReportFormat, ReportType
from app.services.report_service import list_reports

T0 = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
T_START = datetime(2026, 1, 9, 12, 0, tzinfo=timezone.utc)


class FakeReportDataClient:
    def __init__(self, data=None):
        self.data = data or {}

    def fetch_trends(self, db, period_start, period_end, limit=200):
        return self.data.get("trends", [])

    def fetch_keywords(self, db, period_start, period_end, limit=200):
        return self.data.get("keywords", [])

    def fetch_competitors(self, db, period_start, period_end, limit=100):
        return self.data.get("competitors", [])

    def fetch_reviews(self, db, period_start, period_end, limit=300):
        return self.data.get("reviews", [])

    def fetch_opportunities(self, db, period_start, period_end, limit=100):
        return self.data.get("opportunities", [])

    def fetch_product_ideas(self, db, period_start, period_end, limit=100):
        return self.data.get("product_ideas", [])

    def fetch_latest_product_ideas(self, db, limit=20):
        return self.data.get("product_ideas", [])[:limit]

    def count_opportunities(self, db):
        return self.data.get("opportunity_count", 1)


def test_agent_generates_daily_markdown_report(db_session, tmp_path):
    fake_idea = ProductIdea(
        id=1,
        title="Finance SaaS dashboard for indie operators",
        idea_type="saas",
        problem_statement="Rising demand",
        proposed_solution="Build a SaaS workspace",
        target_audience="Solo founders",
        monetization_strategy="Monthly tiers",
        confidence_score=63.0,
        generated_at=T0,
    )
    idea_agent = MagicMock()
    idea_agent.run.return_value = {"total_ideas": 1, "opportunities": {"1": 1}, "skipped": {}}

    client = FakeReportDataClient({"product_ideas": [fake_idea]})
    agent = ReportGeneratorAgent(client=client, idea_agent=idea_agent)

    with patch("app.agents.report_generator_agent.datetime") as mock_dt:
        mock_dt.now.return_value = T0
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        summary = agent.run(
            db_session,
            report_type=ReportType.DAILY,
            report_format=ReportFormat.MARKDOWN,
            period_start=T_START,
            period_end=T0,
            output_dir=str(tmp_path),
            generate_ideas=True,
        )

    idea_agent.run.assert_called_once()
    reports = list_reports(db_session)
    assert summary["report_id"] is not None
    assert summary["ideas_in_report"] == 1
    assert summary["idea_generation"]["total_ideas"] == 1
    assert len(reports) == 1
    assert "Product ideas for you" in Path(summary["file_path"]).read_text(encoding="utf-8")


def test_agent_uses_weekly_period_by_default(db_session, tmp_path):
    idea_agent = MagicMock()
    idea_agent.run.return_value = {"total_ideas": 0, "opportunities": {}, "skipped": {}}
    agent = ReportGeneratorAgent(client=FakeReportDataClient(), idea_agent=idea_agent)

    with patch("app.agents.report_generator_agent.datetime") as mock_dt:
        mock_dt.now.return_value = T0
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        summary = agent.run(
            db_session,
            report_type=ReportType.WEEKLY,
            report_format=ReportFormat.HTML,
            output_dir=str(tmp_path),
        )

    assert summary["report_type"] == "weekly"
    assert "weekly_" in summary["file_path"]
    assert summary["period_start"].startswith("2026-01-03")
