"""
Streamlit dashboard scaffold.

Run with:
    streamlit run src/dashboard.py

Once the PostgreSQL schema is in place (see docs/03_db_design.md), replace the
`load_recent_decisions()` stub with a real DB query.
"""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from agents.ollama_agent import evaluate_news_with_ollama
from utils.scraper import fetch_latest_news


def load_recent_decisions() -> pd.DataFrame:
    """Placeholder until PostgreSQL logging is wired up."""
    return pd.DataFrame(
        columns=["timestamp", "source", "title", "panic_score", "decision", "reason"]
    )


def render_live_feed() -> None:
    st.subheader("ライブ・ニュースフィード")
    if st.button("最新ニュースを取得"):
        with st.spinner("Fetching..."):
            news = fetch_latest_news()
        st.caption(f"{len(news)} 件取得")
        st.dataframe(pd.DataFrame(news), use_container_width=True)


def render_ollama_test() -> None:
    st.subheader("Ollama 一次判定テスト")
    text = st.text_area("ニュース本文", placeholder="例: 日経平均が歴史的な暴落を記録。")
    if st.button("パニック度を評価") and text.strip():
        with st.spinner("Evaluating..."):
            raw = evaluate_news_with_ollama(text)
        try:
            parsed = json.loads(raw)
            st.metric("panic_score", parsed.get("panic_score", "-"))
            st.write(parsed.get("reason", ""))
        except json.JSONDecodeError:
            st.code(raw)


def render_history() -> None:
    st.subheader("AI 判断ログ (PostgreSQL)")
    df = load_recent_decisions()
    if df.empty:
        st.info("DB 連携は未実装です。docs/03_db_design.md を参照。")
        return
    st.dataframe(df, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Vibe Investor Dashboard", page_icon="📈", layout="wide")
    st.title("📈 Vibe Investor Dashboard")
    st.caption(f"Last rendered: {datetime.now().isoformat(timespec='seconds')}")

    tabs = st.tabs(["Live feed", "Ollama test", "History"])
    with tabs[0]:
        render_live_feed()
    with tabs[1]:
        render_ollama_test()
    with tabs[2]:
        render_history()


if __name__ == "__main__":
    main()
