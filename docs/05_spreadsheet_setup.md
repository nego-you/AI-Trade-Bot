# 05. Google スプレッドシート連携セットアップ

最終更新: 2026-04-24

## 1) 概要

`main.py` が Gemini の判定を行うたびに、結果を Google スプレッドシートへ自動追記します。  
蓄積されたデータを Gem（カスタム Gemini）に読み込ませ、勝率分析やプロンプト改善提案に活用します。

## 2) 記録されるカラム

| # | カラム名 | 内容 |
|---|---------|------|
| 1 | 日時 | 判定実行時刻 |
| 2 | ニュース見出し | RSS から取得したタイトル |
| 3 | パニックスコア | Ollama の一次判定スコア (0-100) |
| 4 | Gemini の判断 | `BUY` または `SKIP` |
| 5 | 判断理由 | Gemini が返した理由テキスト |
| 6 | 仮想損益 | 初期値 0（手動または後続処理で更新） |

## 3) GCP サービスアカウント発行手順

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを選択（なければ新規作成）
3. **API とサービス → ライブラリ** で以下を有効化:
   - Google Sheets API
   - Google Drive API
4. **API とサービス → 認証情報** → **サービスアカウントを作成**
   - 名前: `vibe-investor-sheets`（任意）
   - ロール: 不要（スプレッドシート側で共有するため）
5. 作成したサービスアカウントの **鍵** タブ → **鍵を追加 → JSON**
6. ダウンロードした JSON ファイルをプロジェクトルートに配置  
   例: `service_account.json`

> ⚠️ JSON キーファイルは `.gitignore` に追加し、Git にコミットしないでください。

## 4) スプレッドシートの準備

1. [Google スプレッドシート](https://sheets.google.com/) で新規シートを作成
2. URL から **スプレッドシート ID** を控える  
   `https://docs.google.com/spreadsheets/d/＜ここがID＞/edit`
3. **共有** ボタン → サービスアカウントのメールアドレスを追加（編集者権限）  
   メールアドレスはサービスアカウント JSON 内の `client_email` フィールドに記載

## 5) `.env` 設定

```dotenv
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
SPREADSHEET_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ...
```

## 6) `.gitignore` への追加

```gitignore
# GCP service account key
service_account.json
*.json
!package.json
```

## 7) 動作確認

```bash
python src/utils/spreadsheet.py
```

スプレッドシートにテスト行が追記されれば成功です。

## 8) トラブルシューティング

- **`gspread.exceptions.SpreadsheetNotFound`**  
  → スプレッドシートがサービスアカウントに共有されていない
- **`FileNotFoundError` (JSON キー)**  
  → `GOOGLE_SERVICE_ACCOUNT_JSON` のパスを確認
- **`APIError 429`**  
  → Sheets API のレート制限。連続書き込みが多い場合はバッチ化を検討
