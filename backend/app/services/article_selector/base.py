from typing import List, Protocol
from app.models.article import RawArticle

class ArticleSelector(Protocol):
    """文章選擇器基礎介面"""
    
    def select_articles(
        self, 
        articles: List[RawArticle], 
        limit: int
    ) -> List[RawArticle]:
        """
        選擇要進行摘要的文章
        
        Args:
            articles: 候選文章列表
            limit: 選擇數量限制
            
        Returns:
            List[RawArticle]: 選中的文章列表
        """
        raise NotImplementedError 