from datetime import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.scrapers.scheduler import scheduler

router = APIRouter()

class SchedulerConfig(BaseModel):
    """Scheduler Configuration Model"""
    start_time: Optional[str] = "09:00"  # Format: "HH:MM"
    end_time: Optional[str] = "17:30"    # Format: "HH:MM" 
    freq: Optional[int] = 1800           # Seconds

@router.post("/start")
async def start_scheduler(config: SchedulerConfig):
    """
    Start the news scheduling system
    
    - start_time: Daily start time (default: "09:00")
    - end_time: Daily end time (default: "17:30") 
    - freq: Execution frequency in seconds (default: 1800 seconds = 30 minutes)
    """
    try:
        # Parse time strings
        start_hour, start_minute = map(int, config.start_time.split(":"))
        end_hour, end_minute = map(int, config.end_time.split(":"))
        
        # Start scheduler
        await scheduler.start(
            start_time=time(start_hour, start_minute),
            end_time=time(end_hour, end_minute),
            freq=config.freq
        )
        return {"status": "success", "message": "Scheduler system started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")

@router.post("/stop") 
async def stop_scheduler():
    """Stop the news scheduling system"""
    try:
        await scheduler.stop()
        return {"status": "success", "message": "Scheduler system stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")

@router.get("/status")
async def get_scheduler_status():
    """Get scheduler system status"""
    return {
        "is_running": scheduler.is_running,
        "current_config": {
            "start_time": f"{scheduler.current_start_time.hour:02d}:{scheduler.current_start_time.minute:02d}" if scheduler.current_start_time else None,
            "end_time": f"{scheduler.current_end_time.hour:02d}:{scheduler.current_end_time.minute:02d}" if scheduler.current_end_time else None,
            "freq": scheduler.current_freq
        } if scheduler.is_running else None
    }