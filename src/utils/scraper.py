import requests
from bs4 import BeautifulSoup

def fetch_latest_news():
    """
    複数のRSSフィードから最新のニュースを取得し、リスト形式で返す関数
    """
    feeds = [
        {"source": "Yahoo", "url": "https://news.yahoo.co.jp/rss/topics/business.xml"},
        {"source": "PR TIMES", "url": "https://prtimes.jp/index.rdf"},
        {"source": "Nikkei", "url": "https://assets.nikkei.jp/data/rss/news/macro.rdf"}
    ]

    news_list = []
    
    # 【追加】Bot弾きを回避するための「ブラウザ偽装ヘッダー」
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for feed in feeds:
        try:
            # headersを追加してリクエストを送る
            response = requests.get(feed["url"], headers=headers, timeout=10)
            response.raise_for_status() 
            
            # 解析エンジンに "lxml-xml" を指定
            soup = BeautifulSoup(response.content, "lxml-xml")
            items = soup.find_all("item")
            
            for item in items[:5]:
                title = item.title.text if item.title else "No Title"
                content = item.description.text if item.description else ""
                link = item.link.text if item.link else ""
                
                news_list.append({
                    "source": feed["source"],
                    "title": title.strip(),
                    "content": content.strip(),
                    "url": link.strip()
                })
                
        except Exception as e:
            print(f"Error fetching from {feed['source']}: {e}")
            continue

    return news_list

if __name__ == "__main__":
    test_news = fetch_latest_news()
    print(f"取得したニュースの総数: {len(test_news)}件\n")
    for news in test_news[:3]:
        print(f"[{news['source']}] {news['title']}")