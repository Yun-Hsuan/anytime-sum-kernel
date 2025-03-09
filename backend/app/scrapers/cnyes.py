import httpx
from typing import Dict, List
from datetime import datetime, timezone
from sqlmodel import select
import logging
import os
import json
from pathlib import Path

from app.models.article import RawArticle
from .base import BaseScraper
from app.models.enums import CnyesSource

logger = logging.getLogger(__name__)

def load_mock_data() -> Dict:
    """
    Load mock data from JSON file
    """
    try:
        mock_file = Path(__file__).parent / "mock_data" / "cnyes_mock.json"
        if not mock_file.exists():
            logger.error(f"Mock data file not found: {mock_file}")
            return {"statusCode": 200, "message": "OK", "data": []}
            
        with open(mock_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading mock data: {str(e)}")
        return {"statusCode": 200, "message": "OK", "data": []}

class CnyesScraper(BaseScraper):
    """
    Scraper for Cnyes articles using B2B API
    Handles fetching and storing articles from Cnyes financial news platform
    """
    BASE_URL = "https://openapi.api.cnyes.com/openapi/api/v1"
    ENDPOINT = "/news/categoryB2B"
    
    # API auth tokens for different sources
    SOURCE_AUTH_TOKENS = {
        "TW_Stock_Summary": "B2ByushanAI88xsfqa2QyesTW",
        "US_Stock_Summary": "B2ByushanAI88xsfqa2QyesUS",
        "Hot_News_Summary": "B2ByushanAI88xsfqa2QyesHL",
    }
    
    def __init__(self, db, source="TW_Stock_Summary"):
        source_enum = CnyesSource(source)  # 將字符串轉換為枚舉
        super().__init__(source=source_enum, db=db)
        self.auth_token = self.SOURCE_AUTH_TOKENS.get(source)
        if not self.auth_token:
            raise ValueError(f"Invalid source: {source}")
            
        self.headers = {
            "Authorization": self.auth_token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        logger.info(f"Initialized CnyesScraper for source: {source} with token: {self.auth_token}")
    
    async def fetch_article_list(self, **kwargs) -> List[Dict]:
        """
        Fetch latest articles from B2B API based on the source type
        
        Returns:
            List[Dict]: List of article data from the API
        
        Raises:
            HTTPError: If the API request fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.BASE_URL}{self.ENDPOINT}"
            logger.info(f"Making request to {url} with source {self.source}")
            logger.info(f"Using auth token: {self.auth_token}")
            
            try:
                response = await client.get(url, headers=self.headers)
                logger.info(f"Response status code: {response.status_code}")
                logger.info(f"Response headers: {response.headers}")
                logger.info(f"Raw response: {response.text}")
                
                try:
                    data = response.json()
                    logger.info(f"Parsed response data: {json.dumps(data, indent=2, ensure_ascii=False)}")
                except ValueError as e:
                    logger.error(f"Failed to parse JSON response: {str(e)}")
                    return []
               
                if not data.get("data"):
                    logger.warning(f"Empty data array in API response for source {self.source}")
                    logger.info("Using mock data instead")
                    mock_data = load_mock_data()
                    logger.debug(f"Using mock data: {mock_data}")
                    return mock_data.get("data", [])
                
                if data.get("statusCode") != 200:
                    logger.error(f"API returned error status: {data.get('statusCode')}, message: {data.get('message')}")
                    return []
                
                articles = data.get("data", [])
                logger.info(f"Successfully fetched {len(articles)} articles from {self.source} API")
                logger.info(f"First article sample: {json.dumps(articles[0] if articles else {}, indent=2, ensure_ascii=False)}")
                return articles
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP Error from {self.source} API: {str(e)}")
                logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response'}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error from {self.source} API: {str(e)}")
                raise
    
    async def fetch_article_content(self, news_id: str) -> Dict:
        """
        Fetch full content of a specific article
        Note: For Cnyes API, we don't need to fetch content separately as it's included in the list response
        
        Args:
            news_id: Article ID
            
        Returns:
            Dict: Empty dict as content is already included in list response
        """
        return {}
        
    async def save_raw_article(self, article_data: Dict) -> RawArticle:
        """
        Save raw article data to database with news_id and title fields
        """
        if not self.db:
            logger.error("Database session is not initialized")
            raise ValueError("Database session is not initialized")
        
        news_id = str(article_data.get("newsId"))
        if not news_id:
            logger.warning("Skipping article with no news_id")
            return None
        
        try:
            # 檢查是否已存在相同的 news_id 和 source
            stmt = select(RawArticle).where(
                RawArticle.news_id == news_id,
                RawArticle.source == self.source.value
            )
            result = await self.db.execute(stmt)
            existing_article = result.first() if result else None
            
            if existing_article:
                logger.info(f"Article with news_id {news_id} and source {self.source.value} already exists, skipping")
                return None

            # Create article with all fields
            logger.debug(f"Creating article with source: {self.source}")
            article = RawArticle(
                news_id=news_id,
                source=self.source.value,  # 使用枚舉的值而不是枚舉本身
                title=article_data.get("title", ""),  # Use empty string if not present
                copyright=article_data.get("copyright", ""),  # Use empty string if not present  
                creator=article_data.get("creator", ""),  # Use empty string if not present
                category_id=article_data.get("categoryId", 0),  # Use 0 if not present
                category_name=article_data.get("categoryName", ""),  # Use empty string if not present
                pub_date=article_data.get("pubDate", 0),  # Use 0 if not present
                news_content=article_data.get("newsContent", ""),  # Add news_content field
                stock=article_data.get("stock", []),  # Add stock field, default empty list
                tags=article_data.get("tags", [])  # Add tags field, default empty list
            )
            
            logger.debug(f"Created article object with news_id: {news_id}")
            self.db.add(article)
            
            try:
                await self.db.commit()
                await self.db.refresh(article)
                logger.info(f"Successfully saved article {news_id}")
                return article
            except Exception as commit_error:
                logger.error(f"Failed to commit article {news_id}: {str(commit_error)}")
                await self.db.rollback()
                raise
            
        except Exception as e:
            logger.error(f"Failed to save article {news_id}: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            await self.db.rollback()
            raise
    
    async def process_article_list(self, **kwargs) -> List[RawArticle]:
        """
        Fetch and save a list of articles
        """
        try:
            logger.debug("Starting process_article_list in CnyesScraper")
            articles = await self.fetch_article_list(**kwargs)
            logger.debug(f"Fetched {len(articles)} articles")
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
            
            logger.info(f"Successfully processed {len(saved_articles)} new articles")
            return saved_articles
        except Exception as e:
            logger.error(f"Error in process_article_list: {str(e)}")
            raise 