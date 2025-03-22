"""
Dependencies for pipeline operations
"""

from typing import Annotated
from fastapi import Depends

from .definitions.settings import PipelineSettings

def get_pipeline_settings() -> PipelineSettings:
    """Get pipeline settings"""
    return PipelineSettings()

# 定義可重用的依賴
PipelineSettingsDep = Annotated[PipelineSettings, Depends(get_pipeline_settings)] 