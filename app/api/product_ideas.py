"""
API routes for AI Idea Generator (Module 8).

POST /api/product-ideas/generate  -> generates ideas from market opportunities
GET  /api/product-ideas           -> lists generated product ideas
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.ai_idea_generator_agent import AiIdeaGeneratorAgent
from app.core.database import get_db
from app.models.schemas import ProductIdeaGenerateRequest, ProductIdeaOut
from app.services.product_idea_service import list_product_ideas

router = APIRouter()


@router.post("/generate")
def generate_ideas(
    request: ProductIdeaGenerateRequest,
    db: Session = Depends(get_db),
) -> dict:
    agent = AiIdeaGeneratorAgent()
    return agent.run(
        db,
        opportunity_ids=request.opportunity_ids,
        min_opportunity_score=request.min_opportunity_score,
        ideas_per_opportunity=request.ideas_per_opportunity,
        opportunity_limit=request.opportunity_limit,
    )


@router.get("", response_model=list[ProductIdeaOut])
def get_product_ideas(
    idea_type: str | None = Query(default=None, pattern="^(mobile_app|saas|ai_product)$"),
    min_confidence_score: float | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return list_product_ideas(
        db,
        idea_type=idea_type,
        min_confidence_score=min_confidence_score,
        limit=limit,
    )
