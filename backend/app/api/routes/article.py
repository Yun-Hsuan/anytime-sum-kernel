"""
Article related routes
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import logging
from sqlalchemy import desc

from app.db.session import get_session
from app.models.article import ProcessedArticle, LatestSummary
from app.services.article_service import ArticleService
from app.schemas.article import (
    ProcessedArticleResponse,
    ProcessPendingResponse,
    LatestSummariesResponse,
)
from app.services.summary_service import SummaryService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/category-summary")
async def get_category_summary(
    source_type: str,
    db: Session = Depends(get_session)
) -> dict:
    """
    Get latest category summary for specified source type
    
    Args:
        source_type: Summary source type (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
        db: Database session
        
    Returns:
        dict: Dictionary containing category summary content
    """
    try:
        # Query latest summary by created_at
        statement = (
            select(LatestSummary)
            .where(LatestSummary.source == source_type)
            .order_by(desc(LatestSummary.created_at))
            .limit(1)
        )
        result = await db.execute(statement)
        summary = result.first()
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found for {source_type}"
            )
            
        summary = summary[0]
        
        # 將時間加上8小時並轉換為epoch time
        created_at_utc8 = summary.created_at
        created_at_epoch = int(created_at_utc8.timestamp())
        
        # Build response format
        response = {
            "source": summary.source,
            "summary": summary.summary,
            "created_at": created_at_epoch,
            "title": summary.title,
            "related": summary.related
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving category summary: {str(e)}"
        )

@router.post("/process-pending", response_model=ProcessPendingResponse)
async def process_pending_articles(
    limit: Optional[int] = 150,
    db: Session = Depends(get_session)
) -> ProcessPendingResponse:
    """
    Process pending articles (RawArticles without generated summaries)
    
    Args:
        limit: Maximum number of articles to process, defaults to 150
        db: Database connection
        
    Returns:
        ProcessPendingResponse: Processing results including total pending count, 
                              number of processed articles and list of processed articles
    """
    try:
        article_service = ArticleService()
        processed_articles, processed_count, total_pending = (
            await article_service.process_pending_articles(db, limit)
        )
        
        return ProcessPendingResponse(
            message=f"Successfully processed {processed_count} articles, {total_pending - processed_count} remaining",
            total_pending=total_pending,
            processed_count=processed_count,
            processed_articles=[
                ProcessedArticleResponse.from_orm(article)
                for article in processed_articles
            ]
        )
    except Exception as e:
        logger.error(f"Error processing pending articles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing articles: {str(e)}"
        )

@router.post("/latest-summaries")
async def generate_latest_summaries(
    source: str,
    fetch_limit: Optional[int] = 30,
    summary_limit: Optional[int] = 20,
    db: Session = Depends(get_session)
) -> LatestSummariesResponse:
    """
    Get and generate latest article summaries for a specific source
    
    Args:
        source: Article source type. Must be one of:
               - "TW_Stock_Summary": Taiwan stock market news
               - "US_Stock_Summary": US stock market news
               - "Hot_News_Summary": Hot topics and trending news
        fetch_limit: Maximum number of articles to fetch from database (default: 30)
        summary_limit: Number of articles to include in summary (default: 20)
        db: Database session
        
    Returns:
        LatestSummariesResponse: Response containing summary and related articles
        
    Raises:
        HTTPException(400): If source is not one of the allowed values
        HTTPException(500): If error occurs during summary generation
    """
    # Validate source
    allowed_sources = ["TW_Stock_Summary", "US_Stock_Summary", "Hot_News_Summary"]
    if source not in allowed_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Allowed values are: {', '.join(allowed_sources)}"
        )

    try:
        summary_service = SummaryService()
        latest_summary, selected_articles = await summary_service.generate_category_summary(
            db=db,
            source=source,
            fetch_limit=fetch_limit,
            summary_limit=summary_limit
        )
        
        if not latest_summary:
            return LatestSummariesResponse(
                message="No articles found",
                source=source,
                count=0,
                articles=[]
            )
            
        return LatestSummariesResponse(
            message="Successfully generated latest summaries",
            source=source,
            count=len(selected_articles),
            articles=[
                ProcessedArticleResponse.from_orm(article)
                for article in selected_articles
            ]
        )
    except Exception as e:
        logger.error(f"Error generating article summaries: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating article summaries: {str(e)}"
        )