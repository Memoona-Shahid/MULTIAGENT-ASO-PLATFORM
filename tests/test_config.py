from app.core.config import Settings, get_settings


def test_settings_load_defaults():
    s = Settings(_env_file=None)
    assert s.app_name == "AI ASO Platform"
    assert s.agent_runtime == "mock"
    assert s.database_url.startswith("sqlite")


def test_get_settings_is_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
