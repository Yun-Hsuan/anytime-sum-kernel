from datetime import datetime
from typing import Dict, Any, Callable, Awaitable
from .base import ScheduledTask
from ..exceptions import TaskExecutionError

class PipelineTask(ScheduledTask):
    """Pipeline 排程任務類"""
    
    def __init__(
        self,
        name: str,
        pipeline_func: Callable[..., Awaitable[Any]],
        config: Dict[str, Any] = None
    ):
        super().__init__()
        self.name = name
        self.pipeline_func = pipeline_func
        self.config = config or {}
    
    async def execute(self) -> None:
        """執行 pipeline 任務"""
        try:
            self.status = "running"
            self.error = None
            self.last_run = datetime.now()
            
            await self.pipeline_func(**self.config)
            
            self.status = "completed"
        except Exception as e:
            self.status = "failed"
            self.error = str(e)
            raise TaskExecutionError(f"Pipeline execution failed for {self.name}: {str(e)}") 