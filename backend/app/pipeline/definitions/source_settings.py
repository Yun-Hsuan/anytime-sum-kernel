"""
Pipeline system settings
"""

from typing import Dict
from pydantic import computed_field
from pydantic_settings import BaseSettings
from functools import lru_cache
from app.core.config import settings as core_settings

# 只保留必要的導入
from app.pipeline.definitions.settings.api_config import APIEndpoints
from app.pipeline.definitions.settings.task_config import TaskConfig
from app.pipeline.definitions.settings.log_config import LogConfig

class PipelineSettings(BaseSettings):
    """Pipeline system settings"""
    
    # 核心配置
    ENVIRONMENT: str = core_settings.ENVIRONMENT
    
    # Pipeline 基本配置
    PIPELINE_REQUEST_TIMEOUT: int = 30
    PIPELINE_BATCH_SIZE: int = 150
    PIPELINE_MAX_RETRIES: int = 3
    
    # 任務間隔配置
    FETCH_TASK_INTERVAL: int = 300  # 5 minutes
    PROCESS_TASK_INTERVAL: int = 600  # 10 minutes
    SUMMARY_TASK_INTERVAL: int = 1800  # 30 minutes
    
    # API 配置
    api_endpoints: APIEndpoints = APIEndpoints()
    
    # 任務配置
    task_config: TaskConfig = TaskConfig()
    
    # 日誌配置
    log_config: LogConfig = LogConfig()
    
    @computed_field
    @property
    def API_BASE_URL(self) -> str:
        """從核心配置獲取 API 基礎 URL"""
        # 不要使用 FRONTEND_HOST，改用後端 API 的 URL
        return "http://localhost:8000"  # 或從環境變數獲取
    
    model_config = {
        "env_file": core_settings.model_config["env_file"],
        "env_prefix": "PIPELINE_",
        "extra": "allow"  # 允許額外的欄位
    }

@lru_cache()
def get_pipeline_settings() -> PipelineSettings:
    """Get cached instance of Pipeline settings"""
    return PipelineSettings()