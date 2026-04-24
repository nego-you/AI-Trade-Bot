import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# OAuth リダイレクト先が http://localhost のため必須（oauthlib の HTTPS 強制を解除）
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SHEET_RANGE = 'シート1!A1'

# スプレッドシートのヘッダー列定義
HEADERS = ['取得日時', 'ソース', 'タイトル', 'URL', '発行日時', 'パニックスコア', '判断', '理由']


def get_service():
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


def _ensure_headers(service) -> None:
    """シートが空の場合にヘッダー行を書き込む"""
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='シート1!A1:A1'
    ).execute()
    if not result.get('values'):
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=SHEET_RANGE,
            valueInputOption='USER_ENTERED',
            body={'values': [HEADERS]}
        ).execute()


def append_news_rows(news_items: list[dict]) -> bool:
    """
    ニュースアイテムのリストをスプレッドシートに一括追記する。

    Args:
        news_items: {"source", "title", "url", "published", "summary",
                     "panic_score", "decision", "reason"} のリスト
    Returns:
        True if successful, False otherwise.
    """
    if not news_items:
        return True

    try:
        service = get_service()
        _ensure_headers(service)

        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows = [
            [
                now,
                item.get('source', ''),
                item.get('title', ''),
                item.get('url', ''),
                item.get('published', ''),
                item.get('panic_score', ''),
                item.get('decision', ''),
                item.get('reason', ''),
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
