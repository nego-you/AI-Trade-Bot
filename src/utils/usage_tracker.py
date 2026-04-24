"""
Gemini API の無料枠使用量をローカルファイル（usage.json）で追跡する。
無料枠: Gemini 2.5 Flash = 500 リクエスト / 日
"""
import json
import os
import datetime

TRACKER_FILE = 'usage.json'
GEMINI_FREE_DAILY_LIMIT = 500


def _load() -> dict:
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            return json.load(f)
    return {}


def _save(data: dict) -> None:
    with open(TRACKER_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def record_gemini_calls(count: int = 1) -> None:
    """Gemini API 呼び出し回数を記録する"""
    today = datetime.date.today().isoformat()
    data = _load()
    data[today] = data.get(today, 0) + count
    _save(data)


def get_daily_stats() -> dict:
    """
    本日の Gemini API 使用状況を返す。

    Returns:
        {"used": int, "limit": int, "remaining": int, "date": str}
    """
    today = datetime.date.today().isoformat()
    data = _load()
    used = data.get(today, 0)
    remaining = max(0, GEMINI_FREE_DAILY_LIMIT - used)
    return {
        'date':      today,
        'used':      used,
        'limit':     GEMINI_FREE_DAILY_LIMIT,
        'remaining': remaining,
    }
