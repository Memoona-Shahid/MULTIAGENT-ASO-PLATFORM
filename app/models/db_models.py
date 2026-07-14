"""
ORM models (SQLAlchemy 2.0 style) for every entity the platform tracks.

These map directly to the Core Requirements in the project brief:
  1-2. Trending apps (App Store + Google Play)      -> TrendingApp
  3.   Keyword research                              -> Keyword
  4.   Competitor analysis                           -> Competitor
  5.   Review intelligence                           -> Review
  6.   AI-generated product ideas                    -> ProductIdea
  7-8. Daily / weekly reports                        -> Report
  9.   Long-term memory of trends/competitors/reports -> MemoryEntry
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Platform(str, PyEnum):
    APP_STORE = "app_store"
    GOOGLE_PLAY = "google_play"


class ChartType(str, PyEnum):
    TOP_FREE = "top_free"
    TOP_PAID = "top_paid"
    TOP_GROSSING = "top_grossing"
    FAST_GROWING = "fast_growing"


class ReportType(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"


class ReportFormat(str, PyEnum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    HTML = "html"


class TrendingApp(Base):
    """An app observed on a store chart (Requirement 1 & 2)."""

    __tablename__ = "trending_apps"
    __table_args__ = (
        UniqueConstraint("platform", "store_app_id", "chart_type", "captured_at",
                          name="uq_trending_app_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False, index=True)
    store_app_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    developer: Mapped[str] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    chart_type: Mapped[ChartType] = mapped_column(Enum(ChartType), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=True)
    icon_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    store_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Keyword(Base):
    """A researched ASO keyword (Requirement 3).

    Deliberately has no uniqueness constraint on (term, platform,
    captured_at): unlike TrendingApp's chart snapshots (one fixed rank slot
    per app per capture), the same keyword term can legitimately surface
    from multiple different seed terms within a single research run — each
    row's `related_apps` records which seed produced it.
    """

    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    search_volume: Mapped[float] = mapped_column(Float, nullable=True)
    difficulty_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-100, higher = more competitive
    opportunity_score: Mapped[float] = mapped_column(Float, nullable=True)  # derived: volume vs difficulty
    related_apps: Mapped[dict] = mapped_column(JSON, nullable=True)  # list of app ids ranking for this term
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Competitor(Base):
    """A competitor app being tracked in depth (Requirement 4)."""

    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    store_app_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    developer: Mapped[str] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=True)
    estimated_downloads: Mapped[str] = mapped_column(String(100), nullable=True)  # store-reported range/string
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=True)
    pricing_model: Mapped[str] = mapped_column(String(100), nullable=True)  # free/paid/freemium/subscription
    monetization_details: Mapped[dict] = mapped_column(JSON, nullable=True)
    screenshots: Mapped[dict] = mapped_column(JSON, nullable=True)  # list of URLs
    features: Mapped[dict] = mapped_column(JSON, nullable=True)  # extracted feature list
    last_analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    reviews: Mapped[list["Review"]] = relationship(back_populates="competitor")


class Review(Base):
    """A user review pulled for sentiment/bug/feature analysis (Requirement 5)."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), nullable=False, index=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=True)
    review_text: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str] = mapped_column(String(50), nullable=True)  # positive/neutral/negative
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)  # -1..1
    mentions_bug: Mapped[bool] = mapped_column(default=False)
    mentions_feature_request: Mapped[bool] = mapped_column(default=False)
    extracted_topics: Mapped[dict] = mapped_column(JSON, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    competitor: Mapped["Competitor"] = relationship(back_populates="reviews")


class MarketOpportunity(Base):
    """A gap/opportunity synthesized from trends + keywords + competitor + review data (Req. 6-part-of)."""

    __tablename__ = "market_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    supporting_evidence: Mapped[dict] = mapped_column(JSON, nullable=True)  # keyword ids, competitor ids, review ids
    opportunity_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-100
    identified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ProductIdea(Base):
    """An AI-generated app/SaaS/AI product idea (Requirement 6)."""

    __tablename__ = "product_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    idea_type: Mapped[str] = mapped_column(String(50), nullable=True)  # mobile_app / saas / ai_product
    problem_statement: Mapped[str] = mapped_column(Text, nullable=True)
    proposed_solution: Mapped[str] = mapped_column(Text, nullable=True)
    target_audience: Mapped[str] = mapped_column(String(500), nullable=True)
    monetization_strategy: Mapped[str] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-100
    source_opportunity_id: Mapped[int] = mapped_column(ForeignKey("market_opportunities.id"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Report(Base):
    """A generated daily/weekly report (Requirement 7 & 8)."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False, index=True)
    report_format: Mapped[ReportFormat] = mapped_column(Enum(ReportFormat), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MemoryEntry(Base):
    """Long-term memory record used by the Memory Agent (Requirement 9).

    Generic key/value + tag design so any agent can persist durable context
    (e.g. 'this competitor raised prices in June', 'this keyword trended up
    3 weeks running') that later reports/agents can query back out.
    """

    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # trend/competitor/report/etc
    key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    tags: Mapped[dict] = mapped_column(JSON, nullable=True)
    importance: Mapped[float] = mapped_column(Float, default=1.0)  # for future pruning/ranking
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
