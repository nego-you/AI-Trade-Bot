"""
Main loop: poll news feeds, run the three-stage LLM pipeline, and alert on BUY decisions.

Pipeline per news item:
    Ollama (panic score)  ->  [score >= PANIC_THRESHOLD]  ->  Gemini (BUY/SKIP)  ->  Gmail alert on BUY
"""
import json
import logging
import time

import schedule

from agents.gemini_agent import decide_trade_with_gemini
from agents.ollama_agent import evaluate_news_with_ollama
from utils.notifier import send_gmail_alert
from utils.scraper import fetch_latest_news

logger = logging.getLogger(__name__)

PANIC_THRESHOLD = 70          # Ollama score at/above which we escalate to Gemini
POLL_INTERVAL_MINUTES = 15
MAX_SEEN_URLS = 5000          # cap in-memory dedup set

_seen_urls: set[str] = set()


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def process_news_item(news: dict) -> None:
    title = news["title"]
    url = news.get("url") or title
    if url in _seen_urls:
        return
    _seen_urls.add(url)
    if len(_seen_urls) > MAX_SEEN_URLS:
        # Drop oldest-ish by rebuilding; simple and bounded.
        _seen_urls.clear()

    logger.info("[%s] %s", news["source"], title)

    ollama_raw = evaluate_news_with_ollama(f"{title} {news.get('content', '')}")
    ollama = _parse_json(ollama_raw)
    if "error" in ollama or "panic_score" not in ollama:
        logger.warning("Ollama skipped: %s", ollama.get("error", "invalid response"))
        return

    panic_score = int(ollama["panic_score"])
    logger.info("panic_score=%d  reason=%s", panic_score, ollama.get("reason", ""))
    if panic_score < PANIC_THRESHOLD:
        return

    gemini_raw = decide_trade_with_gemini(title, panic_score)
    gemini = _parse_json(gemini_raw)
    if gemini.get("decision") != "BUY":
        logger.info("Gemini decision: %s", gemini.get("decision") or gemini.get("error"))
        return

    reason = gemini.get("reason", "")
    logger.info("BUY signal. Sending alert.")
    send_gmail_alert(title, reason)


def run_once() -> None:
    logger.info("=== Polling news feeds ===")
    for news in fetch_latest_news():
        try:
            process_news_item(news)
        except Exception as e:
            logger.exception("Failed to process news item: %s", e)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_once()
    schedule.every(POLL_INTERVAL_MINUTES).minutes.do(run_once)
    logger.info("Scheduler started (every %d min).", POLL_INTERVAL_MINUTES)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
