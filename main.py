import json
import logging
import schedule
import time
import datetime

from src.agents.gemini_agent import decide_trade_with_gemini
from src.agents.ollama_agent import evaluate_news_with_ollama
from src.utils.scraper import fetch_latest_news
from src.utils.spreadsheet import append_news_rows
from src.utils.notifier import send_gmail_alert
from src.utils.usage_tracker import get_daily_stats, record_gemini_calls

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)

# パニック度スコアがこの値以上 → Gemini に詳細分析（BUY/SKIP判定）を委ねる
PANIC_THRESHOLD = 70
# Gemini が BUY かつパニック度がこの値以上 → Gmail アラート対象
ALERT_THRESHOLD = 85


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _print_usage_stats() -> None:
    stats = get_daily_stats()
    used, limit, remaining = stats['used'], stats['limit'], stats['remaining']
    filled = used * 20 // limit if limit else 0
    bar = '█' * filled + '░' * (20 - filled)
    print(f"\n📊 Gemini API 無料枠 [{bar}] {used}/{limit} 回使用（残り {remaining} 回）")
    if remaining == 0:
        print("🔴 本日の無料枠を使い切りました。明日リセットされます。")
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
    # 2. Gemini でパニックスコア評価 → 閾値超えはさらに詳細分析
    # --------------------------------------------------
    items = []
    alert_targets = []   # ALERT_THRESHOLD 以上かつ BUY のみ

    for news in news_list:
        title = news['title']

        # --- Ollama: パニック度スコアリング ---
        ollama_panic = _parse_json(evaluate_news_with_ollama(title))
        
        if 'error' in ollama_panic:
            panic_score  = 0
            panic_reason = f"Ollama未応答（{ollama_panic.get('error', '')}）"
            logger.warning("Ollama error for panic score '%s': %s", title[:30], ollama_panic['error'])
        else:
            panic_score  = int(ollama_panic.get('panic_score', 0))
            panic_reason = ollama_panic.get('reason', '')

        # --- Gemini: PANIC_THRESHOLD 以上のみ BUY/SKIP 判定 ---
        if panic_score >= PANIC_THRESHOLD:
            gemini = _parse_json(decide_trade_with_gemini(title, panic_score))
            record_gemini_calls(1)
            time.sleep(4) # API Rate Limit対策
            if 'error' in gemini:
                decision        = "ERROR"
                decision_reason = f"Gemini エラー（{gemini.get('error', '')}）"
                logger.warning("Gemini error for '%s': %s", title[:30], gemini['error'])
            else:
                decision        = gemini.get('signal', 'HOLD')
                decision_reason = gemini.get('reason', '')
                company_name    = gemini.get('company_name', '')
                ticker          = gemini.get('ticker')
                
                # 株価データの取得と連携
                if ticker and str(ticker).lower() != 'null':
                    from src.utils.stock_data import fetch_stock_data
                    s_data = fetch_stock_data(str(ticker))
                    if s_data:
                        stock_info = f"【株価: {s_data['current_price']:.1f} (前日比 {s_data['change_percent']:+.2f}%)】"
                        decision_reason = f"{stock_info} {decision_reason}"
        else:
            decision        = "HOLD"
            decision_reason = ""

        item = {
            **news,
            'panic_score':    panic_score,
            'panic_reason':   panic_reason,
            'decision':       decision,
            'decision_reason': decision_reason,
        }
        items.append(item)

        # ALERT_THRESHOLD 以上かつ BUY → メール対象
        if panic_score >= ALERT_THRESHOLD and decision == "BUY":
            alert_targets.append(item)

        icon = "🚨" if item in alert_targets else ("⚠️ " if decision == "BUY" else "  ")
        print(f"  {icon} [{news['source']}] パニック度:{panic_score:3d} {decision:<5} {title[:45]}")

    # --------------------------------------------------
    # 3. スプレッドシートへ一括記録（1ニュース = 1レコード）
    # --------------------------------------------------
    if append_news_rows(items):
        print(f"✅ {len(items)} 件をスプレッドシートへ記録しました。")
    else:
        print("❌ スプレッドシートへの記録に失敗しました。")

    # --------------------------------------------------
    # 4. アラート対象があれば 1 通にまとめて Gmail 送信
    #    （PANIC_THRESHOLD を超えて BUY でも ALERT_THRESHOLD 未満は送信しない）
    # --------------------------------------------------
    if alert_targets:
        print(f"🚨 {len(alert_targets)} 件が ALERT_THRESHOLD({ALERT_THRESHOLD}) 以上の BUY シグナル → Gmail を送信中...")
        send_gmail_alert(alert_targets, get_daily_stats())
    else:
        print(f"📭 ALERT_THRESHOLD({ALERT_THRESHOLD}) 以上の BUY シグナルはありませんでした。")

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

import sys
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vibe Bot Trading Logic")
    parser.add_argument("--run-once", action="store_true", help="Run the trading logic once and exit")
    args = parser.parse_args()

    if args.run_once:
        print("🚀 Vibe Botを1回のみ実行します (GitHub Actions等用)...")
        _print_usage_stats()
        run_trading_logic()
        sys.exit(0)

    print("🚀 Vibe Botが起動しました。スケジュール待機に入ります...")
    _print_usage_stats()

    while True:
        schedule.run_pending()
        time.sleep(1)
