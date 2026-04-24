import os
import smtplib
import logging
from datetime import datetime
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def send_gmail_alert(alert_items: list[dict], usage_stats: dict) -> bool:
    """
    アラート対象ニュースを 1 通にまとめて Gmail で送信する。

    Args:
        alert_items: パニック度が ALERT_THRESHOLD 以上かつ BUY と判断されたニュースのリスト
        usage_stats: get_daily_stats() の戻り値
    Returns:
        True if sent successfully, False otherwise.
    """
    gmail_user       = os.environ.get("GMAIL_USER")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    alert_receiver   = os.environ.get("ALERT_RECEIVER")

    if not (gmail_user and gmail_app_password and alert_receiver):
        logger.error("Gmail 設定が不足しています。.env の GMAIL_USER / GMAIL_APP_PASSWORD / ALERT_RECEIVER を確認してください。")
        return False

    gmail_app_password = gmail_app_password.replace(" ", "")

    count     = len(alert_items)
    timestamp = datetime.now().strftime("%m/%d %H:%M")

    # ---------- 件名 ----------
    subject = f"【VIBE ALERT】{count} 件の BUY シグナル検出 ({timestamp})"

    # ---------- 本文 ----------
    lines = [
        f"🚨 {count} 件の BUY シグナルを検出しました。\n",
    ]
    for i, item in enumerate(alert_items, 1):
        lines += [
            f"[{i}] {item.get('title', '')}",
            f"    ソース      : {item.get('source', '')}",
            f"    パニック度  : {item.get('panic_score', '')} / 100",
            f"    パニック理由: {item.get('panic_reason', '')}",
            f"    AI 判断     : {item.get('decision', '')}",
            f"    判断理由    : {item.get('decision_reason', '')}",
            f"    URL         : {item.get('url', '')}",
            "",
        ]

    remaining = usage_stats.get("remaining", "?")
    used      = usage_stats.get("used", "?")
    limit     = usage_stats.get("limit", "?")
    lines += [
        "─" * 44,
        f"📊 Gemini API 無料枠: {used}/{limit} 回使用（残り {remaining} 回）",
        "残り 50 回を切ると次回の起動時に警告が出ます。" if isinstance(remaining, int) and remaining < 50 else "",
    ]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = gmail_user
    msg["To"]      = alert_receiver
    msg.set_content("\n".join(lines))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.login(gmail_user, gmail_app_password)
            smtp.send_message(msg)
        logger.info("Alert email sent to %s. (%d items)", alert_receiver, count)
        return True
    except (smtplib.SMTPException, OSError) as e:
        logger.error("Error sending alert email: %s", e)
        return False
