from app.utils.category_normalize import infer_category_from_keyword, normalize_category


def test_normalize_category_aliases():
    assert normalize_category("Social Networking") == "Social"
    assert normalize_category("fitness") == "Health & Fitness"
    assert normalize_category("Health & Fitness") == "Health & Fitness"
    assert normalize_category("Habit") == "Productivity"


def test_infer_category_from_keyword_does_not_invent_orphan_buckets():
    assert infer_category_from_keyword("fitness apps") == "Health & Fitness"
    assert infer_category_from_keyword("habit tracker") == "Productivity"
    assert infer_category_from_keyword("finance widget") == "Finance"
    assert infer_category_from_keyword("my random phrase") is None
