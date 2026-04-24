import schedule
import time
import datetime
from src.utils.news import get_latest_news
from src.utils.spreadsheet import append_to_sheet

def run_trading_logic():
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{now}] 🤖 トレードロジックの実行を開始します...")
    
    # --------------------------------------------------
    # 1. ニュースの取得（本物にすげ替え！）
    # --------------------------------------------------
    news = get_latest_news()
    
    if not news:
        print("❌ ニュースが取得できなかったため、処理をスキップします。")
        return
        
    print(f"📰 取得したニュース: {news['title']}")

    # --------------------------------------------------
    # 2. AI判定（今はまだダミーです）
    # --------------------------------------------------
    panic_score = 50
    decision = "HOLD"
    reason = "現在AIモジュールを開発中です。"
    
    # --------------------------------------------------
    # 3. スプレッドシートへ記録
    # --------------------------------------------------
    success = append_to_sheet(news['title'], panic_score, decision, reason, 0)
    
    if success:
        print("✅ スプレッドシートへの記録が完了しました！")
    else:
        print("❌ 記録に失敗しました。")

# ==========================================
# スケジュールの設定
# ==========================================
# 毎時00分ちょうどに実行する
schedule.every().hour.at(":00").do(run_trading_logic)

# テスト用（10秒ごと）は先頭に # を外して使う
# schedule.every(10).seconds.do(run_trading_logic)

if __name__ == "__main__":
    print("🚀 Vibe Botが起動しました。スケジュール待機に入ります...")
    
    while True:
        schedule.run_pending()
        time.sleep(1)