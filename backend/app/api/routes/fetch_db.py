from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime
import httpx
import logging
from uuid import uuid4

from app.db.session import get_session
from app.models.article import RawArticle, ProcessedArticle, LatestSummary
from app.schemas.article import ProcessedArticleResponse

router = APIRouter()
logger = logging.getLogger(__name__)

REMOTE_API_BASE = "http://35.187.155.86/api/v1/fetch"

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

@router.post("/sync-raw-articles/{source}")
async def sync_raw_articles(
    source: str,
    limit: Optional[int] = 10,
    db: Session = Depends(get_session)
) -> dict:
    """
    從遠端 API 同步原始文章資料到本地資料庫

    Args:
        source: 文章來源
        limit: 獲取數量限制
        db: 資料庫連線

    Returns:
        dict: 同步結果
    """
    try:
        # 從遠端 API 獲取資料
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{REMOTE_API_BASE}/raw-articles/{source}",
                params={"limit": limit}
            )
            response.raise_for_status()
            remote_articles = response.json()

        # 寫入本地資料庫
        inserted_count = 0
        for article_data in remote_articles:
            # 檢查文章是否已存在
            statement = select(RawArticle).where(RawArticle.news_id == article_data["news_id"])
            result = await db.execute(statement)
            existing_article = result.first()

            if not existing_article:
                # 創建新文章
                article = RawArticle(**article_data)
                db.add(article)
                inserted_count += 1

        await db.commit()
        
        return {
            "message": "Successfully synced raw articles",
            "source": source,
            "total_fetched": len(remote_articles),
            "inserted": inserted_count
        }
    except Exception as e:
        logger.error(f"Error syncing raw articles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error syncing raw articles: {str(e)}"
        )

@router.post("/sync-processed-articles/{source}")
async def sync_processed_articles(
    source: str,
    limit: Optional[int] = 10,
    db: Session = Depends(get_session)
) -> dict:
    """
    從遠端 API 同步處理過的文章資料到本地資料庫
    """
    try:
        # 從遠端 API 獲取資料
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{REMOTE_API_BASE}/processed-articles/{source}",
                params={"limit": limit}
            )
            response.raise_for_status()
            remote_articles = response.json()
            
        logger.info(f"Retrieved {len(remote_articles)} articles from remote API")
        logger.debug(f"First article data: {remote_articles[0] if remote_articles else 'No articles'}")

        # 寫入本地資料庫
        inserted_count = 0
        skipped_count = 0
        for article_data in remote_articles:
            try:
                # 檢查必要欄位是否存在
                if not article_data.get("content"):
                    logger.warning(f"Skipping article {article_data.get('title')} due to missing content")
                    skipped_count += 1
                    continue

                # 檢查文章是否已存在
                statement = select(ProcessedArticle).where(
                    ProcessedArticle.source == article_data["source"],
                    ProcessedArticle.title == article_data["title"]
                )
                result = await db.execute(statement)
                existing_article = result.first()

                if existing_article:
                    logger.info(f"Article already exists: {article_data.get('title')}")
                    skipped_count += 1
                    continue

                # 生成一個新的 UUID 作為 raw_article_id
                article_data["raw_article_id"] = uuid4()
                
                # 轉換時間格式
                if "published_at" in article_data:
                    article_data["published_at"] = datetime.fromisoformat(article_data["published_at"].replace("Z", "+00:00"))
                if "created_at" in article_data:
                    article_data["created_at"] = datetime.fromisoformat(article_data["created_at"].replace("Z", "+00:00"))
                if "updated_at" in article_data:
                    article_data["updated_at"] = datetime.fromisoformat(article_data["updated_at"].replace("Z", "+00:00"))
                
                # 創建新文章
                article = ProcessedArticle(**article_data)
                db.add(article)
                inserted_count += 1
                logger.info(f"Successfully added article: {article_data.get('title')}")

            except Exception as e:
                logger.error(f"Error processing article {article_data.get('title')}: {str(e)}")
                skipped_count += 1
                continue

        await db.commit()
        
        return {
            "message": "Successfully synced processed articles",
            "source": source,
            "total_fetched": len(remote_articles),
            "inserted": inserted_count,
            "skipped": skipped_count,
            "details": "Check logs for more information"
        }
    except Exception as e:
        logger.error(f"Error syncing processed articles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error syncing processed articles: {str(e)}"
        )

@router.post("/sync-latest-summaries/{source}")
async def sync_latest_summaries(
    source: str,
    limit: Optional[int] = 10,
    db: Session = Depends(get_session)
) -> dict:
    """
    從遠端 API 同步最新摘要資料到本地資料庫
    """
    try:
        # 從遠端 API 獲取資料
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{REMOTE_API_BASE}/latest-summaries/{source}",
                params={"limit": limit}
            )
            response.raise_for_status()
            remote_summaries = response.json()

        # 寫入本地資料庫
        inserted_count = 0
        for summary_data in remote_summaries:
            # 檢查摘要是否已存在（使用 source 和 created_at 組合作為唯一標識）
            statement = select(LatestSummary).where(
                LatestSummary.source == summary_data["source"],
                LatestSummary.created_at == summary_data["created_at"]
            )
            result = await db.execute(statement)
            existing_summary = result.first()

            if not existing_summary:
                # 創建新摘要
                summary = LatestSummary(**summary_data)
                db.add(summary)
                inserted_count += 1

        await db.commit()
        
        return {
            "message": "Successfully synced latest summaries",
            "source": source,
            "total_fetched": len(remote_summaries),
            "inserted": inserted_count
        }
    except Exception as e:
        logger.error(f"Error syncing latest summaries: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error syncing latest summaries: {str(e)}"
        )
