from datetime import datetime
from unittest.mock import patch

from app.models.db_models import Platform
from app.services.competitor_client import AppleCompetitorClient, GooglePlayCompetitorClient


def test_apple_fetch_details_maps_lookup_fields():
    fake_lookup = {
        "results": [
            {
                "trackId": 123,
                "trackName": "Competitor App",
                "artistName": "Example Dev",
                "primaryGenreName": "Productivity",
                "averageUserRating": 4.6,
                "userRatingCount": 1200,
                "price": 0.0,
                "formattedPrice": "Free",
                "currency": "USD",
                "inAppPurchases": ["Premium"],
                "screenshotUrls": ["screen1"],
                "ipadScreenshotUrls": ["screen2"],
                "features": ["iosUniversal"],
                "description": "- Habit tracking\n- AI summaries",
            }
        ]
    }
    client = AppleCompetitorClient(country="us")

    with patch.object(client, "_get_json", return_value=fake_lookup):
        details = client.fetch_details("123")

    assert details["platform"] == Platform.APP_STORE
    assert details["store_app_id"] == "123"
    assert details["pricing_model"] == "freemium"
    assert details["screenshots"] == ["screen1", "screen2"]
    assert "Habit tracking" in details["features"]


def test_apple_fetch_reviews_parses_reviews_rss():
    fake_reviews = {
        "feed": {
            "entry": [
                {"id": {"label": "app"}},
                {
                    "author": {"name": {"label": "Reviewer"}},
                    "im:rating": {"label": "4"},
                    "content": {"label": "Useful app"},
                    "updated": {"label": "2026-01-01T00:00:00Z"},
                },
            ]
        }
    }
    client = AppleCompetitorClient(country="us")

    with patch.object(client, "_get_json", return_value=fake_reviews):
        reviews = client.fetch_reviews("123", limit=5)

    assert len(reviews) == 1
    assert reviews[0]["platform"] == Platform.APP_STORE
    assert reviews[0]["author"] == "Reviewer"
    assert reviews[0]["rating"] == 4
    assert isinstance(reviews[0]["posted_at"], datetime)


class FakeGoogleScraper:
    def app_analyze(self, app_id, lang="en", country="us"):
        return {
            "appId": app_id,
            "title": "Google Competitor",
            "developer": "Google Dev",
            "genre": "Tools",
            "installs": "10,000+",
            "score": 4.2,
            "ratings": 900,
            "free": True,
            "offersIAP": True,
            "containsAds": True,
            "screenshots": ["screen"],
            "description": "- Sync tasks\n- Offline mode",
        }

    def reviews_analyze(self, app_id, count=20, lang="en", country="us"):
        return [{"userName": "G Reviewer", "score": 3, "text": "Needs work", "at": "2026-01-02T00:00:00Z"}]


def test_google_play_fetch_details_maps_scraper_fields():
    client = GooglePlayCompetitorClient(scraper=FakeGoogleScraper())

    details = client.fetch_details("com.example.app")

    assert details["platform"] == Platform.GOOGLE_PLAY
    assert details["store_app_id"] == "com.example.app"
    assert details["estimated_downloads"] == "10,000+"
    assert details["pricing_model"] == "freemium"
    assert "Sync tasks" in details["features"]


def test_google_play_fetch_reviews_maps_scraper_fields():
    client = GooglePlayCompetitorClient(scraper=FakeGoogleScraper())

    reviews = client.fetch_reviews("com.example.app", limit=1)

    assert len(reviews) == 1
    assert reviews[0]["platform"] == Platform.GOOGLE_PLAY
    assert reviews[0]["author"] == "G Reviewer"
    assert reviews[0]["rating"] == 3
