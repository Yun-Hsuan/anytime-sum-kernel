from pydantic import BaseModel, Field
from datetime import time, datetime
from typing import Optional, Dict, Any

class TaskScheduleConfig(BaseModel):
    """任務排程配置"""
    daily_start_time: str = Field(
        default="09:00",
        pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="每日開始時間 (HH:MM)"
    )
    daily_end_time: str = Field(
        default="17:30",
        pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="每日結束時間 (HH:MM)"
    )
    interval_minutes: float = Field(
        default=60.0,
        gt=0,
        description="執行間隔（分鐘）"
    )
    enabled: bool = Field(
        default=True,
        description="是否啟用任務"
    )

class TaskPipelineConfig(BaseModel):
    """任務 Pipeline 配置"""
    context: Dict[str, Any] = Field(
        ...,
        description="Pipeline 的上下文配置",
        example={
            "source_type": "tw",
            "source": "TW_Stock_Summary",
            "limit": 150
        }
    )

class TaskStatus(BaseModel):
    """任務狀態"""
    task_id: str
    name: str
    status: str
    last_run: Optional[datetime]
    error: Optional[str]
    enabled: bool
    schedule: TaskScheduleConfig

class GlobalSchedulerConfig(BaseModel):
    """排程器全局配置"""
    start_datetime: datetime = Field(
        default=datetime(2025, 3, 1),
        description="服務啟動時間"
    )
    license_end_datetime: datetime = Field(
        default=datetime(2025, 12, 31, 23, 59, 59),
        description="授權結束時間"
    )

class SchedulerStatus(BaseModel):
    """排程器狀態"""
    status: str
    tasks: Dict[str, TaskStatus]

class SchedulerConfig(BaseModel):
    """Scheduler Configuration Model"""
    start_time: Optional[str] = "09:00"  # Format: "HH:MM"
    end_time: Optional[str] = "17:30"    # Format: "HH:MM" 
    freq: Optional[int] = 1800           # Seconds

class TaskConfig(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    interval_seconds: int = 3600
    enabled: bool = True 