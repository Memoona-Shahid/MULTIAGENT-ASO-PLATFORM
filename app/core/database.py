"""
SQLAlchemy database engine + session management.

Defaults to SQLite for zero-setup local dev, swap DATABASE_URL to Postgres
for production — no code changes needed elsewhere.
"""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.logging import logger

# Make sure the sqlite data dir exists before the engine tries to open a file
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.split("///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class all ORM models inherit from."""
    pass


def init_db() -> None:
    """Create all tables. Called once at app startup."""
    # Import models here so they're registered on Base.metadata before create_all
    from app.models import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at {}", settings.database_url)


def get_db():
    """FastAPI dependency: yields a DB session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session():
    """Context manager for use outside FastAPI (agents, scripts, scheduler jobs).

    Usage:
        with db_session() as db:
            db.add(obj)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
