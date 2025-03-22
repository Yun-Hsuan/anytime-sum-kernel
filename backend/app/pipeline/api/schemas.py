"""
API schemas for pipeline operations
"""

from typing import Dict, Optional
from pydantic import BaseModel

class PipelineStepResult(BaseModel):
    """Results of a pipeline step"""
    status: str
    articles_count: Optional[int] = None
    error: Optional[str] = None

class PipelineResult(BaseModel):
    """Complete pipeline execution results"""
    source: str
    name: str
    status: str
    steps: Dict[str, PipelineStepResult]
    error: Optional[str] = None

class SourceConfig(BaseModel):
    """Source configuration details"""
    name: str
    fetch_config: Dict
    process_config: Dict
    summary_config: Dict 