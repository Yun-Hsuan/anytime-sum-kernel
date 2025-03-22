from typing import Any, Dict, Optional
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from app.pipeline.definitions.source_settings import get_pipeline_settings
from app.pipeline.definitions.settings.api_config import APIEndpointConfig
from .exceptions import RequestTimeoutError, APIConnectionError, APIResponseError
import logging

class PipelineAPIClient:
    """Pipeline API 客戶端"""
    
    def __init__(self):
        self.settings = get_pipeline_settings()
        self.base_url = self.settings.API_BASE_URL
        self.logger = self.settings.log_config.get_logger("api_client")
        # 設置日誌級別為 DEBUG
        self.logger.setLevel(logging.DEBUG)
        
        # 初始化時檢查配置
        self.logger.debug("="*50)
        self.logger.debug("Initializing PipelineAPIClient with settings:")
        self.logger.debug(f"API Base URL: {self.base_url}")
        self.logger.debug("API Endpoints configuration:")
        self.logger.debug(f"SCRAPER_CONFIG: {self.settings.api_endpoints.SCRAPER_CONFIG}")
        self.logger.debug(f"PROCESS_CONFIG: {self.settings.api_endpoints.PROCESS_CONFIG}")
        self.logger.debug(f"SUMMARY_CONFIG: {self.settings.api_endpoints.SUMMARY_CONFIG}")
        self.logger.debug("="*50)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda retry_state: retry_state.outcome.result()
    )
    async def _make_request(
        self,
        config: APIEndpointConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """執行 API 請求"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}{config.path}"
                params = {**config.params, **kwargs.get("params", {})}
                
                # 修改這部分的邏輯
                if config.method == "POST":
                    # POST 請求時保留 query 參數
                    response = await client.request(
                        method=config.method,
                        url=url,
                        params=kwargs.get("params", {}),  # query 參數
                        json=config.params,  # body 參數
                        headers=config.headers,
                        timeout=config.timeout
                    )
                else:
                    # GET 請求
                    response = await client.request(
                        method=config.method,
                        url=url,
                        params=params,
                        headers=config.headers,
                        timeout=config.timeout
                    )
                
                self.logger.debug(f"Making {config.method} request to {url}")
                self.logger.debug(f"Query params: {kwargs.get('params', {})}")
                self.logger.debug(f"Body: {config.params if config.method == 'POST' else None}")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.ConnectError as e:
            self.logger.error(f"Connection error: {str(e)}")
            raise APIConnectionError(f"連接錯誤: {str(e)}")
            
        except httpx.TimeoutException as e:
            self.logger.error(f"Request timeout: {str(e)}")
            raise RequestTimeoutError(f"請求超時: {str(e)}")
            
        except httpx.HTTPStatusError as e:
            raise APIResponseError(
                status_code=e.response.status_code,
                message=e.response.text
            )
    
    async def fetch_articles(self, source_type: str) -> Dict[str, Any]:
        """爬取文章"""
        self.logger.debug(f"Fetching articles for source_type: {source_type}")
        config = self.settings.api_endpoints.SCRAPER_CONFIG
        return await self._make_request(
            config,
            params={"source_type": source_type}  # 確保參數在 query string 中
        )
    
    async def process_articles(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """處理文章"""
        config = self.settings.api_endpoints.PROCESS_CONFIG
        params = {}
        if limit:
            params["limit"] = limit
        return await self._make_request(config, params=params)
    
    async def get_summaries(self, source: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """獲取摘要"""
        config = self.settings.api_endpoints.SUMMARY_CONFIG
        params = {"source": source}
        if limit:
            params["limit"] = limit
        return await self._make_request(config, params=params)