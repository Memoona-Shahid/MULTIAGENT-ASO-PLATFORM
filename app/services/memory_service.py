"""Persistence/query helpers for MemoryEntry rows."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import MemoryEntry


def save_memory_entry(db: Session, entry: dict, created_at: datetime | None = None) -> MemoryEntry:
    row = MemoryEntry(
        entry_type=entry["entry_type"],
        key=entry["key"],
        value=entry["value"],
        tags=entry.get("tags"),
        importance=entry.get("importance", 1.0),
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("Saved memory entry {}::{}", row.entry_type, row.key)
    return row


def upsert_memory_entry(db: Session, entry: dict, created_at: datetime | None = None) -> MemoryEntry:
    stmt = select(MemoryEntry).where(
        MemoryEntry.entry_type == entry["entry_type"],
        MemoryEntry.key == entry["key"],
    )
    existing = db.scalar(stmt)
    if existing is None:
        return save_memory_entry(db, entry, created_at=created_at)

    existing.value = entry["value"]
    existing.tags = entry.get("tags")
    existing.importance = entry.get("importance", existing.importance)
    if created_at is not None:
        existing.created_at = created_at
    db.commit()
    db.refresh(existing)
    return existing


def get_memory_entry(db: Session, entry_type: str, key: str) -> MemoryEntry | None:
    stmt = select(MemoryEntry).where(MemoryEntry.entry_type == entry_type, MemoryEntry.key == key)
    return db.scalar(stmt)


def list_memory_entries(
    db: Session,
    entry_type: str | None = None,
    key_prefix: str | None = None,
    min_importance: float | None = None,
    limit: int = 100,
) -> list[MemoryEntry]:
    stmt = select(MemoryEntry)
    if entry_type is not None:
        stmt = stmt.where(MemoryEntry.entry_type == entry_type)
    if key_prefix is not None:
        stmt = stmt.where(MemoryEntry.key.like(f"{key_prefix}%"))
    if min_importance is not None:
        stmt = stmt.where(MemoryEntry.importance >= min_importance)
    stmt = stmt.order_by(
        MemoryEntry.importance.desc(),
        MemoryEntry.created_at.desc(),
    ).limit(limit)
    return list(db.scalars(stmt))


def prune_memory_entries(db: Session, below_importance: float) -> int:
    rows = list(
        db.scalars(select(MemoryEntry).where(MemoryEntry.importance < below_importance))
    )
    for row in rows:
        db.delete(row)
    db.commit()
    if rows:
        logger.info("Pruned {} memory entries below importance {}", len(rows), below_importance)
    return len(rows)
