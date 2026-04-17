🤖 Vibe Investor (AI自動売買システム)

LLM（大規模言語モデル）の定性判断をコアに据えた、ニュース駆動型の自動売買A/Bテストシステムです。
Pontaポイント（auカブコム証券のプチ株）を活用し、人間の「恐怖」と「熱狂」を排除した逆張りトレードの有効性を検証します。

🎯 プロジェクトの目的と戦略

従来の「機械学習による株価予測」ではなく、**「LLMにニュースの熱量（パニック度・過熱度）をスコアリングさせる」**アプローチを採用しています。

以下の2つの戦略を並行稼働させ、PostgreSQLに推論プロセスと結果を蓄積します。

Strategy A (パニック買い / Negative Rebound)

悪材料による過剰な投げ売り（パニック）をLLMが判定し、反発を狙って「買い」。

Strategy B (ポジティブ売り / Positive Overheat)

好材料で急騰したタネ株をLLMが判定し、実力以上のバブル（過熱）とみなせば「利確（売り）」。

Note: 前日の米国市場（ダウ、VIX指数等）の動向を「マクロ環境変数」としてLLMのプロンプトに注入し、市場全体の地合いに引きずられただけの値動きをフィルタリングしています。

🏗️ システムアーキテクチャ

LLMのAPI費用を極限まで抑えるため、**「ローカルLLM（一次スクリーニング） ＋ クラウドLLM（最終判断）」のハイブリッド構成（月額0円運用）**としています。

Hardware: MINISFORUM UM890Pro (Ryzen 9 / 32GB RAM / 512GB SSD)

OS: Windows 11 Pro (24/7稼働, マルチアカウント＆指紋認証切り替え)

Infrastructure: Docker Desktop (WSL2)

Database: PostgreSQL (AI推論ログをJSONBでフル蓄積)

LLM (Local): Ollama (Llama 3 / Gemma 2 等) - ニュースの全量一次判定

LLM (Cloud): Gemini 1.5 Flash API (Free Tier) - 最終意思決定

Dashboard: Streamlit - AIの思考プロセスとA/Bテスト結果の可視化

Broker API: auカブコム証券 (kabuステーションAPI)

📁 ディレクトリ構成

詳しい設計や構築手順については、docs/ ディレクトリを参照してください。

.
├── db/init/                # PostgreSQL初期構築DDL (テーブル定義)
├── docs/                   # 📑 システム設計・環境構築ドキュメント
│   ├── 01_architecture.md    # 全体アーキテクチャ設計
│   ├── 02_setup_guide.md     # Windows初期設定・セキュリティ構築ガイド
│   ├── 03_db_design.md       # データベース・JSONB設計
│   └── 04_strategy_logic.md  # 取引ロジックとプロンプト設計
├── src/                    # 💻 Pythonソースコード
│   ├── main.py               # 監視・発注メインループ
│   ├── dashboard.py          # Streamlit可視化UI
│   └── agents/               # LLMプロンプト・通信ロジック
├── docker-compose.yml      # インフラ起動定義
└── README.md


🚀 クイックスタート (10分で環境復元)

PCのリプレイス時や障害発生時でも、このリポジトリとバックアップデータがあれば即座に環境を復元できます。

1. OS・ハードウェアの準備

docs/02_setup_guide.md に従い、Windowsのマルチアカウント設定や指紋認証のセットアップを完了させてください。

2. 環境変数の設定

.env.example をコピーして .env を作成し、Bitwarden（パスワードマネージャー）から以下の機密情報を転記してください。
(※ .env ファイルは絶対にコミットしないでください)

cp .env.example .env
# .env を編集して APIキーやDBパスワードを入力


3. システムの起動

Dockerを使用して、DB、Python実行環境、ローカルLLM、ダッシュボードを一括起動します。

docker compose up -d


起動後、ブラウザで http://localhost:8501 にアクセスすると、Streamlitダッシュボードが表示されます。

Disclaimer: 本システムは技術検証を目的としており、投資による利益を保証するものではありません。
