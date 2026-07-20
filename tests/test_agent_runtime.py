import pytest

from app.core.agent_runtime import AgentTaskResult, MockAgentRuntime, OpenFangZeroClawRuntime


def test_mock_runtime_health_check():
    runtime = MockAgentRuntime()
    assert runtime.health_check() is True


def test_mock_runtime_run_task_without_fn():
    runtime = MockAgentRuntime()
    result = runtime.run_task("KeywordAgent", "research_keywords", {"seed": "fitness"})
    assert isinstance(result, AgentTaskResult)
    assert result.success is True
    assert result.output == {}


def test_mock_runtime_run_task_with_fn():
    runtime = MockAgentRuntime()

    def fake_logic(seed: str):
        return {"keywords": [f"{seed} tracker", f"{seed} app"]}

    result = runtime.run_task("KeywordAgent", "research_keywords", {"fn": fake_logic, "seed": "fitness"})
    assert result.success is True
    assert result.output["keywords"] == ["fitness tracker", "fitness app"]


def test_mock_runtime_run_task_with_failing_fn():
    runtime = MockAgentRuntime()

    def boom(**kwargs):
        raise ValueError("simulated failure")

    result = runtime.run_task("KeywordAgent", "research_keywords", {"fn": boom})
    assert result.success is False
    assert "simulated failure" in result.error


def test_openfang_zeroclaw_runtime_unconfigured_is_unhealthy():
    runtime = OpenFangZeroClawRuntime(base_url="", api_key="")
    assert runtime.health_check() is False
    result = runtime.run_task("Coordinator", "dispatch", {})
    assert result.success is False
    assert "BASE_URL" in (result.error or "")
