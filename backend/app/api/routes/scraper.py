from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Dict
from enum import Enum
from sqlmodel import Session
import logging

from app.models.article import RawArticle
from app.scrapers.scheduler import scheduler
from app.scrapers.cnyes import CnyesScraper
from app.db.session import get_session

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrapers", tags=["scrapers"])

class CnyesSource(str, Enum):
    TW = "tw"
    US = "us"
    HEADLINE = "headline"

# Define source mapping
SOURCE_MAPPING = {
    CnyesSource.TW: "TW_Stock_Summary",
    CnyesSource.US: "US_Stock_Summary",
    CnyesSource.HEADLINE: "Hot_News_Summary"
}

@router.post("/cnyes/fetch-articles")
async def fetch_cnyes_articles(
    source_type: CnyesSource,
    db: Session = Depends(get_session)
) -> Dict:
    """
    Fetch articles from Cnyes API and save them to database
    
    Args:
        source_type: Source type (tw, us, headline)
        db: Database session
        
    Returns:
        Dict: API response containing fetched and saved articles info
    """
    try:
        article_source = SOURCE_MAPPING[source_type]
        scraper = CnyesScraper(db=db, source=article_source)
        
        logger.info(f"Fetching and saving articles from Cnyes API for source: {source_type.value}")
        
        # Get and save articles using process_article_list method
        saved_articles = await scraper.process_article_list()
        
        if not saved_articles:
            logger.warning(f"No articles saved from Cnyes API for source: {source_type.value}")
        
        # Return save results
        return {
            "message": f"Successfully processed articles from {source_type.value}",
            "source": source_type.value,
            "total_saved": len(saved_articles),
            "saved_articles": [
                {
                    "news_id": article.news_id,
                    "title": article.title,
                    "category_name": article.category_name,
                    "pub_date": article.pub_date,
                    "creator": article.creator,
                    "status": article.status
                }
                for article in saved_articles
            ]
        }
    except Exception as e:
        error_msg = f"Error processing articles from Cnyes API: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )