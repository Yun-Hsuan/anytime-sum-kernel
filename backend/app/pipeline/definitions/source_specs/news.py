"""
News source specifications
"""

from typing import Dict
from .base import SourceSpec

class NewsSourceSpec(SourceSpec):
    """Specification for news sources"""
    
    def __init__(
        self,
        source_id: str,
        name: str,
        scraper_type: str,
        fetch_limit: int = 150,
        process_limit: int = 150,
        summary_limit: int = 30
    ):
        self._source_id = source_id
        self._name = name
        self._scraper_type = scraper_type
        self._fetch_limit = fetch_limit
        self._process_limit = process_limit
        self._summary_limit = summary_limit

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def fetch_config(self) -> Dict:
        return {
            "source_type": self._scraper_type,
            "limit": self._fetch_limit
        }

    @property
    def process_config(self) -> Dict:
        return {
            "limit": self._process_limit
        }

    @property
    def summary_config(self) -> Dict:
        return {
            "source": self._source_id,
            "limit": self._summary_limit
        } 