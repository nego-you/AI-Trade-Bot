import json
import re
import sys
import os
import streamlit as st
from google import genai
from google.genai import types

# streamlit_app/ をパスに追加（stock_utils をインポートするため）
_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from stock_utils import render_stock_card

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .sidebar-footer { font-size: 0.75rem; color: #888; margin-top: 2rem; }
    .stock-card { background: #f0f7ff; border-radius: 8px; padding: 0.6rem 1rem; margin: 0.3rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ 設定")

    model_choice = st.selectbox(
        "Gemini モデル",
        ["gemini-2.5-flash", "gemini-2.0-flash"],
        index=0,
    )
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.05)

    st.divider()

    # 注目銘柄リストのサマリー
    targets = st.session_state.get("focus_targets", [])
    st.markdown(f"**📋 注目銘柄リスト：{len(targets)} 銘柄**")
    if targets:
        for t in targets:
            st.caption(f"・{t['company_name']}（{t['ticker']}）")
    else:
        st.caption("まだ追加されていません")

    st.divider()

    if st.button("🗑️ 会話をリセット", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown(
        '<p class="sidebar-footer">TradeBot Assistant v1.0<br>Powered by Gemini API</p>',
        unsafe_allow_html=True,
    )

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📈 TradeBot Assistant")
st.caption("銘柄について話しながら、気になった銘柄を「➕ 追加」ボタンで注目リストに追加できます。")

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "focus_targets" not in st.session_state:
    st.session_state.focus_targets = []

# ── Gemini client ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_gemini_client() -> genai.Client:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("GEMINI_API_KEY が設定されていません。Secrets に登録してください。")
        st.stop()
    return genai.Client(api_key=api_key)


SYSTEM_PROMPT = """あなたは「TradeBot Assistant」です。
ユーザーが運用している自動トレードボット（GitHub Actionsで稼働、Gemini APIでニュース分析）の
専属アシスタントとして、日本株の投資判断をサポートします。

【役割】
- 日本株の市場動向・個別銘柄に関する質問への回答
- トレードボットの戦略ロジック（パニックスコア判定・BUY/SELL/HOLDシグナル）の説明
- 投資判断の補助（注意: 最終判断は必ずユーザー自身が行うこと）

【銘柄提案のルール - 重要】
会話の中で具体的な銘柄を推薦・提案する場合は、通常の回答文の末尾に必ず以下のブロックを追加してください。
このブロックは提案する銘柄がある場合のみ出力し、一般的な質問への回答では出力不要です。

```stocks
[
  {"company_name": "企業名", "ticker": "証券コード4桁", "theme": "テーマ", "reason": "注目理由1〜2文"},
  {"company_name": "企業名2", "ticker": "証券コード4桁", "theme": "テーマ", "reason": "注目理由1〜2文"}
]
```

【ガイドライン】
- 日本語で回答する
- 投資は元本割れリスクがあることを適宜リマインドする
- 確信のない情報は憶測と明記し、誤解を招く断言はしない
- 回答はMarkdownで整理して見やすく提示する"""


STOCKS_PATTERN = re.compile(r"```stocks\s*(\[.*?\])\s*```", re.DOTALL)


def parse_stocks(text: str) -> tuple[str, list[dict]]:
    """
    レスポンスから ```stocks [...] ``` ブロックを抽出し、
    (表示用テキスト, 銘柄リスト) を返す。
    """
    match = STOCKS_PATTERN.search(text)
    if not match:
        return text, []

    display_text = STOCKS_PATTERN.sub("", text).strip()
    try:
        stocks = json.loads(match.group(1))
        if isinstance(stocks, list):
            return display_text, stocks
    except json.JSONDecodeError:
        pass
    return display_text, []


def build_contents(messages: list[dict]) -> list[types.Content]:
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        # Gemini に渡すのは表示テキスト（stocks ブロック除去済み）
        contents.append(
            types.Content(role=role, parts=[types.Part(text=m["display"])])
        )
    return contents


def render_stock_buttons(stocks: list[dict], msg_idx: int):
    """銘柄カード（株価・チャット・追加ボタン）を表示する。"""
    if not stocks:
        return
    st.markdown("---")
    st.markdown("**💡 提案銘柄 — 株価・チャートを確認してワンクリックで追加できます**")
    for j, stock in enumerate(stocks):
        render_stock_card(stock, msg_idx, j)


# ── Render chat history ────────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["display"])
        if msg["role"] == "assistant" and msg.get("stocks"):
            render_stock_buttons(msg["stocks"], idx)

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("銘柄・市場・戦略について聞いてください…"):
    user_msg = {"role": "user", "display": prompt, "stocks": []}
    st.session_state.messages.append(user_msg)
    with st.chat_message("user"):
        st.markdown(prompt)

    client = get_gemini_client()
    contents = build_contents(st.session_state.messages)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            stream = client.models.generate_content_stream(
                model=model_choice,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=temperature,
                ),
            )
            for chunk in stream:
                if chunk.text:
                    full_response += chunk.text
                    # ストリーミング中は stocks ブロックを隠して表示
                    preview, _ = parse_stocks(full_response)
                    placeholder.markdown(preview + "▌")

            display_text, stocks = parse_stocks(full_response)
            placeholder.markdown(display_text)

            if stocks:
                render_stock_buttons(stocks, len(st.session_state.messages))

        except Exception as e:
            display_text = f"⚠️ エラーが発生しました: {e}"
            stocks = []
            placeholder.markdown(display_text)

    st.session_state.messages.append({
        "role":    "assistant",
        "display": display_text,
        "stocks":  stocks,
        # Gemini に返す用に元のレスポンス（stocks ブロック含まない）を保持
        "raw":     full_response,
    })
