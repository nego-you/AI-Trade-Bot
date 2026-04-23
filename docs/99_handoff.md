# 引き継ぎメモ（別 PC で作業再開する用）

最終更新: 2026-04-23

## 🚨 先にやること（必須）

`.env` が過去コミット (`fa62d23`) に含まれた状態で GitHub に push されていた。以下を**作業再開前に**ローテーションする。

- **Gemini API キー**：[Google AI Studio](https://aistudio.google.com/app/apikey) で旧キー削除 → 新規発行
- **Discord Webhook**：対象チャンネル設定で旧 Webhook 削除 → 再作成

Gmail アプリパスワードは未コミットなので影響なし。

## 別 PC でのセットアップ

```bash
git clone https://github.com/nego-you/AI-Trade-Bot.git
cd AI-Trade-Bot
cp .env.example .env
# → .env に以下を記入（値は 1Password 等の秘密管理から取り出す）
#    GEMINI_API_KEY        : 再発行した新キー
#    DISCORD_WEBHOOK_URL   : 再作成した新 URL（Gmail 運用なら空のままでも可）
#    GMAIL_USER            : 送信元 Gmail
#    GMAIL_APP_PASSWORD    : Google アカウントのアプリパスワード（16桁）
#    ALERT_RECEIVER        : 通知送信先

pip install -r requirements.txt
```

動作確認:

```bash
python src/utils/notifier.py       # Gmail 送信テスト
python src/utils/scraper.py        # RSS 取得テスト
python src/agents/ollama_agent.py  # Ollama 応答テスト（ローカル Ollama 必須）
python src/agents/gemini_agent.py  # Gemini API 応答テスト
```

## 現在 `main` に入っている変更（コミット `11812c7`）

- `.gitignore` 追加、`.env` を追跡解除、`.env.example` 追加
- `src/utils/notifier.py` を Discord → Gmail SMTP に差し替え
- `requirements.txt` 修正：`google-generativeai` → `google-genai`、`lxml` 追加

## 旧 PC にローカル保持中（未コミット、必要なら別 PC で書き直す想定）

以下は「古いコードでも動くので必須ではない」判断で未コミット。別 PC で再度やるかどうかは任意。

- `src/utils/scraper.py` — `print` → `logging`、定数を module レベルへ抽出
- `src/agents/ollama_agent.py` — エラー時も JSON 文字列を返すように戻り値型を統一
- `src/agents/gemini_agent.py` — `print` → `logging`、`response.text` の None 対策
- `src/main.py` — scraper → Ollama → Gemini → 通知のパイプライン雛形（`schedule` で定期実行、URL dedup 付き）
- `src/dashboard.py` — Streamlit 3 タブ雛形（Live feed / Ollama test / History）

## 次にやる候補

- PostgreSQL スキーマと書き込みレイヤーの実装（README と `docs/03_db_design.md` 参照）。現状 `src/dashboard.py` の `load_recent_decisions()` はスタブ。
- Strategy A/B ロジックを `src/strategies/` に切り出し（現在フォルダ未作成）。
- auカブコム証券 API 連携（発注）。
- マクロ環境変数（前日 VIX、ダウ等）のプロンプト注入。

## 運用上のルール

- `.env` は Git に絶対乗せない。秘密は 1Password / Bitwarden 等に保管し、PC 間は手で同期。
- キーを再発行したら 1Password のノートもすぐ更新する。
