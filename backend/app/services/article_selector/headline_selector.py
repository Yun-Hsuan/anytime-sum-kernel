from typing import List
from datetime import datetime, timedelta
from .base import ArticleSelector
from app.models.article import RawArticle

class HeadlineSelector(ArticleSelector):
    """頭條新聞選擇器"""
    
    def select_articles(
        self, 
        articles: List[RawArticle], 
        limit: int
    ) -> List[RawArticle]:
        """
        選擇頭條新聞
        
        選擇規則：
        1. 優先選擇閱讀量/點擊量高的新聞
        2. 優先選擇最近12小時內的新聞
        3. 考慮新聞的多樣性（避免同一主題）
        """
        time_threshold = datetime.now() - timedelta(hours=12)
        
        # 過濾並排序文章
        filtered_articles = []
        seen_topics = set()
        
        for article in articles:
            if article.published_at >= time_threshold:
                score = 0
                # 根據閱讀量加分
                score += article.view_count if hasattr(article, 'view_count') else 0
                
                # 檢查主題重複性
                main_topic = article.title.split()[0]  # 簡單用標題第一個詞代表主題
                if main_topic not in seen_topics:
                    score += 5
                    seen_topics.add(main_topic)
                
                filtered_articles.append((article, score))
        
        # 按分數和時間排序
        sorted_articles = sorted(
            filtered_articles,
            key=lambda x: (x[1], x[0].published_at),
            reverse=True
        )
        
        return [article for article, _ in sorted_articles[:limit]] 