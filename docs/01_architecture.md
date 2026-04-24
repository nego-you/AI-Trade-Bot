# 01. アーキテクチャ

最終更新: 2026-04-24

## 1) 目的

本システムは、ニュースの定性情報を LLM で評価し、逆張り売買の判断を半自動で行うための実験基盤です。  
「価格予測モデル」ではなく「ニュースの熱量（パニック/過熱）評価」を主眼とします。

## 2) 構成要素

- **収集層**: `src/utils/scraper.py`
	- Yahoo / PR TIMES / 日経の RSS を取得
	- 正規化したニュース配列（source/title/content/url）を返す
- **一次判定層（ローカル）**: `src/agents/ollama_agent.py`
	- Ollama へ問い合わせ、`panic_score`（0-100）と理由を JSON で取得
- **二次判定層（クラウド）**: `src/agents/gemini_agent.py`
	- Gemini へ問い合わせ、`BUY` または `SKIP` を JSON で取得
- **実行制御層**: `src/main.py`
	- スケジューラ実行（15分ごと）
	- URL 重複排除
	- BUY 時に通知送信
- **通知層**: `src/utils/notifier.py`
	- Gmail SMTP で通知メール送信
- **可視化層**: `src/dashboard.py`
	- Streamlit で Live feed / Ollama test / History を表示
- **データ層**: PostgreSQL（`db/init/01_schema.sql`）
	- ニュース・判定ログ格納（現状は書き込み未接続）

## 3) 論理フロー

1. RSS からニュース取得
2. `main.py` が URL 重複を除外
3. Ollama で `panic_score` を算出
4. しきい値（`PANIC_THRESHOLD=70`）以上のみ Gemini へエスカレーション
5. Gemini が `BUY/SKIP` を返す
6. `BUY` の場合のみ Gmail 通知

## 4) 実行モデル

- 通常運転: `python src/main.py`
- 監視・可視化: `streamlit run src/dashboard.py`
- DB は必要時のみ起動: `docker compose up -d db`

## 5) 主要な設計判断

- **コスト最適化**: 低コストな一次判定で対象を絞ってから Gemini を呼ぶ
- **安全側運用**: JSON 形式を強制し、失敗時は `{"error": ...}` を返す
- **運用容易性**: ローカル開発前提、通知チャネルは Gmail に一本化

## 6) 現在の制約

- DB 書き込みが未実装（`dashboard.py` の履歴表示はスタブ）
- 銘柄抽出・発注 API 連携は未実装
- 過熱判定（売り戦略）の完全実装は未了

## 7) 次の実装優先度

1. DB 書き込みレイヤー
2. Strategy A/B のモジュール分離（`src/strategies/`）
3. 発注 API 実装
4. マクロ要因（VIX・ダウ等）のプロンプト注入

