# 03. データベース設計

最終更新: 2026-04-24

## 1) 目的

ニュース収集結果、LLM 判定結果、実行状態を時系列で保持し、後で検証・可視化できるようにする。

## 2) 現行スキーマ（`db/init/01_schema.sql`）

### 2.1 `trade_logs`

- `id`: 主キー
- `created_at`: 記録時刻
- `ticker_symbol`: 銘柄コード（将来的に抽出）
- `strategy_type`: 戦略種別（例: Strategy A / B）
- `panic_score`: 一次判定スコア
- `ai_decision`: JSONB（LLM の応答原文/構造化結果）
- `execution_status`: `BUY` / `SKIP` / `ERROR`
- `market_context`: JSONB（VIX・ダウ等の環境情報を想定）

### 2.2 `news_articles`

- `id`: 主キー
- `fetched_at`: 取得時刻
- `title`: ニュースタイトル
- `content`: 本文/説明
- `source_url`: 元 URL
- `is_processed`: 判定済みフラグ

## 3) 保存対象の基本方針

- **原文優先**: LLM 応答は JSONB で保存し、後処理を後回しにできる形を維持
- **再処理可能**: `news_articles` を残し、プロンプト改修後に再評価可能にする
- **トレーサビリティ**: `execution_status` で失敗も履歴化

## 4) 推奨インデックス

初期実装後、以下を追加すると検索性能が向上:

```sql
CREATE INDEX IF NOT EXISTS idx_trade_logs_created_at ON trade_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_logs_status ON trade_logs (execution_status);
CREATE INDEX IF NOT EXISTS idx_news_articles_fetched_at ON news_articles (fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_processed ON news_articles (is_processed);
```

## 5) 想定クエリ

- 直近の BUY シグナル一覧
- 日次での `panic_score` 分布
- `strategy_type` 別の判定件数/BUY 比率
- `execution_status=ERROR` の原因追跡

## 6) アプリ実装との対応

- 現状、`src/main.py` はメモリ内処理のみ
- `src/dashboard.py` の `load_recent_decisions()` はスタブ
- 次段階として DB I/O 層（Repository）を追加し、
	- ニュース保存
	- 判定保存
	- 履歴取得
	を分離実装する

## 7) 将来拡張案

- `trade_executions` テーブル（実発注ログ）追加
- `prompt_versions` テーブル（プロンプト A/B 追跡）追加
- `ai_decision` の JSON Schema を固定し、分析 SQL を簡素化

