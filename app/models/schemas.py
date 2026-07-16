"""
Pydantic schemas — the API-facing contracts. Kept separate from the ORM
models (db_models.py) on purpose so internal DB structure can evolve
without breaking the public API shape, and vice versa.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.db_models import ChartType, Platform, ReportFormat, ReportType


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Trending Apps ----------

class TrendingAppOut(ORMBase):
    id: int
    platform: Platform
    store_app_id: str
    name: str
    developer: Optional[str] = None
    category: Optional[str] = None
    chart_type: ChartType
    rank: Optional[int] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    price: Optional[float] = None
    icon_url: Optional[str] = None
    store_url: Optional[str] = None
    captured_at: datetime


# ---------- Keywords ----------

class KeywordOut(ORMBase):
    id: int
    term: str
    platform: Platform
    search_volume: Optional[float] = None
    difficulty_score: Optional[float] = None
    opportunity_score: Optional[float] = None
    captured_at: datetime


class KeywordResearchRequest(BaseModel):
    seed_terms: list[str] = Field(..., min_length=1, description="Seed terms to expand via autocomplete.")
    platforms: Optional[list[Platform]] = Field(
        default=None, description="Defaults to both App Store and Google Play if omitted."
    )
    suggestions_per_seed: int = Field(default=10, ge=1, le=50)


# ---------- Competitors ----------

class CompetitorOut(ORMBase):
    id: int
    platform: Platform
    store_app_id: str
    name: str
    developer: Optional[str] = None
    category: Optional[str] = None
    estimated_downloads: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    pricing_model: Optional[str] = None
    monetization_details: Optional[dict[str, Any]] = None
    screenshots: Optional[list[str]] = None
    features: Optional[list[str]] = None
    last_analyzed_at: datetime


class CompetitorAnalysisTarget(BaseModel):
    platform: Platform
    store_app_id: str = Field(..., min_length=1, description="App Store track ID or Google Play package name.")


class CompetitorAnalysisRequest(BaseModel):
    targets: list[CompetitorAnalysisTarget] = Field(..., min_length=1)
    reviews_per_app: int = Field(default=20, ge=0, le=100)


# ---------- Reviews ----------

class ReviewOut(ORMBase):
    id: int
    competitor_id: int
    platform: Platform
    author: Optional[str] = None
    rating: Optional[int] = None
    review_text: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    mentions_bug: bool
    mentions_feature_request: bool
    posted_at: Optional[datetime] = None


class ReviewIntelligenceRequest(BaseModel):
    competitor_ids: Optional[list[int]] = Field(
        default=None,
        description="If omitted, analyzes tracked competitors up to tracked_competitor_limit.",
    )
    platform: Optional[Platform] = Field(default=None, description="Optional platform filter.")
    reviews_per_competitor: int = Field(default=50, ge=0, le=200)
    tracked_competitor_limit: int = Field(default=100, ge=1, le=500)


# ---------- Market Opportunities ----------

class MarketOpportunityOut(ORMBase):
    id: int
    title: str
    category: Optional[str] = None
    description: Optional[str] = None
    opportunity_score: Optional[float] = None
    identified_at: datetime


class MarketOpportunitySynthesisRequest(BaseModel):
    min_score: float = Field(default=45.0, ge=0, le=100)
    min_keyword_opportunity: float = Field(default=55.0, ge=0, le=100)
    per_source_limit: int = Field(default=300, ge=10, le=2000)


# ---------- Product Ideas ----------

class ProductIdeaOut(ORMBase):
    id: int
    title: str
    idea_type: Optional[str] = None
    problem_statement: Optional[str] = None
    proposed_solution: Optional[str] = None
    target_audience: Optional[str] = None
    monetization_strategy: Optional[str] = None
    confidence_score: Optional[float] = None
    source_opportunity_id: Optional[int] = None
    generated_at: datetime


class ProductIdeaGenerateRequest(BaseModel):
    opportunity_ids: Optional[list[int]] = Field(
        default=None,
        description="If omitted, uses top opportunities up to opportunity_limit.",
    )
    min_opportunity_score: float = Field(default=45.0, ge=0, le=100)
    ideas_per_opportunity: int = Field(default=1, ge=1, le=3)
    opportunity_limit: int = Field(default=50, ge=1, le=500)


# ---------- Reports ----------

class ReportOut(ORMBase):
    id: int
    report_type: ReportType
    report_format: ReportFormat
    title: str
    summary: Optional[str] = None
    file_path: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    generated_at: datetime


class ReportGenerateRequest(BaseModel):
    report_type: ReportType = ReportType.DAILY
    report_format: ReportFormat = ReportFormat.MARKDOWN
    generate_ideas: bool = Field(
        default=True,
        description="When true, generates fresh product ideas before building the report.",
    )
    min_opportunity_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Minimum opportunity score when auto-generating ideas for the report.",
    )
    ideas_per_opportunity: int = Field(default=1, ge=1, le=3)
    opportunity_limit: int = Field(default=10, ge=1, le=100)


# ---------- Memory ----------

class MemoryEntryOut(ORMBase):
    id: int
    entry_type: str
    key: str
    value: dict
    tags: Optional[dict] = None
    importance: float
    created_at: datetime


class MemoryConsolidateRequest(BaseModel):
    lookback_days: int = Field(default=7, ge=1, le=90)
    per_source_limit: int = Field(default=200, ge=10, le=2000)
    min_importance: float = Field(default=0.5, ge=0, le=10)
    prune_below_importance: Optional[float] = Field(default=None, ge=0, le=10)


class MemoryWriteRequest(BaseModel):
    entry_type: str = Field(..., max_length=100)
    key: str = Field(..., max_length=500)
    value: dict
    tags: Optional[dict] = None
    importance: float = Field(default=1.0, ge=0, le=10)


# ---------- Generic ----------

class HealthOut(BaseModel):
    status: str = "ok"
    app_env: str
    agent_runtime: str


class PaginatedResponse(BaseModel):
    total: int
    items: list[Any]
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
