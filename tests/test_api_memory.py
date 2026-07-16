from unittest.mock import patch

from datetime import datetime


def test_memory_endpoint_empty_when_no_data(client):
    with patch("app.services.memory_service.list_memory_entries", return_value=[]):
        response = client.get("/api/memory")
    assert response.status_code == 200
    assert response.json() == []


def test_consolidate_memory_endpoint_triggers_agent(client):
    fake_summary = {
        "consolidated_at": "2026-01-01T00:00:00+00:00",
        "lookback_days": 7,
        "consolidated": {"idea": 3, "trend": 10},
        "skipped": {},
        "pruned": 0,
        "total_entries": 13,
        "sources": {"product_ideas": 3, "trends": 10},
    }

    with patch("app.api.memory.MemoryAgent") as MockAgent:
        MockAgent.return_value.run.return_value = fake_summary
        response = client.post(
            "/api/memory/consolidate",
            json={"lookback_days": 7, "per_source_limit": 200, "min_importance": 0.5},
        )

    assert response.status_code == 200
    assert response.json() == fake_summary


def test_write_memory_endpoint(client):
    from types import SimpleNamespace

    fake_row = SimpleNamespace(
        id=1,
        entry_type="note",
        key="manual:1",
        value={"text": "test"},
        tags=None,
        importance=1.0,
        created_at=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
    )

    with patch("app.api.memory.MemoryAgent") as MockAgent, patch(
        "app.api.memory.get_memory_entry", return_value=fake_row
    ):
        MockAgent.return_value.write_entry.return_value = {"key": "manual:1"}
        response = client.post(
            "/api/memory",
            json={
                "entry_type": "note",
                "key": "manual:1",
                "value": {"text": "test"},
                "importance": 1.0,
            },
        )

    assert response.status_code == 200
    assert response.json()["key"] == "manual:1"
