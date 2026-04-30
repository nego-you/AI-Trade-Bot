import sys
import os
import streamlit as st

# src/ をインポートパスに追加（リポジトリルートからの相対パス）
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from src.utils.spreadsheet import update_focus_targets

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📋 注目銘柄管理")
st.caption("銘柄を追加・削除して、スプレッドシートの「注目銘柄」シートに反映します。")

# ── セッションステートの初期化 ─────────────────────────────────────────────────
if "focus_targets" not in st.session_state:
    st.session_state.focus_targets: list[dict] = []

# ── 銘柄追加フォーム ───────────────────────────────────────────────────────────
st.subheader("銘柄を追加")

with st.form("add_stock_form", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        company_name = st.text_input("企業名 *", placeholder="例: ソニーグループ")
    with col2:
        ticker = st.text_input("証券コード *", placeholder="例: 6758")

    col3, col4 = st.columns([1, 2])
    with col3:
        theme = st.text_input("テーマ", placeholder="例: AI・半導体")
    with col4:
        reason = st.text_area("注目理由", placeholder="例: 生成AI向けイメージセンサー需要の急拡大が見込まれるため。", height=80)

    submitted = st.form_submit_button("➕ リストに追加", use_container_width=True)

    if submitted:
        if not company_name or not ticker:
            st.warning("企業名と証券コードは必須です。")
        elif any(t["ticker"] == ticker for t in st.session_state.focus_targets):
            st.warning(f"証券コード {ticker} はすでにリストにあります。")
        else:
            st.session_state.focus_targets.append({
                "company_name": company_name,
                "ticker": ticker,
                "theme": theme,
                "reason": reason,
            })
            st.success(f"✅ {company_name}（{ticker}）を追加しました。")

st.divider()

# ── 現在のリスト表示 ───────────────────────────────────────────────────────────
st.subheader(f"現在のリスト（{len(st.session_state.focus_targets)} 銘柄）")

if not st.session_state.focus_targets:
    st.info("銘柄がまだ追加されていません。上のフォームから追加してください。")
else:
    for i, target in enumerate(st.session_state.focus_targets):
        with st.container(border=True):
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f"**{target['company_name']}**　`{target['ticker']}`"
                    + (f"　🏷️ {target['theme']}" if target.get("theme") else "")
                )
                if target.get("reason"):
                    st.caption(target["reason"])
            with col_del:
                if st.button("🗑️", key=f"del_{i}", help="削除"):
                    st.session_state.focus_targets.pop(i)
                    st.rerun()

st.divider()

# ── スプレッドシートへ反映 ─────────────────────────────────────────────────────
st.subheader("スプレッドシートへ反映")

spreadsheet_id = st.secrets.get("SPREADSHEET_ID", "")
sa_json = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

if not spreadsheet_id or not sa_json:
    st.warning(
        "スプレッドシート連携には `SPREADSHEET_ID` と `GOOGLE_SERVICE_ACCOUNT_JSON` が必要です。\n\n"
        "Streamlit Cloud の **Settings → Secrets** に追加してください。"
    )
else:
    st.info(
        "「スプレッドシートに反映」を押すと、注目銘柄シートの内容が**上のリストで上書き**されます。"
    )

    col_push, col_clear = st.columns([3, 1])

    with col_push:
        if st.button(
            "📤 スプレッドシートに反映",
            disabled=len(st.session_state.focus_targets) == 0,
            use_container_width=True,
            type="primary",
        ):
            with st.spinner("スプレッドシートに書き込み中…"):
                ok = update_focus_targets(st.session_state.focus_targets)
            if ok:
                st.success("✅ 注目銘柄シートを更新しました！")
                st.balloons()
            else:
                st.error("❌ 書き込みに失敗しました。Secrets の設定を確認してください。")

    with col_clear:
        if st.button("🗑️ リストを全クリア", use_container_width=True):
            st.session_state.focus_targets = []
            st.rerun()
