# 02. セットアップガイド（ローカル開発）

最終更新: 2026-04-24

## 1) 前提

- OS: Windows 10/11
- Python: 3.11 系推奨
- 任意: Docker Desktop（PostgreSQL をコンテナ起動する場合）
- 任意: Ollama（ローカル一次判定を使う場合）

## 2) リポジトリ取得と依存導入

```bash
git clone https://github.com/nego-you/AI-Trade-Bot.git
cd AI-Trade-Bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## 3) `.env` 設定

`.env` に以下を設定:

- `GEMINI_API_KEY` : Google AI Studio で発行したキー
- `GMAIL_USER` : 送信元 Gmail アドレス
- `GMAIL_APP_PASSWORD` : Gmail アプリパスワード（16桁）
- `ALERT_RECEIVER` : 通知先メールアドレス

> 注意: `.env` は絶対に Git にコミットしない。

## 4) PostgreSQL（必要時のみ）

```bash
docker compose up -d db
```

- ポート: `5432`
- DB: `vibe_investor`
- ユーザー: `user`
- パスワード: `password`

初期スキーマは `db/init/01_schema.sql` が自動適用されます。

## 5) Ollama 準備（一次判定）

例:

```bash
ollama pull llama3
ollama serve
```

`src/agents/ollama_agent.py` のデフォルトは `http://host.docker.internal:11434` です。  
ローカル実行で接続できない場合は `localhost:11434` へ変更してください。

## 6) 動作確認（最小）

```bash
python src/utils/scraper.py
python src/agents/ollama_agent.py
python src/agents/gemini_agent.py
python src/utils/notifier.py
```

## 7) 本番相当実行

- 監視ループ起動:

```bash
python src/main.py
```

- ダッシュボード起動:

```bash
streamlit run src/dashboard.py
```

## 8) よくあるトラブル

- **Gemini エラー (`GEMINI_API_KEY is not set`)**
	- `.env` の設定漏れ、またはキー無効化を確認
- **Gmail 送信失敗**
	- アプリパスワードの貼り付け時スペース混入を確認
- **Ollama 接続失敗**
	- `ollama serve` 稼働確認
	- URL を `localhost:11434` に変更
- **RSS 取得失敗**
	- 一時的な通信エラーの可能性。再実行して確認

