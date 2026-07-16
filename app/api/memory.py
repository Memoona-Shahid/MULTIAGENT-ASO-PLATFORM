"""
API routes for Memory Agent (Module 10).

POST /api/memory/consolidate  -> consolidates recent signals into memory
POST /api/memory              -> manual memory write (testing / overrides)
GET  /api/memory              -> lists memory entries
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.memory_agent import MemoryAgent
from app.core.database import get_db
from app.models.schemas import MemoryConsolidateRequest, MemoryEntryOut, MemoryWriteRequest
from app.services.memory_service import get_memory_entry, list_memory_entries

router = APIRouter()


@router.post("/consolidate")
def consolidate_memory(
    request: MemoryConsolidateRequest,
    db: Session = Depends(get_db),
) -> dict:
    agent = MemoryAgent()
    return agent.run(
        db,
        lookback_days=request.lookback_days,
        per_source_limit=request.per_source_limit,
        min_importance=request.min_importance,
        prune_below_importance=request.prune_below_importance,
    )


@router.post("", response_model=MemoryEntryOut)
def write_memory_entry(
    request: MemoryWriteRequest,
    db: Session = Depends(get_db),
) -> MemoryEntryOut:
    agent = MemoryAgent()
    agent.write_entry(
        db,
        {
            "entry_type": request.entry_type,
            "key": request.key,
            "value": request.value,
            "tags": request.tags,
            "importance": request.importance,
        },
    )
    row = get_memory_entry(db, request.entry_type, request.key)
    if row is None:
        raise RuntimeError("Memory entry was not saved")
    return row


@router.get("", response_model=list[MemoryEntryOut])
def get_memory_entries(
    entry_type: str | None = Query(default=None),
    key_prefix: str | None = Query(default=None),
    min_importance: float | None = Query(default=None, ge=0, le=10),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return list_memory_entries(
        db,
        entry_type=entry_type,
        key_prefix=key_prefix,
        min_importance=min_importance,
        limit=limit,
    )
