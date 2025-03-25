"""
Category summary generator
"""

from typing import List, Dict
from datetime import datetime
from sqlmodel import select
import logging

from .base import BaseSummaryGenerator
from app.models.article import RawArticle, LatestSummary
from .prompts.category import get_system_prompt
from .prompts.title import TITLE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class CategorySummaryGenerator(BaseSummaryGenerator):
    """Generator for category-based summaries"""
    
    # Define allowed source types
    ALLOWED_SOURCES = {
        "TW_Stock_Summary",  # Taiwan stock news
        "US_Stock_Summary",  # US stock news 
        "Hot_News_Summary"   # Hot news
    }
    
    # Define source title mapping
    SOURCE_TITLE_MAPPING = {
        "TW_Stock_Summary": "台股市場最新動態",
        "US_Stock_Summary": "美股市場最新動態",
        "Hot_News_Summary": "財經熱門新聞"
    }

    async def generate_summary(self, content: List[dict], source_type: str) -> str:
        """
        Generate summary for multiple articles
        
        Args:
            content: List of article dictionaries, each containing:
                    - title: article title
                    - summary: article summary
                    - news_id: article ID
                    - url: complete article URL
            source_type: Type of news source
            
        Returns:
            str: Generated summary
        """
        try:
            # 將 List[dict] 轉換為適合 prompt 的格式
            formatted_content = []
            for article in content:
                formatted_content.append(
                    f"文章ID：{article['news_id']}\n"
                    f"標題：{article['title']}\n"
                    f"內容：{article['summary']}\n"
                    f"連結：{article['url']}"
                )
            
            # 組合所有文章內容
            combined_content = "\n\n".join(formatted_content)
            
            print(combined_content)
            messages = [
                {
                    "role": "system",
                    "content": get_system_prompt(source_type)
                },
                {
                    "role": "user",
                    "content": combined_content
                }
            ]
            
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=1200
            )
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating category summary: {str(e)}")
            raise ValueError(f"生成摘要失敗: {str(e)}")  # 改為拋出異常而不是返回空字符串

    async def process_category_summary(
        self,
        db,
        source_type: str,
        fetch_limit: int = 30,
        process_limit: int = 15
    ) -> LatestSummary:
        """
        Generate category summary from latest articles
        
        Args:
            db: Database session
            source_type: Type of news source
            fetch_limit: Number of latest articles to fetch
            process_limit: Number of articles to include in summary
            
        Returns:
            LatestSummary: Generated category summary
        """
        if source_type not in self.ALLOWED_SOURCES:
            raise ValueError(f"Invalid source type: {source_type}")

        # Fetch latest articles
        articles = await self._fetch_latest_articles(db, source_type, fetch_limit)
        if not articles:
            return None

        # Select articles for processing
        selected_articles = self._select_articles_for_summary(articles, process_limit)
        
        # Generate summary
        combined_content = self._prepare_articles_content(selected_articles)
        summary = await self.generate_summary(selected_articles, source_type)
        
        # Create or update summary
        return await self._create_or_update_latest_summary(
            db, source_type, summary, selected_articles
        )

    async def _fetch_latest_articles(
        self, 
        db, 
        source_type: str, 
        limit: int
    ) -> List[RawArticle]:
        """
        Fetch latest articles for a category
        
        Args:
            db: Database session
            source_type: Type of news source
            limit: Number of articles to fetch
            
        Returns:
            List[RawArticle]: List of fetched articles
        """
        statement = (
            select(RawArticle)
            .where(RawArticle.source == source_type)
            .order_by(RawArticle.pub_date.desc())
            .limit(limit)
        )
        return (await db.execute(statement)).scalars().all()

    def _select_articles_for_summary(
        self, 
        articles: List[RawArticle], 
        limit: int
    ) -> List[RawArticle]:
        """
        Select articles for summary generation
        
        Args:
            articles: List of articles to select from
            limit: Number of articles to select
            
        Returns:
            List[RawArticle]: Selected articles
        """
        # TODO: Implement more sophisticated selection logic
        return articles[:limit]

    def _prepare_articles_content(self, articles: List[RawArticle]) -> str:
        """
        Prepare articles content for summary generation
        
        Args:
            articles: List of articles to prepare
            
        Returns:
            str: Combined articles content
        """
        article_texts = []
        for article in articles:
            article_texts.append(f"標題：{article.title}\n內容：{article.news_content}\n")
        return "\n---\n".join(article_texts)

    async def _create_or_update_latest_summary(
        self,
        db,
        source_type: str,
        summary: str,
        articles: List[RawArticle]
    ) -> LatestSummary:
        """
        Create or update latest summary
        
        Args:
            db: Database session
            source_type: Type of news source
            summary: Generated summary
            articles: List of related articles
            
        Returns:
            LatestSummary: Created or updated summary
        """
        # Prepare related articles list
        related = [
            {
                "newsId": str(article.news_id),
                "title": article.title
            }
            for article in articles
        ]
        
        # Check if summary exists
        existing = await db.execute(
            select(LatestSummary)
            .where(LatestSummary.source == source_type)
        )
        existing = existing.first()
        
        if existing:
            # Update existing summary
            existing = existing[0]
            existing.summary = summary
            existing.title = self.SOURCE_TITLE_MAPPING[source_type]
            existing.related = related
            existing.updated_at = datetime.utcnow()
            latest_summary = existing
        else:
            # Create new summary
            latest_summary = LatestSummary(
                source=source_type,
                title=self.SOURCE_TITLE_MAPPING[source_type],
                summary=summary,
                related=related
            )
            db.add(latest_summary)
            
        await db.commit()
        return latest_summary

    async def generate_title(self, content: str, source_type: str) -> str:
        """
        Generate title from category summary
        
        Args:
            content: Category summary content
            source_type: Type of news source (TW_Stock_Summary/US_Stock_Summary/Hot_News_Summary)
            
        Returns:
            str: Generated title (max 20 characters)
        """
        try:
            # 添加源類型資訊到內容中以生成更相關的標題
            context = f"新聞類型：{self.SOURCE_TITLE_MAPPING[source_type]}\n摘要內容：{content}"
            
            messages = [
                {
                    "role": "system",
                    "content": TITLE_SYSTEM_PROMPT
                },
                {
                    "role": "user", 
                    "content": context
                }
            ]
            
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=50
            )
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating category title: {str(e)}")
            raise ValueError(f"生成標題失敗: {str(e)}")  # 保持與 generate_summary 一致的錯誤處理方式
