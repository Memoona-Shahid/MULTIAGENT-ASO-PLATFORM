from datetime import datetime, timedelta, timezone

from app.models.db_models import ChartType, Platform
from app.services.trending_app_service import (
    get_latest_snapshot,
    get_previous_snapshot,
    list_trending_apps,
    save_trending_apps,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = T0 + timedelta(days=1)


def _app(store_app_id, rank, name="App"):
    return {
        "platform": Platform.APP_STORE,
        "store_app_id": store_app_id,
        "name": name,
        "chart_type": ChartType.TOP_FREE,
        "rank": rank,
    }


def test_save_and_get_latest_snapshot(db_session):
    save_trending_apps(db_session, [_app("1", 1), _app("2", 2)], captured_at=T0)

    latest = get_latest_snapshot(db_session, Platform.APP_STORE, ChartType.TOP_FREE)
    assert len(latest) == 2
    assert latest[0].rank == 1
    assert latest[0].store_app_id == "1"


def test_get_latest_snapshot_returns_only_most_recent(db_session):
    save_trending_apps(db_session, [_app("1", 5)], captured_at=T0)
    save_trending_apps(db_session, [_app("1", 1)], captured_at=T1)

    latest = get_latest_snapshot(db_session, Platform.APP_STORE, ChartType.TOP_FREE)
    assert len(latest) == 1
    assert latest[0].rank == 1  # from T1, not T0


def test_get_previous_snapshot(db_session):
    save_trending_apps(db_session, [_app("1", 5)], captured_at=T0)
    save_trending_apps(db_session, [_app("1", 1)], captured_at=T1)

    previous = get_previous_snapshot(db_session, Platform.APP_STORE, ChartType.TOP_FREE, before=T1)
    assert len(previous) == 1
    assert previous[0].rank == 5  # from T0


def test_get_previous_snapshot_empty_when_no_history(db_session):
    save_trending_apps(db_session, [_app("1", 1)], captured_at=T0)

    previous = get_previous_snapshot(db_session, Platform.APP_STORE, ChartType.TOP_FREE, before=T0)
    assert previous == []


def test_list_trending_apps_filters(db_session):
    save_trending_apps(db_session, [
        {**_app("1", 1), "category": "Games"},
        {**_app("2", 2, name="B"), "chart_type": ChartType.TOP_PAID, "category": "Finance"},
    ], captured_at=T0)

    games_only = list_trending_apps(db_session, chart_type=ChartType.TOP_FREE)
    assert len(games_only) == 1
    assert games_only[0].category == "Games"

    all_apps = list_trending_apps(db_session)
    assert len(all_apps) == 2
