from unittest.mock import MagicMock

from app.agents.app_store_research_agent import AppStoreResearchAgent
from app.models.db_models import ChartType, Platform
from app.services.trending_app_service import list_trending_apps


def _make_agent(chart_entries, details):
    """Build an agent with a fully mocked AppleAppStoreClient."""
    client = MagicMock()
    client.fetch_chart.return_value = chart_entries
    client.fetch_app_details.return_value = details
    return AppStoreResearchAgent(client=client)


def test_run_saves_single_chart(db_session):
    entries = [
        {"store_app_id": "1", "name": "App One", "developer": "Dev", "category": "Games", "icon_url": "i1", "store_url": "u1", "rank": 1},
        {"store_app_id": "2", "name": "App Two", "developer": "Dev", "category": "Games", "icon_url": "i2", "store_url": "u2", "rank": 2},
    ]
    details = {
        "1": {"rating": 4.8, "rating_count": 500, "price": 0.0, "category": "Games"},
        "2": {"rating": 4.2, "rating_count": 300, "price": 0.0, "category": "Games"},
    }
    agent = _make_agent(entries, details)

    summary = agent.run(db_session, chart_types=[ChartType.TOP_FREE], limit=2)

    assert summary["charts"]["top_free"] == 2
    saved = list_trending_apps(db_session, platform=Platform.APP_STORE, chart_type=ChartType.TOP_FREE)
    assert len(saved) == 2
    assert saved[0].rating in (4.8, 4.2)  # order depends on captured_at/rank sort


def test_run_no_fast_growing_on_first_snapshot(db_session):
    entries = [{"store_app_id": "1", "name": "App One", "rank": 1}]
    agent = _make_agent(entries, {})

    summary = agent.run(db_session, chart_types=[ChartType.TOP_FREE], limit=1)

    assert summary["fast_growing"] == 0


def test_run_detects_fast_growing_climber(db_session):
    # First run: app "1" at rank 50
    agent1 = _make_agent(
        [{"store_app_id": "1", "name": "App One", "rank": 50}], {}
    )
    agent1.run(db_session, chart_types=[ChartType.TOP_FREE], limit=100)

    # Second run: app "1" jumped to rank 5 (delta = 45, above default threshold of 10)
    agent2 = _make_agent(
        [{"store_app_id": "1", "name": "App One", "rank": 5}], {}
    )
    summary = agent2.run(db_session, chart_types=[ChartType.TOP_FREE], limit=100)

    assert summary["fast_growing"] == 1
    fast_growing_rows = list_trending_apps(
        db_session, platform=Platform.APP_STORE, chart_type=ChartType.FAST_GROWING
    )
    assert len(fast_growing_rows) == 1
    assert fast_growing_rows[0].store_app_id == "1"
    assert fast_growing_rows[0].raw_metadata["rank_delta"] == 45
    assert fast_growing_rows[0].raw_metadata["previous_rank"] == 50


def test_run_no_fast_growing_for_small_movement(db_session):
    agent1 = _make_agent([{"store_app_id": "1", "name": "App One", "rank": 10}], {})
    agent1.run(db_session, chart_types=[ChartType.TOP_FREE], limit=100)

    # Moved only 3 ranks — below default threshold of 10
    agent2 = _make_agent([{"store_app_id": "1", "name": "App One", "rank": 7}], {})
    summary = agent2.run(db_session, chart_types=[ChartType.TOP_FREE], limit=100)

    assert summary["fast_growing"] == 0


def test_run_treats_new_entrant_as_fast_growing(db_session):
    agent1 = _make_agent([{"store_app_id": "1", "name": "App One", "rank": 1}], {})
    agent1.run(db_session, chart_types=[ChartType.TOP_FREE], limit=100)

    # App "2" is brand new to the chart on the second run
    agent2 = _make_agent(
        [
            {"store_app_id": "1", "name": "App One", "rank": 2},
            {"store_app_id": "2", "name": "App Two", "rank": 3},
        ],
        {},
    )
    summary = agent2.run(db_session, chart_types=[ChartType.TOP_FREE], limit=100)

    assert summary["fast_growing"] == 1
    fast_growing_rows = list_trending_apps(
        db_session, platform=Platform.APP_STORE, chart_type=ChartType.FAST_GROWING
    )
    assert fast_growing_rows[0].store_app_id == "2"
    assert fast_growing_rows[0].raw_metadata["previous_rank"] is None


def test_run_handles_empty_chart_gracefully(db_session):
    agent = _make_agent([], {})
    summary = agent.run(db_session, chart_types=[ChartType.TOP_FREE], limit=100)
    assert summary["charts"]["top_free"] == 0
    assert summary["fast_growing"] == 0
