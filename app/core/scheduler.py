"""
APScheduler wiring for daily/weekly automated jobs (Requirement 7 & 8).

Actual job bodies (calling the Report Generator Agent etc.) land in Module 9.
This file just sets up the scheduler shell so later modules register jobs
against a single, already-tested scheduler instance.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logging import logger

scheduler = BackgroundScheduler(timezone="UTC")

_WEEKDAY_MAP = {
    "mon": "mon", "tue": "tue", "wed": "wed", "thu": "thu",
    "fri": "fri", "sat": "sat", "sun": "sun",
}


def register_daily_job(func, hour: int | None = None) -> None:
    trigger = CronTrigger(hour=hour if hour is not None else settings.daily_report_hour, minute=0)
    scheduler.add_job(func, trigger, id=f"daily_{func.__name__}", replace_existing=True)
    logger.info("Registered daily job '{}' at {}:00 UTC", func.__name__, trigger)


def register_weekly_job(func, day: str | None = None, hour: int | None = None) -> None:
    weekday = _WEEKDAY_MAP.get(day or settings.weekly_report_day, "mon")
    trigger = CronTrigger(day_of_week=weekday, hour=hour if hour is not None else settings.weekly_report_hour, minute=0)
    scheduler.add_job(func, trigger, id=f"weekly_{func.__name__}", replace_existing=True)
    logger.info("Registered weekly job '{}' on {} at {}:00 UTC", func.__name__, weekday, trigger)


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")
