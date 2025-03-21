"""
Base class for summary generators
"""

from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from sqlmodel import select
import logging

from app.models.article import RawArticle, ProcessedArticle
from app.ai.providers import AzureOpenAIClient

logger = logging.getLogger(__name__)

class BaseSummaryGenerator(ABC):
    """Base class for all summary generators"""
    
    def __init__(self):
        """Initialize the summary generator with AI client"""
        self.ai_client = AzureOpenAIClient()

    @abstractmethod
    async def generate_summary(self, content: str) -> str:
        """
        Generate summary using AI model
        
        Args:
            content: Content to summarize
            
        Returns:
            str: Generated summary
        """
        pass

    async def process_articles(self, db, articles: List[RawArticle]) -> List[ProcessedArticle]:
        """
        Process articles and generate summaries
        
        Args:
            db: Database session
            articles: List of articles to process
            
        Returns:
            List[ProcessedArticle]: List of processed articles
        """
        processed_articles = []
        for article in articles:
            try:
                # Check if already processed
                if await self._is_article_processed(db, article.id):
                    continue
                    
                # Generate summary
                summary = await self.generate_summary(article.news_content)
                
                # Create processed article
                processed_article = await self._create_processed_article(db, article, summary)
                processed_articles.append(processed_article)
                
            except Exception as e:
                logger.error(f"Error processing article {article.id}: {str(e)}")
                continue
                
        await db.commit()
        return processed_articles

    async def _is_article_processed(self, db, raw_article_id: int) -> bool:
        """
        Check if article is already processed
        
        Args:
            db: Database session
            raw_article_id: ID of the raw article
            
        Returns:
            bool: True if article is already processed
        """
        result = await db.execute(
            select(ProcessedArticle)
            .where(ProcessedArticle.raw_article_id == raw_article_id)
        )
        return result.first() is not None

    async def _create_processed_article(
        self, 
        db, 
        raw_article: RawArticle, 
        summary: str
    ) -> ProcessedArticle:
        """
        Create processed article entry
        
        Args:
            db: Database session
            raw_article: Raw article to process
            summary: Generated summary
            
        Returns:
            ProcessedArticle: Created processed article
        """
        processed = ProcessedArticle(
            raw_article_id=raw_article.id,
            news_id=raw_article.news_id,
            title=raw_article.title,
            content=raw_article.news_content,
            summary=summary,
            source=raw_article.source,
            category_id=raw_article.category_id,
            category_name=raw_article.category_name,
            stocks=raw_article.stock,
            tags=raw_article.tags,
            published_at=datetime.fromtimestamp(raw_article.pub_date) if raw_article.pub_date else datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(processed)
        return processed
