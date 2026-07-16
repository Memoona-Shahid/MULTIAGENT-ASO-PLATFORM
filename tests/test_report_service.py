from datetime import datetime, timezone

from app.models.db_models import ReportFormat, ReportType
from app.services.report_service import list_reports, save_report

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_save_and_list_reports(db_session):
    save_report(
        db_session,
        {
            "report_type": ReportType.DAILY,
            "report_format": ReportFormat.MARKDOWN,
            "title": "Daily ASO Intelligence Report — 2026-01-01",
            "summary": "Test summary",
            "file_path": "./data/reports/daily_2026-01-01.md",
            "period_start": T0,
            "period_end": T0,
        },
        generated_at=T0,
    )
    save_report(
        db_session,
        {
            "report_type": ReportType.WEEKLY,
            "report_format": ReportFormat.HTML,
            "title": "Weekly ASO Intelligence Report — 2026-01-01",
            "summary": "Weekly summary",
            "file_path": "./data/reports/weekly_2026-01-01.html",
            "period_start": T0,
            "period_end": T0,
        },
        generated_at=T0,
    )

    daily = list_reports(db_session, report_type=ReportType.DAILY)
    html = list_reports(db_session, report_format=ReportFormat.HTML)
    assert len(daily) == 1
    assert daily[0].title.startswith("Daily")
    assert len(html) == 1
    assert html[0].report_format == ReportFormat.HTML
