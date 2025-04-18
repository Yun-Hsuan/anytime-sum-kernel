from typing import List, Tuple, Dict
from datetime import datetime, timedelta
from .base import ArticleSelector
from app.models.article import ProcessedArticle
import logging

logger = logging.getLogger(__name__)

class HeadlineSelector(ArticleSelector):
    """頭條新聞選擇器"""
    
    # 定義分段限制
    SECTION_LIMITS = [4, 4, 7]  # 第一段5篇，第二段5篇，第三段10篇
    
    # 定義宏觀經濟相關標籤
    MACRO_TAGS = ["全球宏觀", "經濟發展趨勢", "地緣政治局勢"]
    
    # 定義重要公司列表
    TOP_COMPANIES = {
        # 中國公司
        'CN': {
            '騰訊控股': '00700',
            '阿里巴巴': '09988',
            '工商銀行': '01398',
            '中國移動': '00941',
            '建設銀行': '00939',
            '農業銀行': '01288',
            '中國鐵塔': '00788',
            '中國銀行': '03988',
            '小米集團': '01810',
            '美團': '03690',
            '比亞迪': '01211',
            '中國平安': '02318',
            '中國海油': '00883',
            '貴州茅台': '600519',
            '寧德時代': '300750',
            '中芯國際': '00981',
        },
        # 美國公司
        'US': {
            '蘋果': 'AAPL',
            '微軟': 'MSFT',
            '輝達': 'NVDA',
            '亞馬遜': 'AMZN',
            'Meta平台': 'META',
            '特斯拉': 'TSLA',
            '博通': 'AVGO',
            '摩根大通': 'JPM',
            '威士卡': 'V',
            '萬事達卡': 'MA',
        },
        # 台灣公司
        'TW': {
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
        }
    }

    def _is_important_company(self, article: ProcessedArticle) -> bool:
        """
        判斷文章是否與重要公司相關
        
        Args:
            article: 要判斷的文章
            
        Returns:
            bool: 是否包含重要公司
        """
        # 檢查標題和內容
        text_to_check = f"{article.title} {article.content}"
        
        # 檢查各個地區的公司
        for region, companies in self.TOP_COMPANIES.items():
            for company_name in companies:
                if company_name in text_to_check:
                    logger.info(f"文章 {article.news_id} 包含重要公司: {company_name} ({region})")
                    return True
                    
        # 檢查股票代碼（如果有的話）
        stock_codes = getattr(article, 'stock_codes', None)
        if stock_codes:
            # 合併所有地區的股票代碼
            all_codes = set()
            for companies in self.TOP_COMPANIES.values():
                all_codes.update(companies.values())
            
            article_codes = set(stock_codes.split(',')) if isinstance(stock_codes, str) else set()
            
            if article_codes & all_codes:  # 如果有交集
                matched_codes = article_codes & all_codes
                logger.info(f"文章 {article.news_id} 包含重要公司股票代碼: {matched_codes}")
                return True
        
        return False

    def _calculate_macroeconomics_score(self, article: ProcessedArticle) -> int:
        """
        計算文章的宏觀經濟相關分數
        
        Args:
            article: 要計算分數的文章
            
        Returns:
            int: 文章分數
        """
        score = 0
        
        # 檢查是否包含宏觀經濟標籤
        if hasattr(article, 'tags') and article.tags:
            article_tags = set(article.tags)
            macro_matches = article_tags.intersection(self.MACRO_TAGS)
            if macro_matches:
                score += len(macro_matches)
                logger.info(f"文章 {article.news_id} 包含宏觀經濟標籤 {macro_matches}，分數 +{len(macro_matches)}")
        
        return score

    def _select_macroeconomics_articles(
        self,
        articles: List[ProcessedArticle],
        limit: int
    ) -> List[ProcessedArticle]:
        """
        選擇宏觀經濟相關分數最高的文章
        
        Args:
            articles: 要選擇的文章列表
            limit: 選擇數量上限
            
        Returns:
            List[ProcessedArticle]: 選中的文章列表
        """
        # 建立4個空列表，分別存放分數0-3的文章
        scored_articles = [[] for _ in range(4)]
        
        # 將文章依照分數分類
        for article in articles:
            score = self._calculate_macroeconomics_score(article)
            scored_articles[score].append(article)
        
        # 從高分到低分選擇文章
        selected_articles = []
        for score_articles in reversed(scored_articles):  # 從分數3開始往下
            # 每個分數層級的文章按時間排序
            score_articles.sort(key=lambda x: x.published_at, reverse=True)
            selected_articles.extend(score_articles)
            if len(selected_articles) >= limit:
                break
        
        selected_articles = selected_articles[:limit]
        
        # 記錄選擇結果
        logger.info(f"選出分數最高的 {len(selected_articles)} 篇文章：")
        for idx, article in enumerate(selected_articles, 1):
            logger.info(f"  文章 {idx}: ID={article.news_id}, 標題={article.title}")
        
        return selected_articles

    def select_articles(
        self, 
        articles: List[ProcessedArticle],
        select_limit: int = 20,
        top30_stock_limit: int = 7,  # 這裡改為熱門新聞限制
    ) -> Tuple[List[ProcessedArticle], int, int]:
        """
        選擇頭條新聞
        
        Args:
            articles: 要篩選的文章列表
            select_limit: 總共要選擇的文章數量
            top30_stock_limit: 熱門新聞的數量限制
            
        Returns:
            Tuple[List[ProcessedArticle], int, int]: 
                - 選中的文章列表
                - highlight 文章數量
                - 總文章數量
        """
        logger.info(f"開始篩選頭條新聞，輸入文章數量: {len(articles)}")
        
        # 如果文章總數少於限制，直接返回全部
        if len(articles) <= select_limit:
            logger.info(f"文章數量({len(articles)})小於等於{select_limit}篇，返回全部文章")
            return articles, 0, len(articles)

        # 1. 先按時間排序選出最新的文章
        articles.sort(key=lambda x: x.published_at, reverse=True)
        
        # 2. 選出最近12小時內的熱門文章
        time_threshold = datetime.now() - timedelta(hours=12)
        hot_articles = [
            article for article in articles
            if article.published_at >= time_threshold
        ][:top30_stock_limit]
        
        logger.info(f"從{select_limit}篇中選出 {len(hot_articles)} 篇熱門文章")
        
        # 3. 從剩餘文章中選出補充文章
        used_ids = {article.news_id for article in hot_articles}
        remaining_articles = [
            article for article in articles 
            if article.news_id not in used_ids
        ]
        
        # 選擇剩餘文章（已經是按時間排序的）
        remaining_limit = select_limit - len(hot_articles)
        selected_others = remaining_articles[:remaining_limit]
        logger.info(f"選出剩餘 {len(selected_others)} 篇補充文章")
        
        # 合併結果
        selected = hot_articles + selected_others
        
        logger.info(f"篩選完成，共選出 {len(selected)} 篇文章:")
        logger.info(f"- 熱門文章: {len(hot_articles)} 篇")
        logger.info(f"- 其他文章: {len(selected_others)} 篇")
        
        # 記錄選中的文章
        for idx, article in enumerate(selected, 1):
            logger.info(f"已選擇 {idx}: {article.news_id} ({article.title})")
        
        highlight_count = len(hot_articles)
        total_count = len(selected)
        
        return selected, highlight_count, total_count

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
                - 第一段：總經相關（最多5篇）
                - 第二段：重要公司相關（最多5篇）
                - 第三段：其他最新文章（補足至20篇）
        """
        logger.info(f"開始分段篩選頭條新聞，輸入文章數量: {len(articles)}")
        
        # 1. 選出總經相關分數最高的文章作為第一段
        first_section = self._select_macroeconomics_articles(
            articles,
            self.SECTION_LIMITS[0]
        )
        
        # 2. 從剩餘文章中找出重要公司相關的文章作為第二段
        used_ids = {article.news_id for article in first_section}
        remaining_for_company = [
            article for article in articles 
            if article.news_id not in used_ids
        ]
        
        company_articles = [
            article for article in remaining_for_company
            if self._is_important_company(article)
        ]
        second_section = company_articles[:self.SECTION_LIMITS[1]]
        
        # 3. 用最新文章補足第三段
        used_ids.update(article.news_id for article in second_section)
        remaining_articles = [
            article for article in articles 
            if article.news_id not in used_ids
        ]
        
        # 計算第三段需要的文章數量
        total_limit = sum(self.SECTION_LIMITS)  # 20篇
        remaining_limit = total_limit - len(first_section) - len(second_section)
        
        # 按時間排序選擇最新的文章
        remaining_articles.sort(key=lambda x: x.published_at, reverse=True)
        third_section = remaining_articles[:remaining_limit]
        
        # first_section 分成兩半
        first_half = len(first_section) // 2
        first_section_part1 = first_section[:first_half]
        first_section_part2 = first_section[first_half:]

        # second_section 分成兩半
        second_half = len(second_section) // 2
        second_section_part1 = second_section[:second_half]
        second_section_part2 = second_section[second_half:]

        # third_section 分成三份
        third_base_length = len(third_section) // 3
        third_section_part1 = third_section[:third_base_length]
        third_section_part2 = third_section[third_base_length:third_base_length*2]
        third_section_part3 = third_section[third_base_length*2:]  # 自動包含剩餘的部分

        # 初始化空的 sectioned_articles
        sectioned_articles = []

        # 檢查並加入 first_section 的兩個部分
        if len(first_section_part1) > 0:
            sectioned_articles.append(first_section_part1)
        if len(first_section_part2) > 0:
            sectioned_articles.append(first_section_part2)

        # 檢查並加入 second_section 的兩個部分
        if len(second_section_part1) > 0:
            sectioned_articles.append(second_section_part1)
        if len(second_section_part2) > 0:
            sectioned_articles.append(second_section_part2)

        # 檢查並加入 third_section 的三個部分
        if len(third_section_part1) > 0:
            sectioned_articles.append(third_section_part1)
        if len(third_section_part2) > 0:
            sectioned_articles.append(third_section_part2)
        if len(third_section_part3) > 0:
            sectioned_articles.append(third_section_part3)

        # 記錄日誌
        logger.info(f"總共分成 {len(sectioned_articles)} 個段落")
        for idx, section in enumerate(sectioned_articles, 1):
            logger.info(f"第 {idx} 段: 選中 {len(section)} 篇文章")
        
        return sectioned_articles 