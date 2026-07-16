"""Category label normalization for opportunity synthesis and idea generation."""

from __future__ import annotations

# Store / keyword labels that should collapse into one bucket.
CATEGORY_ALIASES: dict[str, str] = {
    "health & fitness": "Health & Fitness",
    "health and fitness": "Health & Fitness",
    "fitness": "Health & Fitness",
    "workout": "Health & Fitness",
    "habit": "Productivity",
    "habits": "Productivity",
    "social networking": "Social",
    "social": "Social",
    "photo & video": "Photo & Video",
    "photo and video": "Photo & Video",
    "music & audio": "Music & Audio",
    "music and audio": "Music & Audio",
    "video players & editors": "Video Players & Editors",
    "food & drink": "Food & Drink",
    "food and drink": "Food & Drink",
    "utilities": "Utilities",
    "tools": "Tools",
    "productivity": "Productivity",
    "finance": "Finance",
    "entertainment": "Entertainment",
    "shopping": "Shopping",
    "communication": "Communication",
    "dating": "Dating",
    "education": "Education",
    "business": "Business",
    "weather": "Weather",
    "personalization": "Personalization",
    "lifestyle": "Lifestyle",
    "travel": "Travel",
    "medical": "Medical",
    "news": "News",
    "sports": "Sports",
    "games": "Games",
}

# Keyword tokens → canonical store category.
KEYWORD_TOKEN_TO_CATEGORY: dict[str, str] = {
    "fitness": "Health & Fitness",
    "workout": "Health & Fitness",
    "gym": "Health & Fitness",
    "yoga": "Health & Fitness",
    "health": "Health & Fitness",
    "habit": "Productivity",
    "habits": "Productivity",
    "todo": "Productivity",
    "task": "Productivity",
    "notes": "Productivity",
    "productivity": "Productivity",
    "finance": "Finance",
    "budget": "Finance",
    "banking": "Finance",
    "invest": "Finance",
    "crypto": "Finance",
    "social": "Social",
    "chat": "Social",
    "dating": "Dating",
    "shop": "Shopping",
    "shopping": "Shopping",
    "commerce": "Shopping",
    "music": "Music & Audio",
    "audio": "Music & Audio",
    "podcast": "Music & Audio",
    "video": "Video Players & Editors",
    "photo": "Photo & Video",
    "camera": "Photo & Video",
    "drama": "Entertainment",
    "movie": "Entertainment",
    "tv": "Entertainment",
    "game": "Games",
    "education": "Education",
    "learn": "Education",
    "food": "Food & Drink",
    "recipe": "Food & Drink",
    "travel": "Travel",
    "weather": "Weather",
    "business": "Business",
    "crm": "Business",
}


def normalize_category(raw: str | None) -> str | None:
    """Collapse store/keyword category labels into a canonical bucket."""
    if raw is None:
        return None
    text = " ".join(str(raw).strip().split())
    if not text:
        return None
    mapped = CATEGORY_ALIASES.get(text.lower())
    if mapped:
        return mapped
    # Title-case unknown labels so "finance" and "Finance" merge.
    return text.title() if text.islower() else text


def infer_category_from_keyword(term: str | None) -> str | None:
    """Map a keyword term to a store category without inventing orphan buckets."""
    if not term:
        return None
    tokens = [tok.strip().lower() for tok in term.replace("-", " ").split() if tok.strip()]
    for token in tokens:
        if token in KEYWORD_TOKEN_TO_CATEGORY:
            return KEYWORD_TOKEN_TO_CATEGORY[token]
    # Prefer multi-word known phrases already covered by tokens above.
    # Do NOT invent categories from the first word (that produced "Habit", "My", etc.).
    return None
