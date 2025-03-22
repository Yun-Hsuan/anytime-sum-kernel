from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import BaseModel
from enum import Enum

class SourceType(str, Enum):
    TW = "tw"
    US = "us" 
    HEADLINE = "headline"

class APIEndpointConfig(BaseModel):
    """Detailed configuration for API endpoints"""
    path: str
    method: str = "GET"
    params: dict = {}
    headers: dict = {}
    timeout: int = 30

class APIEndpoints(BaseSettings):
    """API endpoint configuration management"""
    
    # Define three main endpoints
    SCRAPER_CONFIG: APIEndpointConfig = APIEndpointConfig(
        path="/api/v1/scrapers/scrapers/cnyes/fetch-articles",
        method="POST",
        params={"source_type": "{source_type}"}
    )
    
    PROCESS_CONFIG: APIEndpointConfig = APIEndpointConfig(
        path="/api/v1/articles/process-pending",
        method="POST",
        params={"limit": 150}
    )
    
    SUMMARY_CONFIG: APIEndpointConfig = APIEndpointConfig(
        path="/api/v1/articles/latest-summaries",
        method="POST",
        params={"source": "{source}", "limit": 30}
    )
    
    class Config:
        env_prefix = "PIPELINE_API_"
    
    def get_scraper_url(self, source_type: str) -> str:
        """Get complete scraper URL"""
        return self.SCRAPER_CONFIG.path.format(source_type=source_type)
    
    def get_summary_url(self, source: str) -> str:
        """Get complete summary URL"""
        return self.SUMMARY_CONFIG.path.format(source=source)