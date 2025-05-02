from datetime import datetime, time
from typing import Dict, Optional, Any, List
import asyncio
import logging
from .tasks.base import ScheduledTask
from .models import TaskConfig, TaskInfo
from .exceptions import TaskNotFoundError, TaskConfigurationError, ServiceStateError

class SchedulerService:
    """排程服務"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.tasks: Dict[str, ScheduledTask] = {}
            self.task_configs: Dict[str, TaskConfig] = {}
            self.service_status: str = "stopped"
            self.start_datetime: Optional[datetime] = None
            self.license_end_datetime: Optional[datetime] = None
            self._scheduler_task: Optional[asyncio.Task] = None
            self._sleep_task: Optional[asyncio.Task] = None
            self.task_queue: asyncio.Queue = asyncio.Queue()
            self.worker_tasks: List[asyncio.Task] = []
            self.max_workers: int = 3
            self.semaphore: asyncio.Semaphore = asyncio.Semaphore(5)
            self.metrics: Dict[str, Any] = {
                'tasks_executed': 0,
                'tasks_failed': 0,
                'average_execution_time': 0
            }
            self.logger = logging.getLogger(__name__)
            self.initialized = True
    
    def register_task(
        self, 
        task_id: str, 
        task: ScheduledTask, 
        config: Optional[Dict] = None
    ):
        """註冊新任務"""
        self.tasks[task_id] = task
        if config:
            self.task_configs[task_id] = TaskConfig(**config)
        self.logger.info(f"Task registered: {task_id}")
    
    def update_task_config(self, task_id: str, config: Dict):
        """更新任務配置"""
        if task_id not in self.tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")
        try:
            self.task_configs[task_id] = TaskConfig(**config)
            self.logger.info(f"Updated config for task: {task_id}")
        except ValueError as e:
            raise TaskConfigurationError(f"Invalid configuration: {str(e)}")
    
    async def start_service(
        self,
        start_datetime: datetime,
        license_end_datetime: datetime
    ):
        """啟動排程服務"""
        if datetime.now() > license_end_datetime:
            raise ServiceStateError("License has expired")
        
        self.start_datetime = start_datetime
        self.license_end_datetime = license_end_datetime
        self.service_status = "running"
        
        # 啟動工作者
        for _ in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop())
            self.worker_tasks.append(worker)
        
        # 啟動排程循環
        if self._scheduler_task is None or self._scheduler_task.done():
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            self.logger.info("Scheduler service started")

    def stop_service(self):
        """停止排程服務"""
        self.service_status = "stopped"
        # 取消所有工作者任務
        for worker in self.worker_tasks:
            if not worker.done():
                worker.cancel()
        self.worker_tasks.clear()
        
        # 取消排程任務
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
        self.logger.info("Scheduler service stopped")
    
    def get_task_info(self, task_id: str) -> TaskInfo:
        """獲取任務資訊"""
        if task_id not in self.tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")
            
        task = self.tasks[task_id]
        config = self.task_configs.get(task_id, TaskConfig())
        
        return TaskInfo(
            task_id=task_id,
            name=getattr(task, 'name', task_id),
            **task.get_status(),
            config=config
        )
    
    def get_all_task_info(self) -> Dict[str, TaskInfo]:
        """獲取所有任務資訊"""
        return {
            task_id: self.get_task_info(task_id)
            for task_id in self.tasks
        }

    def _get_min_interval(self) -> int:
        """獲取所有任務中最小的檢查間隔"""
        if not self.tasks:
            return 60  # 默認 1 分鐘
        
        return min(task.interval_minutes for task in self.tasks.values())

    async def _worker_loop(self):
        """工作者循環"""
        self.logger.info("Worker loop started")
        while self.service_status == "running":
            try:
                # 從隊列中獲取任務
                task = await self.task_queue.get()
                start_time = datetime.now()
                
                try:
                    async with self.semaphore:  # 使用信號量限制並發
                        await task.execute()
                        self.metrics['tasks_executed'] += 1
                except Exception as e:
                    self.metrics['tasks_failed'] += 1
                    self.logger.error(f"Task execution failed: {str(e)}")
                finally:
                    # 更新執行時間統計
                    execution_time = (datetime.now() - start_time).total_seconds()
                    self.metrics['average_execution_time'] = (
                        self.metrics['average_execution_time'] * (self.metrics['tasks_executed'] - 1) +
                        execution_time
                    ) / self.metrics['tasks_executed']
                    self.task_queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker loop error: {str(e)}")
                await asyncio.sleep(1)

    async def _scheduler_loop(self):
        """排程主循環"""
        self.logger.info("Scheduler loop started")
        while self.service_status == "running":
            try:
                current_time = datetime.now().time()
                
                for task_id, task in self.tasks.items():
                    try:
                        should_execute = await self._should_execute_task(task, current_time)
                        
                        if should_execute:
                            # 將任務加入隊列而不是直接執行
                            await self.task_queue.put(task)
                            self.logger.info(f"Task {task_id} queued for execution")
                            
                    except Exception as e:
                        self.logger.error(f"Error checking task {task_id}: {str(e)}")

                # 使用最小間隔作為檢查頻率
                check_interval = self._get_min_interval()
                self._sleep_task = asyncio.create_task(asyncio.sleep(check_interval * 60))
                try:
                    await self._sleep_task
                except asyncio.CancelledError:
                    self.logger.info("Sleep interrupted due to configuration update")
                    continue
                
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {str(e)}")
                await asyncio.sleep(60)

    async def _should_execute_task(self, task: ScheduledTask, current_time: time) -> bool:
        """判斷任務是否應該執行"""
        if not task.enabled:
            self.logger.debug(f"Task {task.name} is disabled")
            return False

        # 只檢查是否正在運行，completed 狀態不影響下次執行
        if task.status == "running":
            self.logger.debug(f"Task {task.name} is already running")
            return False

        # 解析任務的時間範圍
        try:
            task_start = datetime.strptime(task.daily_start_time, "%H:%M").time()
            task_end = datetime.strptime(task.daily_end_time, "%H:%M").time()
            
            # 檢查是否在執行時間範圍內
            if not (task_start <= current_time <= task_end):
                self.logger.debug(f"Task {task.name} outside time window: {current_time} not in {task_start}-{task_end}")
                return False

            # 檢查上次執行時間間隔
            if task.last_run:
                minutes_passed = (datetime.now() - task.last_run).total_seconds() / 60
                if minutes_passed < task.interval_minutes:
                    self.logger.debug(f"Task {task.name} interval not reached: {minutes_passed}/{task.interval_minutes} minutes")
                    return False
            
            # 如果所有檢查都通過，將狀態重置為 idle
            if task.status == "completed":
                task.status = "idle"
            
            self.logger.info(f"Task {task.name} is ready to execute")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking task execution time: {str(e)}")
            return False

    async def start_task(self, task_id: str):
        """手動啟動任務"""
        if task_id not in self.tasks:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        if task.status == "running":
            raise ServiceStateError("Task is already running")
        
        await task.execute()

    def update_task_schedule(self, task_id: str, config: Dict[str, Any]) -> None:
        """更新任務排程配置"""
        if task_id not in self.tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        # 更新任務實例
        task.daily_start_time = config["daily_start_time"]
        task.daily_end_time = config["daily_end_time"]
        task.interval_minutes = config["interval_minutes"]
        task.enabled = config["enabled"]
        
        # 更新配置存儲
        if task_id in self.task_configs:
            self.task_configs[task_id].schedule.update(config)
        
        # 取消當前的 sleep 任務，強制重新計算間隔
        if self._sleep_task and not self._sleep_task.done():
            self._sleep_task.cancel()
        
        self.logger.info(f"Updated schedule for task {task_id}: {config}")