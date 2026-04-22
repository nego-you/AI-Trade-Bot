# 🤖 Vibe Investor (AI自動売買システム)

LLM（大規模言語モデル）の定性判断をコアに据えた、ニュース駆動型の自動売買A/Bテストシステムです。
Pontaポイント（auカブコム証券のプチ株）を活用し、人間の「恐怖」と「熱狂」を排除した逆張りトレードの有効性を検証します。

## 🎯 プロジェクトの目的と戦略

従来の「機械学習による株価予測」ではなく、**「LLMにニュースの熱量（パニック度・過熱度）をスコアリングさせる」**アプローチを採用しています。
以下の2つの戦略を並行稼働させ、PostgreSQLに推論プロセスと結果を蓄積します。

### Strategy A (パニック買い / Negative Rebound)
悪材料による過剰な投げ売り（パニック）をLLMが判定し、反発を狙って「買い」。

### Strategy B (ポジティブ売り / Positive Overheat)
好材料で急騰した銘柄をLLMが判定し、実力以上のバブル（過熱）とみなせば「利確（売り）」。

> **Note:** 前日の米国市場（ダウ、VIX指数等）の動向を「マクロ環境変数」としてLLMのプロンプトに注入し、市場全体の地合いに引きずられただけの値動きをフィルタリングします。

## 🏗️ システムアーキテクチャ

月額のAPI費用を極限まで抑えつつ、高いIQを維持する「三段ウォーターフォール構成」を採用しています。

- **Infrastructure:** Docker Desktop (WSL2) / 24時間稼働
- **Database:** PostgreSQL (AI推論ログをJSONB形式でフル蓄積)
- **LLM 1 (Local/無制限):** Ollama (Llama 3 等) - 全ニュースの一次フィルタリング
- **LLM 2 (Cloud/1500回/日):** Gemini 1.5 Flash - 二次詳細判定（スコアリング）
- **LLM 3 (Cloud/50回/日):** Gemini 1.5 Pro - 最終意思決定（BUY/SKIP）
- **Dashboard:** Streamlit - AIの思考プロセスとA/Bテスト結果の可視化
- **Broker API:** auカブコム証券 (kabuステーションAPI)

## 📁 ディレクトリ構成

```text
.
├── .devcontainer/         # VSCode開発環境設定（Docker自動化）
├── .github/                # CI/CD、自動バックアップ設定
├── db/
│   └── init/               # PostgreSQL初期化SQL (DDL)
├── docs/                   # 📑 システム設計・運用ドキュメント
│   ├── 01_architecture.md    # 全体アーキテクチャ設計
│   ├── 02_setup_guide.md     # Windows初期設定・セキュリティ（家族アカウント）
│   ├── 03_db_design.md       # データベース・JSONB構造設計
│   └── 04_strategy_logic.md  # 取引ロジックとプロンプト定義
├── src/                    # 💻 Pythonソースコード
│   ├── main.py               # 監視・発注メインループ
│   ├── dashboard.py          # Streamlit可視化UI
│   ├── agents/               # LLM(Gemini/Ollama)連携ロジック
│   ├── strategies/           # Strategy A/B の判定ロジック
│   └── utils/                # スクレイピング、共通処理
├── tests/                  # A/Bテスト検証用コード
├── docker-compose.yml      # インフラ一括起動設定
└── requirements.txt        # Pythonライブラリ依存関係