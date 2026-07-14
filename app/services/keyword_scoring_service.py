"""
Keyword scoring — turns autocomplete position + competition count into the
search_volume / difficulty_score / opportunity_score fields on the Keyword
model.

THESE ARE HEURISTIC ESTIMATES, NOT REAL DATA. Real search volume and
keyword difficulty require a paid data source (Apple Search Ads API,
Sensor Tower, data.ai, Mobile Action, etc) — nothing free provides actual
numbers. The formulas here follow the same approach used across free/indie
ASO tooling: autocomplete position as a popularity proxy, result count as
a competition proxy. Swap these out for a real provider's numbers later by
replacing the callers in keyword_research_agent.py — the Keyword schema
(0-100 scales) is designed to accept either.
"""

from __future__ import annotations

# Position 1 (top autocomplete suggestion) scores highest; score decays
# per position and floors out rather than hitting zero, since even a
# 10th-place suggestion is still a real, popular-enough search to surface.
_POSITION_DECAY_PER_RANK = 8
_MIN_VOLUME_SCORE = 10
_MAX_SCORE = 100

# Competition count is capped at each client's max result window (200 for
# Apple, 100 for Google Play) — normalized to a 0-100 difficulty scale by
# dividing by that cap rather than an arbitrary constant, so "difficulty 100"
# consistently means "the search results are completely full" on either store.


def volume_score_from_position(position: int) -> float:
    """1-indexed autocomplete position -> 0-100 popularity proxy."""
    if position < 1:
        raise ValueError("position must be >= 1")
    score = _MAX_SCORE - (position - 1) * _POSITION_DECAY_PER_RANK
    return float(max(score, _MIN_VOLUME_SCORE))


def difficulty_score_from_competition(competition_count: int, max_results: int) -> float:
    """Number of matching apps (capped at max_results) -> 0-100 difficulty proxy."""
    if max_results <= 0:
        raise ValueError("max_results must be > 0")
    ratio = min(competition_count, max_results) / max_results
    return round(ratio * _MAX_SCORE, 2)


def opportunity_score(volume_score: float, difficulty_score: float) -> float:
    """Simple, transparent trade-off: high volume minus half the difficulty
    penalty, clamped to 0-100. Favors popular-but-less-contested terms —
    the definition of a good ASO keyword opportunity."""
    score = volume_score - (difficulty_score * 0.5)
    return round(max(0.0, min(_MAX_SCORE, score)), 2)
