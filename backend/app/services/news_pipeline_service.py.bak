"""
News pipeline service for orchestrating the entire news processing flow
"""

from typing import Dict, Any
import logging
import httpx
from fastapi import HTTPException

from app.config.news_sources import NewsSourceConfig

logger = logging.getLogger(__name__)

class NewsPipelineService:
    """Service for orchestrating news fetching, processing and summarization"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"  # 可以移到環境變數
    
    async def _make_api_call(self, endpoint: str, method: str = "GET", params: Dict = None) -> Any:
        """Make API call to internal endpoints"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}{endpoint}"
                response = await client.request(method, url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"API call failed: {endpoint} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"Pipeline step failed: {str(e)}")

    async def process_news_pipeline(self, source: str) -> Dict:
        """
        Execute the complete news processing pipeline
        
        Args:
            source: News source identifier (e.g., "TW_Stock_Summary")
            
        Returns:
            Dict: Processing results including statistics
        """
        try:
            # 獲取來源配置
            config = NewsSourceConfig.get_source_config(source)
            
            # 1. 抓取新聞
            fetch_results = await self._make_api_call(
                f"/api/v1/scrapers/scrapers/cnyes/fetch-articles",
                params={"source_type": config["source_type"]}
            )
            
            # 2. 處理文章摘要
            process_results = await self._make_api_call(
                f"/api/v1/articles/process-pending",
                params={"limit": config["process_limit"]}
            )
            
            # 3. 生成分類摘要
            summary_results = await self._make_api_call(
                f"/api/v1/articles/latest-summaries",
                params={
                    "source": source,
                    "limit": config["summary_limit"]
                }
            )
            
            # 返回處理結果
            return {
                "source": source,
                "source_name": config["name"],
                "fetch_results": {
                    "articles_fetched": len(fetch_results["articles"]) if "articles" in fetch_results else 0
                },
                "process_results": {
                    "articles_processed": process_results["processed_count"],
                    "total_pending": process_results["total_pending"]
                },
                "summary_results": {
                    "articles_summarized": summary_results["count"],
                    "has_summary": bool(summary_results["summary"])
                }
            }
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Pipeline execution failed") 