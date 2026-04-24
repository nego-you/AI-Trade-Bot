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

def append_to_sheet(news_title, panic_score, decision, reason, p_l=0):
    """スプレッドシートの末尾に1行追加する"""
    try:
        service = get_service()
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        values = [[now, news_title, panic_score, decision, reason, p_l]]
        
        body = {'values': values}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='シート1!A1',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        return True
    except Exception as e:
        print(f"Spreadsheet Error: {e}")
        return False
