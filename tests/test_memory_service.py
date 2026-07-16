from datetime import datetime, timezone

from app.services.memory_service import (
    get_memory_entry,
    list_memory_entries,
    prune_memory_entries,
    save_memory_entry,
    upsert_memory_entry,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _entry(entry_type="idea", key="idea:1", importance=0.8):
    return {
        "entry_type": entry_type,
        "key": key,
        "value": {"title": "Finance SaaS"},
        "tags": {"source_agent": "ai_idea_generator_agent"},
        "importance": importance,
    }


def test_save_and_list_memory_entries(db_session):
    save_memory_entry(db_session, _entry(), created_at=T0)

    rows = list_memory_entries(db_session, entry_type="idea")
    assert len(rows) == 1
    assert rows[0].key == "idea:1"
    assert rows[0].value["title"] == "Finance SaaS"


def test_upsert_memory_entry_updates_existing(db_session):
    upsert_memory_entry(db_session, _entry(), created_at=T0)
    upsert_memory_entry(
        db_session,
        {
            **_entry(),
            "value": {"title": "Updated Finance SaaS"},
            "importance": 0.95,
        },
        created_at=T0,
    )

    row = get_memory_entry(db_session, "idea", "idea:1")
    assert row is not None
    assert row.value["title"] == "Updated Finance SaaS"
    assert row.importance == 0.95
    assert len(list_memory_entries(db_session)) == 1


def test_list_memory_entries_filters_by_importance(db_session):
    save_memory_entry(db_session, _entry(key="idea:1", importance=0.9), created_at=T0)
    save_memory_entry(db_session, _entry(key="idea:2", importance=0.4), created_at=T0)

    high = list_memory_entries(db_session, min_importance=0.8)
    assert len(high) == 1
    assert high[0].key == "idea:1"


def test_prune_memory_entries(db_session):
    save_memory_entry(db_session, _entry(key="idea:1", importance=0.9), created_at=T0)
    save_memory_entry(db_session, _entry(key="idea:2", importance=0.2), created_at=T0)

    removed = prune_memory_entries(db_session, below_importance=0.5)
    assert removed == 1
    assert len(list_memory_entries(db_session)) == 1
