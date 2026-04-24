import schedule
import time
import datetime
from src.utils.scraper import fetch_latest_news
from src.utils.spreadsheet import append_news_rows
from src.utils.notifier import send_gmail_alert
from src.utils.usage_tracker import get_daily_stats, record_gemini_calls

# パニック度がこの値以上になったら Gmail アラートを送信する
PANIC_THRESHOLD = 70


def _print_usage_stats() -> None:
    stats = get_daily_stats()
    remaining = stats['remaining']
    used = stats['used']
    limit = stats['limit']
    bar = '█' * (used * 20 // limit) + '░' * (20 - used * 20 // limit) if limit else ''
    print(f"\n📊 Gemini API 無料枠 [{bar}] {used}/{limit} 回使用（残り {remaining} 回）")
    if remaining == 0:
        print("🔴 本日の無料枠を使い切りました。明日まで Gemini は呼び出しません。")
    elif remaining < 50:
        print(f"⚠️  残り {remaining} 回で有償プランに切り替わります。")


def run_trading_logic():
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{now}] 🤖 トレードロジックの実行を開始します...")

    # --------------------------------------------------
    # 1. 全フィードからニュースを取得
    # --------------------------------------------------
    news_list = fetch_latest_news()

    if not news_list:
        print("❌ ニュースが取得できなかったため、処理をスキップします。")
        return

    print(f"📰 {len(news_list)} 件のニュースを取得しました。")

    # --------------------------------------------------
    # 2. 各ニュースに AI 判定を付与（現在はダミー）
    #    将来は Ollama → Gemini のパイプラインに差し替え
    # --------------------------------------------------
    items = []
    alert_targets = []

    for news in news_list:
        panic_score = 50       # ← ここが将来 Ollama の結果に変わる
        decision    = "HOLD"   # ← ここが将来 Gemini の結果に変わる
        reason      = "現在AIモジュールを開発中です。"

        # --- Gemini を呼んだ場合はここでカウント ---
        # record_gemini_calls(1)

        items.append({
            **news,
            "panic_score": panic_score,
            "decision":    decision,
            "reason":      reason,
        })

        print(f"  [{news['source']}] パニック度:{panic_score} {decision} - {news['title'][:50]}")

        if panic_score >= PANIC_THRESHOLD:
            alert_targets.append(items[-1])

    # --------------------------------------------------
    # 3. スプレッドシートへ一括記録（1ニュース = 1レコード）
    # --------------------------------------------------
    success = append_news_rows(items)
    if success:
        print(f"✅ {len(items)} 件をスプレッドシートへ記録しました。")
    else:
        print("❌ スプレッドシートへの記録に失敗しました。")

    # --------------------------------------------------
    # 4. パニック度が閾値以上のニュースは Gmail でアラート送信
    # --------------------------------------------------
    for target in alert_targets:
        print(f"🚨 パニック度 {target['panic_score']} >= {PANIC_THRESHOLD}：Gmail を送信中...")
        send_gmail_alert(
            news_title=target['title'],
            panic_score=target['panic_score'],
            decision=target['decision'],
            reason=target['reason'],
        )

    # --------------------------------------------------
    # 5. Gemini API 無料枠の残量を表示
    # --------------------------------------------------
    _print_usage_stats()


# ==========================================
# スケジュールの設定
# ==========================================
# 毎時00分ちょうどに実行する
schedule.every().hour.at(":00").do(run_trading_logic)

# テスト用（10秒ごと）は先頭の # を外して使う
# schedule.every(10).seconds.do(run_trading_logic)

if __name__ == "__main__":
    print("🚀 Vibe Botが起動しました。スケジュール待機に入ります...")
    _print_usage_stats()

    while True:
        schedule.run_pending()
        time.sleep(1)
