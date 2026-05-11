import json
import logging
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
BATCH_MODEL  = "gemini-1.5-flash"
BATCH_SIZE   = 10


def evaluate_news_with_gemini(news_text: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set.")
        return json.dumps({"error": "GEMINI_API_KEY is not set"})
    client = genai.Client(api_key=api_key)
    sys_inst = (
        "あなたは優秀な金融アナリストです。\n"
        "以下のニュースが株価に与える影響（パニック度）0～100で評価し、"
        "その理由をJSON形式で返してください。\n"
        "出力は以下のJSONのみ。Markdownのコードブロックは不要。\n"
        '{"panic_score": 85, "reason": "理由"}'
    )
    try:
        chat = client.chats.create(model=GEMINI_MODEL, config=types.GenerateContentConfig(
            system_instruction=sys_inst, temperature=0.1))
        response = chat.send_message("ニュース: " + news_text)
        t = (response.text or "").strip()
        if t.startswith("```"):
            t = t.split("```")[1].lstrip("json").strip()
        return t
    except Exception as e:
        logger.error("Gemini panic score error: %s", e)
        return json.dumps({"error": str(e)})


def search_ticker(company_name: str) -> str:
    mock_db = {
        "トヨタ自動車": "7203",
        "ソニーグループ": "6758",
        "ソフトバンクグループ": "9984",
        "任天堂": "7974",
        "ファーストリテイリング": "9983",
        "三菱UFJフィナンシャル・グループ": "8306",
    }
    logger.info("  [Agent Tool] searching ticker for: %s", company_name)
    return mock_db.get(company_name, "見つかりませんでした")


def decide_trade_with_gemini(news_text: str, panic_score: int) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return json.dumps({"error": "GEMINI_API_KEY is not set"})
    client = genai.Client(api_key=api_key)
    sys_inst = (
        "あなたはウォール街でトップクラスの実績を持つ、自律型のクオンツ・アナリスト・エージェントです。\n"
        "「ニュース」と「パニック度」を分析し、BUY/SELL/HOLDシグナルをJSON形式で返してください。\n\n"
        "《出力スキーマ》\n"
        '{"company_name":"...","ticker":"4桁 or null","signal":"BUY","reason":"...","confidence":80,'
        '"holding_days":3,"take_profit_pct":12.0,"stop_loss_pct":7.0}\n\n'
        "Markdownコードブロックは不要。証券コード不明なら search_ticker ツールを展開くこと。"
    )
    prompt = "ニュース: {news}\nパニック度: {score}".format(
        news=news_text, score=panic_score)
    try:
        chat = client.chats.create(model=GEMINI_MODEL, config=types.GenerateContentConfig(
            system_instruction=sys_inst, temperature=0.1, tools=[search_ticker]))
        response = chat.send_message(prompt)
        t = (response.text or "").strip()
        if t.startswith("```"):
            t = t.split("```")[1].lstrip("json").strip()
        return t
    except Exception as e:
        logger.error("Gemini trade decide error: %s", e)
        return json.dumps({"error": str(e)})


def decide_trade_batch_with_gemini(
    news_batch: list[dict],
    focus_targets: list[dict] | None = None,
) -> list[dict]:
    """
    Batch-judge multiple news articles in a single Gemini call.

    Args:
        news_batch    : [{"index": int, "title": str, "panic_score": int}]
        focus_targets : [{"company_name": str, "ticker": str, "theme": str}]

    Returns:
        [{"index": int, "company_name": str, "ticker": str|None,
          "signal": str, "reason": str, "confidence": int,
          "holding_days": int, "take_profit_pct": float,
          "stop_loss_pct": float}]
    """
    if not news_batch:
        return []
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set.")
        return []

    # Watch list block
    if focus_targets:
        wl = "\n".join(
            "  - {n}({t}) theme:{th}".format(
                n=t.get("company_name", ""),
                t=t.get("ticker") or "N/A",
                th=t.get("theme", ""),
            )
            for t in focus_targets
        )
        watch_block = "[WATCH LIST]\n" + wl
    else:
        watch_block = "[WATCH LIST]\n  (none)"

    # Rules (short enough to avoid truncation, using unicode escapes for long JP strings)
    # Rule 1: Association Buy
    r1 = (
        "[ルール1: 連想買い(Association Buy)を積極活用せよ]\n"
        "ニュースに直接登場しなくても、恩恵を受けるセクター・テーマを推測しWATCH LISTや日本株と紐づけてBUYを出せ。\n"
        "例: プラスチックごみ規制 -> 積水化学工業など化学・リサイクル関連をBUY"
    )
    # Rule 2: Good News Buy
    r2 = (
        "[ルール2: 順張り(Good News Buy)を積極活用せよ]\n"
        "パニックスコアが低くても(<=40)、新技術・好決算・大型提携・規制緩和・補助金などポジティブ材料があれば过らず BUY。\n"
        "「パニック低い=動かない」は禁止。好材料は順張りでBUY。"
    )
    # Rule 3: Raise HOLD threshold
    r3 = (
        "[ルール3: HOLDのハードルを最大限引き上げよ]\n"
        "「企業を特定できない」「直接関係ない」という理由のHOLDは禁止。\n"
        "市場全体（日経平均・TOPIX）でも少しでも関連するセクターがあればBUYを選ぶ。\n"
        "HOLDが許容されるのは純粋な中立材料のみ。"
    )
    # Schema example
    schema = (
        '[{"index":0,"company_name":"企業名","ticker":"4桁 or null",'
        '"signal":"BUY","reason":"根拠2~3文","confidence":75,'
        '"holding_days":3,"take_profit_pct":10.0,"stop_loss_pct":5.0}]'
    )

    sys_inst = "\n\n".join([
        (
            "あなたはウォール街でトップクラスの実績を持つ、積極的な自律型クオンツ・アナリスト・エージェントです。\n"
            "入力された複数のニュース記事を一括分析し、自動売買システムの投資シグナルをJSON配列で生成してください。"
        ),
        watch_block,
        "=== 戦略ルール（絶対遵守） ===\n\n" + r1 + "\n\n" + r2 + "\n\n" + r3,
        (
            "=== 思考プロセス（各記事に適用） ===\n"
            "1. 特定: 直接関連する上場企業を探る\n"
            "2. 連想: WATCH LISTやセクター全般との関連付けを積極的に行う\n"
            "3. センチメント: ポジティブ(BUY候補)かネガティブ(SELL候補)かを判定\n"
            "4. 決断: BUY > SELL > HOLDの優先順位で判断（HOLDは最終手段）"
        ),
        (
            "=== 出力要件 ===\n"
            "入力記事数と同じ要素数のJSON配列のみで返すこと。Markdownコードブロックは不要。\n\n"
            + schema
        ),
    ])

    article_lines = "\n".join(
        "[{idx}] panic={score:3d} | {title}".format(
            idx=item["index"], score=item["panic_score"], title=item["title"])
        for item in news_batch
    )
    prompt = (
        "{n}件のニュース記事を分析し、"
        "各記事の投資シグナルをJSON配列で返してください。\n\n"
        "記事一覧:\n{articles}"
    ).format(n=len(news_batch), articles=article_lines)

    client = genai.Client(api_key=api_key)
    result_text = ""
    try:
        chat = client.chats.create(
            model=BATCH_MODEL,
            config=types.GenerateContentConfig(system_instruction=sys_inst, temperature=0.1),
        )
        response = chat.send_message(prompt)
        result_text = (response.text or "").strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1].lstrip("json").strip()
        parsed = json.loads(result_text)
        if isinstance(parsed, list):
            return parsed
        logger.warning("decide_trade_batch: expected list, got %s", type(parsed))
        return []
    except json.JSONDecodeError as e:
        logger.error("decide_trade_batch JSON parse error: %s | raw: %.200s", e, result_text)
        return []
    except Exception as e:
        logger.error("decide_trade_batch Gemini error: %s", e)
        return []


