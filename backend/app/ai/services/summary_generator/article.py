"""
Single article summary generator
"""

from typing import List
from sqlmodel import select
import logging

from .base import BaseSummaryGenerator
from app.models.article import RawArticle, ProcessedArticle
from .prompts.article import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class SingleArticleSummaryGenerator(BaseSummaryGenerator):
    """Generator for single article summaries"""
    
    async def generate_summary(self, content: str) -> str:
        """
        Generate summary for a single article
        
        Args:
            content: Article content
            
        Returns:
            str: Generated summary
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=1200
            )
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating article summary: {str(e)}")
            return ""

    async def process_latest_articles(self, db, limit: int = 15) -> List[ProcessedArticle]:
        """
        Process latest unprocessed articles
        
        Args:
            db: Database session
            limit: Number of articles to process
            
        Returns:
            List[ProcessedArticle]: List of processed articles
        """
        # Query latest unprocessed articles
        statement = (
            select(RawArticle)
            .order_by(RawArticle.created_at.desc())
            .limit(limit)
        )
        articles = (await db.execute(statement)).scalars().all()
        return await self.process_articles(db, articles)
