"""Tests for ZeroClaw runtime + CrewAI tool wiring (Modules 11–12)."""

from unittest.mock import MagicMock, patch

from app.core.agent_runtime import AgentTaskResult, OpenFangZeroClawRuntime
from app.models.db_models import ReportFormat


def test_zeroclaw_health_check_ok():
    runtime = OpenFangZeroClawRuntime(base_url="http://zeroclaw.test", api_key="tok")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}

    with patch("app.core.agent_runtime.httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.get.return_value = mock_response
        client_cls.return_value = client
        assert runtime.health_check() is True
        client.get.assert_called_once_with("http://zeroclaw.test/health")


def test_zeroclaw_health_check_missing_base_url():
    runtime = OpenFangZeroClawRuntime(base_url="", api_key="")
    assert runtime.health_check() is False


def test_zeroclaw_run_task_posts_to_api_chat():
    runtime = OpenFangZeroClawRuntime(base_url="http://zeroclaw.test", api_key="tok")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "acknowledged"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.core.agent_runtime.httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.post.return_value = mock_response
        client_cls.return_value = client

        result = runtime.run_task("coordinator", "daily_pipeline_start", {"started_at": "now"})

    assert isinstance(result, AgentTaskResult)
    assert result.success is True
    assert result.output == "acknowledged"
    assert client.post.call_args.args[0] == "http://zeroclaw.test/api/chat"
    headers = client.post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer tok"


def test_zeroclaw_run_task_falls_back_to_webhook():
    runtime = OpenFangZeroClawRuntime(base_url="http://zeroclaw.test", api_key="tok")

    not_found = MagicMock()
    not_found.status_code = 404

    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {"response": "from-webhook"}
    ok.raise_for_status = MagicMock()

    with patch("app.core.agent_runtime.httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.post.side_effect = [not_found, ok]
        client_cls.return_value = client

        result = runtime.run_task("aso_crew", "ping", {})

    assert result.success is True
    assert result.output == "from-webhook"
    assert client.post.call_args_list[1].args[0] == "http://zeroclaw.test/webhook"


def test_zeroclaw_run_task_without_base_url_returns_error():
    runtime = OpenFangZeroClawRuntime(base_url="", api_key="")
    result = runtime.run_task("x", "y", {})
    assert result.success is False
    assert "BASE_URL" in (result.error or "")


def test_build_aso_tools_names(db_session):
    from app.agents.crew.tools import build_aso_tools

    tools = build_aso_tools(db_session)
    names = {t.name for t in tools}
    assert "research_keywords" in names
    assert "generate_daily_report" in names
    assert "synthesize_market_opportunities" in names


def test_run_daily_crew_falls_back_without_llm(db_session):
    from app.agents.crew.aso_crew import run_daily_crew

    with patch("app.agents.crew.aso_crew.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        mock_settings.anthropic_api_key = ""
        mock_settings.orchestration_mode = "crewai"

        with patch("app.agents.coordinator_agent.CoordinatorAgent") as coord_cls:
            instance = MagicMock()
            instance.run_daily_pipeline.return_value = {
                "pipeline": "daily_intelligence",
                "success": True,
                "report_id": 1,
            }
            coord_cls.return_value = instance

            # Import path used inside run_daily_crew
            with patch("app.agents.coordinator_agent.CoordinatorAgent", coord_cls):
                summary = run_daily_crew(
                    db_session,
                    report_format=ReportFormat.MARKDOWN,
                    research_keywords=False,
                    analyze_competitors=False,
                    synthesize_opportunities=False,
                )

    assert summary["success"] is True
    assert summary["report_id"] == 1
    instance.run_daily_pipeline.assert_called_once()
    assert instance.run_daily_pipeline.call_args.kwargs.get("use_crewai") is False


def test_coordinator_can_force_direct_mode(db_session):
    from app.agents.coordinator_agent import CoordinatorAgent

    keyword_agent = MagicMock()
    keyword_agent.run.return_value = {"total_keywords": 0, "seeds": {}}
    competitor_agent = MagicMock()
    competitor_agent.run.return_value = {"total_competitors": 0}
    opportunity_agent = MagicMock()
    opportunity_agent.run.return_value = {"opportunities": 0}
    report_agent = MagicMock()
    report_agent.run.return_value = {
        "report_id": 3,
        "file_path": "data/reports/daily.md",
        "ideas_in_report": 0,
        "idea_generation": {"total_ideas": 0},
    }

    agent = CoordinatorAgent(
        opportunity_agent=opportunity_agent,
        report_agent=report_agent,
        keyword_agent=keyword_agent,
        competitor_agent=competitor_agent,
    )
    summary = agent.run_daily_pipeline(
        db_session,
        use_crewai=False,
        research_keywords=False,
        analyze_competitors=False,
    )
    assert summary["report_id"] == 3
    report_agent.run.assert_called_once()
