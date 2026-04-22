import os
import json
from dotenv import load_dotenv  # 追加: dotenvの読み込み
from google import genai

load_dotenv()  # 追加: .envファイルの中身をシステムに読み込ませる

def decide_trade_with_gemini(news_text, panic_score):
    """
    最新の公式SDK (google-genai) を使用して、Geminiで最終判断を行う関数
    """
    # Dockerの環境変数からAPIキーを取得
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return json.dumps({"error": "GEMINI_API_KEY is not set"})

    # 新しいGenAIクライアントの初期化
    client = genai.Client(api_key=api_key)
    
    # Geminiに与えるプロンプト（指示書）
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
        # Gemini 1.5 Flashモデルを呼び出し
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # 結果のテキストを取得し、念のためMarkdown記法(```json)が含まれていたら除去する
        result_text = response.text.strip()
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()
            
        return result_text
        
    except Exception as e:
        return json.dumps({"error": f"Error communicating with Gemini API: {e}"})

# ファイル直接実行時のテスト用
if __name__ == "__main__":
    test_news = "日経平均が歴史的な暴落を記録。しかし企業の業績は底堅い。"
    print(decide_trade_with_gemini(test_news, 90))