import json
import os
import datetime
import zoneinfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# OAuth リダイレクト先が http://localhost のため必須（oauthlib の HTTPS 強制を解除）
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SHEET_NAME = 'シート1'
SHEET_RANGE = f'{SHEET_NAME}!A1'
FOCUS_SHEET_NAME = '注目銘柄'
FOCUS_HEADERS = ['更新日時', '企業名', '証券コード', 'テーマ', '注目理由']
FOCUS_TARGETS_FILE = 'ai_focus_targets.json'
SIMULATION_SHEET_NAME = '売買シミュレーション'
SIMULATION_HEADERS = [
    '企業名', '証券コード',
    'BUY日時', 'BUY価格(円)',
    '保有予定日数', 'クローズ予定日', '利確目標(%)', '損切りライン(%)',
    'SELL日時', 'SELL理由', 'SELL価格(円)', '損益(円)', '損益(%)',
]
# 列インデックス定数（ヘッダー変更時はここだけ直す）
_SIM_COL_SELL_DATE   = 8   # I列
_SIM_COL_SELL_REASON = 9   # J列
_SIM_COL_SELL_PRICE  = 10  # K列
_SIM_COL_PROFIT_YEN  = 11  # L列
_SIM_COL_PROFIT_PCT  = 12  # M列

# 列定義（順番と名前を変えたらここだけ直す）
HEADERS = [
    '取得日時',
    'ソース',
    'タイトル',
    'URL',
    '発行日時',
    'パニックスコア',
    'パニック理由',
    '判断',
    '判断理由',
]


def get_service():
    # GitHub Actions 等の CI 環境ではサービスアカウント認証を優先する
    sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if sa_json:
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return build('sheets', 'v4', credentials=creds)

    # ローカル開発用 OAuth2 フロー
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                SCOPES,
                redirect_uri='http://localhost:8080/'
            )

            auth_url, _ = flow.authorization_url(prompt='consent')

            print("\n" + "="*60)
            print("👇 以下のURLをコピーして、ブラウザで開いてログインしてください 👇")
            print(auth_url)
            print("="*60 + "\n")
            print("⚠️ ログイン完了後、「このサイトにアクセスできません」というエラー画面になります。")
            print("⚠️ そのエラー画面の一番上にある「URL（http://localhost:8080/?state=... から始まる長い文字列）」をすべてコピーして、以下に貼り付けてください。\n")

            redirected_url = input("🔗 ここにURLを貼り付けてEnterを押す: ")

            flow.fetch_token(authorization_response=redirected_url.strip())
            creds = flow.credentials

        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("\n✅ token.json を保存しました！次回からは全自動で書き込みます。")

    return build('sheets', 'v4', credentials=creds)


def _get_first_sheet_id(service) -> int:
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    return meta['sheets'][0]['properties']['sheetId']


def _ensure_sheet_exists(service, sheet_name: str) -> None:
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    exists = any(s['properties']['title'] == sheet_name for s in meta['sheets'])
    if not exists:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        ).execute()


def _ensure_headers(service) -> None:
    """
    A1 が期待するヘッダーでない場合、先頭に1行挿入してヘッダーを書き込む。
    既存データは1行下にずれるだけで削除されない。
    """
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A1'
    ).execute()
    existing_a1 = (result.get('values') or [['']])[0][0]

    if existing_a1 == HEADERS[0]:
        return  # 既にヘッダーあり

    sheet_id = _get_first_sheet_id(service)
    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={
            'requests': [{
                'insertDimension': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': 0,
                        'endIndex': 1,
                    },
                    'inheritFromBefore': False,
                }
            }]
        }
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=SHEET_RANGE,
        valueInputOption='USER_ENTERED',
        body={'values': [HEADERS]}
    ).execute()


