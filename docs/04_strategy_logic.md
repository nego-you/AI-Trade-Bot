# 04. 戦略ロジック

最終更新: 2026-04-24

## 1) 基本思想

本プロジェクトの中心は「価格予測」ではなく、ニュース起因の市場心理（恐怖/過熱）を LLM に定性評価させる点にある。

## 2) 現在の実装ロジック（`src/main.py`）

### 2.1 前処理

- RSS からニュース取得（`fetch_latest_news()`）
- URL 単位で重複排除（`_seen_urls`）

### 2.2 一次判定（Ollama）

- 入力: `title + content`
- 出力: `{"panic_score": int, "reason": str}`
- 失敗時: `{"error": ...}` を返し、そのニュースをスキップ

### 2.3 しきい値判定

- `PANIC_THRESHOLD = 70`
- `panic_score < 70` は Gemini を呼ばずに終了（コスト削減）

### 2.4 二次判定（Gemini）

- 入力: ニュース本文 + `panic_score`
- 出力: `{"decision": "BUY"|"SKIP", "reason": str}`

### 2.5 通知

- `decision == BUY` の場合のみ Gmail 通知

## 3) Strategy A/B の定義（設計）

### Strategy A: パニック買い（Negative Rebound）

- 悪材料による過剰下落を検知し、反発狙いで買い
- 参考条件:
	- 高い `panic_score`
	- 事業継続性への致命傷が薄い
	- 一過性ショックの可能性

### Strategy B: ポジティブ売り（Positive Overheat）

- 好材料で急騰した局面を過熱とみなし、利確方向で判断
- 参考条件:
	- 過熱語彙（急騰、連騰、最高値更新）
	- ファンダよりセンチメント先行

> 現時点のコードは BUY/SKIP 判定が中心で、B 戦略を分離実装していない。

## 4) 今後の分離実装案

- `src/strategies/strategy_a.py`
- `src/strategies/strategy_b.py`

共通インターフェース例:

- `evaluate(news: dict, context: dict) -> dict`
- 返却: `{"decision": "BUY"|"SKIP"|"SELL", "reason": str, "meta": {...}}`

## 5) 改善ポイント

- マクロ環境（VIX、ダウ、米金利）を `market_context` として注入
- 銘柄抽出精度向上（NER / ルール）
- 判定ログの定量評価（Precision/Recall 的な運用 KPI）

