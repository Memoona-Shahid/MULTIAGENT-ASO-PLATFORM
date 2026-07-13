from unittest.mock import MagicMock, patch

from app.models.db_models import ChartType
from app.services.app_store_client import AppleAppStoreClient


def _mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


def test_fetch_chart_parses_rss_feed():
    fake_feed = {
        "feed": {
            "results": [
                {
                    "id": "111",
                    "name": "App One",
                    "artistName": "Dev One",
                    "artworkUrl100": "http://icon1",
                    "url": "http://store/1",
                    "genres": [{"name": "Productivity"}],
                },
                {
                    "id": "222",
                    "name": "App Two",
                    "artistName": "Dev Two",
                    "artworkUrl100": "http://icon2",
                    "url": "http://store/2",
                    "genres": [],
                },
            ]
        }
    }

    client = AppleAppStoreClient(country="us")
    with patch.object(client, "_get", return_value=fake_feed) as mock_get:
        entries = client.fetch_chart(ChartType.TOP_FREE, limit=2)

    mock_get.assert_called_once()
    assert len(entries) == 2
    assert entries[0]["store_app_id"] == "111"
    assert entries[0]["rank"] == 1
    assert entries[0]["category"] == "Productivity"
    assert entries[1]["rank"] == 2
    assert entries[1]["category"] is None


def test_fetch_chart_rejects_fast_growing():
    client = AppleAppStoreClient()
    try:
        client.fetch_chart(ChartType.FAST_GROWING)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_fetch_app_details_maps_fields():
    fake_lookup = {
        "results": [
            {
                "trackId": 111,
                "trackName": "App One",
                "artistName": "Dev One",
                "primaryGenreName": "Productivity",
                "averageUserRating": 4.5,
                "userRatingCount": 1000,
                "price": 0.0,
                "artworkUrl100": "http://icon1",
                "trackViewUrl": "http://store/1",
            }
        ]
    }

    client = AppleAppStoreClient(country="us")
    with patch.object(client, "_get", return_value=fake_lookup) as mock_get:
        details = client.fetch_app_details(["111"])

    mock_get.assert_called_once()
    assert "111" in details
    assert details["111"]["rating"] == 4.5
    assert details["111"]["rating_count"] == 1000


def test_fetch_app_details_batches_large_lists():
    client = AppleAppStoreClient()
    ids = [str(i) for i in range(250)]  # forces 3 chunks at size 100

    with patch.object(client, "_get", return_value={"results": []}) as mock_get:
        client.fetch_app_details(ids)

    assert mock_get.call_count == 3


def test_fetch_app_details_dedupes_ids():
    client = AppleAppStoreClient()
    ids = ["111", "111", "222"]

    with patch.object(client, "_get", return_value={"results": []}) as mock_get:
        client.fetch_app_details(ids)

    called_params = mock_get.call_args.kwargs["params"]
    assert called_params["id"] == "111,222"
