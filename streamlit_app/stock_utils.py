"""株価データ取得・チャート描画ユーティリティ"""
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta


def _normalize_ticker(ticker: str) -> str:
    """日本株4桁コードに .T を付与する。"""
    t = str(ticker).strip()
    if t.isdigit() and len(t) == 4:
        return f"{t}.T"
    return t


@st.cache_data(ttl=300)  # 5分キャッシュ
def fetch_stock_info(ticker: str) -> dict | None:
    """
    現在値・前日比・52週高安・出来高を返す。
    取得失敗時は None。
    """
    t = _normalize_ticker(ticker)
    try:
        stock = yf.Ticker(t)
        hist = stock.history(period="5d")
        if hist.empty:
            return None

        latest   = hist.iloc[-1]
        prev     = hist.iloc[-2] if len(hist) > 1 else latest
        price    = float(latest["Close"])
        prev_c   = float(prev["Close"])
        chg_pct  = (price - prev_c) / prev_c * 100 if prev_c else 0.0

        info = stock.info or {}
        return {
            "ticker":        t,
            "price":         price,
            "prev_close":    prev_c,
            "change_pct":    chg_pct,
            "volume":        int(latest.get("Volume", 0)),
            "week52_high":   info.get("fiftyTwoWeekHigh"),
            "week52_low":    info.get("fiftyTwoWeekLow"),
            "currency":      info.get("currency", "JPY"),
        }
    except Exception:
        return None


@st.cache_data(ttl=300)  # 5分キャッシュ
def fetch_history(ticker: str, period: str = "3mo") -> "pd.DataFrame | None":
    """指定期間の終値履歴を返す。"""
    import pandas as pd
    t = _normalize_ticker(ticker)
    try:
        hist = yf.Ticker(t).history(period=period)
        if hist.empty:
            return None
        return hist[["Close"]].rename(columns={"Close": "終値"})
    except Exception:
        return None


def render_stock_card(stock: dict, msg_idx: int, stock_idx: int):
    """
    銘柄カード（株価情報＋チャート＋追加ボタン）を描画する。

    stock: {"company_name", "ticker", "theme", "reason"}
    """
    ticker      = stock.get("ticker", "")
    name        = stock.get("company_name", "")
    theme       = stock.get("theme", "")
    reason      = stock.get("reason", "")
    already     = any(t["ticker"] == ticker for t in st.session_state.get("focus_targets", []))
    btn_key     = f"stock_{msg_idx}_{stock_idx}"

    with st.container(border=True):
        # ── 銘柄名 & 追加ボタン ──────────────────────────────
        col_name, col_btn = st.columns([5, 1])
        with col_name:
            st.markdown(
                f"**{name}**　`{ticker}`"
                + (f"　🏷️ {theme}" if theme else "")
            )
            if reason:
                st.caption(reason)
        with col_btn:
            if already:
                st.button("✅ 追加済", key=btn_key, disabled=True)
            else:
                if st.button("➕ 追加", key=btn_key, type="primary"):
                    st.session_state.focus_targets.append({
                        "company_name": name,
                        "ticker":       ticker,
                        "theme":        theme,
                        "reason":       reason,
                    })
                    st.rerun()

        # ── 株価情報 ─────────────────────────────────────────
        info = fetch_stock_info(ticker)
        if info:
            currency = "円" if info["currency"] == "JPY" else info["currency"]
            chg = info["change_pct"]
            chg_str  = f"{chg:+.2f}%"
            chg_color = "🔴" if chg < 0 else "🟢"

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("現在値",    f"{info['price']:,.0f} {currency}")
            m2.metric("前日比",    chg_str, delta=chg_str,
                      delta_color="normal" if chg >= 0 else "inverse")
            m3.metric("出来高",    f"{info['volume']:,}")
            m4.metric("52週高値",  f"{info['week52_high']:,.0f}" if info.get("week52_high") else "—")

            # ── チャート（expander で折りたたみ） ──────────────
            with st.expander("📊 チャートを表示", expanded=False):
                period_map = {"1ヶ月": "1mo", "3ヶ月": "3mo", "6ヶ月": "6mo", "1年": "1y"}
                period_label = st.radio(
                    "期間", list(period_map.keys()),
                    index=1, horizontal=True,
                    key=f"period_{btn_key}"
                )
                hist_df = fetch_history(ticker, period_map[period_label])
                if hist_df is not None and not hist_df.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=hist_df.index,
                        y=hist_df["終値"],
                        mode="lines",
                        line=dict(color="#2563EB", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(37,99,235,0.08)",
                        name="終値",
                    ))
                    fig.update_layout(
                        height=280,
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(tickformat=",.0f", ticksuffix=f" {currency}"),
                        hovermode="x unified",
                        showlegend=False,
                        plot_bgcolor="white",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.caption("チャートデータを取得できませんでした。")
        else:
            st.caption("⚠️ 株価データを取得できませんでした（ticker を確認してください）")
