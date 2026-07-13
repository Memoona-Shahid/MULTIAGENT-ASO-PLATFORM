"""
Centralized logging configuration using loguru.

Import `logger` anywhere in the codebase:
    from app.core.logging import logger
    logger.info("Something happened")

Logs go to:
  - stdout (colored, human-readable) at LOG_LEVEL
  - logs/app.log (rotating, plain text) at DEBUG level, always
  - logs/errors.log (rotating) for ERROR and above only
"""

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def configure_logging() -> None:
    logger.remove()  # remove default handler

    # Console
    logger.add(
        sys.stdout,
        level=settings.log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
            "- <level>{message}</level>"
        ),
    )

    # Full rotating file log
    logger.add(
        LOG_DIR / "app.log",
        level="DEBUG",
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    # Errors-only file log (easy to scan for problems)
    logger.add(
        LOG_DIR / "errors.log",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )


configure_logging()

__all__ = ["logger"]
