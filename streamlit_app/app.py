import os
import streamlit as st

# ── Secrets → 環境変数へ反映（spreadsheet.py が os.getenv() で読む）──────────
for key in ("GEMINI_API_KEY", "SPREADSHEET_ID", "GOOGLE_SERVICE_ACCOUNT_JSON"):
    val = st.secrets.get(key, "")
    if val:
        os.environ[key] = val

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TradeBot Assistant",
    page_icon="📈",
    layout="centered",
)

# ── Navigation ────────────────────────────────────────────────────────────────
chat_page   = st.Page("pages/chat.py",   title="チャット",     icon="💬", default=True)
stocks_page = st.Page("pages/stocks.py", title="注目銘柄管理", icon="📋")

pg = st.navigation([chat_page, stocks_page])
pg.run()
