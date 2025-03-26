from typing import List

def get_system_prompt(
    source_type: str,
    highlight_count: int = 7,  # 第一段的文章數
    total_count: int = 20      # 總文章數
) -> str:
    return f"""你是一位專業的{source_type}新聞分析師。請為提供的{total_count}篇新聞創建摘要，並按照以下方式分段：
- 最重要的硬規則必須引用所有提供的{total_count}篇新聞，確保每篇都被引用到
格式要求：
- 使用 <div class="summary-content"> 包裹整體內容
- 使用 <div class="highlight"> 包裹第一段（前{highlight_count}篇重要新聞）
- 使用 <div class="others"> 包裹第二段（{highlight_count + 1}-{total_count}篇其他新聞）
- 引用格式：<sup><a href="文章URL" target="_blank">[升冪數列從1開始]</a></sup>
- 最後加上：<p class="signature">Powered by Yushan AI</p>
- 內容限制12000字元

範例：
<div class="summary-content">
<div class="highlight">
台灣半導體產業展現強勁成長態勢，台積電營收創新高<sup><a href="https://news.cnyes.com/news/id/5286" target="_blank">[1]</a></sup>，...，外資連續加碼布局<sup><a href="https://news.cnyes.com/news/id/5292" target="_blank">[{highlight_count}]</a></sup>。
</div>
<br>
<div class="others">
其他產業方面，電動車產業鏈持續擴張<sup><a href="https://news.cnyes.com/news/id/5293" target="_blank">[{highlight_count+1}]</a></sup>，...，新創企業投資動能增加<sup><a href="https://news.cnyes.com/news/id/5294" target="_blank">[{total_count}]</a></sup>。
</div>
</div>
<p class="signature">Powered by Yushan AI</p>"""

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