def analyze_market_trends(high_panic_titles: list[str]) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return json.dumps({"error": "GEMINI_API_KEY is not set"})
    client = genai.Client(api_key=api_key)
    news_block = "\n".join("- " + t for t in high_panic_titles)
    sys_inst = (
        "あなたはマクロ市場のトレンドを読む専門のクオンツ・ストラテジストです。\n"
        "複数の重要ニュース（パニック度70以上）を俦瞰し、現在の市場で注目すべきテーマや銀柄を抽出してください。\n"
        "出力は以下のJSONのみ。Markdownコードブロック不要。\n"
        '{"targets":[{"company_name":"...","ticker":"... or null","theme":"...","reason":"..."}]}'
    )
    prompt = "以下の重要ニュース群を分析し、注目銀柄を抽出してください:\n" + news_block
    try:
        chat = client.chats.create(model=GEMINI_MODEL, config=types.GenerateContentConfig(
            system_instruction=sys_inst, temperature=0.2))
        response = chat.send_message(prompt)
        t = (response.text or "").strip()
        if t.startswith("```"):
            t = t.split("```")[1].lstrip("json").strip()
        return t
    except Exception as e:
        logger.error("Error in analyze_market_trends: %s", e)
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    test = (
        "ソニーグループは本日、新型のエンターテインメントロボットを発表。"
        "初年度の販売目標を大きく上回る予約を記録しており、来期の業績を押し上げる見込みだ。"
    )
    print(decide_trade_with_gemini(test, 90))
