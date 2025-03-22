from app.services.scheduler.service import SchedulerService
from app.services.scheduler.tasks.configs import get_news_summary_pipeline_configs

# 創建服務實例
scheduler_service = SchedulerService()

# 註冊任務
task_configs = get_news_summary_pipeline_configs()
for task_id, config in task_configs.items():
    task = config["task"]
    schedule = config["schedule"]
    
    # 設置任務的調度配置
    task.daily_start_time = schedule["daily_start_time"]
    task.daily_end_time = schedule["daily_end_time"]
    task.interval_minutes = schedule["interval_minutes"]
    task.enabled = schedule["enabled"]
    
    # 註冊任務
    scheduler_service.tasks[task_id] = task

# 導出服務實例
__all__ = ['scheduler_service'] 