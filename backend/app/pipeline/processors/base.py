"""
Base processor for pipeline operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from app.pipeline.api.client import PipelineAPIClient
from app.pipeline.definitions.source_settings import get_pipeline_settings

logger = logging.getLogger(__name__)

class BaseTask(ABC):
    """任務基礎類"""
    
    def __init__(self):
        self.settings = get_pipeline_settings()
        self.client = PipelineAPIClient()
        self.logger = self.settings.log_config.get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """執行任務"""
        pass
    
    @abstractmethod
    async def validate(self, context: Dict[str, Any]) -> bool:
        """驗證任務參數"""
        pass
    
    async def on_success(self, result: Dict[str, Any]) -> None:
        """Callback after task succeeds"""
        self.logger.info(f"Task completed successfully: {self.__class__.__name__}")
    
    async def on_failure(self, error: Exception) -> None:
        """Callback after task fails"""
        self.logger.error(f"Task failed: {self.__class__.__name__}, error: {str(error)}")

class BaseProcessor(ABC):
    """Base class for all pipeline processors"""

    @abstractmethod
    async def process(self, config: Dict) -> Dict[str, Any]:
        """
        Execute the processing step
        
        Args:
            config: Processing configuration
            
        Returns:
            Dict[str, Any]: Processing results
        """
        pass