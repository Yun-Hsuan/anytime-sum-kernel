from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.schemas.scheduler import (
    GlobalSchedulerConfig,
    TaskScheduleConfig,
    TaskPipelineConfig,
    TaskStatus,
    SchedulerStatus
)
from app.services.scheduler import scheduler_service  # 導入已初始化的服務
from app.api.deps import get_current_user  # 可能需要的權限控制
import asyncio
from app.pipeline.functions.news_summary_pipeline import news_summary_pipeline

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

@router.post("/service/start", 
    summary="啟動排程服務",
    description="""
    啟動全局排程服務，並設置服務運行時間和授權時間。
    
    注意事項：
    - start_datetime 必須大於等於當前時間
    - license_end_datetime 必須大於 start_datetime
    - 如果授權已過期，服務將無法啟動
    
    返回：
    - 服務啟動狀態和配置信息
    """)
async def start_scheduler_service(config: GlobalSchedulerConfig):
    if datetime.now() > config.license_end_datetime:
        raise HTTPException(
            status_code=400, 
            detail="License has expired"
        )
    
    await scheduler_service.start_service(
        start_datetime=config.start_datetime,
        license_end_datetime=config.license_end_datetime
    )
    return {
        "status": "service_started",
        "config": config.dict()
    }

@router.get("/service/status",
    summary="獲取服務狀態",
    description="""
    獲取排程服務的當前運行狀態。
    
    返回：
    - service_status: 服務狀態（running/stopped/error/license_expired）
    - start_datetime: 服務啟動時間
    - license_end_datetime: 授權結束時間
    - current_datetime: 當前時間
    """)
async def get_service_status() -> Dict[str, Any]:
    return {
        "service_status": scheduler_service.service_status,
        "start_datetime": scheduler_service.start_datetime,
        "license_end_datetime": scheduler_service.license_end_datetime,
        "current_datetime": datetime.now()
    }

@router.post("/tasks/{task_id}/schedule",
    summary="更新任務排程配置",
    description="""
    更新指定任務的運行時間配置。
    
    參數：
    - task_id: 任務ID，例如 "news_summary"
    
    配置規則：
    - daily_start_time 必須早於 daily_end_time
    - interval_minutes 必須小於每日運行時間範圍
    - 時間格式必須為 24 小時制 (HH:MM)
    
    示例請求：
    ```json
    {
        "daily_start_time": "09:00",
        "daily_end_time": "17:30",
        "interval_minutes": 5,
        "enabled": true
    }
    ```
    """)
async def update_task_schedule(task_id: str, config: TaskScheduleConfig):
    scheduler_service.update_task_schedule(
        task_id=task_id,
        config=config.dict()
    )
    return {
        "task_id": task_id,
        "schedule": config.dict()
    }

@router.post("/tasks/{task_id}/pipeline-config",
    summary="更新任務 Pipeline 配置",
    description="""
    更新指定任務的 Pipeline 上下文配置。
    
    參數：
    - task_id: 任務ID，例如 "news_summary"
    
    配置說明：
    context 字典中的可用參數取決於具體的 pipeline 類型：
    
    新聞摘要 Pipeline (news_summary):
    - source_type: 數據源類型 (例如: "tw", "us")
    - source: 數據源名稱 (例如: "TW_Stock_Summary")
    - limit: 處理數量限制 (1-1000 的整數)
    
    示例請求：
    ```json
    {
        "context": {
            "source_type": "tw",
            "source": "TW_Stock_Summary",
            "limit": 150
        }
    }
    ```
    """)
async def update_task_pipeline_config(
    task_id: str, 
    config: TaskPipelineConfig
) -> Dict[str, Any]:
    if task_id not in scheduler_service.tasks:
        raise HTTPException(
            status_code=404, 
            detail=f"Task {task_id} not found"
        )
    
    task = scheduler_service.tasks[task_id]
    task.config["context"] = config.context
    
    return {
        "task_id": task_id,
        "pipeline_config": task.config
    }

@router.get("/status",
    summary="獲取排程器整體狀態",
    description="""
    獲取排程器及其所有任務的當前運行狀態。
    
    返回：
    - status: 排程器狀態（running/stopped/error）
    - tasks: 所有任務的狀態信息
      - status: 任務狀態（idle/running/completed/failed）
      - last_run: 上次執行時間
    
    示例響應：
    ```json
    {
        "status": "running",
        "tasks": {
            "news_summary": {
                "status": "completed",
                "last_run": "2024-01-01T10:00:00"
            }
        }
    }
    ```
    """)
async def get_scheduler_status() -> Dict[str, Any]:
    return {
        "status": scheduler_service.service_status,
        "tasks": {
            task_id: {
                "status": task.status,
                "last_run": task.last_run
            }
            for task_id, task in scheduler_service.tasks.items()
        }
    }

@router.post("/tasks/{task_id}/start",
    summary="啟動特定任務",
    description="""
    手動啟動指定的任務。
    
    參數：
    - task_id: 任務ID，例如 "news_summary"
    
    注意事項：
    - 任務必須已經註冊在排程器中
    - 任務不能處於運行狀態
    
    可能的錯誤：
    - 404: 任務不存在
    - 400: 任務已在運行中
    
    示例響應：
    ```json
    {
        "status": "started",
        "task_id": "news_summary"
    }
    ```
    """)
