"""News pipeline task configurations"""
from typing import Dict, Any
from ..pipeline import PipelineTask
from app.pipeline.functions.news_summary_pipeline import news_summary_pipeline

def get_news_summary_pipeline_configs() -> Dict[str, Dict[str, Any]]:
    """獲取新聞相關的 pipeline 配置"""
    return {
        "news_summary": {
            "task": PipelineTask(
                name="news_summary",
                pipeline_func=news_summary_pipeline,
                config={
                    "context": {
                        "source_type": "tw",
                        "source": "TW_Stock_Summary",
                        "limit": 150
                    }
                }
            ),
            "schedule": {
                "daily_start_time": "00:00",
                "daily_end_time": "23:59",
                "interval_minutes": 15,
                "enabled": True
            }
        }
    } 