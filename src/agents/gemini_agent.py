"""
Gemini agent: final BUY/SKIP decision based on news and panic score.
"""
import json
import logging
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"


def decide_trade_with_gemini(news_text: str, panic_score: int) -> str:
    """
    Ask Gemini to decide BUY or SKIP based on the news and primary panic score.

    Returns a JSON string. On success: {"decision": "BUY"|"SKIP", "reason": str}.
    On failure: {"error": "..."}.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set.")
        return json.dumps({"error": "GEMINI_API_KEY is not set"})

    client = genai.Client(api_key=api_key)

    prompt = f"""
あなたはプロの投資家です。以下のニュースと、一次判定スコア（パニック度）をもとに、逆張りで買うべきか（BUY）、見送るべきか（SKIP）を判断し、理由とともにJSON形式で返してください。
出力は以下のJSONフォーマットのみとし、余計な文章やマークダウンは含めないでください。

- ニュース: {news_text}
- パニック度: {panic_score}

期待する出力フォーマット:
{{
    "decision": "BUY",
    "reason": "ここに判断理由を記載"
}}
"""

    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        result_text = (response.text or "").strip()
        # Strip markdown fences if the model ignored instructions.
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()
        return result_text
    except Exception as e:
        logger.error("Error communicating with Gemini API: %s", e)
        return json.dumps({"error": f"Error communicating with Gemini API: {e}"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    test_news = "日経平均が歴史的な暴落を記録。しかし企業の業績は底堅い。"
    print(decide_trade_with_gemini(test_news, 90))
