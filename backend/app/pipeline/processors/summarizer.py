"""
Article summarization processor
"""

from typing import Dict, Any
import httpx
from .base import BaseProcessor

class ArticleSummarizer(BaseProcessor):
    """Processor for generating article summaries"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def process(self, config: Dict) -> Dict[str, Any]:
        """
        Generate summaries for articles
        
        Args:
            config: Processing configuration containing:
                   - limit: Number of articles to process
                   
        Returns:
            Dict[str, Any]: Processing results
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/articles/process-pending",
                params=config
            )
            response.raise_for_status()
            return response.json() 