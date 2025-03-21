"""
News pipeline routes
"""

from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db.session import get_session
from app.services.news_pipeline_service import NewsPipelineService
from app.config.news_sources import NewsSourceConfig

router = APIRouter()

@router.post("/process-news/{source}", response_model=Dict)
async def process_news_pipeline(
    source: str,
    db: Session = Depends(get_session)
) -> Dict:
    """
    Execute complete news processing pipeline for specified source
    
    Args:
        source: News source identifier (e.g., "TW_Stock_Summary")
        db: Database session
        
    Returns:
        Dict: Processing results and statistics
    """
    if source not in NewsSourceConfig.get_all_sources():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Allowed values: {', '.join(NewsSourceConfig.get_all_sources())}"
        )
    
    pipeline_service = NewsPipelineService()
    return await pipeline_service.process_news_pipeline(source)

@router.get("/available-sources")
async def get_available_sources() -> Dict:
    """Get all available news sources and their configurations"""
    return {
        "sources": NewsSourceConfig.SOURCES
    } 