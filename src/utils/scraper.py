"""
News scraper: fetches items from multiple RSS feeds.
"""
import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FEEDS = [
    {"source": "Yahoo", "url": "https://news.yahoo.co.jp/rss/topics/business.xml"},
    {"source": "PR TIMES", "url": "https://prtimes.jp/index.rdf"},
    {"source": "Nikkei", "url": "https://assets.nikkei.jp/data/rss/news/macro.rdf"},
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_latest_news(per_feed_limit: int = 5) -> list[dict]:
    """
    Fetch the latest items from each RSS feed.

    Returns:
        list of dicts: {"source", "title", "content", "url"}.
    """
    news_list: list[dict] = []
    headers = {"User-Agent": USER_AGENT}

    for feed in FEEDS:
        try:
            response = requests.get(feed["url"], headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "lxml-xml")
            items = soup.find_all("item")

            for item in items[:per_feed_limit]:
                title = item.title.text if item.title else "No Title"
                content = item.description.text if item.description else ""
                link = item.link.text if item.link else ""
                news_list.append(
                    {
                        "source": feed["source"],
                        "title": title.strip(),
                        "content": content.strip(),
                        "url": link.strip(),
                    }
                )
        except requests.RequestException as e:
            logger.warning("Error fetching from %s: %s", feed["source"], e)
            continue

    return news_list


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    test_news = fetch_latest_news()
    print(f"取得したニュースの総数: {len(test_news)}件\n")
    for news in test_news[:3]:
        print(f"[{news['source']}] {news['title']}")
