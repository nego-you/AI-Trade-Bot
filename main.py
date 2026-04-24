import schedule
import time
import datetime
from src.utils.scraper import fetch_latest_news
from src.utils.spreadsheet import append_news_rows


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
    # --------------------------------------------------
    items = []
    for news in news_list:
        print(f"  [{news['source']}] {news['title']}")
        items.append({
            **news,
            "panic_score": 50,
            "decision":    "HOLD",
            "reason":      "現在AIモジュールを開発中です。",
        })

    # --------------------------------------------------
    # 3. スプレッドシートへ一括記録（1ニュース = 1レコード）
    # --------------------------------------------------
    success = append_news_rows(items)

    if success:
        print(f"✅ {len(items)} 件をスプレッドシートへ記録しました。")
    else:
        print("❌ スプレッドシートへの記録に失敗しました。")


# ==========================================
# スケジュールの設定
# ==========================================
# 毎時00分ちょうどに実行する
schedule.every().hour.at(":00").do(run_trading_logic)

# テスト用（10秒ごと）は先頭の # を外して使う
# schedule.every(10).seconds.do(run_trading_logic)

if __name__ == "__main__":
    print("🚀 Vibe Botが起動しました。スケジュール待機に入ります...")

    while True:
        schedule.run_pending()
        time.sleep(1)
