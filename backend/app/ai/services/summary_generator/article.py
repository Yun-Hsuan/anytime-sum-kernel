"""
Single article summary generator
"""

from typing import List
from sqlmodel import select
import logging

from .base import BaseSummaryGenerator
from app.models.article import RawArticle, ProcessedArticle
from .prompts.article import SYSTEM_PROMPT
from .prompts.title import TITLE_SYSTEM_PROMPT
from .prompts.category_check import CATEGORY_CHECK_PROMPT

logger = logging.getLogger(__name__)

class SingleArticleSummaryGenerator(BaseSummaryGenerator):
    """Generator for single article summaries"""
    
    async def generate_summary(self, content: str) -> str:
        """
        Generate summary for a single article
        
        Args:
            content: Article content
            
        Returns:
            str: Generated summary
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=1200
            )
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating article summary: {str(e)}")
            return ""

    async def process_latest_articles(self, db, limit: int = 15) -> List[ProcessedArticle]:
        """
        Process latest unprocessed articles
        
        Args:
            db: Database session
            limit: Number of articles to process
            
        Returns:
            List[ProcessedArticle]: List of processed articles
        """
        # Query latest unprocessed articles
        statement = (
            select(RawArticle)
            .order_by(RawArticle.created_at.desc())
            .limit(limit)
        )
        articles = (await db.execute(statement)).scalars().all()
        return await self.process_articles(db, articles)

    async def generate_title(self, content: str) -> str:
        """
        Generate title from article summary
        
        Args:
            content: Article summary content
            
        Returns:
            str: Generated title (max 20 characters)
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": TITLE_SYSTEM_PROMPT
                },
                {
                    "role": "user", 
                    "content": content
                }
            ]
            
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=50  # 標題較短，可以設置較小的 max_tokens
            )
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating article title: {str(e)}")
            return ""

    async def check_is_category(self, content: str, category: str) -> bool:
        """
        使用 AI 判斷文章是否屬於指定類別
        
        Args:
            content: 文章內容（標題 + 內容）
            category: 要檢查的類別名稱
            
        Returns:
            bool: 是否屬於該類別
        """
        try:
            # 構建提示詞
            system_prompt = CATEGORY_CHECK_PROMPT.format(category=category)
            
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            # 調用 AI 進行判斷
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.1,  # 使用較低的溫度以獲得更確定的答案
                max_tokens=10     # 只需要簡短的回答
            )
            
            result = response["choices"][0]["message"]["content"].strip().lower()
            
            # 記錄判斷結果
            logger.info(f"類別判斷 - 內容長度: {len(content)}, 類別: {category}, 結果: {result}")
            
            # 解析回應（預期回應為 "yes" 或 "no"）
            return result == "yes"
            
        except Exception as e:
            logger.error(f"判斷文章類別時發生錯誤: {str(e)}")
            return False
