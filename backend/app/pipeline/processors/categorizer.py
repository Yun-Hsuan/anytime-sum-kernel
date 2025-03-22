"""
Category summary processor
"""

from typing import Dict, Any
import httpx
from .base import BaseProcessor

class CategorySummarizer(BaseProcessor):
    """Processor for generating category summaries"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def process(self, config: Dict) -> Dict[str, Any]:
        """
        Generate category summary
        
        Args:
            config: Summary configuration containing:
                   - source: Source identifier
                   - limit: Number of articles to include
                   
        Returns:
            Dict[str, Any]: Summary results
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/articles/latest-summaries",
                params=config
            )
            response.raise_for_status()
            return response.json() 