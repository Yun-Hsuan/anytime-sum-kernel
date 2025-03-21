import asyncio
from datetime import datetime, time
import logging
from typing import Optional
from sqlmodel import Session
from app.db.session import async_session
from app.models.enums import CnyesSource
from app.scrapers.cnyes import CnyesScraper
from app.services.summary_service import SummaryService

logger = logging.getLogger(__name__)

class NewsScheduler:
    """News Scheduling System"""
    
    def __init__(self):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.current_start_time: Optional[time] = None
        self.current_end_time: Optional[time] = None
        self.current_freq: Optional[int] = None
        
    async def _process_source(self, source: CnyesSource, db: Session):
        """Process news from a single source"""
        try:
            # 1. Fetch news
            scraper = CnyesScraper(db=db)
            saved_articles = await scraper.process_article_list()
            logger.info(f"Fetched {len(saved_articles)} articles from {source.value}")
            
            # 2. Generate article summaries
            if saved_articles:
                summary_service = SummaryService()
                processed_count = await summary_service.process_pending_articles(db)
                logger.info(f"Generated {processed_count} article summaries for {source.value}")
                
        except Exception as e:
            logger.error(f"Error processing {source.value}: {str(e)}")
    
    async def _process_latest_summaries(self, db: Session):
        """Generate latest summaries for all sources"""
        try:
            summary_service = SummaryService()
            source_types = ["TW_Stock_Summary", "US_Stock_Summary", "Hot_News_Summary"]
            
            for source_type in source_types:
                try:
                    latest_summary = await summary_service.generate_category_summary(
                        db=db,
                        category=source_type
                    )
                    if latest_summary:
                        logger.info(f"Successfully generated latest summary for {source_type}")
                    else:
                        logger.warning(f"Unable to generate latest summary for {source_type}")
                except Exception as e:
                    logger.error(f"Error generating latest summary for {source_type}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing latest summaries: {str(e)}")
    
    async def _run_schedule(self, start_time: time, end_time: time, freq: int):
        """
        Execute scheduled tasks
        
        Args:
            start_time: Start time
            end_time: End time
            freq: Execution frequency (seconds)
        """
        while self.is_running:
            try:
                current_time = datetime.now().time()
                
                # Check if within execution time range
                if start_time <= current_time <= end_time:
                    async with async_session() as db:
                        # 1. Process all news sources
                        for source in CnyesSource:
                            print("--------------------------------")
                            print("source", source)
                            print("--------------------------------")
                            await self._process_source(source, db)
                            
                        # 2. Generate latest summaries
                        await self._process_latest_summaries(db)
                        
                    logger.info(f"Completed schedule cycle, waiting {freq} seconds before next run")
                else:
                    logger.info(f"Current time {current_time} is outside execution time range")
                    
                await asyncio.sleep(freq)
                
            except Exception as e:
                logger.error(f"Error during schedule execution: {str(e)}")
                await asyncio.sleep(freq)  # Wait even if error occurs
    
    async def start(self, start_time: time = time(9, 0), end_time: time = time(17, 30), freq: int = 1800):
        """
        Start the scheduling system
        
        Args:
            start_time: Start time, default 9:00
            end_time: End time, default 17:30
            freq: Execution frequency (seconds), default 1800 seconds (30 minutes)
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        self.current_start_time = start_time
        self.current_end_time = end_time
        self.current_freq = freq
        self.task = asyncio.create_task(self._run_schedule(start_time, end_time, freq))
        logger.info(f"Scheduler started, execution time: {start_time} - {end_time}, frequency: {freq} seconds")
    
    async def stop(self):
        """Stop the scheduling system"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
            
        self.is_running = False
        self.current_start_time = None
        self.current_end_time = None
        self.current_freq = None
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        logger.info("Scheduler stopped")

# Create global instance
scheduler = NewsScheduler()