import os
import sys
import streamlit as st

# ── Page config (must be first Streamlit command) ─────────────────────────────
st.set_page_config(
    page_title="TradeBot Assistant",
    page_icon="📈",
    layout="centered",
)

# ── Secrets → 環境変数へ反映（spreadsheet.py が os.getenv() で読む）──────────
for key in ("GEMINI_API_KEY", "SPREADSHEET_ID", "GOOGLE_SERVICE_ACCOUNT_JSON"):
    val = st.secrets.get(key, "")
    if val:
        os.environ[key] = val

# ── src/ をインポートパスに追加 ──────────────────────────────────────────────
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# ── 初回セッション: 注目銘柄をスプレッドシートから自動読み込み ──────────────────
if "focus_targets" not in st.session_state:
    st.session_state.focus_targets = []
    if st.secrets.get("SPREADSHEET_ID") and st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        try:
            from src.utils.spreadsheet import get_service, SPREADSHEET_ID, FOCUS_SHEET_NAME
            _service = get_service()
            _result = _service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{FOCUS_SHEET_NAME}!A:E"
            ).execute()
            _rows = _result.get("values", [])
            _targets = []
            for _row in _rows[1:]:
                if len(_row) < 2:
                    continue
                _targets.append({
                    "company_name": _row[1] if len(_row) > 1 else "",
                    "ticker":       _row[2] if len(_row) > 2 else "",
                    "theme":        _row[3] if len(_row) > 3 else "",
                    "reason":       _row[4] if len(_row) > 4 else "",
                })
            st.session_state.focus_targets = _targets
        except Exception:
            pass  # 読み込み失敗時は空リストのまま続行

# ── Navigation ────────────────────────────────────────────────────────────────
chat_page       = st.Page("pages/chat.py",       title="チャット",       icon="💬", default=True)
stocks_page     = st.Page("pages/stocks.py",     title="注目銘柄管理",   icon="📋")
simulation_page = st.Page("pages/simulation.py", title="シミュレーション結果", icon="💹")

pg = st.navigation([chat_page, stocks_page, simulation_page])
pg.run()
