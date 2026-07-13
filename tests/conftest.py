"""Shared pytest fixtures — isolated in-memory SQLite DB per test."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base


@pytest.fixture()
def db_session():
    """Fresh in-memory SQLite DB per test, fully isolated."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # Import models so they're registered on Base.metadata
    from app.models import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(monkeypatch, tmp_path):
    """FastAPI TestClient wired to a temp SQLite file DB."""
    from fastapi.testclient import TestClient

    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    # Settings is cached via lru_cache — clear it so the new env var is picked up
    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.main import app
    with TestClient(app) as c:
        yield c
