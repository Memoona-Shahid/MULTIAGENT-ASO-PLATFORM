"""
AgentRuntime abstraction layer.

WHY THIS EXISTS
----------------
The project brief specifies "OpenFang/ZeroClaw" as the agent runtime. Every
agent talks to an `AgentRuntime` interface instead of a concrete SDK:

  1. Modules 2–10 / 12–14 work with `MockAgentRuntime` (AGENT_RUNTIME=mock).
  2. Module 11 implements `OpenFangZeroClawRuntime` against the ZeroClaw
     HTTP gateway (https://zeroclaw.net / zeroclaw-labs). Flip
     AGENT_RUNTIME=openfang_zeroclaw once a gateway is running.

"OpenFang" in the brief maps to OpenClaw's lineage; ZeroClaw is the
lightweight Rust runtime that exposes /health, /webhook, and /api/chat.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

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


def _json_safe(value: Any) -> Any:
    """Drop callables / non-JSON values so payloads can be sent to ZeroClaw."""
    if callable(value):
        return "<callable>"
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


class OpenFangZeroClawRuntime(AgentRuntime):
    """
    ZeroClaw HTTP gateway client (OpenClaw-compatible lineage).

    Expects a running `zeroclaw gateway` (default http://127.0.0.1:42617) with:
      GET  /health
      POST /api/chat   — agent loop with tools (preferred)
      POST /webhook    — simple chat fallback

    Auth: Authorization: Bearer <OPENFANG_ZEROCLAW_API_KEY> when set.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ):
        resolved_base_url = base_url if base_url is not None else settings.openfang_zeroclaw_base_url
        self.base_url = (resolved_base_url or "").rstrip("/")
        self.api_key = api_key if api_key is not None else settings.openfang_zeroclaw_api_key
        self.timeout = timeout if timeout is not None else max(settings.request_timeout_seconds, 60)
        if not self.base_url:
            logger.warning(
                "AGENT_RUNTIME=openfang_zeroclaw but OPENFANG_ZEROCLAW_BASE_URL is not set."
            )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def health_check(self) -> bool:
        if not self.base_url:
            return False
        try:
            with httpx.Client(timeout=min(self.timeout, 10), follow_redirects=True) as client:
                response = client.get(f"{self.base_url}/health")
            if response.status_code != 200:
                return False
            data = response.json()
            status = str(data.get("status", "")).lower()
            return status in {"ok", "healthy", "up", "ready"} or data.get("ok") is True
        except Exception as exc:  # noqa: BLE001
            logger.warning("ZeroClaw health_check failed: {}", exc)
            return False

    def run_task(self, agent_name: str, task_name: str, inputs: dict) -> AgentTaskResult:
        if not self.base_url:
            return AgentTaskResult(
                agent_name=agent_name,
                task_name=task_name,
                output=None,
                success=False,
                error="OPENFANG_ZEROCLAW_BASE_URL is not configured",
            )

        payload_inputs = _json_safe({k: v for k, v in inputs.items() if k != "fn"})
        message = (
            f"ASO platform task.\n"
            f"agent: {agent_name}\n"
            f"task: {task_name}\n"
            f"inputs_json: {json.dumps(payload_inputs, ensure_ascii=False)}\n"
            "Acknowledge the task and summarize what should happen next."
        )

        try:
            raw, output = self._post_chat(message, agent_name=agent_name, task_name=task_name)
            return AgentTaskResult(
                agent_name=agent_name,
                task_name=task_name,
                output=output,
                success=True,
                raw=raw if isinstance(raw, dict) else {"response": raw},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("ZeroClaw run_task {}::{} failed", agent_name, task_name)
            return AgentTaskResult(
                agent_name=agent_name,
                task_name=task_name,
                output=None,
                success=False,
                error=str(exc),
            )

    def _post_chat(self, message: str, *, agent_name: str, task_name: str) -> tuple[Any, Any]:
        body = {
            "message": message,
            "session_id": f"aso:{agent_name}:{task_name}",
            "context": [
                {"role": "system", "content": "You are the runtime for an ASO multi-agent platform."}
            ],
        }
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            # Prefer the tool-capable chat endpoint; fall back to simple webhook.
            response = client.post(
                f"{self.base_url}/api/chat",
                headers=self._headers(),
                json=body,
            )
            if response.status_code in {404, 405}:
                response = client.post(
                    f"{self.base_url}/webhook",
                    headers=self._headers(),
                    json={"message": message},
                )
            response.raise_for_status()
            data = response.json()

        if isinstance(data, dict):
            output = data.get("response") or data.get("full_response") or data.get("output") or data
            return data, output
        return data, data


def get_agent_runtime() -> AgentRuntime:
    """Factory: returns the configured runtime backend based on settings.agent_runtime."""
    if settings.agent_runtime == "openfang_zeroclaw":
        return OpenFangZeroClawRuntime()
    return MockAgentRuntime()


# Module-level singleton, mirrors the pattern used for `settings`.
agent_runtime: AgentRuntime = get_agent_runtime()
