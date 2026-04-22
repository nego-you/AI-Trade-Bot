"""
Notifier module for sending alerts to Discord via Webhook.
"""
import os
import requests
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


def send_discord_alert(news_title: str, reason: str) -> bool:
    """
    Send an alert message to a Discord channel using a Webhook.

    Args:
        news_title (str): The title of the news article.
        reason (str): The AI's reasoning for the decision.

    Returns:
        bool: True if the message was sent successfully, False otherwise.
    """
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL is not set in the environment variables.")
        return False

    message = (
        "🚨 **VIBE INVESTOR ALERT: 逆張りチャンス検出！** 🚨\n"
        f"**ニュース:** {news_title}\n"
        f"**AI判断理由:** {reason}"
    )

    payload = {
        "content": message
    }

    try:
        logger.info("Sending alert to Discord...")
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Alert sent successfully.")
        return True
    except requests.RequestException as e:
        logger.error(f"Error sending alert to Discord: {str(e)}")
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Example usage
    example_news_title = "日経平均が歴史的な暴落を記録。"
    example_reason = "市場の過剰反応により、逆張りの好機と判断されました。"

    success = send_discord_alert(example_news_title, example_reason)
    print("Alert sent successfully." if success else "Failed to send alert.")