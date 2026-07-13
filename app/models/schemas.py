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
    search_volume: Optional[int] = None
    difficulty_score: Optional[float] = None
    opportunity_score: Optional[float] = None
    captured_at: datetime


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


# ---------- Market Opportunities ----------

class MarketOpportunityOut(ORMBase):
    id: int
    title: str
    category: Optional[str] = None
    description: Optional[str] = None
    opportunity_score: Optional[float] = None
    identified_at: datetime


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
    generated_at: datetime


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
