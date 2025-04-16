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
        
        # TODO: 未來應將這些類別設定移到配置文件中
        source_categories = {
            "Hot_News_Summary": ["全球宏觀", "經濟發展趨勢", "地緣政治局勢"],
            "TW_Stock_Summary": ["外資台股大盤買賣超"]
        }
        
        # TODO: 未來應將文章處理邏輯拆分到獨立的處理器中
        for i, article in enumerate(pending_articles):
            if article.source in source_categories:
                article_content = f"標題：{article.title}\n內容：{article.news_content}"
                matched_categories = []
                
                # 檢查文章類別
                for category in source_categories[article.source]:
                    if await self.summary_generator.check_is_category(article_content, category):
                        matched_categories.append(category)
                
                # 直接更新 pending_articles 中的 tags
                if matched_categories:
                    # 記錄修改前的 tags
                    logger.info(f"修改前 - 文章 {article.news_id} 的 tags: {article.tags}")
                    
                    article.tags = matched_categories
                    # 驗證修改是否生效
                    logger.info(f"修改後 - 文章 {article.news_id} 的 tags: {pending_articles[i].tags}")
        
        # 再次驗證所有文章的 tags
        for article in pending_articles:
            if article.source in source_categories:
                logger.info(f"最終檢查 - 文章 {article.news_id} 的 tags: {article.tags}")
        
        # 保持原有的處理邏輯
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

    async def process_hot_news_articles(
        self, 
        db, 
        limit: int = 150
    ) -> Tuple[List[ProcessedArticle], int, int]:
        """
        處理熱門新聞文章，使用特殊規則：
        1. 檢查文章是否屬於特定熱門類別
        2. 只處理最新的未處理文章
        3. 生成更簡短、吸引人的摘要
        """
        try:
            # 獲取待處理文章總數
            total_pending = await self.get_pending_articles_count(db)
            
            # 獲取所有待處理文章
            pending_articles = await self.get_pending_articles(db, limit)
            
            # 篩選出 Hot News 類型的文章
            hot_news_articles = [
                article for article in pending_articles 
                if article.source == "Hot_News_Summary"
            ]
            
            if not hot_news_articles:
                logger.info("沒有找到需要處理的熱門新聞文章")
                return [], 0, total_pending
                
            processed_articles = []
            hot_categories = ["全球宏觀", "經濟發展趨勢", "地緣政治局勢"]
            
            for article in hot_news_articles:
                # 組合文章內容用於分類判斷
                article_content = f"標題：{article.title}\n內容：{article.news_content}"
                
                # 檢查是否屬於任何熱門類別
                is_hot_news = False
                matched_categories = []
                
                for category in hot_categories:
                    if await self.summary_generator.check_is_category(article_content, category):
                        is_hot_news = True
                        matched_categories.append(category)
                
                if not is_hot_news:
                    logger.info(f"文章 {article.news_id} 不屬於任何熱門類別，跳過處理")
                    continue
                    
                # 生成摘要
                summary = await self.summary_generator.generate_summary(article_content)
                
                if not summary:
                    logger.warning(f"無法為文章 {article.news_id} 生成摘要，跳過")
                    continue
                    
                # 創建 ProcessedArticle
                processed_article = ProcessedArticle(
                    raw_article_id=article.id,
                    news_id=article.news_id,
                    title=article.title,
                    content=article.news_content,
                    summary=summary,
                    source=article.source,
                    category_id=article.category_id,
                    category_name=article.category_name,
                    stocks=article.stock,
                    tags=matched_categories,  # 使用新的分類結果作為 tags
                    published_at=datetime.fromtimestamp(article.pub_date) if article.pub_date else datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                processed_articles.append(processed_article)
                
                # 記錄處理結果
                logger.info(
                    f"成功處理熱門新聞 - ID: {article.news_id}, "
                    f"標題: {article.title}, "
                    f"匹配類別: {matched_categories}"
                )
            
            # 批量保存到數據庫
            if processed_articles:
                db.add_all(processed_articles)
                await db.commit()
                
            logger.info(f"完成處理 {len(processed_articles)} 篇熱門新聞")
            return processed_articles, len(processed_articles), total_pending
            
        except Exception as e:
            logger.error(f"處理熱門新聞時發生錯誤: {str(e)}")
            await db.rollback()
            raise 