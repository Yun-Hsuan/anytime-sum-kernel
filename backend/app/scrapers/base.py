from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from sqlmodel import Session, select
from sqlalchemy import and_
import logging

from app.models.article import RawArticle, ArticleStatus
from app.models.enums import CnyesSource

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    Base scraper class that defines the interface for all scrapers
    """
    def __init__(self, source: CnyesSource, db: Session):
        self.source = source
        self.db = db
        logger.debug(f"Initializing BaseScraper with source: {source}")
        logger.debug(f"Source type: {type(source)}")
        logger.debug(f"Database session type: {type(db)}")

    async def check_article_exists(self, news_id: str) -> bool:
        """
        檢查文章是否已存在
        
        Args:
            news_id: 文章ID
            
        Returns:
            bool: 如果文章已存在返回 True，否則返回 False
        """
        print("==== USING BASE CLASS check_article_exists ====")
        print(f"Checking article: news_id={news_id}, source={self.source.value}")
        
        existing_article = await self.db.execute(
            select(RawArticle).where(
                and_(
                    RawArticle.news_id == news_id,
                    RawArticle.source == self.source.value  # 使用枚舉的值而不是枚舉本身
                )
            )
        )
        result = await existing_article.first()
        if result:
            print(f"Found existing article: {result}")
            logger.debug(f"Found existing article - news_id: {news_id}, source: {self.source.value}")
        print("============================================")
        return result is not None
        
    @abstractmethod
    async def fetch_article_list(self, **kwargs) -> List[Dict]:
        """
        Fetch list of articles from the source
        """
        print("--------------------------------")
        print("Executing fetch_article_list in BaseScraper")
        print("--------------------------------")
        pass
    
    @abstractmethod
    async def fetch_article_content(self, news_id: str) -> Dict:
        """
        Fetch full content of a specific article
        Returns the complete article data
        """
        pass
    
    async def save_raw_article(self, article_data: Dict) -> RawArticle:
        """
        Save raw article data to database with only news_id field
        """
        print("==== USING BASE CLASS save_raw_article ====")
        logger.debug("Starting save_raw_article in BaseScraper")
        logger.debug(f"Current source value: {self.source}")
        logger.debug(f"Current source type: {type(self.source)}")
        
        if not self.db:
            logger.error("Database session is not initialized")
            raise ValueError("Database session is not initialized")
        
        news_id = str(article_data.get("newsId"))
        if not news_id:
            logger.warning("Skipping article with no news_id")
            return None
            
        try:
            # 檢查文章是否已存在
            if await self.check_article_exists(news_id):
                logger.info(f"Article with news_id {news_id} and source {self.source} already exists, skipping")
                return None

            # Create article with all fields
            logger.debug(f"Creating article with source: {self.source}")
            print(f"Creating new article: news_id={news_id}, source={self.source.value}")
            
            article = RawArticle(
                news_id=news_id,
                source=self.source.value,  # 使用枚舉的值而不是枚舉本身
                title=article_data.get("title", ""),  # 如果沒有則使用空字符串
                copyright=article_data.get("copyright", ""),  # 如果沒有則使用空字符串
                creator=article_data.get("creator", ""),  # 如果沒有則使用空字符串
                category_id=article_data.get("categoryId", 0),  # 如果沒有則使用 0
                category_name=article_data.get("categoryName", ""),  # 如果沒有則使用空字符串
                pub_date=article_data.get("pubDate", 0),  # 如果沒有則使用 0
                news_content=article_data.get("newsContent", ""),  # 添加 news_content 字段
                stock=article_data.get("stock", []),  # 添加 stock 字段，默認為空列表
                tags=article_data.get("tags", [])  # 添加 tags 字段，默認為空列表
            )
            
            logger.debug(f"Created article object with news_id: {news_id}")
            self.db.add(article)
            logger.debug("Added article to session")
            
            await self.db.commit()
            logger.debug("Committed to database")
            
            await self.db.refresh(article)
            logger.debug("Refreshed article from database")
            print("============================================")
            
            return article
            
        except Exception as e:
            logger.error(f"Error in save_raw_article: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            await self.db.rollback()
            raise
    
    async def process_article_list(self, **kwargs) -> List[RawArticle]:
        """
        Fetch and save a list of articles
        """
        print("--------------------------------")
        print("Executing process_article_list in BaseScraper")
        print("--------------------------------")
        
        logger.debug("Starting process_article_list")
        articles = await self.fetch_article_list(**kwargs)
        
        print("--------------------------------")
        print(f"Fetched articles: {articles}")
        print("--------------------------------")
        
        saved_articles = []
        
        for article_data in articles:
            try:
                saved_article = await self.save_raw_article(article_data)
                if saved_article:
                    saved_articles.append(saved_article)
            except Exception as e:
                news_id = str(article_data.get("newsId", "unknown"))
                logger.error(f"Error processing article {news_id}: {str(e)}")
                continue
        
        return saved_articles 