"""
Summary generation related business logic
"""

from typing import List, Tuple
from datetime import datetime, timezone, timedelta
from sqlmodel import select
import logging
import asyncio

from app.models.article import ProcessedArticle, LatestSummary
from app.ai.services.summary_generator.category import CategorySummaryGenerator
from app.services.article_selector_service import article_selector_service

logger = logging.getLogger(__name__)

class SummaryService:
    """Service for summary related business logic"""
    
    # 來源類型映射
    SOURCE_TYPE_MAPPING = {
        "TW_Stock_Summary": "tw",
        "US_Stock_Summary": "us",
        "Hot_News_Summary": "headline"
    }
    
    def __init__(self):
        self.category_generator = CategorySummaryGenerator()
        # 設定為 UTC+8 時區
        self.taiwan_tz = timezone(timedelta(hours=+8))
    
    async def get_latest_articles_by_source(
        self,
        db,
        source: str,
        fetch_limit: int = 30
    ) -> List[ProcessedArticle]:
        """
        Get latest articles from specified source
        
        Args:
            db: Database session
            source: Article source (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
            fetch_limit: Limit for number of articles to fetch
            
        Returns:
            List[ProcessedArticle]: List of latest articles
        """
        statement = (
            select(ProcessedArticle)
            .where(ProcessedArticle.source == source)
            .order_by(ProcessedArticle.published_at.desc())
            .limit(fetch_limit)
        )
        return (await db.execute(statement)).scalars().all()

    def select_articles_for_summary(
        self,
        articles: List[ProcessedArticle],
        source: str,
        select_limit: int = 20
    ) -> Tuple[List[ProcessedArticle], int, int]:
        """
        使用對應的選擇器選擇文章
        
        Args:
            articles: 候選文章列表
            source: 來源類型 (TW_Stock_Summary etc.)
            limit: 選擇數量限制
            
        Returns:
            Tuple[List[ProcessedArticle], int, int]:
                - 選中的文章列表
                - highlight 文章數量
                - 總文章數量
        """
        logger.info(f"開始選擇文章 - 來源: {source}, 候選文章數量: {len(articles)}")
        
        # 轉換來源類型
        selector_type = self.SOURCE_TYPE_MAPPING.get(source)
        if not selector_type:
            logger.error(f"未知的來源類型: {source}")
            raise ValueError(f"Unknown source type: {source}")
        
        logger.info(f"來源類型映射: {source} -> {selector_type}")
        
        # 獲取對應的選擇器
        try:
            selector = article_selector_service.get_selector(selector_type)
            logger.info(f"成功獲取選擇器: {selector.__class__.__name__}")
        except Exception as e:
            logger.error(f"獲取選擇器失敗: {str(e)}")
            raise
        
        # 記錄候選文章的詳細信息
        logger.info("候選文章詳細信息:")
        for idx, article in enumerate(articles, 1):
            # 使用 getattr 安全地獲取屬性，如果不存在則返回 'N/A'
            article_info = {
                'ID': article.news_id,
                '標題': article.title,
                '來源': article.source,
                '發布時間': article.published_at,
                '更新時間': article.updated_at,
                '摘要': f"{article.summary[:100]}..." if article.summary else 'N/A',
                '內容': f"{article.content[:100]}..." if article.content else 'N/A',
                '標籤': getattr(article, 'tags', 'N/A'),
                '股票代碼': getattr(article, 'stock_codes', 'N/A'),
                '相關股票': getattr(article, 'related_stocks', 'N/A')
            }
            
            log_message = f"文章 {idx}:\n" + "\n".join(
                f"  {key}: {value}" for key, value in article_info.items()
            ) + "\n  ----------------------"
            
            logger.info(log_message)
        
        # 使用選擇器選擇文章
        try:
            top30_limit = int(select_limit/3) + 1
            selected, highlight_count, total_count = selector.select_articles(
                articles, 
                select_limit=select_limit,
                top30_stock_limit=top30_limit
            )
            logger.info(f"選擇完成，選中 {len(selected)} 篇文章，其中 highlight 文章 {highlight_count} 篇")
            
            # 記錄選中的文章
            if selected:
                logger.info("選中的文章列表:")
                for idx, article in enumerate(selected, 1):
                    logger.info(f"選中文章 {idx}: ID={article.news_id}, 標題={article.title}")
            else:
                logger.warning("沒有文章被選中！")
            
            return selected, highlight_count, total_count
        
        except Exception as e:
            logger.error(f"文章選擇過程發生錯誤: {str(e)}")
            raise

    def prepare_content_for_summary(self, articles: List[ProcessedArticle]) -> str:
        """
        Prepare content for summary generation, including complete article links
        
        Args:
            articles: List of selected articles
            
        Returns:
            str: Formatted article content string for summary generation
        """
        formatted_articles = []
        for article in articles:
            # 限制摘要長度以控制總輸入長度
            summary = article.summary[:300] if article.summary else ''
            formatted_articles.append(
                f"文章ID：{article.news_id}\n"
                f"標題：{article.title}\n" 
                f"內容：{summary}\n"
                f"連結：https://news.cnyes.com/news/id/{article.news_id}"
            )
        
        # 確保返回字串
        combined_content = "\n\n".join(formatted_articles)
        logger.info(f"準備了 {len(articles)} 篇文章的內容，總長度：{len(combined_content)} 字元")
        return combined_content
    

    async def generate_category_summary(
        self,
        db,
        source: str,
        fetch_limit: int = 30,
        summary_limit: int = 20
    ) -> Tuple[LatestSummary, List[ProcessedArticle]]:
        """
        Generate category summary
        
        Args:
            db: Database session
            source: Article source (TW_Stock_Summary, US_Stock_Summary, Hot_News_Summary)
            fetch_limit: Initial fetch limit
            summary_limit: Final selection limit
            
        Returns:
            Tuple[LatestSummary, List[ProcessedArticle]]:
                - Generated category summary
                - List of selected articles
        """
        logger.info(f"開始生成分類摘要 - 來源: {source}, 獲取限制: {fetch_limit}, 摘要限制: {summary_limit}")
        
        # 1. Get latest articles
        try:
            latest_articles = await self.get_latest_articles_by_source(
                db, source, fetch_limit
            )
            logger.info(f"從數據庫獲取到 {len(latest_articles) if latest_articles else 0} 篇文章")
            
            if not latest_articles:
                logger.warning(f"未找到來源為 {source} 的文章")
                return None, []
        except Exception as e:
            logger.error(f"獲取最新文章時發生錯誤: {str(e)}")
            raise

        # 2. Select articles to include
        try:
            selected_articles, highlight_count, total_count = self.select_articles_for_summary(
                latest_articles, 
                source,
                summary_limit
            )
            logger.info(f"完成文章選擇，選中 {len(selected_articles)} 篇文章")
        except Exception as e:
            logger.error(f"選擇文章時發生錯誤: {str(e)}")
            raise

        # 3. Prepare content
        try:
            prepared_articles = self.prepare_content_for_summary(selected_articles)
            logger.info(f"完成文章內容準備，處理了 {len(prepared_articles)} 篇文章")
        except Exception as e:
            logger.error(f"準備文章內容時發生錯誤: {str(e)}")
            raise

        # 4. Generate summary
        try:
            summary = await self.category_generator.generate_summary(
                content=prepared_articles,
                source_type=source,
                highlight_count=highlight_count,
                total_count=total_count
            )
            logger.info("成功生成摘要")
            
            # 4.1 Generate title based on summary
            title = await self.category_generator.generate_title(
                content=summary,
                source_type=source
            )
            logger.info("成功生成標題")
        except Exception as e:
            logger.error(f"生成摘要或標題時發生錯誤: {str(e)}")
            raise

        # 5. Create or update LatestSummary
        try:
            # 始終使用 UTC 時間存儲
            current_time = datetime.now(timezone.utc)
            
            latest_summary = LatestSummary(
                source=source,
                title=title,
                summary=summary,
                related=[
                    {
                        "newsId": str(article.news_id),
                        "title": article.title
                    }
                    for article in selected_articles
                ],
                created_at=current_time,
                updated_at=current_time
            )
            
            db.add(latest_summary)
            await db.commit()
            logger.info("成功保存最新摘要到數據庫")
            
            return latest_summary, selected_articles
        except Exception as e:
            logger.error(f"保存摘要時發生錯誤: {str(e)}")
            raise 

    def select_articles_by_sections(
        self,
        articles: List[ProcessedArticle],
        source: str
    ) -> List[List[ProcessedArticle]]:
        """
        將文章依照不同段落分組選擇
        
        Args:
            articles: 候選文章列表
            source: 來源類型 (TW_Stock_Summary etc.)
            
        Returns:
            List[List[ProcessedArticle]]: 分段後的文章列表，每個子列表代表一個段落的文章
        """
        logger.info(f"開始分段選擇文章 - 來源: {source}, 候選文章數量: {len(articles)}")
        
        # 轉換來源類型
        selector_type = self.SOURCE_TYPE_MAPPING.get(source)
        if not selector_type:
            logger.error(f"未知的來源類型: {source}")
            raise ValueError(f"Unknown source type: {source}")
        
        logger.info(f"來源類型映射: {source} -> {selector_type}")
        
        # 獲取對應的選擇器
        try:
            selector = article_selector_service.get_selector(selector_type)
            logger.info(f"成功獲取選擇器: {selector.__class__.__name__}")
        except Exception as e:
            logger.error(f"獲取選擇器失敗: {str(e)}")
            raise
        
        # 使用選擇器選擇文章並分段
        try:
            # 先選出所有文章
            sectioned_articles = selector.select_articles_by_sections(
                articles
            )
            
            # 檢查返回值
            if sectioned_articles is None:
                logger.warning("選擇器返回了空值，使用預設分組")
                # 如果沒有返回值，創建一個預設的分組（全部文章放在一個段落）
                return [articles]
            
            # 記錄分段結果
            logger.info(f"文章分段完成，共 {len(sectioned_articles)} 個段落")
            for i, section in enumerate(sectioned_articles, 1):
                logger.info(f"第 {i} 段包含 {len(section)} 篇文章")
            
            return sectioned_articles
            
        except Exception as e:
            logger.error(f"文章分段選擇過程發生錯誤: {str(e)}")
            raise 


    async def generate_category_summary_by_sections(
        self,
        db,
        source: str,
        fetch_limit: int = 50,
        summary_limit: int = 20
    ) -> Tuple[LatestSummary, List[ProcessedArticle]]:
        """
        Generate category summary by sections
        """
        try:
            # 1. Get latest articles
            latest_articles = await self.get_latest_articles_by_source(
                db, source, fetch_limit
            )
            if not latest_articles:
                logger.warning(f"未找到來源為 {source} 的文章")
                return None, []

            # 2. Select articles by sections
            sectioned_articles = self.select_articles_by_sections(
                articles=latest_articles,
                source=source
            )
            
            # 組合所有段落的文章成一個列表
            selected_articles = []
            for main_section in sectioned_articles:
                for sub_section in main_section:
                    selected_articles.extend(sub_section)
            
            # 3. Generate summaries for each section
            summaries = []
            start_idx = 1
            
            # 第一層迴圈：處理主要段落（宏觀、公司、其他）
            for main_section_idx, main_section in enumerate(sectioned_articles, 1):
                start_idx_main = start_idx
                
                # 用來收集這個主要段落的所有小段落摘要
                main_section_summaries = []
                
                # 第二層迴圈：處理每個主要段落中的小段落
                for sub_section_idx, sub_section in enumerate(main_section, 1):
                    section_content = self.prepare_content_for_summary(sub_section)
                    end_idx = start_idx + len(sub_section) - 1
                    
                    # 決定段落類型：第一個主要段落是 highlight，其他是 others
                    paragraph_type = "highlight" if main_section_idx == 1 else "others"
                    
                    # 生成小段落的摘要
                    section_summary = await self.category_generator.generate_paragraph(
                        content=section_content,
                        begin_idx=start_idx,
                        end_idx=end_idx,
                        source_type=source,
                        paragraph_type=paragraph_type
                    )
                    
                    main_section_summaries.append(section_summary)
                    start_idx = end_idx + 1  # 更新下一個小段落的起始索引
                
                # 將這個主要段落的所有小段落摘要合併
                if main_section_summaries:
                    # 合併該主要段落的所有小段落
                    combined_summary = "\n".join(main_section_summaries)
                    
                    # 對合併後的段落進行檢查
                    try:
                        inspected_section_summary = await self.category_generator.summary_inspection(
                            summary_html=combined_summary
                        )
                        
                        # 為這個段落生成標題
                        section_title = await self.category_generator.generate_title(
                            content=inspected_section_summary,
                            source_type=source
                        )
                        
                        # 將標題和摘要組合
                        formatted_section = f"<h3>{section_title}</h3>\n{inspected_section_summary}"
                        summaries.append(formatted_section)
                        
                        logger.info(f"完成第 {main_section_idx} 個主要段落的摘要生成和檢查，標題：{section_title}")
                    except Exception as e:
                        logger.error(f"處理第 {main_section_idx} 個主要段落時發生錯誤: {str(e)}")
                        # 如果發生錯誤，使用原始的合併摘要
                        summaries.append(combined_summary)
            
            # 組合完整摘要
            full_summary = (
                '<div class="summary-content">' +
                '<br>'.join(summaries) +
                '</div>' +
                '<p class="signature">Powered by <a href="https://www.yushan.ai/" target="_blank">Yushan.AI</a></p>'
            )

            # 新增：呼叫 summary_inspection 並加在 full_summary 後面
            try:
                inspected_summary = await self.category_generator.summary_inspection(
                    summary_html=full_summary
                )
            except Exception as e:
                logger.error(f"summary_inspection 發生錯誤: {str(e)}")
                # 若檢查失敗，仍回傳原本的 full_summary

            # Generate title
            title = await self.category_generator.generate_title(
                content=inspected_summary,
                source_type=source
            )
            
            # Create LatestSummary
            current_time = datetime.now(timezone.utc)
            
            # 按照文章在摘要中的順序重新排列
            ordered_articles = []
            for main_section in sectioned_articles:
                for sub_section in main_section:
                    ordered_articles.extend(sub_section)
            
            latest_summary = LatestSummary(
                source=source,
                title=title,
                summary=inspected_summary,
                related=[
                    {
                        "newsId": str(article.news_id),
                        "title": article.title
                    }
                    for article in ordered_articles
                ],
                created_at=current_time,
                updated_at=current_time
            )
            
            db.add(latest_summary)
            await db.commit()
            
            return latest_summary, selected_articles
            
        except Exception as e:
            logger.error(f"生成分段摘要時發生錯誤: {str(e)}")
            raise 

    def get_latest_articles_by_source_sync(
        self,
        db,
        source: str,
        fetch_limit: int = 30
    ) -> List[ProcessedArticle]:
        """同步版本的獲取最新文章"""
        statement = (
            select(ProcessedArticle)
            .where(ProcessedArticle.source == source)
            .order_by(ProcessedArticle.published_at.desc())
            .limit(fetch_limit)
        )
        return db.execute(statement).scalars().all()

    def generate_category_summary_by_sections_sync(
        self,
        db,
        source: str,
        fetch_limit: int = 30,
        summary_limit: int = 20
    ):
        """同步版本的分類摘要生成"""
        try:
            # 1. Get latest articles (使用同步方法)
            latest_articles = self.get_latest_articles_by_source_sync(
                db, source, fetch_limit
            )
            if not latest_articles:
                logger.warning(f"未找到來源為 {source} 的文章")
                return None, []

            # 2. Select articles by sections (這個本來就是同步的)
            sectioned_articles = self.select_articles_by_sections(
                articles=latest_articles,
                source=source
            )
            
            # 組合所有段落的文章成一個列表
            selected_articles = []
            for main_section in sectioned_articles:
                for sub_section in main_section:
                    selected_articles.extend(sub_section)
            
            # 3. Generate summaries for each section
            summaries = []
            start_idx = 1
            
            # 建立新的事件迴圈來執行異步操作
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 第一層迴圈：處理主要段落
                for main_section_idx, main_section in enumerate(sectioned_articles, 1):
                    main_section_summaries = []
                    
                    # 第二層迴圈：處理每個主要段落中的小段落
                    for sub_section_idx, sub_section in enumerate(main_section, 1):
                        section_content = self.prepare_content_for_summary(sub_section)
                        end_idx = start_idx + len(sub_section) - 1
                        
                        paragraph_type = "highlight" if main_section_idx == 1 else "others"
                        
                        # 在迴圈中執行異步操作
                        section_summary = loop.run_until_complete(
                            self.category_generator.generate_paragraph(
                                content=section_content,
                                begin_idx=start_idx,
                                end_idx=end_idx,
                                source_type=source,
                                paragraph_type=paragraph_type
                            )
                        )
                        
                        main_section_summaries.append(section_summary)
                        start_idx = end_idx + 1
                    
                    if main_section_summaries:
                        combined_summary = "\n".join(main_section_summaries)
                        
                        try:
                            inspected_section_summary = loop.run_until_complete(
                                self.category_generator.summary_inspection(
                                    summary_html=combined_summary
                                )
                            )
                            
                            section_title = loop.run_until_complete(
                                self.category_generator.generate_title(
                                    content=inspected_section_summary,
                                    source_type=source
                                )
                            )
                            
                            formatted_section = f"<h3>{section_title}</h3>\n{inspected_section_summary}"
                            summaries.append(formatted_section)
                            
                        except Exception as e:
                            logger.error(f"處理第 {main_section_idx} 個主要段落時發生錯誤: {str(e)}")
                            summaries.append(combined_summary)
                
                # 組合完整摘要
                full_summary = (
                    '<div class="summary-content">' +
                    '<br>'.join(summaries) +
                    '</div>' +
                    '<p class="signature">Powered by <a href="https://www.yushan.ai/" target="_blank">Yushan.AI</a></p>'
                )

                inspected_summary = loop.run_until_complete(
                    self.category_generator.summary_inspection(
                        summary_html=full_summary
                    )
                )

                title = loop.run_until_complete(
                    self.category_generator.generate_title(
                        content=inspected_summary,
                        source_type=source
                    )
                )
                
                # Create LatestSummary
                current_time = datetime.now(timezone.utc)
                
                # 按照文章在摘要中的順序重新排列
                ordered_articles = []
                for main_section in sectioned_articles:
                    for sub_section in main_section:
                        ordered_articles.extend(sub_section)
                
                latest_summary = LatestSummary(
                    source=source,
                    title=title,
                    summary=inspected_summary,
                    related=[
                        {
                            "newsId": str(article.news_id),
                            "title": article.title
                        }
                        for article in ordered_articles
                    ],
                    created_at=current_time,
                    updated_at=current_time
                )
                
                db.add(latest_summary)
                db.commit()
                
                return latest_summary, selected_articles
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"生成分段摘要時發生錯誤: {str(e)}")
            raise 