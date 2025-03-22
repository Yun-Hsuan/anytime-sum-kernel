"""
API routes for pipeline operations
"""

from fastapi import APIRouter
from typing import Dict, List

from app.pipeline.api.deps import PipelineSettingsDep
from app.pipeline.definitions.source_registry import SourceRegistry
from app.pipeline.orchestration.executor import PipelineExecutor
from app.pipeline.api.schemas import PipelineResult

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

@router.post("/execute/{source_id}", response_model=PipelineResult)
async def execute_pipeline(
    source_id: str,
    settings: PipelineSettingsDep,
) -> PipelineResult:
    """
    Execute the complete news processing pipeline for a source
    
    Args:
        source_id: Source identifier (e.g., "TW_Stock_Summary")
        
    Returns:
        PipelineResult: Pipeline execution results
    """
    executor = PipelineExecutor(settings)
    return await executor.execute(source_id)

@router.get("/sources", response_model=Dict[str, Dict])
async def get_sources() -> Dict[str, Dict]:
    """Get all available pipeline sources and their configurations"""
    return {
        "sources": SourceRegistry.get_source_specs()
    }

@router.get("/sources/list", response_model=List[str])
async def list_sources() -> List[str]:
    """Get list of all available source IDs"""
    return SourceRegistry.get_all_sources() 