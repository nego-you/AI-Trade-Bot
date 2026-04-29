# 07. Grok API 統合ガイド（将来実装向け）

最終更新: 2026-04-29

xAI 社の **Grok API** を本ボットへ組み込む際の参考資料です。
現時点では未実装ですが、将来 Gemini の代替または補完として使う際に参照してください。

---

## Grok API の基本情報

| 項目 | 内容 |
|---|---|
| ベース URL | `https://api.x.ai/v1` |
| 認証 | `Authorization: Bearer <XAI_API_KEY>` |
| APIキー取得 | [console.x.ai](https://console.x.ai) → API Keys → Create New Key |
| OpenAI SDK 互換 | **完全互換**（`base_url` を変えるだけで動作） |

---

## 利用可能なモデル

| モデル名 | 特徴 | 用途目安 |
|---|---|---|
| `grok-3-mini` | 軽量・高速・安価 | Ollama の代替候補（パニックスコア1次判定） |
| `grok-3` | バランス型 | Gemini Flash の代替候補（BUY/SELL判定） |
| `grok-4.1-fast` | 高速・高精度 | トレンド分析など中負荷タスク |
| `grok-4` | 最高精度・高コスト | 重要判断のみに絞って使う |

---

## 料金の目安

| モデル | 入力 | 出力 |
|---|---|---|
| `grok-4.1-fast` | $0.20 / 100万トークン | $0.50 / 100万トークン |
| `grok-4` | $3.00 / 100万トークン | $15.00 / 100万トークン |

- **新規アカウント**: $25 の無料クレジット付与
- レート制限: `grok-4.1-fast` で 4M トークン/分、480 リクエスト/分

---

## Python での呼び出し方法

OpenAI SDK が**そのまま使える**ため、追加パッケージは不要です。

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

response = client.chat.completions.create(
    model="grok-3",
    messages=[
        {"role": "system", "content": "システムプロンプト"},
        {"role": "user",   "content": "分析対象のニュース"},
    ],
    temperature=0.1,
)

print(response.choices[0].message.content)
```

---

## 本ボットへの組み込み方針（案）

### ① Gemini の完全代替として使う

`src/agents/gemini_agent.py` の `genai.Client` を OpenAI SDK に差し替えるだけで動作します。

```python
# 変更前
from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# 変更後
from openai import OpenAI
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)
```

レスポンスの取り出し方も変わります：

```python
# 変更前（Gemini）
result_text = response.text

# 変更後（Grok / OpenAI互換）
result_text = response.choices[0].message.content
```

### ② Gemini と Grok を使い分ける（ハイブリッド案）

| 処理 | 現在 | Grok 追加後の候補 |
|---|---|---|
| 1次パニックスコア | Ollama（無料） | そのまま Ollama を継続 |
| BUY/SELL/HOLD 判定 | Gemini Flash | Grok 3 または Grok 4.1-fast |
| トレンド分析（注目銘柄） | Gemini Flash | Grok 4（精度重視） |

---

## 実装時のチェックリスト

- [ ] [console.x.ai](https://console.x.ai) で APIキーを発行
- [ ] GitHub Secrets に `XAI_API_KEY` を追加
- [ ] `.github/workflows/trading_bot.yml` の `env` に `XAI_API_KEY` を追加
- [ ] `requirements.txt` に `openai>=1.0.0` を追加（すでに入っていれば不要）
- [ ] `src/agents/gemini_agent.py` に Grok 呼び出し関数を追加
- [ ] `.env` に `XAI_API_KEY=...` を追加（ローカル開発用）

---

## 参考リンク

- [xAI 公式ドキュメント](https://docs.x.ai/)
- [モデル一覧・料金](https://docs.x.ai/developers/models)
- [レート制限](https://docs.x.ai/docs/key-information/consumption-and-rate-limits)
- [xAI Python SDK（公式）](https://github.com/xai-org/xai-sdk-python)
