import os
import smtplib
import logging
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def send_gmail_alert(news_title: str, panic_score: int, decision: str, reason: str) -> bool:
    """
    パニックスコアが閾値を超えた際に Gmail でアラートを送信する。

    Returns:
        True if sent successfully, False otherwise.
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

    # アプリパスワードにスペースが混入していても動作するよう除去
    gmail_app_password = gmail_app_password.replace(" ", "")

    msg = EmailMessage()
    msg["Subject"] = f"【VIBE ALERT】{decision} 検出 / パニック度 {panic_score}：{news_title[:40]}"
    msg["From"] = gmail_user
    msg["To"] = alert_receiver
    msg.set_content(
        f"🚨 VIBE INVESTOR ALERT 🚨\n\n"
        f"ニュース   : {news_title}\n"
        f"パニック度 : {panic_score} / 100\n"
        f"AI 判断   : {decision}\n"
        f"理由      : {reason}\n"
    )

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.login(gmail_user, gmail_app_password)
            smtp.send_message(msg)
        logger.info("Alert email sent to %s.", alert_receiver)
        return True
    except (smtplib.SMTPException, OSError) as e:
        logger.error("Error sending alert email: %s", e)
        return False
