import logging
from typing import Dict, Any, List
from app.pipeline.orchestration.executor import PipelineExecutor
from app.pipeline.processors.tasks import (
    FetchArticlesTask,
    ProcessArticlesTask,
    GenerateSummariesTask
)

async def process_single_source(source_config: Dict[str, Any]) -> None:
    """處理單個來源的新聞摘要"""
    logging.info(f"Starting process_single_source with config: {source_config}")
    
    executor = PipelineExecutor()
    
    try:
        logging.info("Attempting to set context...")
        logging.info(f"Context data: {source_config}")
        executor.set_context(source_config)
        
        logging.info("Context set successfully, adding tasks...")
        executor.add_task(FetchArticlesTask())
        executor.add_task(ProcessArticlesTask())
        executor.add_task(GenerateSummariesTask())
        
        logging.info("Executing pipeline...")
        await executor.execute()
        
    except Exception as e:
        logging.error(f"Error in process_single_source: {str(e)}")
        logging.error(f"Config that caused error: {source_config}")
        raise

async def news_summary_pipeline(**kwargs) -> None:
    """執行新聞摘要 pipeline，支援多個來源"""
    # 定義支援的來源類型
    SUPPORTED_SOURCES = [
        {
            "source_type": "tw",
            "source": "TW_Stock_Summary",
            "limit": 150
        },
        {
            "source_type": "us",
            "source": "US_Stock_Summary",
            "limit": 150
        },
        {
            "source_type": "headline",
            "source": "Hot_News_Summary",
            "limit": 150
        }
    ]
    
    logging.info("Starting news summary pipeline for multiple sources")
    
    for source_config in SUPPORTED_SOURCES:
        try:
            logging.info(f"Processing source: {source_config['source']}")
            await process_single_source(source_config)
            logging.info(f"Completed processing source: {source_config['source']}")
            
        except Exception as e:
            logging.error(f"Error processing source {source_config['source']}: {str(e)}")
            # 繼續處理下一個來源，而不是完全中斷
            continue 