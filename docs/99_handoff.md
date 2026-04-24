# 引き継ぎメモ（別 PC で作業再開する用）

最終更新: 2026-04-24

## 🚨 先にやること（必須）

`.env` が過去コミット (`fa62d23`) に含まれた状態で GitHub に push されていた。以下を**作業再開前に**ローテーションする。

- **Gemini API キー**：[Google AI Studio](https://aistudio.google.com/app/apikey) で旧キー削除 → 新規発行

Gmail アプリパスワードは未コミットなので影響なし。

## 別 PC でのセットアップ

```bash
git clone https://github.com/nego-you/AI-Trade-Bot.git
cd AI-Trade-Bot
cp .env.example .env
# → .env に以下を記入（値は 1Password 等の秘密管理から取り出す）
#    GEMINI_API_KEY        : 再発行した新キー
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

## 現在の構成メモ

- 開発方針はローカル実行前提（Dev Container 不使用）
- 通知チャネルは Gmail のみ
- DB は Docker Compose で必要時に `db` のみ起動

## 次にやる候補

- PostgreSQL スキーマと書き込みレイヤーの実装（README と `docs/03_db_design.md` 参照）。現状 `src/dashboard.py` の `load_recent_decisions()` はスタブ。
- Strategy A/B ロジックを `src/strategies/` に切り出し（現在フォルダ未作成）。
- auカブコム証券 API 連携（発注）。
- マクロ環境変数（前日 VIX、ダウ等）のプロンプト注入。

## 運用上のルール

- `.env` は Git に絶対乗せない。秘密は 1Password / Bitwarden 等に保管し、PC 間は手で同期。
- キーを再発行したら 1Password のノートもすぐ更新する。
