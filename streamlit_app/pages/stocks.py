import sys
import os
import streamlit as st

# src/ をインポートパスに追加（リポジトリルートからの相対パス）
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from src.utils.spreadsheet import update_focus_targets


def _sync_to_spreadsheet() -> None:
    """注目銘柄リストをスプレッドシートに自動同期する（失敗しても無視）。"""
    try:
        update_focus_targets(st.session_state.get("focus_targets", []))
    except Exception:
        pass


# ── Header ────────────────────────────────────────────────────────────────────
st.title("📋 注目銘柄管理")
st.caption("チャットで追加した銘柄の一覧です。削除するとスプレッドシートにも即時反映されます。")

st.divider()

# ── 現在のリスト表示 ───────────────────────────────────────────────────────────
targets = st.session_state.get("focus_targets", [])
st.subheader(f"現在のリスト（{len(targets)} 銘柄）")

if not targets:
    st.info("銘柄がまだ追加されていません。チャットで銘柄について話し、「➕ 追加」ボタンで登録してください。")
else:
    for i, target in enumerate(targets):
        with st.container(border=True):
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f"**{target['company_name']}**　`{target['ticker']}`"
                    + (f"　🏷️ {target['theme']}" if target.get("theme") else "")
                )
                if target.get("reason"):
                    st.caption(target["reason"])
                # TradingView リンク
                raw_ticker = str(target['ticker']).replace(".T", "")
                if raw_ticker.isdigit() and len(raw_ticker) == 4:
                    tv_url = f"https://jp.tradingview.com/chart/?symbol=TSE:{raw_ticker}"
                else:
                    tv_url = f"https://jp.tradingview.com/chart/?symbol={raw_ticker}"
                st.link_button("📊 TradingView", tv_url)
            with col_del:
                if st.button("🗑️", key=f"del_{i}", help="削除"):
                    st.session_state.focus_targets.pop(i)
                    _sync_to_spreadsheet()
                    st.rerun()
