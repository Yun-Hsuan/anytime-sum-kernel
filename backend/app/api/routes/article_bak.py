"""
Article related routes
"""

from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
import logging
from sqlalchemy import desc
from datetime import datetime, timedelta
import asyncio

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

# 使用簡單的字典作為記憶體快取
class SummaryCache:
    def __init__(self):
        self.cache: Dict[str, dict] = {}
        logger.info("SummaryCache initialized")

    def get(self, source_type: str) -> Optional[dict]:
        if source_type not in self.cache:
            logger.info(f"Cache miss: {source_type} not in cache")
            return None
        
        logger.info(f"Cache hit: returning cached data for {source_type}")
        return self.cache[source_type]

    def set(self, source_type: str, data: dict):
        self.cache[source_type] = data
        logger.info(f"Cache updated for {source_type}")

# 創建快取實例
summary_cache = SummaryCache()

# 用於追蹤任務狀態的簡單字典
task_status = {
    "process_pending": {
        "is_running": False,
        "last_run": None,
        "result": None,
        "error": None
    }
}

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
        # 先檢查快取
        cached_summary = summary_cache.get(source_type)
        if cached_summary:
            return cached_summary

        # 如果快取沒有或過期，從資料庫讀取
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
        created_at_epoch = int(summary.created_at.timestamp())
        
        # 建立回應格式
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

def process_pending_background(limit: int = 150):
    """背景處理待處理文章的任務"""
    try:
        # 更新任務狀態
        task_status["process_pending"]["is_running"] = True
        task_status["process_pending"]["last_run"] = datetime.now()
        task_status["process_pending"]["error"] = None
        
        from app.db.session import get_sync_db
        from app.services.article_service import ArticleService
        
        # 使用同步的資料庫會話
        db = get_sync_db()
        try:
            article_service = ArticleService()
            processed_articles, processed_count, total_pending = article_service.process_pending_articles_sync(db, limit)
            
            result_message = f"處理了 {processed_count} 篇文章，還剩 {total_pending - processed_count} 篇待處理"
            logger.info(f"背景任務完成：{result_message}")
            
            # 更新任務結果
            task_status["process_pending"]["result"] = {
                "processed_count": processed_count,
                "remaining": total_pending - processed_count,
                "completed_at": datetime.now()
            }
                
        finally:
            db.close()
            
    except Exception as e:
        error_message = f"背景處理文章時發生錯誤: {str(e)}"
        logger.error(error_message)
        # 記錄錯誤
        task_status["process_pending"]["error"] = error_message
    finally:
        # 標記任務完成
        task_status["process_pending"]["is_running"] = False

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

@router.get("/process-pending/status")
async def get_process_pending_status():
    """獲取文章處理任務的狀態"""
    return task_status["process_pending"]

@router.post("/latest-summaries-legacy")
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

@router.post("/latest-summaries")
async def generate_latest_summaries_by_sections(
    background_tasks: BackgroundTasks,
    source: str,
    fetch_limit: Optional[int] = 30,
    summary_limit: Optional[int] = 20,
    db: Session = Depends(get_session)
) -> LatestSummariesResponse:
    """生成最新的分類摘要（非阻塞）"""
    
    def generate_summary_background(source: str, fetch_limit: int, summary_limit: int):
        try:
            from app.db.session import get_sync_db
            
            # 使用同步的資料庫會話
            db = get_sync_db()
            try:
                summary_service = SummaryService()
                latest_summary, selected_articles = summary_service.generate_category_summary_by_sections_sync(
                    db=db,
                    source=source,
                    fetch_limit=fetch_limit,
                    summary_limit=summary_limit
                )
                
                if latest_summary:
                    created_at_epoch = int(latest_summary.created_at.timestamp())
                    cache_data = {
                        "source": latest_summary.source,
                        "summary": latest_summary.summary,
                        "created_at": created_at_epoch,
                        "title": latest_summary.title,
                        "related": latest_summary.related
                    }
                    summary_cache.set(source, cache_data)
                    logger.info(f"Background task: Summary generated and cached for {source}")
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Background task error: {str(e)}")

    # 驗證 source
    allowed_sources = ["TW_Stock_Summary", "US_Stock_Summary", "Hot_News_Summary"]
    if source not in allowed_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Allowed values are: {', '.join(allowed_sources)}"
        )

    # 將摘要生成加入背景任務
    background_tasks.add_task(
        generate_summary_background,
        source,
        fetch_limit,
        summary_limit
    )
    
    # 檢查是否有快取的摘要
    cached_summary = summary_cache.get(source)
    
    return LatestSummariesResponse(
        message=f"Summary generation for {source} started in background",
        source=source,
        count=0,
        articles=[],
        current_summary=cached_summary  # 返回目前的快取摘要
    )

@router.post("/process-hot-news-pending", response_model=ProcessPendingResponse)
async def process_hot_news_pending(
    limit: Optional[int] = 150,
    db: Session = Depends(get_session)
) -> ProcessPendingResponse:
    """
    處理待處理的熱門新聞文章
    
    Args:
        limit: 最大處理文章數量，預設為 150
        db: 資料庫連線
        
    Returns:
        ProcessPendingResponse: 處理結果，包含：
            - 處理訊息
            - 待處理文章總數
            - 本次處理數量
            - 處理完成的文章列表
    """
    try:
        article_service = ArticleService()
        processed_articles, processed_count, total_pending = (
            await article_service.process_hot_news_articles(db, limit)
        )
        
        return ProcessPendingResponse(
            message=f"成功處理 {processed_count} 篇熱門新聞，還有 {total_pending - processed_count} 篇待處理",
            total_pending=total_pending,
            processed_count=processed_count,
            processed_articles=[
                ProcessedArticleResponse.from_orm(article)
                for article in processed_articles
            ]
        )
    except Exception as e:
        logger.error(f"處理熱門新聞時發生錯誤: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"處理熱門新聞時發生錯誤: {str(e)}"
        )