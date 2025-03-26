from typing import List, Tuple, Dict, Set
from datetime import datetime, timedelta
from .base import ArticleSelector
from app.models.article import ProcessedArticle
import logging

logger = logging.getLogger(__name__)

class USStockSelector(ArticleSelector):
    """美股新聞選擇器"""
    
    # 定義前30大企業的資訊
    TOP_30_COMPANIES = {
        '蘋果': 'AAPL',
        '微軟': 'MSFT',
        '輝達': 'NVDA',
        '亞馬遜': 'AMZN',
        'Alphabet': 'GOOG',  # 合併 C 類股
        'Google': 'GOOGL',   # 合併 A 類股
        'Meta': 'META',
        '波克夏': 'BRK',     # 合併 A/B 類股
        '台積電': 'TSM',
        '博通': 'AVGO',
        '禮來': 'LLY',
        '特斯拉': 'TSLA',
        '沃爾瑪': 'WMT',
        '威士卡': 'V',
        '摩根大通': 'JPM',
        '萬事達卡': 'MA',
        '埃克森美孚': 'XOM',
        '聯合健康': 'UNH',
        '甲骨文': 'ORCL',
        '好市多': 'COST',
        '寶潔': 'PG',
        '嬌生': 'JNJ',
        '艾伯維': 'ABBV',
        '家得寶': 'HD',
        '網飛': 'NFLX',
        '阿里巴巴': 'BABA',
        '可口可樂': 'KO',
        '思愛普': 'SAP',
        'T-Mobile': 'TMUS'
    }
    
    def _is_top30_stock(self, article: ProcessedArticle) -> bool:
        """
        判斷文章是否與市值前30大台股相關
        
        Args:
            article: 要判斷的文章
            
        Returns:
            bool: 是否包含前30大企業
        """
        # 檢查標題和內容
        text_to_check = f"{article.title} {article.content}"
        
        # 檢查是否包含任何一個前30大企業名稱
        for company_name in self.TOP_30_COMPANIES:
            if company_name in text_to_check:
                logger.info(f"文章 {article.news_id} 包含前30大企業: {company_name}")
                return True
                
        # 檢查股票代碼（如果有的話）
        stock_codes = getattr(article, 'stock_codes', None)
        if stock_codes:
            top30_codes = set(self.TOP_30_COMPANIES.values())
            article_codes = set(stock_codes.split(',')) if isinstance(stock_codes, str) else set()
            
            if article_codes & top30_codes:  # 如果有交集
                matched_codes = article_codes & top30_codes
                logger.info(f"文章 {article.news_id} 包含前30大股票代碼: {matched_codes}")
                return True
        
        return False
    
    def select_articles(
        self, 
        articles: List[ProcessedArticle],
        select_limit: int = 20,
        top30_stock_limit: int = 7,
    ) -> Tuple[List[ProcessedArticle], int, int]:
        """
        選擇台股相關新聞
        
        Args:
            articles: 要篩選的文章列表
            select_limit: 總共要選擇的文章數量
            top30_stock_limit: top30相關文章的數量限制
            
        Returns:
            Tuple[List[ProcessedArticle], int, int]: 
                - 選中的文章列表
                - highlight 文章數量
                - 總文章數量
        """
        logger.info(f"開始篩選台股新聞，輸入文章數量: {len(articles)}")
        
        # 如果文章總數少於15篇，直接返回全部
        if len(articles) <= select_limit:
            logger.info(f"文章數量({len(articles)})小於等於{select_limit}篇，返回全部文章")
            return articles, 0, len(articles)
        # 1. 先按時間排序選出最新的30篇
        articles.sort(key=lambda x: x.published_at, reverse=True)
        logger.info(f"選出最新的{select_limit}篇文章")
        
        # 2. 從這些文章中找出 top30 相關的文章，並限制數量
        top30_stock_articles = [
            article for article in articles
            if self._is_top30_stock(article)
        ][:top30_stock_limit]
        
        logger.info(f"從{select_limit}篇中選出 {len(top30_stock_articles)} 篇市值前30大相關文章")
        
        # 3. 從剩餘文章中選出補充文章
        used_ids = {article.news_id for article in top30_stock_articles}
        remaining_articles = [
            article for article in articles 
            if article.news_id not in used_ids
        ]
        
        # 選擇剩餘文章（已經是按時間排序的）
        remaining_limit = select_limit - len(top30_stock_articles)
        selected_others = remaining_articles[:remaining_limit]
        logger.info(f"選出剩餘 {len(selected_others)} 篇補充文章")
        
        # 合併結果
        selected = top30_stock_articles + selected_others
        
        logger.info(f"篩選完成，共選出 {len(selected)} 篇文章:")
        logger.info(f"- 市值前30大相關: {len(top30_stock_articles)} 篇")
        logger.info(f"- 其他文章: {len(selected_others)} 篇")
        
        # 記錄選中的文章
        for idx, article in enumerate(selected, 1):
            logger.info(f"已選擇 {idx}: {article.news_id} ({article.title})")
        
        # 最後返回時加入兩個新的值
        highlight_count = len(top30_stock_articles)
        total_count = len(selected)
        
        return selected, highlight_count, total_count  