import logging
import feedparser

logger = logging.getLogger(__name__)

FEEDS = [
    {"source": "Yahoo",    "url": "https://news.yahoo.co.jp/rss/topics/business.xml"},
    {"source": "PR TIMES", "url": "https://prtimes.jp/index.rdf"},
    {"source": "Nikkei",   "url": "https://assets.nikkei.jp/data/rss/news/macro.rdf"},
]


def fetch_latest_news(per_feed_limit: int = 5) -> list[dict]:
    """
    全フィードから最新ニュースを取得する。

    Returns:
        list of dicts: {"source", "title", "url", "published", "summary"}
    """
    news_list: list[dict] = []

    for feed_info in FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:per_feed_limit]:
                news_list.append({
                    "source":    feed_info["source"],
                    "title":     entry.get("title", "").strip(),
                    "url":       entry.get("link", "").strip(),
                    "published": entry.get("published", "").strip(),
                    "summary":   entry.get("summary", "").strip(),
                })
        except Exception as e:
            logger.warning("Error fetching from %s: %s", feed_info["source"], e)

    return news_list


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    items = fetch_latest_news()
    print(f"取得したニュースの総数: {len(items)}件\n")
    for item in items[:5]:
        print(f"[{item['source']}] {item['title']}")
