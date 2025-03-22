"""
Base specifications for pipeline sources
"""

from typing import Dict
from abc import ABC, abstractmethod

class SourceSpec(ABC):
    """Base class for all source specifications"""
    
    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier for the source"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human readable name"""
        pass

    @property
    @abstractmethod
    def fetch_config(self) -> Dict:
        """Configuration for fetching articles"""
        pass

    @property
    @abstractmethod
    def process_config(self) -> Dict:
        """Configuration for processing articles"""
        pass

    @property
    @abstractmethod
    def summary_config(self) -> Dict:
        """Configuration for generating summaries"""
        pass 