from app.models.db_models import Platform
from app.services.competitor_client import CompetitorSourceUnavailableError
from app.services.review_client import AppleReviewClient, GooglePlayReviewClient, ReviewSourceUnavailableError


class FakeCompetitorReviewClient:
    def __init__(self, reviews=None, error=None):
        self.reviews = reviews or []
        self.error = error

    def fetch_reviews(self, app_id, limit=50):
        if self.error:
            raise self.error
        return self.reviews[:limit]


def test_apple_review_client_sets_platform():
    client = AppleReviewClient(
        competitor_client=FakeCompetitorReviewClient([{"author": "A", "review_text": "Great"}])
    )

    reviews = client.fetch_reviews("123", limit=1)

    assert reviews[0]["platform"] == Platform.APP_STORE


def test_google_play_review_client_sets_platform():
    client = GooglePlayReviewClient(
        competitor_client=FakeCompetitorReviewClient([{"author": "G", "review_text": "Great"}])
    )

    reviews = client.fetch_reviews("com.example.app", limit=1)

    assert reviews[0]["platform"] == Platform.GOOGLE_PLAY


def test_review_client_translates_source_errors():
    client = AppleReviewClient(
        competitor_client=FakeCompetitorReviewClient(
            error=CompetitorSourceUnavailableError("store down")
        )
    )

    try:
        client.fetch_reviews("123")
        assert False, "expected ReviewSourceUnavailableError"
    except ReviewSourceUnavailableError:
        pass
