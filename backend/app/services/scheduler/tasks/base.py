from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional

class ScheduledTask(ABC):
    """排程任務基礎類"""
    
    def __init__(self):
        # 任務基本信息
        self.name: str = ""
        self.enabled: bool = True
        
        # 執行狀態
        self.status: str = "idle"  # idle/running/completed/failed
        self.last_run: Optional[datetime] = None
        self.error: Optional[str] = None
        
        # 排程配置
        self.daily_start_time: str = "09:00"
        self.daily_end_time: str = "17:30"
        self.interval_minutes: int = 60
    
    @abstractmethod
    async def execute(self) -> None:
        """執行任務的抽象方法"""
        raise NotImplementedError
    
    def get_status(self) -> Dict[str, Any]:
        """獲取任務狀態"""
        return {
            "status": self.status,
            "last_run": self.last_run,
            "error": self.error
        } 