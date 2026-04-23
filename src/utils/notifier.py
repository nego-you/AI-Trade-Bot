"""
Notifier module for sending alerts via Gmail (SMTP).
"""
import os
import smtplib
import logging
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def send_gmail_alert(news_title: str, reason: str) -> bool:
    """
    Send a VIBE ALERT email via Gmail SMTP.

    Args:
        news_title (str): The title of the news article.
        reason (str): The AI's reasoning for the decision.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    alert_receiver = os.environ.get("ALERT_RECEIVER")

    if not (gmail_user and gmail_app_password and alert_receiver):
        logger.error(
            "Gmail settings are missing. "
            "Please set GMAIL_USER, GMAIL_APP_PASSWORD, and ALERT_RECEIVER in .env."
        )
        return False

    # Gmail app passwords are issued as 16 chars; users often paste them with spaces.
    gmail_app_password = gmail_app_password.replace(" ", "")

    msg = EmailMessage()
    msg["Subject"] = f"【VIBE ALERT】逆張りチャンス：{news_title}"
    msg["From"] = gmail_user
    msg["To"] = alert_receiver
    msg.set_content(
        "🚨 VIBE INVESTOR ALERT: 逆張りチャンス検出！ 🚨\n"
        f"ニュース: {news_title}\n"
        f"AI判断理由: {reason}\n"
    )

    try:
        logger.info("Sending alert email via Gmail...")
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.login(gmail_user, gmail_app_password)
            smtp.send_message(msg)
        logger.info("Alert email sent successfully to %s.", alert_receiver)
        return True
    except (smtplib.SMTPException, OSError) as e:
        logger.error("Error sending alert email via Gmail: %s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    example_news_title = "日経平均が歴史的な暴落を記録。"
    example_reason = "市場の過剰反応により、逆張りの好機と判断されました。"

    success = send_gmail_alert(example_news_title, example_reason)
    print("Alert sent successfully." if success else "Failed to send alert.")
