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
