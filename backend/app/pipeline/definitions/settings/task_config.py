from pydantic_settings import BaseSettings

class TaskConfig(BaseSettings):
    """Task configuration management"""
    
    # Task execution configuration
    MAX_CONCURRENT_TASKS: int = 3
    TASK_QUEUE_SIZE: int = 1000
    
    # Task retry configuration  
    RETRY_DELAY: int = 60  # seconds
    MAX_RETRIES: int = 3
    
    # Task timeout configuration
    FETCH_TIMEOUT: int = 30
    PROCESS_TIMEOUT: int = 120
    SUMMARY_TIMEOUT: int = 180
    
    class Config:
        env_prefix = "PIPELINE_TASK_"