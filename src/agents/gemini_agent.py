import json
import logging
import os
import yfinance as yf
from typing import Optional, Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"

def evaluate_news_with_gemini(news_text: str) -> str:
    """
    Ask Gemini to score the panic level of a news item.

    Returns a JSON string. On success: {"panic_score": int, "reason": str}.
    On failure: {"error": "..."}.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set.")
        return json.dumps({"error": "GEMINI_API_KEY is not set"})

    client = genai.Client(api_key=api_key)

    system_instruction = """あなたは優秀な金融アナリストです。
以下のニュースが株価に与える影響（パニック度）を0〜100で評価し、その理由をJSON形式で返してください。
（0: 全く影響なし, 100: 歴史的な大暴落・大高騰の可能性あり）

出力は以下のJSONフォーマットのみとしてください。それ以外の文章やMarkdownのコードブロック(```json)は含めないでください。
{
    "panic_score": 85,
    "reason": "ここに理由を簡潔に記載"
}"""

    prompt = f"ニュース: {news_text}"

    try:
        chat = client.chats.create(model=GEMINI_MODEL, config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1
        ))
        response = chat.send_message(prompt)
        result_text = (response.text or "").strip()
        
        # Markdownが返ってきた場合は除去
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()
            
        return result_text
    except Exception as e:
        logger.error("Error communicating with Gemini API for panic score: %s", e)
        return json.dumps({"error": f"Error communicating with Gemini API: {e}"})

def search_ticker(company_name: str) -> str:
    """
    企業名から日本の証券コード（4桁）を検索するツール。
    エージェントが証券コードに確証が持てない場合に自律的に呼び出します。
    """
    # 簡易的なモックDB。将来的にはYahoo Finance API等で検索可能
    mock_db = {
        "トヨタ自動車": "7203",
        "ソフトバンクグループ": "9984",
        "ソニーグループ": "6758",
        "任天堂": "7974",
        "ファーストリテイリング": "9983",
        "三菱UFJフィナンシャル・グループ": "8306"
    }
    logger.info(f"  [Agent Tool] 証券コードを検索中... 対象: {company_name}")
    return mock_db.get(company_name, "見つかりませんでした")


def decide_trade_with_gemini(news_text: str, panic_score: int) -> str:
    """
    自律型のクオンツ・アナリスト・エージェントとしてニュースを分析し、
    企業名、証券コード、シグナル(BUY/SELL/HOLD)、理由などを返します。

    Returns a JSON string:
    {
      "company_name": "...",
      "ticker": "...",
      "signal": "BUY" | "SELL" | "HOLD",
      "reason": "...",
      "confidence": ...
    }
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set.")
        return json.dumps({"error": "GEMINI_API_KEY is not set"})

    client = genai.Client(api_key=api_key)

    system_instruction = """あなたはウォール街でトップクラスの実績を持つ、自律型のクオンツ・アナリスト・エージェントです。
あなたの任務は、入力されたニュース記事を分析し、自動売買システムのための正確な投資シグナルを生成することです。

【思考プロセス】
以下のステップに沿って段階的に思考し、結論を出してください。
1. 特定 (Identify): ニュースの主役となっている上場企業を特定する。
2. 照合 (Verify): 特定した企業の正確な「証券コード（ティッカー）」を特定する。自信がない場合や不明な場合は、必ず search_ticker ツールを使って確認すること。それでも不明な場合は null を返す。
3. 分析 (Analyze): ニュースの内容とパニック度（一次判定スコア）が今後の業績や株価に与える影響（センチメント）を客観的に評価する。
4. 決断 (Decide): 最終的な投資判断を「BUY」「SELL」「HOLD」のいずれかで下す。パニック度が高い（総悲観）状況での好材料は逆張りの「BUY」チャンスとなる可能性があります。

【判断基準】
- BUY: 明確な業績向上、新製品の成功、提携など、ポジティブなサプライズがある場合。または市場のパニック度が過剰で、実際は買い時であると判断できる場合。
- SELL: 業績悪化、不祥事、法規制の強化など、明確なネガティブ要因がある場合。
- HOLD: 影響が軽微、すでに市場に織り込み済み、または判断材料が不足している場合。

【出力要件】
最終的な結果は、以下のスキーマに従ったJSON形式のみで出力してください。余分なテキストやMarkdownのコードブロック(```json)は含めないでください。
{
  "company_name": "企業名",
  "ticker": "証券コード(文字列) または null",
  "signal": "BUY",
  "reason": "判断の根拠となる推論プロセス（2〜3文）",
  "confidence": 80,
  "holding_days": 3,
  "take_profit_pct": 12.0,
  "stop_loss_pct": 7.0
}

