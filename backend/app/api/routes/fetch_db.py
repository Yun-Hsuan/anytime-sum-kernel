from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime

from app.db.session import get_session
from app.models.article import RawArticle, ProcessedArticle, LatestSummary
from app.schemas.article import ProcessedArticleResponse

router = APIRouter()

@router.get("/raw-articles/{source}")
async def get_raw_articles(
    source: str,
    limit: Optional[int] = 10,
    db: Session = Depends(get_session)
) -> List[RawArticle]:
    """
    獲取指定來源的最新原始文章

    Args:
        source: 文章來源 (cnyes_tw, cnyes_us, cnyes_headline)
        limit: 返回文章數量限制
        db: 資料庫連線

    Returns:
        List[RawArticle]: 原始文章列表
    """
    try:
        statement = (
            select(RawArticle)
            .where(RawArticle.source == source)
            .order_by(RawArticle.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(statement)
        articles = result.scalars().all()
        
        if not articles:
            raise HTTPException(
                status_code=404,
                detail=f"No raw articles found for source: {source}"
            )
        
        return articles
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching raw articles: {str(e)}"
        )

@router.get("/processed-articles/{source}")
async def get_processed_articles(
    source: str,
    limit: Optional[int] = 10,
    db: Session = Depends(get_session)
) -> List[ProcessedArticleResponse]:
    """
    獲取指定來源的最新處理過的文章

    Args:
        source: 文章來源 (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
        limit: 返回文章數量限制
        db: 資料庫連線

    Returns:
        List[ProcessedArticleResponse]: 處理過的文章列表
    """
    try:
        statement = (
            select(ProcessedArticle)
            .where(ProcessedArticle.source == source)
            .order_by(ProcessedArticle.published_at.desc())
            .limit(limit)
        )
        result = await db.execute(statement)
        articles = result.scalars().all()
        
        if not articles:
            raise HTTPException(
                status_code=404,
                detail=f"No processed articles found for source: {source}"
            )
        
        return [ProcessedArticleResponse.from_orm(article) for article in articles]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching processed articles: {str(e)}"
        )

@router.get("/latest-summaries/{source}")
async def get_latest_summaries(
    source: str,
    limit: Optional[int] = 10,
    db: Session = Depends(get_session)
) -> List[LatestSummary]:
    """
    獲取指定來源的最新摘要

    Args:
        source: 摘要來源 (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
        limit: 返回摘要數量限制
        db: 資料庫連線

    Returns:
        List[LatestSummary]: 最新摘要列表
    """
    try:
        statement = (
            select(LatestSummary)
            .where(LatestSummary.source == source)
            .order_by(LatestSummary.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(statement)
        summaries = result.scalars().all()
        
        if not summaries:
            raise HTTPException(
                status_code=404,
                detail=f"No summaries found for source: {source}"
            )
        
        return summaries
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching latest summaries: {str(e)}"
        )
