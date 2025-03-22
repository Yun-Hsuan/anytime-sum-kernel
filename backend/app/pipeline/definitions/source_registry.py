"""
Registry for pipeline sources
"""

from typing import Dict, List
from .source_specs.news import NewsSourceSpec

class SourceRegistry:
    """Registry for managing pipeline sources"""

    _sources: Dict[str, NewsSourceSpec] = {
        "TW_Stock_Summary": NewsSourceSpec(
            source_id="TW_Stock_Summary",
            name="台股市場最新動態",
            scraper_type="tw_stock"
        ),
        "US_Stock_Summary": NewsSourceSpec(
            source_id="US_Stock_Summary",
            name="美股市場最新動態",
            scraper_type="us_stock"
        ),
        "Hot_News_Summary": NewsSourceSpec(
            source_id="Hot_News_Summary",
            name="財經熱門新聞",
            scraper_type="hot_news"
        )
    }

    @classmethod
    def get_source(cls, source_id: str) -> NewsSourceSpec:
        """Get source specification by ID"""
        if source_id not in cls._sources:
            raise ValueError(f"Invalid source: {source_id}")
        return cls._sources[source_id]

    @classmethod
    def get_all_sources(cls) -> List[str]:
        """Get all registered source IDs"""
        return list(cls._sources.keys())

    @classmethod
    def get_source_specs(cls) -> Dict[str, Dict]:
        """Get all source specifications"""
        return {
            source_id: {
                "name": spec.name,
                "fetch_config": spec.fetch_config,
                "process_config": spec.process_config,
                "summary_config": spec.summary_config
            }
            for source_id, spec in cls._sources.items()
        } 