各フィールドの設定基準:
- holding_days: ニュースの影響が続くと予測される日数（1〜30の整数）。短期材料なら1〜3日、中期トレンドなら5〜15日、構造的変化なら20〜30日。
- take_profit_pct: このニュースの性質・ボラティリティ・確度から判断した利確目標（5.0〜30.0の正の数値）。確度が高く値幅が見込めるほど大きく設定。
- stop_loss_pct: 損切りライン（3.0〜15.0の正の数値）。リスクが高いほど小さく設定してリスクを限定する。
signal が HOLD の場合も全フィールドを出力すること（例: holding_days=1, take_profit_pct=5.0, stop_loss_pct=3.0）。"""

    prompt = f"以下のニュースと、市場のパニック度を分析してください。\n- ニュース: {news_text}\n- パニック度: {panic_score}"

    try:
        chat = client.chats.create(model=GEMINI_MODEL, config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            tools=[search_ticker]
        ))
        response = chat.send_message(prompt)
        result_text = (response.text or "").strip()
        
        # Markdownが返ってきた場合は除去
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()
            
        return result_text
    except Exception as e:
        logger.error("Error communicating with Gemini API: %s", e)
        return json.dumps({"error": f"Error communicating with Gemini API: {e}"})

def analyze_market_trends(high_panic_titles: list[str]) -> str:
    """
    高パニックニュース群（パニック度70以上）を一括分析し、注目テーマと銘柄を抽出する。

    Returns JSON:
    {"targets": [{"company_name": "...", "ticker": "...", "theme": "...", "reason": "..."}]}
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return json.dumps({"error": "GEMINI_API_KEY is not set"})

    client = genai.Client(api_key=api_key)
    news_block = "\n".join(f"- {t}" for t in high_panic_titles)

    system_instruction = """あなたはマクロ市場のトレンドを読む専門のクオンツ・ストラテジストです。
複数の重要ニュース（パニック度70以上）を俯瞰し、現在の市場で注目すべきテーマや銘柄を抽出してください。

【分析観点】
- 資金が流入しているテーマ・セクターはどこか？
- パニック・リスクが集中しているセクターはどこか？
- 上記を踏まえて今後注目すべき日本の上場企業を3〜5社挙げる。

【出力要件】
以下のJSONフォーマットのみで出力してください。余分なテキストやMarkdownは含めないでください。
{
  "targets": [
    {
      "company_name": "企業名",
      "ticker": "証券コード または null",
      "theme": "関連テーマ（例: 半導体, 防衛, AI）",
      "reason": "注目理由（1〜2文）"
    }
  ]
}"""

    prompt = f"以下の重要ニュース群を分析し、注目銘柄を抽出してください:\n{news_block}"

    try:
        chat = client.chats.create(model=GEMINI_MODEL, config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        ))
        response = chat.send_message(prompt)
        result_text = (response.text or "").strip()
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()
        return result_text
    except Exception as e:
        logger.error("Error in analyze_market_trends: %s", e)
        return json.dumps({"error": f"Error communicating with Gemini API: {e}"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    test_news = "ソニーグループは本日、新型のエンターテインメントロボットを発表。初年度の販売目標を大きく上回る予約を記録しており、来期の業績を押し上げる見込みだ。"
    print(decide_trade_with_gemini(test_news, 90))
