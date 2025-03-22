"""
Article fetching processor
"""

from typing import Dict, Any
import httpx
from .base import BaseProcessor

class ArticleFetcher(BaseProcessor):
    """Processor for fetching articles"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def process(self, config: Dict) -> Dict[str, Any]:
        """
        Fetch articles from the source
        
        Args:
            config: Fetching configuration containing:
                   - source_type: Type of source to fetch from
                   - limit: Number of articles to fetch
                   
        Returns:
            Dict[str, Any]: Fetching results
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/scrapers/scrapers/cnyes/fetch-articles",
                params=config
            )
            response.raise_for_status()
            return response.json() 