def append_news_rows(news_items: list[dict]) -> bool:
    """
    ニュースアイテムのリストをスプレッドシートに一括追記する。

    各 dict のキー:
        source, title, url, published  （スクレイパー由来）
        panic_score, panic_reason       （Gemini 由来）
        decision, decision_reason       （Gemini 由来）
    """
    if not news_items:
        return True

    try:
        service = get_service()
        _ensure_headers(service)

        now = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
        rows = [
            [
                now,
                item.get('source', ''),
                item.get('title', ''),
                item.get('url', ''),
                item.get('published', ''),
                item.get('panic_score', ''),
                item.get('panic_reason', ''),
                item.get('decision', ''),
                item.get('decision_reason', ''),
            ]
            for item in news_items
        ]

        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=SHEET_RANGE,
            valueInputOption='USER_ENTERED',
            body={'values': rows}
        ).execute()
        return True
    except Exception as e:
        print(f"Spreadsheet Error: {e}")
        return False


def update_focus_targets(targets: list[dict]) -> bool:
    """
    注目銘柄シートを最新内容で上書きし、ai_focus_targets.json とも同期する。

    targets の各 dict キー: company_name, ticker, theme, reason
    """
    now = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')

    # ローカルファイルへ同期（GitHub Actions では ephemeral だが参照用として残す）
    try:
        with open(FOCUS_TARGETS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"updated_at": now, "targets": targets}, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"ai_focus_targets.json 書き込み失敗: {e}")

    if not SPREADSHEET_ID:
        return False

    try:
        service = get_service()
        _ensure_sheet_exists(service, FOCUS_SHEET_NAME)

        rows = [FOCUS_HEADERS] + [
            [
                now,
                t.get('company_name', ''),
                str(t.get('ticker') or ''),
                t.get('theme', ''),
                t.get('reason', ''),
            ]
            for t in targets
        ]

        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{FOCUS_SHEET_NAME}!A:E'
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{FOCUS_SHEET_NAME}!A1',
            valueInputOption='USER_ENTERED',
            body={'values': rows}
        ).execute()
        return True
    except Exception as e:
        print(f"Focus Targets Spreadsheet Error: {e}")
        return False


def _sim_init_sheet(service) -> list:
    """シートが存在しヘッダーが正しければ現在の行リストを返す。違えば初期化して返す。"""
    _ensure_sheet_exists(service, SIMULATION_SHEET_NAME)
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SIMULATION_SHEET_NAME}!A:M'
    ).execute()
    rows = result.get('values', [])
    if not rows or rows[0] != SIMULATION_HEADERS:
        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SIMULATION_SHEET_NAME}!A:M'
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SIMULATION_SHEET_NAME}!A1',
            valueInputOption='USER_ENTERED',
            body={'values': [SIMULATION_HEADERS]}
        ).execute()
        return [SIMULATION_HEADERS]
    return rows


def _find_open_position(rows: list, ticker: str) -> dict | None:
    """SELL日時（I列=インデックス8）が空の行を検索して返す。"""
    for i, row in enumerate(rows[1:], start=2):
        if (len(row) > 1 and row[1] == ticker
                and (len(row) <= _SIM_COL_SELL_DATE or not row[_SIM_COL_SELL_DATE])):
            return {
                'sheet_row':      i,
                'buy_price':      float(row[3]) if len(row) > 3 and row[3] else 0.0,
                'take_profit_pct': float(row[6]) if len(row) > 6 and row[6] else 15.0,
                'stop_loss_pct':  float(row[7]) if len(row) > 7 and row[7] else 10.0,
                'close_date':     row[5] if len(row) > 5 else '',
                'company_name':   row[0] if row else '',
            }
    return None


def _close_position(service, pos: dict, sell_price: float, sell_reason: str, now: str) -> None:
    """オープンポジションをクローズし、SELL列（I〜M列）を書き込む。"""
    buy_price  = pos['buy_price']
    profit_yen = round(sell_price - buy_price, 1)
    profit_pct = round((sell_price - buy_price) / buy_price * 100, 2) if buy_price > 0 else 0.0
    row = pos['sheet_row']
    col_start  = chr(ord('A') + _SIM_COL_SELL_DATE)   # I
    col_end    = chr(ord('A') + _SIM_COL_PROFIT_PCT)   # M
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SIMULATION_SHEET_NAME}!{col_start}{row}:{col_end}{row}",
        valueInputOption='USER_ENTERED',
        body={'values': [[now, sell_reason, sell_price, profit_yen, profit_pct]]}
    ).execute()
    sign = "+" if profit_yen >= 0 else ""
    print(f"  [Sim] 📉 SELL({sell_reason}): {pos.get('company_name','')}({pos['sheet_row']}) "
          f"@ {sell_price:.1f}円 (損益: {sign}{profit_yen}円 / {sign}{profit_pct}%)")


