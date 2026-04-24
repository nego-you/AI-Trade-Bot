import feedparser

def get_latest_news():
    """Yahoo!ニュースの経済トピックスから最新のニュースを1件取得する"""
    rss_url = "https://news.yahoo.co.jp/rss/topics/business.xml"
    
    try:
        feed = feedparser.parse(rss_url)
        
        # ニュースが取得できなかった場合のフェイルセーフ
        if not feed.entries:
            print("⚠️ ニュースの取得に失敗しました（データが空です）")
            return None
            
        # 一番新しいニュース（リストの先頭）を取得
        latest_entry = feed.entries[0]
        
        # 必要な情報だけを抽出
        news_data = {
            "title": latest_entry.get("title", ""),
            "link": latest_entry.get("link", ""),
            "published": latest_entry.get("published", ""),
        }
        
        return news_data

    except Exception as e:
        print(f"News Fetch Error: {e}")
        return None