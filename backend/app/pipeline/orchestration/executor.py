"""
Pipeline execution orchestrator
"""

from typing import Dict, List, Type, Any
import logging
from fastapi import HTTPException
import asyncio

from app.pipeline.definitions.source_registry import SourceRegistry
from app.pipeline.definitions.source_settings import get_pipeline_settings
from app.pipeline.processors.fetcher import ArticleFetcher
from app.pipeline.processors.summarizer import ArticleSummarizer
from app.pipeline.processors.categorizer import CategorySummarizer
from app.pipeline.processors.base import BaseTask

logger = logging.getLogger(__name__)

class PipelineExecutor:
    """Pipeline executor"""
    
    def __init__(self):
        self.settings = get_pipeline_settings()
        self.logger = self.settings.log_config.get_logger("pipeline_executor")
        self.tasks: List[BaseTask] = []
        self.context: Dict[str, Any] = {}
    
    def add_task(self, task: BaseTask) -> 'PipelineExecutor':
        """Add task to pipeline"""
        self.tasks.append(task)
        return self
    
    def set_context(self, context: Dict[str, Any]) -> 'PipelineExecutor':
        """Set execution context"""
        self.context = context
        return self
    
    async def execute(self) -> Dict[str, Any]:
        """Execute entire pipeline"""
        result = {}
        
        for task in self.tasks:
            try:
                self.logger.info(f"Executing task: {task.__class__.__name__}")
                
                # Validate task parameters
                if not await task.validate(self.context):
                    raise ValueError(f"Task validation failed: {task.__class__.__name__}")
                
                # Execute task
                task_result = await task.execute(self.context)
                
                # Update context and result
                self.context.update(task_result)
                result.update(task_result)
                
                # Call success callback
                await task.on_success(task_result)
                
            except Exception as e:
                self.logger.error(f"Task failed: {task.__class__.__name__}, error: {str(e)}")
                await task.on_failure(e)
                raise
        
        return result

    async def execute_single(self, source_id: str) -> Dict[str, Any]:
        """
        Execute the complete pipeline for a given source
        
        Args:
            source_id: Source identifier
            
        Returns:
            Dict[str, Any]: Pipeline execution results
        """
        try:
            # Get source specification
            source_spec = SourceRegistry.get_source(source_id)
            
            # 1. Fetch articles
            fetch_results = await self.fetcher.process(
                source_spec.fetch_config
            )
            
            # 2. Generate article summaries
            process_results = await self.summarizer.process(
                source_spec.process_config
            )
            
            # 3. Generate category summaries
            summary_results = await self.categorizer.process(
                source_spec.summary_config
            )
            
            # Integrate and return results
            return {
                "source": source_id,
                "name": source_spec.name,
                "status": "success",
                "steps": {
                    "fetch": {
                        "status": "success",
                        "articles_fetched": len(fetch_results.get("articles", []))
                    },
                    "process": {
                        "status": "success",
                        "articles_processed": process_results.get("processed_count", 0),
                        "total_pending": process_results.get("total_pending", 0)
                    },
                    "summarize": {
                        "status": "success",
                        "articles_summarized": summary_results.get("count", 0),
                        "has_summary": bool(summary_results.get("summary", ""))
                    }
                }
            }
            
        except ValueError as e:
            logger.error(f"Invalid source configuration: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            return {
                "source": source_id,
                "status": "error",
                "error": str(e)
            } 