def get_open_positions() -> list[dict]:
    """
    売買シミュレーションシートからオープンポジション一覧を返す。
    自動クローズチェック（main.py）から呼び出す用。
    """
    if not SPREADSHEET_ID:
        return []
    try:
        service = get_service()
        rows = _sim_init_sheet(service)
        positions = []
        for i, row in enumerate(rows[1:], start=2):
            if (len(row) > 1
                    and (len(row) <= _SIM_COL_SELL_DATE or not row[_SIM_COL_SELL_DATE])):
                positions.append({
                    'sheet_row':       i,
                    'company_name':    row[0] if len(row) > 0 else '',
                    'ticker':          row[1] if len(row) > 1 else '',
                    'buy_price':       float(row[3]) if len(row) > 3 and row[3] else 0.0,
                    'close_date':      row[5] if len(row) > 5 else '',
                    'take_profit_pct': float(row[6]) if len(row) > 6 and row[6] else 15.0,
                    'stop_loss_pct':   float(row[7]) if len(row) > 7 and row[7] else 10.0,
                })
        return positions
    except Exception as e:
        print(f"get_open_positions Error: {e}")
        return []


def close_open_position(pos: dict, sell_price: float, sell_reason: str) -> bool:
    """自動クローズ（利確・損切り・期限到来）用のクローズ関数。"""
    if not SPREADSHEET_ID:
        return False
    now = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
    try:
        service = get_service()
        _close_position(service, pos, sell_price, sell_reason, now)
        return True
    except Exception as e:
        print(f"close_open_position Error: {e}")
        return False


def record_simulation(
    company_name: str,
    ticker: str,
    decision: str,
    price: float,
    holding_days: int = 3,
    take_profit_pct: float = 15.0,
    stop_loss_pct: float = 10.0,
) -> bool:
    """
    売買シミュレーションシートを更新する。

    - BUY : オープンポジションがなければ新規行を追加（保有条件を記録）
    - SELL: オープンポジションがあれば AIシグナルとしてクローズ
    同一銘柄のオープンポジションが既存の場合のBUY、
    オープンポジションがない場合のSELLはスキップ。
    """
    if not SPREADSHEET_ID:
        return False

    import logging
    _logger = logging.getLogger(__name__)
    now = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
    jst = zoneinfo.ZoneInfo('Asia/Tokyo')

    try:
        service = get_service()
        rows = _sim_init_sheet(service)
        pos = _find_open_position(rows, ticker)

        if decision == 'BUY':
            if pos:
                _logger.info("[Sim] %s はオープンポジションあり → BUYスキップ", ticker)
                return True
            close_date = (datetime.datetime.now(jst) + datetime.timedelta(days=holding_days)).strftime('%Y-%m-%d')
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{SIMULATION_SHEET_NAME}!A1',
                valueInputOption='USER_ENTERED',
                body={'values': [[
                    company_name, ticker,
                    now, price,
                    holding_days, close_date, take_profit_pct, stop_loss_pct,
                    '', '', '', '', '',
                ]]}
            ).execute()
            print(f"  [Sim] 📈 BUY記録: {company_name}({ticker}) @ {price:.1f}円 "
                  f"[利確+{take_profit_pct}% / 損切-{stop_loss_pct}% / {holding_days}日]")

        elif decision == 'SELL':
            if not pos:
                _logger.info("[Sim] %s はオープンポジションなし → SELLスキップ", ticker)
                return True
            _close_position(service, pos, price, 'AIシグナル', now)

        return True
    except Exception as e:
        print(f"Simulation Spreadsheet Error: {e}")
        return False