async def start_task(task_id: str):
    try:
        await scheduler_service.start_task(task_id)
        return {"status": "started", "task_id": task_id}
    except KeyError:
        raise HTTPException(404, f"Task {task_id} not found")
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/tasks",
    summary="獲取所有任務信息",
    description="""
    獲取所有已註冊任務的詳細信息。
    
    返回信息包括：
    - name: 任務名稱
    - status: 當前狀態
    - last_run: 上次執行時間
    - error: 錯誤信息（如果有）
    - schedule: 排程配置
      - daily_start_time: 每日開始時間
      - daily_end_time: 每日結束時間
      - interval_minutes: 執行間隔
      - enabled: 是否啟用
    - pipeline_config: Pipeline 配置
    
    示例響應：
    ```json
    {
        "news_summary": {
            "name": "news_summary",
            "status": "completed",
            "last_run": "2024-01-01T10:00:00",
            "error": null,
            "schedule": {
                "daily_start_time": "09:00",
                "daily_end_time": "17:30",
                "interval_minutes": 5,
                "enabled": true
            },
            "pipeline_config": {
                "context": {
                    "source_type": "tw",
                    "source": "TW_Stock_Summary",
                    "limit": 150
                }
            }
        }
    }
    ```
    """)
async def get_tasks() -> Dict[str, Any]:
    tasks = {}
    for task_id, task in scheduler_service.tasks.items():
        tasks[task_id] = {
            "name": task.name,
            "status": task.status,
            "last_run": task.last_run,
            "error": task.error,
            "schedule": {
                "daily_start_time": task.daily_start_time,
                "daily_end_time": task.daily_end_time,
                "interval_minutes": task.interval_minutes,
                "enabled": task.enabled
            },
            "pipeline_config": task.config
        }
    return tasks

@router.post("/tasks/{task_id}/toggle",
    summary="切換任務啟用狀態",
    description="""
    切換指定任務的啟用/禁用狀態。
    
    參數：
    - task_id: 任務ID，例如 "news_summary"
    
    注意事項：
    - 如果任務當前已啟用，則會被禁用
    - 如果任務當前已禁用，則會被啟用
    - 不會影響正在執行的任務，但會影響下次排程
    
    可能的錯誤：
    - 404: 任務不存在
    
    示例響應：
    ```json
    {
        "task_id": "news_summary",
        "enabled": false
    }
    ```
    """)
async def toggle_task(task_id: str) -> Dict[str, Any]:
    if task_id not in scheduler_service.tasks:
        raise HTTPException(
            status_code=404, 
            detail=f"Task {task_id} not found"
        )
    
    task = scheduler_service.tasks[task_id]
    task.enabled = not task.enabled
    return {"task_id": task_id, "enabled": task.enabled}

@router.post("/tasks/{task_id}/execute",
    summary="手動執行任務",
    description="""
    立即執行指定的任務，不考慮排程設置。
    
    參數：
    - task_id: 任務ID，例如 "news_summary"
    
    注意事項：
    - 任務會立即執行，不受排程時間限制
    - 如果任務正在執行，會返回錯誤
    - 執行結果會更新到任務狀態中
    
    可能的錯誤：
    - 404: 任務不存在
    - 500: 任務執行失敗
    
    示例響應：
    ```json
    {
        "task_id": "news_summary",
        "status": "completed",
        "last_run": "2024-01-01T10:00:00"
    }
    ```
    """)
async def execute_task(task_id: str) -> Dict[str, Any]:
    if task_id not in scheduler_service.tasks:
        raise HTTPException(
            status_code=404, 
            detail=f"Task {task_id} not found"
        )
    
    task = scheduler_service.tasks[task_id]
    try:
        await task.execute()
        return {
            "task_id": task_id,
            "status": task.status,
            "last_run": task.last_run
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}",
    summary="獲取特定任務詳細信息",
    description="""
    獲取指定任務的所有詳細信息。
    
    參數：
    - task_id: 任務ID，例如 "news_summary"
    
    返回信息包括：
    - task_id: 任務ID
    - name: 任務名稱
    - status: 當前狀態
    - last_run: 上次執行時間
    - error: 錯誤信息（如果有）
    - enabled: 是否啟用
    - schedule: 排程配置
    
    可能的錯誤：
    - 404: 任務不存在
    
    示例響應：
    ```json
    {
        "task_id": "news_summary",
        "name": "news_summary",
        "status": "completed",
        "last_run": "2024-01-01T10:00:00",
        "error": null,
        "enabled": true,
        "schedule": {
            "daily_start_time": "09:00",
            "daily_end_time": "17:30",
            "interval_minutes": 5,
            "enabled": true
        }
    }
    ```
    """)
async def get_task_details(task_id: str) -> Dict[str, Any]:
    if task_id not in scheduler_service.tasks:
        raise HTTPException(
            status_code=404, 
            detail=f"Task {task_id} not found"
        )
    
    task = scheduler_service.tasks[task_id]
    return {
        "task_id": task_id,
        "name": task.name,
        "status": task.status,
        "last_run": task.last_run,
        "error": task.error,
        "enabled": task.enabled,
        "schedule": {
            "daily_start_time": task.daily_start_time,
            "daily_end_time": task.daily_end_time,
            "interval_minutes": task.interval_minutes,
            "enabled": task.enabled
        }
    }

@router.post("/service/stop", 
    summary="停止排程服務",
    description="""
    停止全局排程服務。
    
    注意事項：
    - 會停止所有正在排程的任務
    - 不會影響正在執行中的任務
    - 服務停止後可以通過 /service/start 重新啟動
    
    返回：
    - 服務停止狀態
    
    示例響應：
    ```json
    {
        "status": "stopped",
        "stop_time": "2024-01-01T10:30:00"
    }
    ```
    """)
async def stop_scheduler_service():
    """停止排程服務"""
    scheduler_service.stop_service()
    return {
        "status": "stopped",
        "stop_time": datetime.now().isoformat()
    }