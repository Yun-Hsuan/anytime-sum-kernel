from typing import List

def get_system_prompt(source_type: str) -> str:
    return f"""你是一位專業的{source_type}新聞分析師。請為提供的新聞創建摘要：

格式要求：
- 使用單一個 <p> 標籤包裹整體內容
- 引用格式：<sup><a href="文章URL" target="_blank">[升冪數列從1開始]</a></sup>
- 最後加上：<p class="signature">Powered by Yushan AI</p>
- 內容限制3000字元

範例：
<p>台灣半導體產業展現強勁成長<sup><a href="https://news.cnyes.com/news/id/5286" target="_blank">[1]</a></sup></p>"""

def get_user_prompt(articles: List[dict]) -> str:
    formatted_articles = []
    for article in articles:
        formatted_articles.append(
            f"文章 {article['news_id']}：\n"
            f"標題：{article['title']}\n"
            f"內容：{article['summary']}\n"
            f"連結：{article['url']}\n"
        )
    
    return "請分析並摘要以下新聞文章：\n\n" + "\n".join(formatted_articles)

def get_assistant_message() -> str:
    return "我將創建一個流暢的摘要段落，並使用文章原始的 news_id 作為引用標記。" 