"""
Article related schemas
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID

class ArticleBase(BaseModel):
    """文章基本資料"""
    title: str
    category_name: Optional[str] = None
    source: Optional[str] = None

class RawArticleResponse(ArticleBase):
    """原始文章響應模型"""
    id: UUID
    news_id: str
    news_content: str
    pub_date: Optional[datetime] = None
    created_at: datetime

class ProcessedArticleResponse(ArticleBase):
    """已處理文章響應模型"""
    id: UUID
    raw_article_id: UUID
    summary: str
    published_at: datetime
    created_at: datetime
    
    class Config:
        """Pydantic 配置"""
        from_attributes = True

class ProcessPendingResponse(BaseModel):
    """處理待處理文章的響應模型"""
    message: str
    total_pending: int  # 待處理的總數
    processed_count: int  # 本次處理的數量
    processed_articles: List[ProcessedArticleResponse]

class LatestSummariesResponse(BaseModel):
    """Response model for latest article summaries"""
    message: str
    source: str  # Source type of the articles (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
    count: int
    articles: List[ProcessedArticleResponse]

class CategorySummaryResponse(BaseModel):
    """Response model for category summaries"""
    source: str  # Source type of the articles (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
    title: str
    summary: str
    created_at: datetime
    related: List[dict]  # List of related articles 