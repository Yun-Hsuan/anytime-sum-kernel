"""
Category summary generator
"""

from typing import List, Dict
from datetime import datetime
from sqlmodel import select
import logging

from .base import BaseSummaryGenerator
from app.models.article import RawArticle, LatestSummary
from .prompts.category import get_system_prompt, get_system_prompt_paragraph
from .prompts.title import TITLE_SYSTEM_PROMPT
from .prompts.summary_inspection import get_system_prompt as get_summary_inspection_prompt

logger = logging.getLogger(__name__)

class CategorySummaryGenerator(BaseSummaryGenerator):
    """Generator for category-based summaries"""
    
    # Define allowed source types
    ALLOWED_SOURCES = {
        "TW_Stock_Summary",  # Taiwan stock news
        "US_Stock_Summary",  # US stock news 
        "Hot_News_Summary"   # Hot news
    }
    
    # Define source title mapping
    SOURCE_TITLE_MAPPING = {
        "TW_Stock_Summary": "台股市場最新動態",
        "US_Stock_Summary": "美股市場最新動態",
        "Hot_News_Summary": "財經熱門新聞"
    }

    async def generate_summary(self, content: str, source_type: str, highlight_count: int = 6, total_count: int = 20) -> str:
        """
        Generate summary for multiple articles
        
        Args:
            content: Formatted article content
            source_type: Type of news source
            highlight_count: Number of articles in highlight section
            
        Returns:
            str: Generated summary
        """
        try:
            total_count = len(content.split('文章 ')) - 1  # 計算總文章數
            
            # 添加日誌來追蹤內容長度
            logger.info(f"Input content length: {len(content)} characters")
            logger.info(f"Number of articles: {total_count}")
            
            messages = [
                {
                    "role": "system",
                    "content": get_system_prompt(
                        source_type=source_type,
                        highlight_count=highlight_count,
                        total_count=total_count
                    )
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            print("--------------------------------")
            print(content)
            print("--------------------------------")
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.75,
                max_tokens=12000
            )
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating category summary: {str(e)}")
            raise ValueError(f"生成摘要失敗: {str(e)}")


    async def generate_title(self, content: str, source_type: str) -> str:
        """
        Generate title from category summary
        
        Args:
            content: Category summary content
            source_type: Type of news source (TW_Stock_Summary/US_Stock_Summary/Hot_News_Summary)
            
        Returns:
            str: Generated title (max 20 characters)
        """
        try:
            # 添加源類型資訊到內容中以生成更相關的標題
            context = f"新聞類型：{self.SOURCE_TITLE_MAPPING[source_type]}\n摘要內容：{content}"
            
            messages = [
                {
                    "role": "system",
                    "content": TITLE_SYSTEM_PROMPT
                },
                {
                    "role": "user", 
                    "content": context
                }
            ]
            
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=50
            )
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating category title: {str(e)}")
            raise ValueError(f"生成標題失敗: {str(e)}")  # 保持與 generate_summary 一致的錯誤處理方式

    async def generate_paragraph(
        self,
        content: str,
        begin_idx: int,
        end_idx: int,
        source_type: str,
        paragraph_type: str = "highlight"
    ) -> str:
        """
        生成單個段落的摘要
        
        Args:
            content: 要摘要的文章內容
            begin_idx: 引用編號的起始值
            end_idx: 引用編號的結束值
            source_type: 新聞來源類型
            paragraph_type: 段落類型 (default: "highlight")
            
        Returns:
            str: 生成的段落摘要
        """
        try:
            logger.info(f"Generating {paragraph_type} paragraph for articles {begin_idx}-{end_idx}")
            logger.info(f"Input content length: {len(content)} characters")
            
            messages = [
                {
                    "role": "system",
                    "content": get_system_prompt_paragraph(
                        source_type=source_type,
                        begin_idx=begin_idx,
                        end_idx=end_idx,
                        paragraph_type=paragraph_type
                    )
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=4000
            )
            
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating paragraph: {str(e)}")
            raise ValueError(f"生成段落失敗: {str(e)}")

    async def summary_inspection(
        self,
        summary_html: str,
    ) -> str:
        """
        對已生成的 summary 進行最後檢查與結語追加

        Args:
            summary_html: 已生成的 summary HTML 內容
            source_type: 新聞來源類型

        Returns:
            str: 經過檢查與追加結語後的 summary
        """
        try:
            logger.info("開始進行 summary_inspection 檢查")
            messages = [
                {
                    "role": "system",
                    "content": get_summary_inspection_prompt()
                },
                {
                    "role": "user",
                    "content": summary_html
                }
            ]
            response = await self.ai_client.get_completion(
                messages=messages,
                temperature=0.4,
                max_tokens=4000
            )
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"summary_inspection 發生錯誤: {str(e)}")
            raise ValueError(f"summary_inspection 失敗: {str(e)}")
