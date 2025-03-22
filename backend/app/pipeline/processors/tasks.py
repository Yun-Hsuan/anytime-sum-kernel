from typing import Any, Dict
from .base import BaseTask

class FetchArticlesTask(BaseTask):
    """爬取文章任務"""
    
    async def validate(self, context: Dict[str, Any]) -> bool:
        return "source_type" in context
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        source_type = context["source_type"]
        result = await self.client.fetch_articles(source_type)
        return {"fetched_articles": result}

class ProcessArticlesTask(BaseTask):
    """處理文章任務"""
    
    async def validate(self, context: Dict[str, Any]) -> bool:
        return True  # 這個任務不需要特別的參數
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        limit = context.get("limit", self.settings.PIPELINE_BATCH_SIZE)
        result = await self.client.process_articles(limit)
        return {"processed_articles": result}

class GenerateSummariesTask(BaseTask):
    """生成摘要任務"""
    
    async def validate(self, context: Dict[str, Any]) -> bool:
        return "source" in context
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        source = context["source"]
        limit = context.get("limit", 30)
        result = await self.client.get_summaries(source, limit)
        return {"summaries": result}