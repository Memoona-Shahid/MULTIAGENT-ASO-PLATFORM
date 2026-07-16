"""Derive keyword seeds and competitor targets from trending apps."""

from __future__ import annotations

import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import Platform, TrendingApp
from app.utils.category_normalize import normalize_category

_STOP = {
    "the", "and", "for", "app", "apps", "free", "pro", "plus", "new", "best",
    "with", "from", "your", "you", "offline", "online", "video", "live",
}


def build_keyword_seeds_from_trends(db: Session, limit: int = 12) -> list[str]:
    """Build diverse keyword seeds from trending categories and app-name tokens."""
    rows = list(
        db.scalars(
            select(TrendingApp)
            .order_by(TrendingApp.captured_at.desc(), TrendingApp.rank.asc().nulls_last())
            .limit(400)
        )
    )
    if not rows:
        return ["productivity app", "social app", "finance app", "shopping app"]

    category_counts: Counter[str] = Counter()
    token_counts: Counter[str] = Counter()

    for row in rows:
        category = normalize_category(row.category)
        if category:
            category_counts[category] += 1
        for token in _tokens(row.name):
            token_counts[token] += 1

    seeds: list[str] = []
    seen: set[str] = set()

    # Prefer top categories as seeds (broad market coverage).
    for category, _ in category_counts.most_common(limit):
        seed = category.lower().replace("&", "and")
        _add_seed(seeds, seen, seed)
        if len(seeds) >= limit:
            return seeds

    # Fill with high-frequency name tokens from trending apps.
    for token, _ in token_counts.most_common(40):
        _add_seed(seeds, seen, token)
        if len(seeds) >= limit:
            break

    return seeds or ["productivity app", "social app", "finance app"]


def build_competitor_targets_from_trends(db: Session, limit: int = 6) -> list[dict]:
    """Pick top trending apps across categories as competitor analysis targets."""
    rows = list(
        db.scalars(
            select(TrendingApp)
            .order_by(TrendingApp.rank.asc().nulls_last(), TrendingApp.captured_at.desc())
            .limit(300)
        )
    )
    targets: list[dict] = []
    seen_apps: set[str] = set()
    seen_categories: set[str] = set()

    # First pass: one app per category for diversity.
    for row in rows:
        key = f"{row.platform.value}:{row.store_app_id}"
        if key in seen_apps or not row.store_app_id:
            continue
        category = normalize_category(row.category) or "General"
        if category in seen_categories:
            continue
        seen_apps.add(key)
        seen_categories.add(category)
        targets.append({"platform": row.platform, "store_app_id": row.store_app_id})
        if len(targets) >= limit:
            return targets

    # Second pass: fill remaining slots with highest-ranked apps.
    for row in rows:
        key = f"{row.platform.value}:{row.store_app_id}"
        if key in seen_apps or not row.store_app_id:
            continue
        seen_apps.add(key)
        targets.append({"platform": row.platform, "store_app_id": row.store_app_id})
        if len(targets) >= limit:
            break

    return targets


def _tokens(name: str | None) -> list[str]:
    if not name:
        return []
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", name.lower())
    out = []
    for part in cleaned.split():
        if len(part) < 4 or part in _STOP or part.isdigit():
            continue
        out.append(part)
    return out


def _add_seed(seeds: list[str], seen: set[str], seed: str) -> None:
    value = " ".join(seed.strip().lower().split())
    if not value or value in seen:
        return
    seen.add(value)
    seeds.append(value)
