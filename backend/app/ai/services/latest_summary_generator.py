import logging
from typing import List, Dict
from datetime import datetime
from sqlmodel import select
from uuid import UUID

from app.models.article import RawArticle, LatestSummary
from ..providers import AzureOpenAIClient

logger = logging.getLogger(__name__)

class LatestSummaryGenerator:
    """Latest news summary generation service"""
    
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
    
    def __init__(self):
        self.ai_client = AzureOpenAIClient()
        
    async def generate_category_summary(
        self,
        articles: List[RawArticle],
        source_type: str
    ) -> str:
        """
        Generate summary for a specific news category
        
        Args:
            articles: List of news articles
            source_type: Source type
            
        Returns:
            str: Generated summary
        """
        try:
            # Prepare article content
            article_texts = []
            for article in articles:
                article_texts.append(f"標題：{article.title}\n內容：{article.news_content}\n")
            
            combined_text = "\n---\n".join(article_texts)
            
            messages = [
                {
                    "role": "system",
                    "content": f"""你是一個專業的{source_type}新聞摘要生成器。請針對提供的多篇新聞內容生成一個整體性的摘要報告，需要：
1. 使用流暢的文字總結主要市場動態和重要新聞，在一個段落內。
2. 嚴格限制字數不能超過500字元
3. 重點摘要新聞中提到的具體數據和重要變化
4. 摘要內容應該完整且前後連貫
5. 簡單的 html 格式:<p> summary content </p> <p> power by Yushan AI </p>"""
                },
                {
                    "role": "user",
                    "content": combined_text
                }
            ]
            
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=4000
            )
            
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating category summary: {str(e)}")
            return ""
            
    async def process_latest_news(
        self,
        db,
        limit: int = 10,
        source_type: str = "TW_Stock_Summary"
    ) -> LatestSummary:
        """
        Process latest news and generate summary
        
        Args:
            db: Database session
            limit: Number of articles to process
            source_type: Summary source type
            
        Returns:
            LatestSummary: Generated summary
        """
        try:
            # Validate source_type
            if source_type not in self.ALLOWED_SOURCES:
                logger.error(f"Invalid source_type: {source_type}")
                return None
                
            # Query latest news articles
            statement = (
                select(RawArticle)
                .where(RawArticle.source == source_type)
                .order_by(RawArticle.pub_date.desc())
                .limit(limit)
            )
            articles = (await db.execute(statement)).scalars().all()
            
            if not articles:
                logger.warning(f"No news found for source {source_type}")
                return None
                
            # Generate summary
            summary = await self.generate_category_summary(articles, source_type)
            
            # Get corresponding title
            title = self.SOURCE_TITLE_MAPPING.get(source_type, f"{source_type} Latest Updates")
            
            # Prepare related news list
            related = [
                {
                    "newsId": str(article.news_id),
                    "title": article.title
                }
                for article in articles
            ]
            
            # Check if summary for this category already exists
            existing = await db.execute(
                select(LatestSummary)
                .where(LatestSummary.source == source_type)
            )
            existing = existing.first()
            
            if existing:
                # Update existing summary
                existing = existing[0]
                existing.summary = summary
                existing.title = title
                existing.related = related
                existing.updated_at = datetime.utcnow()
                latest_summary = existing
            else:
                # Create new summary
                latest_summary = LatestSummary(
                    source=source_type,
                    title=title,
                    summary=summary,
                    related=related
                )
                db.add(latest_summary)
            
            await db.commit()
            return latest_summary
            
        except Exception as e:
            logger.error(f"Error processing latest news: {str(e)}")
            await db.rollback()
            raise