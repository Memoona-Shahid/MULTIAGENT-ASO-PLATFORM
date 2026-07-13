"""
Reusable retry decorator for network calls, scraping, and external API calls
that may fail transiently (rate limits, timeouts, flaky endpoints).

Usage:
    from app.utils.retry import with_retry

    @with_retry()
    def fetch_something():
        ...

    @with_retry(max_attempts=5)
    async def fetch_something_async():
        ...
"""

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import logging

from app.core.config import settings
from app.core.logging import logger

# tenacity's before_sleep_log wants a stdlib logger; loguru intercepts stdlib
# logging globally in this project so this still routes through our sinks.
_std_logger = logging.getLogger("retry")


def with_retry(
    max_attempts: int | None = None,
    min_wait: int = 1,
    max_wait: int = 10,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Decorator factory: exponential backoff retry for flaky I/O calls.

    Args:
        max_attempts: overrides settings.max_retries if provided.
        min_wait / max_wait: bounds (seconds) for exponential backoff.
        exceptions: exception types that should trigger a retry.
    """
    attempts = max_attempts or settings.max_retries

    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=settings.retry_backoff_seconds, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(_std_logger, logging.WARNING),
        reraise=True,
    )
