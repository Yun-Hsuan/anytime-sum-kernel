"""Scheduler task registry"""
from app.services.scheduler.tasks.configs import get_all_task_configs

def register_tasks(scheduler_service):
    """註冊所有預定義的任務"""
    task_configs = get_all_task_configs()
    
    for task_id, config in task_configs.items():
        # 分別傳入 task 和 schedule 配置
        task = config["task"]
        schedule_config = config["schedule"]
        
        # 設置任務的調度配置
        task.interval_seconds = schedule_config["interval_seconds"]
        task.enabled = schedule_config["enabled"]
        task.start_time = schedule_config["start_time"]
        task.end_time = schedule_config["end_time"]
        
        # 註冊任務
        scheduler_service.register_task(
            task_id=task_id,
            task=task
        ) 