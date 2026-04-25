import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
# GitHub Actions等での実行速度を考慮し軽量モデル(llama3.2)を指定
OLLAMA_MODEL = "llama3.2"

def evaluate_news_with_ollama(news_text: str) -> str:
    """
    Ask Ollama to score the panic level of a news item.
    Returns a JSON string: {"panic_score": int, "reason": str}.
    """
    system_prompt = '''あなたは優秀な金融アナリストです。
以下のニュースが株価に与える影響（パニック度）を0〜100で評価し、その理由をJSON形式で返してください。
（0: 全く影響なし, 100: 歴史的な大暴落・大高騰の可能性あり）

出力は必ず以下のJSONフォーマットのみとしてください。それ以外の文章やマークダウンを含めないでください。
{
    "panic_score": 85,
    "reason": "ここに理由を簡潔に記載"
}'''

    prompt = f"ニュース: {news_text}"

    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        req = urllib.request.Request(
            OLLAMA_URL, 
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            response_text = result.get("response", "").strip()
            
            # Markdownブロックの除去
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
                
            return response_text
    except urllib.error.URLError as e:
        logger.error(f"Error communicating with Ollama: {e}")
        return json.dumps({"error": f"Error communicating with Ollama: {e}"})
    except Exception as e:
        logger.error(f"Unexpected error with Ollama: {e}")
        return json.dumps({"error": f"Unexpected error with Ollama: {e}"})

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(evaluate_news_with_ollama("日銀が利上げを発表。為替は一気に円高に振れた。"))
