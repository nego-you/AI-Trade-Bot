# 🤖 Vibe Investor (AI自動売買システム)

LLM（大規模言語モデル）の定性判断をコアに据えた、ニュース駆動型の自動売買A/Bテストシステムです。  
Pontaポイント（auカブコム証券のプチ株）を活用し、人間の「恐怖」と「熱狂」を排除した逆張りトレードの有効性を検証します。

## 💻 開発方針

このリポジトリは **ローカル開発（Windows + Python 仮想環境）** 前提です。

## 🚀 ローカルセットアップ

```bash
git clone https://github.com/nego-you/AI-Trade-Bot.git
cd AI-Trade-Bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## 🗄️ PostgreSQL 起動（必要時のみ）

DB は Docker Compose で単体起動できます。

```bash
docker compose up -d db
```

## 📚 Docs 目次

- [01_architecture.md](docs/01_architecture.md) - 全体アーキテクチャと実行フロー
- [02_setup_guide.md](docs/02_setup_guide.md) - ローカル開発セットアップ手順
- [03_db_design.md](docs/03_db_design.md) - DB スキーマと設計方針
- [04_strategy_logic.md](docs/04_strategy_logic.md) - 現行ロジックと Strategy A/B 設計
- [05_gem_system_prompt.md](docs/05_gem_system_prompt.md) - Gem 用システムプロンプト（分析アナリスト）
- [06_spreadsheet_setup.md](docs/06_spreadsheet_setup.md) - Google スプレッドシート連携セットアップ
- [99_handoff.md](docs/99_handoff.md) - 引き継ぎメモ

## 📁 ディレクトリ構成

```text
.
├── db/
│   └── init/
├── docs/
├── src/
│   ├── agents/
│   └── utils/
├── docker-compose.yml
└── requirements.txt
```
