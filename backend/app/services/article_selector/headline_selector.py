from typing import List, Tuple, Dict
from datetime import datetime, timedelta
from .base import ArticleSelector
from app.models.article import ProcessedArticle
import logging

logger = logging.getLogger(__name__)

class HeadlineSelector(ArticleSelector):
    """頭條新聞選擇器"""
    
    # 定義分段限制
    SECTION_LIMITS = [8, 7, 0]  # 第一段5篇，第二段5篇，第三段10篇
    
    # 定義宏觀經濟相關標籤
    MACRO_TAGS = ["全球宏觀", "經濟發展趨勢", "地緣政治局勢"]

    TOP_TAGS = ["top"]
    
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
    
    def _is_top_article(self, article: ProcessedArticle) -> bool:
        """
        判斷文章是否為 top 類型
        
        Args:
            article: 要判斷的文章
            
        Returns:
            bool: 是否為 top 類型文章
        """
        # 1. 檢查是否為三小時內的文章
        time_threshold = datetime.now() - timedelta(hours=3)
        if article.published_at < time_threshold:
            return False
        
        # 2. 檢查文章標籤
        if hasattr(article, 'tags') and article.tags:
            # 將標籤轉換為小寫進行比對
            article_tags = [tag.lower() if isinstance(tag, str) else tag for tag in article.tags]
            
            # 檢查是否包含 TOP_TAGS 中的任何標籤
            if any(tag in article_tags for tag in self.TOP_TAGS):
                logger.info(f"文章 {article.news_id} 是 top 文章，標題：{article.title}")
                return True
        
        return False 

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
    
    def _select_top_articles(
        self,
        articles: List[ProcessedArticle]
    ) -> List[ProcessedArticle]:
        """
        選擇所有符合 top 類型的文章
        
        Args:
            articles: 要選擇的文章列表
            
        Returns:
            List[ProcessedArticle]: 選中的文章列表
        """
        # 篩選出所有符合 top 條件的文章
        top_articles = [
            article for article in articles
            if self._is_top_article(article)
        ]
        
        # 按發布時間排序（最新的在前）
        top_articles.sort(key=lambda x: x.published_at, reverse=True)
        
        # 記錄選擇結果
        logger.info(f"選出 {len(top_articles)} 篇 top 文章：")
        for idx, article in enumerate(top_articles, 1):
            logger.info(f"  文章 {idx}: ID={article.news_id}, 標題={article.title}")
        
        return top_articles 
    
    def select_articles_by_sections(
        self, 
        articles: List[ProcessedArticle]
    ) -> List[List[List[ProcessedArticle]]]:
        """
        將文章依照不同段落分組選擇
        
        Args:
            articles: 要篩選的文章列表
            
        Returns:
            List[List[List[ProcessedArticle]]]: 三層結構：整篇文章 -> 段落 -> 小段落
        """
        logger.info(f"開始分段篩選頭條新聞，輸入文章數量: {len(articles)}")
        
        sectioned_articles = []
        total_selected = 0
        used_ids = set()  # 用於追蹤已選取的文章ID
        
        # 1. 先處理 top 文章（最多14篇）
        top_articles = self._select_top_articles(articles)[:14]
        if top_articles:
            top_main_section = []
            num_top = len(top_articles)
            
            if num_top % 2 == 1 and num_top > 5:  # 奇數且超過5篇
                # 每段2篇，最後一段3篇
                for i in range(0, num_top-3, 2):
                    if top_articles[i:i+2]:
                        top_main_section.append(top_articles[i:i+2])
                if top_articles[-3:]:
                    top_main_section.append(top_articles[-3:])
            else:  # 偶數或小於等於5篇
                # 每段2篇
                for i in range(0, num_top, 2):
                    if top_articles[i:i+2]:
                        top_main_section.append(top_articles[i:i+2])
            
            if top_main_section:
                sectioned_articles.append(top_main_section)
                total_selected = num_top
                # 更新已選取的文章ID
                used_ids.update(article.news_id for subsection in top_main_section for article in subsection)
                logger.info(f"選出 top 文章 {num_top} 篇，分成 {len(top_main_section)} 個小段落")
        
        # 如果 top 文章不足14篇，進入二階段篩選
        if total_selected < 14:
            # 2. 總經相關文章
            remaining = [article for article in articles if article.news_id not in used_ids]
            macro_articles = self._select_macroeconomics_articles(remaining, self.SECTION_LIMITS[0])
            
            if macro_articles:
                macro_main_section = []
                # 將總經文章分成小段落（每段2篇）
                for i in range(0, len(macro_articles), 2):
                    if macro_articles[i:i+2]:
                        macro_main_section.append(macro_articles[i:i+2])
                
                if macro_main_section:
                    sectioned_articles.append(macro_main_section)
                    total_selected += len(macro_articles)
                    # 更新已選取的文章ID
                    used_ids.update(article.news_id for subsection in macro_main_section for article in subsection)
                    logger.info(f"選出總經文章 {len(macro_articles)} 篇，分成 {len(macro_main_section)} 個小段落")
            
            # 3. 重要公司相關文章
            if total_selected < 15:
                remaining = [article for article in articles if article.news_id not in used_ids]
                company_articles = [article for article in remaining if self._is_important_company(article)]
                company_articles = company_articles[:self.SECTION_LIMITS[1]]
                
                if company_articles:
                    company_main_section = []
                    # 將公司文章分成小段落（每段2篇）
                    for i in range(0, len(company_articles), 2):
                        if company_articles[i:i+2]:
                            company_main_section.append(company_articles[i:i+2])
                    
                    if company_main_section:
                        sectioned_articles.append(company_main_section)
                        total_selected += len(company_articles)
                        # 更新已選取的文章ID
                        used_ids.update(article.news_id for subsection in company_main_section for article in subsection)
                        logger.info(f"選出重要公司文章 {len(company_articles)} 篇，分成 {len(company_main_section)} 個小段落")
        
        # 4. 如果文章總數不足15篇，從剩餘文章中選擇最新的文章來補足
        if total_selected < 15:
            remaining = [article for article in articles if article.news_id not in used_ids]
            if remaining:
                # 按發布時間排序
                remaining.sort(key=lambda x: x.published_at, reverse=True)
                # 計算需要補充的文章數量
                need_more = 15 - total_selected
                # 選擇最新的文章
                latest_articles = remaining[:need_more]
                
                # 將補充的文章分成小段落（每段2篇）
                latest_main_section = []
                for i in range(0, len(latest_articles), 2):
                    if latest_articles[i:i+2]:
                        latest_main_section.append(latest_articles[i:i+2])
                
                if latest_main_section:
                    sectioned_articles.append(latest_main_section)
                    total_selected += len(latest_articles)
                    # 更新已選取的文章ID
                    used_ids.update(article.news_id for subsection in latest_main_section for article in subsection)
                    logger.info(f"補充最新文章 {len(latest_articles)} 篇，分成 {len(latest_main_section)} 個小段落")
        
        # 記錄最終結果
        logger.info(f"總共選出 {total_selected} 篇文章")
        logger.info(f"分成 {len(sectioned_articles)} 個主要段落")
        for main_idx, main_section in enumerate(sectioned_articles, 1):
            logger.info(f"第 {main_idx} 個主要段落包含 {len(main_section)} 個小段落")
            for sub_idx, sub_section in enumerate(main_section, 1):
                logger.info(f"  第 {main_idx}-{sub_idx} 小段落: {len(sub_section)} 篇文章")
        
        # 記錄所有選取的文章ID
        logger.info("所有選取的文章ID:")
        for main_idx, main_section in enumerate(sectioned_articles, 1):
            for sub_idx, sub_section in enumerate(main_section, 1):
                for article in sub_section:
                    logger.info(f"  - {article.news_id}")
        
        return sectioned_articles

