"""
Ollama agent: scores news "panic level" (0-100) using a local LLM.
"""
import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

# Docker 内なら host.docker.internal、ローカル直接実行なら localhost
_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_URL = f"{_OLLAMA_HOST}/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "90"))


def evaluate_news_with_ollama(news_text: str) -> str:
    """
    Ask Ollama to score the panic level of a news item.

    Returns a JSON string. On success: {"panic_score": int, "reason": str}.
    On failure: {"error": "..."}.
    """
    prompt = f"""
あなたは優秀な金融アナリストです。
以下のニュースが株価に与える影響（パニック度）を0〜100で評価し、その理由をJSON形式で返してください。
（0: 全く影響なし, 100: 歴史的な大暴落・大高騰の可能性あり）

ニュース: {news_text}

出力は以下のJSONフォーマットのみとしてください。それ以外の文章は含めないでください。
{{
    "panic_score": 85,
    "reason": "ここに理由を簡潔に記載"
}}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        return response.json().get("response", "") or json.dumps(
            {"error": "Empty response from Ollama"}
        )
    except requests.RequestException as e:
        logger.error("Error communicating with Ollama API: %s", e)
        return json.dumps({"error": f"Error communicating with Ollama API: {e}"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    test_news = "日経平均株価が急落。市場は不安定な状況に。"
    print(evaluate_news_with_ollama(test_news))
