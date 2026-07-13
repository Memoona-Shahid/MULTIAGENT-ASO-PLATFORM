"""
AgentRuntime abstraction layer.

WHY THIS EXISTS
----------------
The project brief specifies "OpenFang/ZeroClaw" as the agent runtime. That's
not a runtime I can find any public documentation for, so instead of
guessing at an API and baking that guess into every agent, every agent in
this codebase talks to an `AgentRuntime` interface instead of a concrete
SDK. Two things follow from that:

  1. Every module (2-10) can be built and fully tested right now using
     `MockAgentRuntime`, which runs CrewAI agents locally with whatever LLM
     key you put in .env (OpenAI/Anthropic/etc).
  2. When you get OpenFang/ZeroClaw docs (Module 11), we implement
     `OpenFangZeroClawRuntime` below to satisfy this same interface and
     flip `AGENT_RUNTIME=openfang_zeroclaw` in .env. Nothing else in the
     codebase changes.

This is exactly the same pattern used for EmailProviderClient in your
Customer Support Automation Platform project.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import logger


@dataclass
class AgentTaskResult:
    """Normalized result returned by any runtime after running an agent task."""
    agent_name: str
    task_name: str
    output: Any
    success: bool = True
    error: Optional[str] = None
    raw: dict = field(default_factory=dict)


class AgentRuntime(ABC):
    """Abstract interface every agent runtime backend must implement."""

    @abstractmethod
    def run_task(self, agent_name: str, task_name: str, inputs: dict) -> AgentTaskResult:
        """Execute a single named task for a named agent and return its result."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the runtime backend is reachable/configured correctly."""
        raise NotImplementedError


class MockAgentRuntime(AgentRuntime):
    """
    Local runtime used for development, testing, and CrewAI-only execution.

    This does NOT call CrewAI itself — it's a thin passthrough runtime that
    agents can use directly, or agents can call CrewAI Crews themselves and
    just use this runtime for logging/telemetry consistency. It always
    "succeeds" with an empty output unless a caller-supplied inputs["fn"] is
    given (used heavily in unit tests to stub behavior without a live LLM).
    """

    def run_task(self, agent_name: str, task_name: str, inputs: dict) -> AgentTaskResult:
        logger.debug("MockAgentRuntime running {}::{} inputs={}", agent_name, task_name, inputs)

        fn = inputs.get("fn")
        if callable(fn):
            try:
                result = fn(**{k: v for k, v in inputs.items() if k != "fn"})
                return AgentTaskResult(agent_name=agent_name, task_name=task_name, output=result)
            except Exception as exc:  # noqa: BLE001
                logger.exception("MockAgentRuntime task {}::{} failed", agent_name, task_name)
                return AgentTaskResult(
                    agent_name=agent_name, task_name=task_name, output=None,
                    success=False, error=str(exc),
                )

        return AgentTaskResult(agent_name=agent_name, task_name=task_name, output={})

    def health_check(self) -> bool:
        return True


class OpenFangZeroClawRuntime(AgentRuntime):
    """
    PLACEHOLDER — not implemented.

    OpenFang/ZeroClaw isn't a runtime I have documentation for. Rather than
    fabricate an API and give you code that silently does the wrong thing,
    this raises clearly until it's implemented. See the ChatGPT prompt for
    Module 11 to get the real spec, then fill in run_task()/health_check()
    to match its actual API (likely: auth, submit task, poll/stream result).
    """

    def __init__(self):
        if not settings.openfang_zeroclaw_base_url:
            logger.warning(
                "AGENT_RUNTIME=openfang_zeroclaw but OPENFANG_ZEROCLAW_BASE_URL is not set."
            )

    def run_task(self, agent_name: str, task_name: str, inputs: dict) -> AgentTaskResult:
        raise NotImplementedError(
            "OpenFangZeroClawRuntime is a placeholder. Implement this once you have "
            "the OpenFang/ZeroClaw SDK/API docs (see Module 11)."
        )

    def health_check(self) -> bool:
        return False


def get_agent_runtime() -> AgentRuntime:
    """Factory: returns the configured runtime backend based on settings.agent_runtime."""
    if settings.agent_runtime == "openfang_zeroclaw":
        return OpenFangZeroClawRuntime()
    return MockAgentRuntime()


# Module-level singleton, mirrors the pattern used for `settings`.
agent_runtime: AgentRuntime = get_agent_runtime()
