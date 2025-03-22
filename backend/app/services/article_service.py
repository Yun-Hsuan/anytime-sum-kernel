"""
Article related business logic
"""

from typing import List, Tuple
from sqlmodel import select, func
import logging
from datetime import datetime

from app.models.article import RawArticle, ProcessedArticle
from app.ai.services.summary_generator.article import SingleArticleSummaryGenerator

logger = logging.getLogger(__name__)

class ArticleService:
    """文章相關的業務邏輯服務"""
    
    def __init__(self):
        self.summary_generator = SingleArticleSummaryGenerator()
    
    async def get_pending_articles_count(self, db) -> int:
        """
        獲取待處理文章的總數
        
        Args:
            db: 數據庫會話
            
        Returns:
            int: 待處理文章總數
        """
        # 子查詢：已處理的文章 ID
        processed_subquery = (
            select(ProcessedArticle.raw_article_id)
        )
        
        # 計算未處理的文章數量
        statement = (
            select(func.count())
            .select_from(RawArticle)
            .where(~RawArticle.id.in_(processed_subquery))
        )
        
        result = await db.execute(statement)
        return result.scalar()
    
    async def get_pending_articles(self, db, limit: int = 150) -> List[RawArticle]:
        """
        獲取待處理的文章（存在於 RawArticle 但不存在於 ProcessedArticle 的文章）
        
        Args:
            db: 數據庫會話
            limit: 獲取數量限制
            
        Returns:
            List[RawArticle]: 待處理的文章列表
        """
        # 子查詢：獲取已處理的文章 ID
        processed_subquery = (
            select(ProcessedArticle.raw_article_id)
        )
        
        # 主查詢：獲取未處理的文章
        statement = (
            select(RawArticle)
            .where(~RawArticle.id.in_(processed_subquery))
            .order_by(RawArticle.created_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(statement)
        return result.scalars().all()
    
    async def process_pending_articles(
        self, 
        db, 
        limit: int = 150
    ) -> Tuple[List[ProcessedArticle], int, int]:
        """
        處理待處理的文章
        
        Args:
            db: 數據庫會話
            limit: 處理數量限制
            
        Returns:
            Tuple[List[ProcessedArticle], int, int]: 
                - 處理後的文章列表
                - 本次處理數量
                - 待處理總數
        """
        # 獲取待處理文章總數
        total_pending = await self.get_pending_articles_count(db)
        
        # 獲取待處理文章
        pending_articles = await self.get_pending_articles(db, limit)
        if not pending_articles:
            return [], 0, total_pending
            
        # 生成摘要
        processed_articles = await self.summary_generator.process_articles(
            db, 
            pending_articles
        )
        
        return processed_articles, len(processed_articles), total_pending
        
    async def get_latest_processed_articles(
        self,
        db,
        category: str,
        limit: int = 15
    ) -> List[ProcessedArticle]:
        """
        獲取最新的已處理文章
        
        Args:
            db: 數據庫會話
            category: 文章類別
            limit: 獲取數量限制
            
        Returns:
            List[ProcessedArticle]: 已處理的文章列表
        """
        statement = (
            select(ProcessedArticle)
            .where(ProcessedArticle.category_name == category)
            .order_by(ProcessedArticle.published_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(statement)
        return result.scalars().all() 