import streamlit as st
from google import genai
from google.genai import types

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TradeBot Assistant",
    page_icon="📈",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* チャット入力欄を画面下部に固定 */
    .stChatInputContainer { padding-bottom: 0.5rem; }
    /* サイドバーのフッター */
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
        ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        index=0,
    )

    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.05)

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
st.caption("AIトレードボットについて何でも聞いてください。市場分析・銘柄調査・戦略の相談を受け付けます。")

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render chat history ────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Gemini client (lazy init) ─────────────────────────────────────────────────
@st.cache_resource
def get_gemini_client() -> genai.Client:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("GEMINI_API_KEY が設定されていません。`.streamlit/secrets.toml` またはクラウドの Secrets に登録してください。")
        st.stop()
    return genai.Client(api_key=api_key)


SYSTEM_PROMPT = """あなたは「TradeBot Assistant」です。
ユーザーが運用している自動トレードボット（GitHub Actionsで稼働、Gemini APIでニュース分析）の
専属アシスタントとして、以下の役割を担います。

【役割】
- 日本株の市場動向・個別銘柄に関する質問への回答
- トレードボットの戦略ロジック（パニックスコア判定・BUY/SELL/HOLDシグナル）の説明
- 投資判断の補助（注意: 最終判断は必ずユーザー自身が行うこと）
- Python / GitHub Actions / Streamlit に関する技術的な質問への回答

【ガイドライン】
- 日本語で回答する
- 投資は元本割れリスクがあることを適宜リマインドする
- 確信のない情報は憶測と明記し、誤解を招く断言はしない
- 回答はMarkdownで整理して見やすく提示する"""


def build_contents(messages: list[dict]) -> list[types.Content]:
    """st.session_state.messages を Gemini SDK の Contents 形式に変換する。"""
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=m["content"])])
        )
    return contents


# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("メッセージを入力してください…"):
    # ユーザーメッセージを履歴に追加して即時表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gemini にストリーミングで問い合わせ
    client = get_gemini_client()
    contents = build_contents(st.session_state.messages)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
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
                    response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)

        except Exception as e:
            full_response = f"⚠️ エラーが発生しました: {e}"
            response_placeholder.markdown(full_response)

    # アシスタントの返答を履歴に追加
    st.session_state.messages.append({"role": "assistant", "content": full_response})
