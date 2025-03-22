"""
Summary generation related business logic
"""

from typing import List, Tuple
from datetime import datetime
from sqlmodel import select
import logging

from app.models.article import ProcessedArticle, LatestSummary
from app.ai.services.summary_generator.category import CategorySummaryGenerator
from app.services.article_selector_service import article_selector_service

logger = logging.getLogger(__name__)

class SummaryService:
    """Service for summary related business logic"""
    
    # 來源類型映射
    SOURCE_TYPE_MAPPING = {
        "TW_Stock_Summary": "tw",
        "US_Stock_Summary": "us",
        "Hot_News_Summary": "headline"
    }
    
    def __init__(self):
        self.category_generator = CategorySummaryGenerator()

    async def get_latest_articles_by_source(
        self,
        db,
        source: str,
        fetch_limit: int = 30
    ) -> List[ProcessedArticle]:
        """
        Get latest articles from specified source
        
        Args:
            db: Database session
            source: Article source (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
            fetch_limit: Limit for number of articles to fetch
            
        Returns:
            List[ProcessedArticle]: List of latest articles
        """
        statement = (
            select(ProcessedArticle)
            .where(ProcessedArticle.source == source)
            .order_by(ProcessedArticle.published_at.desc())
            .limit(fetch_limit)
        )
        return (await db.execute(statement)).scalars().all()

    def select_articles_for_summary(
        self,
        articles: List[ProcessedArticle],
        source: str,
        limit: int = 15
    ) -> List[ProcessedArticle]:
        """
        使用對應的選擇器選擇文章
        
        Args:
            articles: 候選文章列表
            source: 來源類型 (TW_Stock_Summary etc.)
            limit: 選擇數量限制
            
        Returns:
            List[ProcessedArticle]: 選中的文章列表
        """
        logger.info(f"開始選擇文章 - 來源: {source}, 候選文章數量: {len(articles)}")
        
        # 轉換來源類型
        selector_type = self.SOURCE_TYPE_MAPPING.get(source)
        if not selector_type:
            logger.error(f"未知的來源類型: {source}")
            raise ValueError(f"Unknown source type: {source}")
        
        logger.info(f"來源類型映射: {source} -> {selector_type}")
        
        # 獲取對應的選擇器
        try:
            selector = article_selector_service.get_selector(selector_type)
            logger.info(f"成功獲取選擇器: {selector.__class__.__name__}")
        except Exception as e:
            logger.error(f"獲取選擇器失敗: {str(e)}")
            raise
        
        # 記錄候選文章的詳細信息
        logger.info("候選文章詳細信息:")
        for idx, article in enumerate(articles, 1):
            # 使用 getattr 安全地獲取屬性，如果不存在則返回 'N/A'
            article_info = {
                'ID': article.news_id,
                '標題': article.title,
                '來源': article.source,
                '發布時間': article.published_at,
                '更新時間': article.updated_at,
                '摘要': f"{article.summary[:100]}..." if article.summary else 'N/A',
                '內容': f"{article.content[:100]}..." if article.content else 'N/A',
                '標籤': getattr(article, 'tags', 'N/A'),
                '股票代碼': getattr(article, 'stock_codes', 'N/A'),
                '相關股票': getattr(article, 'related_stocks', 'N/A')
            }
            
            log_message = f"文章 {idx}:\n" + "\n".join(
                f"  {key}: {value}" for key, value in article_info.items()
            ) + "\n  ----------------------"
            
            logger.info(log_message)
        
        # 使用選擇器選擇文章
        try:
            selected = selector.select_articles(articles, limit)
            logger.info(f"選擇完成，選中 {len(selected)} 篇文章")
            
            # 記錄選中的文章
            if selected:
                logger.info("選中的文章列表:")
                for idx, article in enumerate(selected, 1):
                    logger.info(f"選中文章 {idx}: ID={article.news_id}, 標題={article.title}")
            else:
                logger.warning("沒有文章被選中！")
            
            return selected
        except Exception as e:
            logger.error(f"文章選擇過程發生錯誤: {str(e)}")
            raise

    def prepare_content_for_summary(self, articles: List[ProcessedArticle]) -> List[dict]:
        """
        Prepare content for summary generation, including complete article links
        
        Args:
            articles: List of selected articles
            
        Returns:
            List[dict]: List of complete article information
        """
        return [
            {
                'title': article.title,
                'summary': article.summary,
                'news_id': article.news_id,
                'url': f"https://news.cnyes.com/news/id/{article.news_id}"
            }
            for article in articles
        ]

    async def generate_category_summary(
        self,
        db,
        source: str,
        fetch_limit: int = 30,
        summary_limit: int = 15
    ) -> Tuple[LatestSummary, List[ProcessedArticle]]:
        """
        Generate category summary
        
        Args:
            db: Database session
            source: Article source (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
            fetch_limit: Initial fetch limit
            summary_limit: Final selection limit
            
        Returns:
            Tuple[LatestSummary, List[ProcessedArticle]]:
                - Generated category summary
                - List of selected articles
        """
        logger.info(f"開始生成分類摘要 - 來源: {source}, 獲取限制: {fetch_limit}, 摘要限制: {summary_limit}")
        
        # 1. Get latest articles
        try:
            latest_articles = await self.get_latest_articles_by_source(
                db, source, fetch_limit
            )
            logger.info(f"從數據庫獲取到 {len(latest_articles) if latest_articles else 0} 篇文章")
            
            if not latest_articles:
                logger.warning(f"未找到來源為 {source} 的文章")
                return None, []
        except Exception as e:
            logger.error(f"獲取最新文章時發生錯誤: {str(e)}")
            raise

        # 2. Select articles to include
        try:
            selected_articles = self.select_articles_for_summary(
                latest_articles, 
                source,
                summary_limit
            )
            logger.info(f"完成文章選擇，選中 {len(selected_articles)} 篇文章")
        except Exception as e:
            logger.error(f"選擇文章時發生錯誤: {str(e)}")
            raise

        # 3. Prepare content
        try:
            prepared_articles = self.prepare_content_for_summary(selected_articles)
            logger.info(f"完成文章內容準備，處理了 {len(prepared_articles)} 篇文章")
        except Exception as e:
            logger.error(f"準備文章內容時發生錯誤: {str(e)}")
            raise

        # 4. Generate summary
        try:
            summary = await self.category_generator.generate_summary(
                content=prepared_articles,
                source_type=source
            )
            logger.info("成功生成摘要")
        except Exception as e:
            logger.error(f"生成摘要時發生錯誤: {str(e)}")
            raise

        # 5. Create or update LatestSummary
        try:
            latest_summary = LatestSummary(
                source=source,
                title=f"{source} 最新動態",
                summary=summary,
                related=[
                    {
                        "newsId": str(article.news_id),
                        "title": article.title
                    }
                    for article in selected_articles
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(latest_summary)
            await db.commit()
            logger.info("成功保存最新摘要到數據庫")
            
            return latest_summary, selected_articles
        except Exception as e:
            logger.error(f"保存摘要時發生錯誤: {str(e)}")
            raise 