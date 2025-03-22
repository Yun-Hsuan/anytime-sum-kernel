from pydantic_settings import BaseSettings

class TaskConfig(BaseSettings):
    """任務配置管理"""
    
    # 任務執行配置
    MAX_CONCURRENT_TASKS: int = 3
    TASK_QUEUE_SIZE: int = 1000
    
    # 任務重試配置
    RETRY_DELAY: int = 60  # seconds
    MAX_RETRIES: int = 3
    
    # 任務超時配置
    FETCH_TIMEOUT: int = 30
    PROCESS_TIMEOUT: int = 120
    SUMMARY_TIMEOUT: int = 180
    
    class Config:
        env_prefix = "PIPELINE_TASK_" 