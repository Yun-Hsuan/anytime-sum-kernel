import logging
from typing import List
from sqlmodel import select
from datetime import datetime

from app.models.article import RawArticle, ProcessedArticle, ArticleSource
from ..providers import AzureOpenAIClient

logger = logging.getLogger(__name__)

class SummaryGenerator:
    """文章摘要生成服務"""
    
    def __init__(self):
        self.ai_client = AzureOpenAIClient()
        
    async def generate_summary(self, content: str) -> str:
        """
        使用 Azure OpenAI 生成文章摘要
        
        Args:
            content: 文章內容
            
        Returns:
            str: 生成的摘要
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": """你是一個專業的新聞摘要生成器。請針對提供的新聞內容生成一個簡短的摘要，需要：
                                    1. 摘要長度必須嚴格限制在50字元內
                                    2. 摘要長度以3句話為限
                                    3. 保留文章最重要的信息點
                                    4. 客觀的語氣"""
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            print("--------------------------------")   
            print(response)
            print("--------------------------------")
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"生成摘要時發生錯誤: {str(e)}")
            return ""
            
    async def process_articles(self, db, limit: int = 10) -> List[ProcessedArticle]:
        """
        處理原始文章並生成摘要
        
        Args:
            db: 資料庫會話
            limit: 處理的文章數量
            
        Returns:
            List[ProcessedArticle]: 處理後的文章列表
        """
        try:
            # 查詢尚未處理的原始文章
            statement = select(RawArticle).limit(limit)
            raw_articles = (await db.execute(statement)).scalars().all()
            
            print("--------------------------------")   
            print(f"len(raw_articles): {len(raw_articles)}")
            print("--------------------------------")
            
            processed_articles = []
            for raw_article in raw_articles:
                try:
                    # 檢查是否已經存在對應的處理過的文章
                    processed_exists = await db.execute(
                        select(ProcessedArticle).where(
                            ProcessedArticle.raw_article_id == raw_article.id
                        )
                    )
                    if processed_exists.first():
                        continue
                    
                    # 生成摘要
                    summary = await self.generate_summary(raw_article.news_content)
                    
                    # 從 pub_date 轉換為 datetime
                    published_at = datetime.fromtimestamp(raw_article.pub_date) if raw_article.pub_date else datetime.utcnow()
                    
                    # 創建處理後的文章
                    processed_article = ProcessedArticle(
                        raw_article_id=raw_article.id,
                        title=raw_article.title,
                        content=raw_article.news_content,
                        summary=summary,
                        source=raw_article.source,
                        category_id=raw_article.category_id,
                        category_name=raw_article.category_name,
                        stocks=raw_article.stock,
                        tags=raw_article.tags,
                        published_at=published_at,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    db.add(processed_article)
                    processed_articles.append(processed_article)
                    
                except Exception as e:
                    logger.error(f"處理文章 {raw_article.id} 時發生錯誤: {str(e)}")
                    continue
            
            await db.commit()
            return processed_articles
            
        except Exception as e:
            logger.error(f"批量處理文章時發生錯誤: {str(e)}")
            await db.rollback()
            raise 