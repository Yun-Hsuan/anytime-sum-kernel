from typing import Dict, Type
from app.services.article_selector.base import ArticleSelector
from app.services.article_selector.tw_selector import TWStockSelector
from app.services.article_selector.us_selector import USStockSelector
from app.services.article_selector.headline_selector import HeadlineSelector

class ArticleSelectorService:
    """文章選擇器服務"""
    
    _selector_mapping: Dict[str, Type[ArticleSelector]] = {
        "tw": TWStockSelector,
        "us": USStockSelector,
        "headline": HeadlineSelector
    }
    
    @classmethod
    def get_selector(cls, source_type: str) -> ArticleSelector:
        """
        獲取對應的文章選擇器
        
        Args:
            source_type: 來源類型 (tw/us/headline)
            
        Returns:
            ArticleSelector: 對應的選擇器實例
        
        Raises:
            ValueError: 如果找不到對應的選擇器
        """
        selector_class = cls._selector_mapping.get(source_type)
        if not selector_class:
            raise ValueError(f"Unknown source type: {source_type}")
        
        return selector_class()

# 創建服務實例
article_selector_service = ArticleSelectorService() 