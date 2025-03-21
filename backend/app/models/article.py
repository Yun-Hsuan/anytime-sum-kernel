from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel
from sqlalchemy import JSON

class ArticleSource(str, Enum):
    CNYES_TW = "cnyes_tw"    # Anue Taiwan Stock News
    CNYES_US = "cnyes_us"    # Anue US Stock News
    CNYES_HEADLINE = "cnyes_headline"  # Anue Headlines
    ELIFE = "elife"      # eLife

class ArticleStatus(str, Enum):
    PENDING = "pending"      # Waiting to be processed
    PROCESSING = "processing"  # Currently being processed
    PROCESSED = "processed"    # Processing completed
    FAILED = "failed"         # Processing failed

class ImageInfo(SQLModel):
    """Image information model"""
    src: str
    width: int
    height: int

class RawArticle(SQLModel, table=True):
    """Raw article data model, designed based on Anue API response format"""
    
    # System fields
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source: str = Field(index=True)  # Source type for summary
    status: ArticleStatus = Field(default=ArticleStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Article basic information
    news_id: str = Field(index=True)          # News ID
    title: str = Field(index=True)            # Title
    copyright: str                            # Copyright information
    creator: str                              # Author
    
    # Category information
    category_id: int = Field(index=True)      # Category ID
    category_name: str = Field(index=True)    # Category name
    
    # Time information
    pub_date: int                            # Publication timestamp
    
    # Content
    news_content: str                        # News content
    
    # Image information
    image_url: Optional[Dict] = Field(default=None, sa_type=JSON)    # Small image
    image_l: Optional[Dict] = Field(default=None, sa_type=JSON)      # Large image
    
    # Tags
    stock: List[str] = Field(default=[], sa_type=JSON)              # Related stock codes
    tags: List[str] = Field(default=[], sa_type=JSON)               # Tags
    
    class Config:
        schema_extra = {
            "example": {
                "news_id": "5889905",
                "title": "Ming-Chien Chiu: Domestic Employment Faces Transformation, Government Should Raise Civil Servant Salaries",
                "copyright": "Anue",
                "creator": "Anue Reporter Wei-Hao, Taipei",
                "category_id": 828,
                "category_name": "Taiwan Politics & Economics",
                "pub_date": 1741508322,
                "image_url": {
                    "src": "https://cimg.cnyes.cool/prod/news/5889905/s/xxx.jpg",
                    "width": 180,
                    "height": 101
                },
                "image_l": {
                    "src": "https://cimg.cnyes.cool/prod/news/5889905/l/xxx.jpg",
                    "width": 640,
                    "height": 360
                },
                "stock": ["3680"],
                "tags": ["Jiadeng", "National", "Innovation"]
            }
        }

class ProcessedArticle(SQLModel, table=True):
    """Model for storing cleaned and structured article data"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    raw_article_id: UUID = Field(foreign_key="rawarticle.id", index=True)
    news_id: str = Field(index=True)  # News ID, corresponding to raw article
    
    # Basic Information
    title: str = Field(index=True)
    content: str
    summary: Optional[str] = None
    
    # Metadata
    source: str = Field(index=True)  # Source type for summary
    category_id: int = Field(index=True)
    category_name: str = Field(index=True)
    author: Optional[str] = None
    published_at: datetime = Field(index=True)
    
    # Classification Tags
    stocks: List[str] = Field(default=[], sa_type=JSON)     # Related stock codes
    tags: List[str] = Field(default=[], sa_type=JSON)       # Tags
    
    # Image Information
    image_url: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    
    # System Information
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    processed_data: Dict = Field(default={}, sa_type=JSON)  # Processed data
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Machine Tool Show Concludes! Indian Buyers Top Procurement",
                "content": "The show jointly organized by TAITRA and TAMI...",
                "summary": "Machine Tool Show attracts international buyers, with Indian buyers ranking first",
                "source": "cnyes_tw",
                "category_id": 827,
                "category_name": "Taiwan Stock News",
                "news_id": "5889905",  # 添加示例 news_id
                "author": "Anue Reporter",
                "stocks": ["2049", "1597"],
                "tags": ["Machine Tools", "TIMTOS", "Robotics"]
            }
        }

class LatestSummary(SQLModel, table=True):
    """Latest news summary aggregation"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source: str = Field(index=True)  # Source type for summary
    title: str
    summary: str
    related: List[Dict] = Field(default=[], sa_type=JSON)  # Related news
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "source": "TW_Stock_Summary",
                "title": "Taiwan Stock Market Pre-market Summary",
                "summary": "Today's Taiwan stock market opens...",
                "related": [
                    {
                        "newsId": "5884805",
                        "title": "TSMC Takes a Break as Small-cap Stocks Take the Lead"
                    }
                ]
            }
        }