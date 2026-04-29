# 07. Grok API 統合ガイド（将来実装向け）

最終更新: 2026-04-29

xAI 社の **Grok API** を本ボットへ組み込む際の参考資料です。

---

## Grok を導入する理由

Grok の最大の差別化ポイントは **X（旧Twitter）へのリアルタイムアクセス**です。

現在のボットは RSS フィードからニュースを取得し、Gemini でテキスト分析しています。
このフローに Grok を「Gemini の代替」として差し込むだけでは、リアルタイム性の恩恵は**ほぼ得られません**。Gemini と同じ土俵になるだけです。

**Grok を入れる価値が出るのは、Live Search 機能を使って X のセンチメントを取得するときです。**

```
RSS ニュース（事実）
  ＋
X のリアルタイム反応（市場参加者の感情・速報）  ← Grok Live Search で取得
  ↓
より精度の高い BUY/SELL/HOLD 判定
```

RSSニュースは「何が起きたか」を教えてくれますが、
「市場がどう受け取ったか」は X のリアルタイムの声の方が速く正確に現れます。

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

| モデル名 | 特徴 | 本ボットでの用途候補 |
|---|---|---|
| `grok-3-mini` | 軽量・高速・安価 | X センチメント取得（件数が多いため安価モデルを使う） |
| `grok-3` | バランス型 | X センチメント＋BUY/SELL 補強判定 |
| `grok-4.1-fast` | 高速・高精度 | 重要銘柄の深掘り分析 |
| `grok-4` | 最高精度・高コスト | 必要な場合のみ |

---

## 料金の目安

| モデル | 入力 | 出力 |
|---|---|---|
| `grok-3-mini` | 安価（要確認） | 安価（要確認） |
| `grok-4.1-fast` | $0.20 / 100万トークン | $0.50 / 100万トークン |
| `grok-4` | $3.00 / 100万トークン | $15.00 / 100万トークン |

- **新規アカウント**: $25 の無料クレジット付与
- レート制限: `grok-4.1-fast` で 4M トークン/分、480 リクエスト/分

---

## Live Search を使った X センチメント取得（推奨実装）

Grok の `search_parameters` に `{"mode": "on"}` を指定すると、
プロンプト内容に関連する X の投稿をリアルタイムで検索した上で回答を生成します。

```python
from openai import OpenAI
import os, json

client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

def fetch_x_sentiment(news_title: str, ticker: str) -> dict:
    """
    ニュースタイトルと証券コードをもとに X のリアルタイム反応を取得する。
    Returns: {"sentiment": "強気/弱気/中立", "summary": "...", "signal_boost": "BUY/SELL/NEUTRAL"}
    """
    prompt = f"""
以下のニュースについて、現在 X（旧Twitter）で投資家・トレーダーがどう反応しているか調べてください。
- ニュース: {news_title}
- 証券コード: {ticker}

調査結果を以下の JSON 形式のみで返してください：
{{
  "sentiment": "強気 または 弱気 または 中立",
  "summary": "X上の反応を2〜3文でまとめる",
  "signal_boost": "BUY または SELL または NEUTRAL"
}}
"""
    response = client.chat.completions.create(
        model="grok-3",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        # Live Search を有効化
        extra_body={"search_parameters": {"mode": "on"}},
    )
    result = response.choices[0].message.content.strip()
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"sentiment": "中立", "summary": result, "signal_boost": "NEUTRAL"}
```

---

## 本ボットへの組み込み方針

### 推奨：Gemini + Grok のハイブリッド構成

| ステップ | 処理 | 担当 | 理由 |
|---|---|---|---|
| 1次スクリーニング | パニックスコア判定 | Ollama（無料） | コスト最小 |
| 2次判定 | BUY/SELL/HOLD 判定 | Gemini Flash | 現状維持 |
| **3次補強（新規）** | **X センチメント取得** | **Grok Live Search** | リアルタイム性 |
| 最終判定 | Gemini と Grok の結果を統合 | Gemini Flash | 最終決断 |

Grok の `signal_boost` が Gemini の `signal` と一致した場合は確信度を上げ、
逆向きだった場合は HOLD に引き下げる、といったロジックが考えられます。

### 補足：Gemini の代替としての使い方（単純差し替え）

リアルタイム性は活かせませんが、コスト比較や精度比較のために
Gemini と差し替えて使うことも可能です。

```python
# 変更前（Gemini）
from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
response = chat.send_message(prompt)
result_text = response.text

# 変更後（Grok / OpenAI互換）
from openai import OpenAI
client = OpenAI(api_key=os.environ.get("XAI_API_KEY"), base_url="https://api.x.ai/v1")
response = client.chat.completions.create(model="grok-3", messages=[...])
result_text = response.choices[0].message.content
```

---

## 実装時のチェックリスト

- [ ] [console.x.ai](https://console.x.ai) で APIキーを発行
- [ ] GitHub Secrets に `XAI_API_KEY` を追加
- [ ] `.github/workflows/trading_bot.yml` の `env` に `XAI_API_KEY` を追加
- [ ] `requirements.txt` に `openai>=1.0.0` を追加
- [ ] `src/agents/grok_agent.py` を新規作成（`gemini_agent.py` とは別ファイル推奨）
- [ ] `main.py` で Gemini の BUY/SELL 判定後に Grok センチメントを取得・統合
- [ ] `.env` に `XAI_API_KEY=...` を追加（ローカル開発用）

---

## 参考リンク

- [xAI 公式ドキュメント](https://docs.x.ai/)
- [Live Search 機能](https://docs.x.ai/docs/guides/live-search)
- [モデル一覧・料金](https://docs.x.ai/developers/models)
- [レート制限](https://docs.x.ai/docs/key-information/consumption-and-rate-limits)
- [xAI Python SDK（公式）](https://github.com/xai-org/xai-sdk-python)
