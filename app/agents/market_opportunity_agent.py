"""
Market Opportunity Agent (Requirement 6 in roadmap numbering / Module 7).

Synthesizes category-level opportunities from:
  - trending app movement
  - high-opportunity keywords
  - competitor coverage
  - negative/bug/feature-request review signals
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.services.market_opportunity_client import MarketSignalClient
from app.services.market_opportunity_service import save_market_opportunities
from app.utils.category_normalize import infer_category_from_keyword, normalize_category

DEFAULT_MIN_SCORE = 45.0
DEFAULT_MIN_KEYWORD_OPPORTUNITY = 55.0


class MarketOpportunityAgent:
    def __init__(self, client: MarketSignalClient | None = None):
        self.client = client or MarketSignalClient()

    def run(
        self,
        db: Session,
        min_score: float = DEFAULT_MIN_SCORE,
        min_keyword_opportunity: float = DEFAULT_MIN_KEYWORD_OPPORTUNITY,
        per_source_limit: int = 300,
    ) -> dict:
        identified_at = datetime.now(timezone.utc)
        summary: dict = {
            "identified_at": identified_at.isoformat(),
            "signals": {},
            "skipped": {},
            "opportunities": 0,
        }

        trend_rows = self._safe_fetch(
            "trends",
            summary,
            lambda: self.client.fetch_trend_signals(db, limit=per_source_limit),
        )
        keyword_rows = self._safe_fetch(
            "keywords",
            summary,
            lambda: self.client.fetch_keyword_signals(
                db, min_opportunity_score=min_keyword_opportunity, limit=per_source_limit
            ),
        )
        competitor_rows = self._safe_fetch(
            "competitors",
            summary,
            lambda: self.client.fetch_competitor_signals(db, limit=per_source_limit),
        )
        review_rows = self._safe_fetch(
            "reviews",
            summary,
            lambda: self.client.fetch_review_signals(db, limit=per_source_limit * 2),
        )

        opportunities = self._synthesize(
            trend_rows=trend_rows,
            keyword_rows=keyword_rows,
            competitor_rows=competitor_rows,
            review_rows=review_rows,
            min_score=min_score,
        )
        saved = save_market_opportunities(db, opportunities, identified_at=identified_at) if opportunities else []
        summary["opportunities"] = len(saved)

        logger.info("MarketOpportunityAgent run complete: {}", summary)
        return summary

    def _safe_fetch(self, source: str, summary: dict, fn):
        try:
            rows = fn()
            summary["signals"][source] = len(rows)
            return rows
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping source {}: {}", source, exc)
            summary["signals"][source] = 0
            summary["skipped"][source] = str(exc)
            return []

    def _synthesize(
        self,
        trend_rows: list,
        keyword_rows: list,
        competitor_rows: list,
        review_rows: list,
        min_score: float,
    ) -> list[dict]:
        buckets: dict[str, dict] = defaultdict(lambda: {
            "trend_ids": [],
            "fast_growing_count": 0,
            "keyword_ids": [],
            "keyword_avg_opp": 0.0,
            "competitor_ids": [],
            "review_ids": [],
            "review_negative": 0,
            "review_bugs": 0,
            "review_requests": 0,
        })

        for row in trend_rows:
            category = normalize_category(row.category)
            if not category:
                continue
            bucket = buckets[category]
            bucket["trend_ids"].append(row.id)
            chart = getattr(row, "chart_type", None)
            chart_value = chart.value if hasattr(chart, "value") else chart
            if chart_value == "fast_growing":
                bucket["fast_growing_count"] += 1

        keyword_scores: dict[str, list[float]] = defaultdict(list)
        for row in keyword_rows:
            category = infer_category_from_keyword(row.term)
            if not category:
                continue
            bucket = buckets[category]
            bucket["keyword_ids"].append(row.id)
            if row.opportunity_score is not None:
                keyword_scores[category].append(float(row.opportunity_score))

        for category, scores in keyword_scores.items():
            buckets[category]["keyword_avg_opp"] = round(sum(scores) / len(scores), 2)

        competitor_category_by_id = {}
        for row in competitor_rows:
            category = normalize_category(row.category)
            if not category:
                continue
            competitor_category_by_id[row.id] = category
            buckets[category]["competitor_ids"].append(row.id)

        for row in review_rows:
            category = competitor_category_by_id.get(row.competitor_id)
            if not category:
                continue
            bucket = buckets[category]
            bucket["review_ids"].append(row.id)
            if row.sentiment == "negative":
                bucket["review_negative"] += 1
            if row.mentions_bug:
                bucket["review_bugs"] += 1
            if row.mentions_feature_request:
                bucket["review_requests"] += 1

        opportunities = []
        for category, bucket in buckets.items():
            trend_score = min(40.0, bucket["fast_growing_count"] * 8 + len(bucket["trend_ids"]) * 1.5)
            keyword_score = min(30.0, bucket["keyword_avg_opp"] * 0.30) if bucket["keyword_ids"] else 0.0
            # Mild coverage bonus so trend-heavy categories still surface without keywords.
            coverage_bonus = 8.0 if bucket["trend_ids"] and not bucket["keyword_ids"] else 0.0
            pain_score = min(
                30.0,
                bucket["review_negative"] * 2.0 + bucket["review_bugs"] * 3.0 + bucket["review_requests"] * 2.5,
            )
            score = round(min(100.0, trend_score + keyword_score + pain_score + coverage_bonus), 2)
            if score < min_score:
                continue

            title = self._opportunity_title(category, bucket)
            opportunities.append({
                "title": title,
                "category": category,
                "description": (
                    f"{category} shows momentum ({len(bucket['trend_ids'])} trend signals, "
                    f"{bucket['fast_growing_count']} fast-growing) with keyword upside "
                    f"(avg opportunity {bucket['keyword_avg_opp']}) and user pain from reviews "
                    f"({bucket['review_negative']} negative, {bucket['review_bugs']} bug mentions, "
                    f"{bucket['review_requests']} feature requests)."
                ),
                "opportunity_score": score,
                "supporting_evidence": {
                    "trending_app_ids": bucket["trend_ids"][:25],
                    "keyword_ids": bucket["keyword_ids"][:25],
                    "competitor_ids": bucket["competitor_ids"][:25],
                    "review_ids": bucket["review_ids"][:50],
                    "signal_breakdown": {
                        "trend_score": round(trend_score, 2),
                        "keyword_score": round(keyword_score, 2),
                        "pain_score": round(pain_score, 2),
                        "coverage_bonus": coverage_bonus,
                    },
                },
            })

        opportunities.sort(key=lambda item: item["opportunity_score"], reverse=True)
        return opportunities

    def _opportunity_title(self, category: str, bucket: dict) -> str:
        if bucket["review_bugs"] or bucket["review_negative"] >= 3:
            return f"{category}: fix review pain while demand is rising"
        if bucket["keyword_ids"] and bucket["keyword_avg_opp"] >= 60:
            return f"{category}: high-demand keywords with weak competition"
        if bucket["fast_growing_count"] > 0:
            return f"{category}: fast-growing apps signal an open niche"
        if len(bucket["trend_ids"]) >= 20:
            return f"{category}: strong chart presence, room for differentiation"
        return f"{category}: emerging market gap to validate"
