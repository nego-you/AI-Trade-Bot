import sys
import os
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

# パス設定
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_app_dir   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (_repo_root, _app_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.utils.spreadsheet import get_simulation_history, get_open_positions
from stock_utils import fetch_stock_info

# ── ページ設定 ────────────────────────────────────────────────────────────────
st.title("💹 シミュレーション結果")
st.caption("ボットが検出した BUY/SELL シグナルの実績と現在の保有状況を確認できます。")

# ── Secrets チェック ──────────────────────────────────────────────────────────
if not st.secrets.get("SPREADSHEET_ID") or not st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
    st.warning("スプレッドシート連携の Secrets が設定されていません。")
    st.stop()

# ── データ読み込み ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data():
    return get_simulation_history()

if st.button("🔄 最新データに更新", use_container_width=False):
    st.cache_data.clear()

records = load_data()

if not records:
    st.info("まだシミュレーションデータがありません。ボットが BUY/SELL を検出すると自動で記録されます。")
    st.stop()

df = pd.DataFrame(records)

# クローズ済み / オープン分類
closed = df[df['sell_date'] != ''].copy()
opened = df[df['sell_date'] == ''].copy()

# ── ① サマリーカード ──────────────────────────────────────────────────────────
st.subheader("📊 サマリー")

total_trades  = len(closed)
wins          = len(closed[closed['profit_yen'] > 0])
win_rate      = wins / total_trades * 100 if total_trades else 0
total_profit  = closed['profit_yen'].sum()
open_count    = len(opened)

col1, col2, col3, col4 = st.columns(4)
col1.metric("総取引数（決済済）",  f"{total_trades} 件")
col2.metric("勝率",               f"{win_rate:.1f}%",
            delta=f"{wins}勝 {total_trades - wins}敗" if total_trades else None)
col3.metric("実現損益合計",
            f"{'▲' if total_profit < 0 else '+'}{abs(total_profit):,.0f} 円",
            delta_color="normal" if total_profit >= 0 else "inverse")
col4.metric("オープンポジション",  f"{open_count} 件")

st.divider()

# ── ② 累積損益チャート ────────────────────────────────────────────────────────
if not closed.empty:
    st.subheader("📈 累積損益推移")

    closed_sorted = closed.sort_values('sell_date').copy()
    closed_sorted['累積損益'] = closed_sorted['profit_yen'].cumsum()
    closed_sorted['決済日']   = pd.to_datetime(closed_sorted['sell_date'], errors='coerce')

    fig = go.Figure()
    # 0ライン
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    # 累積損益ライン
    colors = ['#16a34a' if v >= 0 else '#dc2626' for v in closed_sorted['累積損益']]
    fig.add_trace(go.Scatter(
        x=closed_sorted['決済日'],
        y=closed_sorted['累積損益'],
        mode='lines+markers',
        line=dict(color='#2563EB', width=2),
        marker=dict(color=colors, size=8),
        fill='tozeroy',
        fillcolor='rgba(37,99,235,0.08)',
        name='累積損益',
        hovertemplate='%{x|%Y-%m-%d}<br>累積損益: %{y:,.0f}円<extra></extra>',
    ))
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(tickformat=',.0f', ticksuffix=' 円'),
        xaxis=dict(showgrid=False),
        hovermode='x unified',
        plot_bgcolor='white',
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # 取引別損益バー
    st.subheader("📊 取引別損益")
    bar_colors = ['#16a34a' if v >= 0 else '#dc2626' for v in closed_sorted['profit_yen']]
    fig2 = go.Figure(go.Bar(
        x=closed_sorted['company_name'] + '\n' + closed_sorted['sell_date'].str[:10],
        y=closed_sorted['profit_yen'],
        marker_color=bar_colors,
        hovertemplate='%{x}<br>損益: %{y:,.0f}円<extra></extra>',
    ))
    fig2.update_layout(
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(tickformat=',.0f', ticksuffix=' 円'),
        xaxis=dict(tickangle=-30),
        plot_bgcolor='white',
        showlegend=False,
    )
    fig2.add_hline(y=0, line_dash='dot', line_color='gray', opacity=0.5)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── ③ オープンポジション（含み損益をリアルタイム表示）─────────────────────────
st.subheader(f"🟢 保有中ポジション（{open_count} 件）")

if opened.empty:
    st.info("現在、保有中のポジションはありません。")
else:
    for _, row in opened.iterrows():
        with st.container(border=True):
            col_name, col_price, col_unrealized = st.columns([3, 2, 2])

            with col_name:
                st.markdown(f"**{row['company_name']}**　`{row['ticker']}`")
                st.caption(
                    f"BUY: {row['buy_date'][:16] if row['buy_date'] else '—'} ｜ "
                    f"保有予定: {row['holding_days']}日 ｜ 期限: {row['close_date']}"
                )

            buy_p = row['buy_price']
            with col_price:
                st.metric("BUY価格", f"{buy_p:,.0f} 円" if buy_p else "未取得")
                st.caption(f"利確 +{row['take_profit_pct']}% ／ 損切 -{row['stop_loss_pct']}%")

            with col_unrealized:
                # リアルタイム株価で含み損益を計算
                info = fetch_stock_info(row['ticker'])
                if info and buy_p > 0:
                    curr   = info['price']
                    unreal = curr - buy_p
                    unreal_pct = unreal / buy_p * 100
                    sign = "+" if unreal >= 0 else ""
                    color = "normal" if unreal >= 0 else "inverse"
                    st.metric(
                        f"現在値",
                        f"{curr:,.0f} 円",
                        delta=f"{sign}{unreal:,.0f}円 ({sign}{unreal_pct:.1f}%)",
                        delta_color=color,
                    )
                elif buy_p == 0:
                    st.metric("現在値", "価格未取得")
                    st.caption("BUY時に株価が取得できませんでした")
                else:
                    st.metric("現在値", "—")
                    st.caption("リアルタイム取得失敗")

st.divider()

# ── ④ 決済済み取引履歴テーブル ────────────────────────────────────────────────
st.subheader(f"📋 決済済み取引履歴（{len(closed)} 件）")

if closed.empty:
    st.info("まだ決済済みの取引はありません。")
else:
    display_df = closed[[
        'company_name', 'ticker', 'buy_date', 'buy_price',
        'sell_date', 'sell_reason', 'sell_price', 'profit_yen', 'profit_pct'
    ]].copy()

    display_df.columns = [
        '企業名', '証券コード', 'BUY日時', 'BUY価格(円)',
        'SELL日時', 'SELL理由', 'SELL価格(円)', '損益(円)', '損益(%)'
    ]

    # 日時を短縮表示
    for col in ['BUY日時', 'SELL日時']:
        display_df[col] = display_df[col].str[:16]

    # 損益に色付け
    def color_profit(val):
        if isinstance(val, (int, float)):
            color = '#16a34a' if val > 0 else ('#dc2626' if val < 0 else '')
            return f'color: {color}; font-weight: bold' if color else ''
        return ''

    st.dataframe(
        display_df.style.applymap(color_profit, subset=['損益(円)', '損益(%)']),
        use_container_width=True,
        hide_index=True,
    )
