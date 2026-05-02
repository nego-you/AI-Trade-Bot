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

from stock_utils import render_stock_card, fetch_stock_info

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .sidebar-footer { font-size: 0.75rem; color: #888; margin-top: 2rem; }
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


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """あなたは「TradeBot Assistant」です。
ユーザーが運用している自動トレードボット（GitHub Actionsで稼働、Gemini APIでニュース分析）の
専属アシスタントとして、日本株の投資判断をサポートします。

【役割】
- 日本株の市場動向・個別銘柄に関する質問への回答
- トレードボットの戦略ロジック（パニックスコア判定・BUY/SELL/HOLDシグナル）の説明
- 投資判断の補助（注意: 最終判断は必ずユーザー自身が行うこと）

【絶対ルール：銘柄ブロックの出力】
特定の企業・銘柄について言及・分析・紹介する場合は、回答文の最後に必ず下記の ```stocks``` ブロックを出力すること。
このルールに例外はありません。マネーフォワードについて話すなら、マネーフォワードをブロックに含めること。

出力形式（このまま使うこと。``` の前後に余分なテキスト不可）:
```stocks
[{"company_name": "企業の正式名称", "ticker": "証券コード数字4桁のみ", "theme": "関連テーマ", "reason": "注目理由を1〜2文で"}]
```

複数銘柄の場合はリストに追加する:
```stocks
[
  {"company_name": "企業A", "ticker": "1234", "theme": "テーマA", "reason": "理由A"},
  {"company_name": "企業B", "ticker": "5678", "theme": "テーマB", "reason": "理由B"}
]
```

【ガイドライン】
- 日本語で回答する
- 投資は元本割れリスクがあることを適宜リマインドする
- 確信のない情報は憶測と明記し、誤解を招く断言はしない
- 回答はMarkdownで整理して見やすく提示する"""


# ── パース：```stocks``` ブロック抽出 ─────────────────────────────────────────
STOCKS_PATTERN = re.compile(r"```stocks\s*(\[.*?\])\s*```", re.DOTALL)
# フォールバック：本文中の（数字4桁）パターンを抽出
TICKER_INLINE  = re.compile(r"[（(](\d{4})[）)]")


def parse_stocks(text: str) -> tuple[str, list[dict]]:
    """
    ```stocks [...] ``` ブロックを抽出して (表示テキスト, 銘柄リスト) を返す。
    ブロックがない場合は本文中の（4桁）をフォールバック検出する。
    """
    match = STOCKS_PATTERN.search(text)
    if match:
        display_text = STOCKS_PATTERN.sub("", text).strip()
        try:
            stocks = json.loads(match.group(1))
            if isinstance(stocks, list) and stocks:
                return display_text, stocks
        except json.JSONDecodeError:
            pass

    # ── フォールバック：本文中の（4桁）を拾う ────────────────────────────────
    tickers_found = TICKER_INLINE.findall(text)
    if tickers_found:
        stocks = []
        for ticker in dict.fromkeys(tickers_found):  # 重複排除・順序保持
            # 企業名をテキストから推定（ticker の前の単語を取る簡易抽出）
            name_match = re.search(
                rf"([　-鿿゠-ヿ･-ﾟA-Za-z一-鿿]+)[（(]{ticker}[）)]",
                text
            )
            company_name = name_match.group(1) if name_match else ticker
            stocks.append({
                "company_name": company_name,
                "ticker": ticker,
                "theme": "",
                "reason": "",
            })
        return text, stocks

    return text, []


def build_contents(messages: list[dict]) -> list[types.Content]:
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=m["display"])])
        )
    return contents


def render_stock_section(stocks: list[dict], msg_idx: int):
    """銘柄カード（株価・チャート・追加ボタン）セクションを表示する。"""
    if not stocks:
        return
    st.markdown("---")
    st.markdown("**💡 言及銘柄 — 株価・チャートを確認してワンクリックで追加できます**")
    for j, stock in enumerate(stocks):
        render_stock_card(stock, msg_idx, j)


# ── Render chat history ────────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["display"])
        if msg["role"] == "assistant" and msg.get("stocks"):
            render_stock_section(msg["stocks"], idx)

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
        display_text  = ""
        stocks: list[dict] = []

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
                    preview, _ = parse_stocks(full_response)
                    placeholder.markdown(preview + "▌")

            display_text, stocks = parse_stocks(full_response)
            placeholder.markdown(display_text)

            if stocks:
                render_stock_section(stocks, len(st.session_state.messages))

        except Exception as e:
            display_text = f"⚠️ エラーが発生しました: {e}"
            placeholder.markdown(display_text)

    st.session_state.messages.append({
        "role":    "assistant",
        "display": display_text,
        "stocks":  stocks,
    })
