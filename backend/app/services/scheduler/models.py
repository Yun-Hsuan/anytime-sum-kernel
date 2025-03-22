from datetime import time, datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, validator

class TaskConfig(BaseModel):
    """任務配置模型"""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    interval_seconds: int = 3600
    enabled: bool = True
    
    @validator('interval_seconds')
    def validate_interval(cls, v):
        if v < 60:  # 最小間隔 1 分鐘
            raise ValueError("Interval must be at least 60 seconds")
        return v

class TaskInfo(BaseModel):
    """任務資訊模型"""
    task_id: str
    name: str
    status: str
    last_run: Optional[datetime] = None
    config: TaskConfig
    error: Optional[str] = None 