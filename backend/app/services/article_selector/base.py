from typing import List, Protocol, Tuple
from app.models.article import RawArticle, ProcessedArticle

class ArticleSelector(Protocol):
    """文章選擇器基礎介面"""
    
    def select_articles(
        self, 
        articles: List[ProcessedArticle], 
        select_limit: int = 20,
        top30_stock_limit: int = 7,
    ) -> Tuple[List[ProcessedArticle], int, int]:
        """
        選擇要進行摘要的文章
        
        Args:
            articles: 候選文章列表
            select_limit: 總共要選擇的文章數量
            top30_stock_limit: top30相關文章的數量限制
            
        Returns:
            Tuple[List[ProcessedArticle], int, int]: 
                - 選中的文章列表
                - highlight 文章數量
                - 總文章數量
        """
        raise NotImplementedError
        
    def select_articles_by_sections(
        self, 
        articles: List[ProcessedArticle]
    ) -> List[List[ProcessedArticle]]:
        """
        將文章依照不同段落分組選擇
        
        Args:
            articles: 要篩選的文章列表
            
        Returns:
            List[List[ProcessedArticle]]: 分段後的文章列表
        """
        raise NotImplementedError 