from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.article import ProcessedArticle, LatestSummary
from app.ai.services.summary_generator import SummaryGenerator
from app.ai.services.latest_summary_generator import LatestSummaryGenerator

router = APIRouter()

@router.post("/generate-summary", response_model=List[ProcessedArticle])
async def generate_summary(
    limit: int = 200,
    db: Session = Depends(get_session)
) -> List[ProcessedArticle]:
    """
    Generate summaries for raw articles and save to processed articles table
    
    Args:
        limit: Number of articles to process, default 10
        db: Database session
        
    Returns:
        List[ProcessedArticle]: List of processed articles
    """
    try:
        generator = SummaryGenerator()
        processed_articles = await generator.process_articles(db, limit)
        return processed_articles
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summaries: {str(e)}"
        )

@router.post("/generate-latest-summary", response_model=LatestSummary)
async def generate_latest_summary(
    source_type: str = "TW_Stock_Summary",
    limit: int = 10,
    db: Session = Depends(get_session)
) -> LatestSummary:
    """
    Generate summary compilation of latest news
    
    Args:
        source_type: Summary source type, options: TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary
        limit: Number of articles to process, default 10
        db: Database session
        
    Returns:
        LatestSummary: Generated summary
    """
    # Validate source_type is allowed
    allowed_source_types = ["TW_Stock_Summary", "US_Stock_Summary", "Hot_News_Summary"]
    if source_type not in allowed_source_types:
        raise HTTPException(
            status_code=400,
            detail=f"source_type must be one of: {', '.join(allowed_source_types)}"
        )

    try:
        generator = LatestSummaryGenerator()
        latest_summary = await generator.process_latest_news(
            db=db,
            limit=limit,
            source_type=source_type
        )
        
        if not latest_summary:
            raise HTTPException(
                status_code=404,
                detail=f"No news found for {source_type}"
            )
            
        return latest_summary
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating latest summary: {str(e)}"
        )

@router.get("/summaries")
async def get_latest_summary(
    source: str,
    db: Session = Depends(get_session)
) -> dict:
    """
    Get latest summary for specified source
    
    Args:
        source: Summary source type (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
        db: Database session
        
    Returns:
        dict: Dictionary containing summary content
    """
    try:
        # Query latest summary
        statement = (
            select(LatestSummary)
            .where(LatestSummary.source == source)
        )
        result = await db.execute(statement)
        summary = result.first()
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found for {source}"
            )
            
        summary = summary[0]
        
        # Build response format
        response = {
            "source": summary.source,
            "summary": summary.summary,
            "created_at": summary.created_at.isoformat() + "Z",
            "title": summary.title,
            "related": summary.related
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving summary: {str(e)}"
        )