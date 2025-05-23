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

    SECTION_LIMITS = [4, 6]  # 第一段5篇，第二段15篇
    
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


    def select_articles_by_sections(
        self, 
        articles: List[ProcessedArticle]
    ) -> List[List[List[ProcessedArticle]]]:
        """
        將文章依照不同段落分組選擇
        
        Args:
            articles: 要篩選的文章列表
            
        Returns:
            List[List[List[ProcessedArticle]]]: 三層結構的文章列表
                - 第一層：主要段落（Top30相關、時間排序）
                - 第二層：每個主要段落中的子段落
                - 第三層：每個子段落中的文章
        """
        logger.info(f"開始分段篩選美股新聞，輸入文章數量: {len(articles)}")
        
        # 1. 先按時間排序
        articles.sort(key=lambda x: x.published_at, reverse=True)
        
        # 2. 找出所有 top30 相關的文章
        top30_stock_articles = [
            article for article in articles
            if self._is_top30_stock(article)
        ]
        
        # 第一段：使用 top30 相關文章，最多 section_limits[0] 篇
        first_section = top30_stock_articles[:self.SECTION_LIMITS[0]]
        
        # 3. 找出非 top30 的文章，按時間排序
        used_ids = {article.news_id for article in first_section}
        remaining_articles = [
            article for article in articles 
            if article.news_id not in used_ids
        ]
        
        # 第二段：剩餘文章，數量為總限制減去第一段的數量
        total_limit = self.SECTION_LIMITS[0] + self.SECTION_LIMITS[1]
        second_section_limit = total_limit - len(first_section)
        second_section = remaining_articles[:second_section_limit]
        
        # 將 first_section 分成兩個子段落
        first_half = len(first_section) // 2
        first_section_part1 = first_section[:first_half]
        first_section_part2 = first_section[first_half:]

        # 將 second_section 分成三個子段落
        base_length = len(second_section) // 3
        second_section_part1 = second_section[:base_length]
        second_section_part2 = second_section[base_length:base_length*2]
        second_section_part3 = second_section[base_length*2:]  # 自動包含剩餘的部分

        # 建立三層結構
        sectioned_articles = [
            # 第一個主要段落：Top30相關新聞
            [
                section for section in [first_section_part1, first_section_part2]
                if len(section) > 0
            ],
            # 第二個主要段落：時間排序新聞
            [
                section for section in [second_section_part1, second_section_part2, second_section_part3]
                if len(section) > 0
            ]
        ]

        # 記錄日誌
        logger.info("文章分段完成：")
        logger.info(f"第一個主要段落（Top30相關）:")
        for idx, section in enumerate(sectioned_articles[0], 1):
            logger.info(f"  子段落 {idx}: 選中 {len(section)} 篇文章")
            for article_idx, article in enumerate(section, 1):
                logger.info(f"    文章 {article_idx}: ID={article.news_id}, 標題={article.title}")

        logger.info(f"第二個主要段落（時間排序）:")
        for idx, section in enumerate(sectioned_articles[1], 1):
            logger.info(f"  子段落 {idx}: 選中 {len(section)} 篇文章")
            for article_idx, article in enumerate(section, 1):
                logger.info(f"    文章 {article_idx}: ID={article.news_id}, 標題={article.title}")

        return sectioned_articles 