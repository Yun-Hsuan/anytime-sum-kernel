from typing import List, Tuple, Dict, Set
from datetime import datetime, timedelta
from .base import ArticleSelector
from app.models.article import ProcessedArticle
import logging

logger = logging.getLogger(__name__)

class TWStockSelector(ArticleSelector):
    """台股新聞選擇器"""
    
    # 定義前30大企業的資訊
    TOP_30_COMPANIES = {
        '台積電': '2330',
        '鴻海': '2317',
        '聯發科': '2454',
        '富邦金': '2881',
        '廣達': '2382',
        '台達電': '2308',
        '中華電': '2412',
        '國泰金': '2882',
        '中信金': '2891',
        '日月光投控': '3711',
        '兆豐金': '2886',
        '聯電': '2303',
        '長榮': '2603',
        '華碩': '2357',
        '統一': '1216',
        '玉山金': '2884',
        '元大金': '2885',
        '台灣大': '3045',
        '第一金': '2892',
        '中鋼': '2002',
        '華南金': '2880',
        '台塑化': '6505',
        '合庫金': '5880',
        '緯穎': '6669',
        '智邦': '2345',
        '大立光': '3008',
        '研華': '2395',
        '世紀': '5314',
        '遠傳': '4904',
        '和泰車': '2207'
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
        limit: int = 15
    ) -> List[ProcessedArticle]:
        """
        選擇台股相關新聞
        
        規則：
        1. 輸入文章最多30篇
        2. 如果總數少於15篇，直接返回全部
        3. 市值前30大相關新聞優先選5篇（按時間排序）
        4. 剩餘名額由其他文章依照時間順序補滿
        """
        logger.info(f"開始篩選台股新聞，輸入文章數量: {len(articles)}")
        
        # 如果文章總數少於15篇，直接返回全部
        if len(articles) <= limit:
            logger.info(f"文章數量({len(articles)})小於等於{limit}篇，返回全部文章")
            return articles
            
        # 先找出所有 top30 相關的文章
        top30_articles = []
        for article in articles:
            if self._is_top30_stock(article):
                top30_articles.append(article)
        
        logger.info(f"找到市值前30大相關文章: {len(top30_articles)}篇")
        
        # 按發布時間排序並選擇最新的5篇 top30 文章
        top30_articles.sort(key=lambda x: x.published_at, reverse=True)
        selected_top30 = top30_articles[:5]
        logger.info(f"選出最新的 {len(selected_top30)} 篇市值前30大相關文章")
        
        # 將未被選中的 top30 文章和其他文章合併，作為候選文章
        used_ids = {article.news_id for article in selected_top30}
        other_candidates = [
            article for article in articles 
            if article.news_id not in used_ids
        ]
        
        # 對剩餘文章按時間排序
        other_candidates.sort(key=lambda x: x.published_at, reverse=True)
        
        # 選擇剩餘名額
        remaining_slots = limit - len(selected_top30)
        selected_others = other_candidates[:remaining_slots]
        
        logger.info(f"從剩餘 {len(other_candidates)} 篇文章中選出 {len(selected_others)} 篇補充")
        
        # 合併結果
        selected = selected_top30 + selected_others
        
        logger.info(f"篩選完成，共選出 {len(selected)} 篇文章:")
        logger.info(f"- 市值前30大相關: {len(selected_top30)} 篇")
        logger.info(f"- 其他文章: {len(selected_others)} 篇")
        
        # 記錄選中的文章
        for idx, article in enumerate(selected, 1):
            logger.info(f"已選擇 {idx}: {article.news_id} ({article.title})")
        
        return selected 