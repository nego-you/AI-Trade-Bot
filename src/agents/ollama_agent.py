import requests
import json

def evaluate_news_with_ollama(news_text):
    """
    Ollama APIを叩いて、ニュースのパニック度を評価する関数
    """
    url = "http://host.docker.internal:11434/api/generate"
    
    # AIに与える指示（プロンプト）
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

    # Ollamaに送るデータ（ペイロード）
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False,  # 一括で結果を受け取るためにFalse
        "format": "json"  # OllamaにJSON形式での出力を強制する機能
    }

    try:
        # ホスト側のOllamaにリクエストを送信
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()  # 400や500エラーがあればここでキャッチ
        
        # 成功した場合、レスポンスの文字列をパースして返す
        result_json = response.json()
        return result_json.get("response", "")
        
    except Exception as e:
        return {"error": f"Error communicating with Ollama API: {e}"}

# ファイル直接実行時のテスト用
if __name__ == "__main__":
    test_news = "日経平均株価が急落。市場は不安定な状況に。"
    print(evaluate_news_with_ollama(test_news))