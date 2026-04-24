"""
Google Spreadsheet logger: appends trade inference results for post-hoc analysis.

Requires:
    - A GCP service account JSON key file (path set in GOOGLE_SERVICE_ACCOUNT_JSON)
    - The spreadsheet shared with the service account email
    - SPREADSHEET_ID set in .env
"""
import logging
import os
from datetime import datetime

import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Column headers (written once if sheet is empty)
HEADERS = [
    "日時",
    "ニュース見出し",
    "パニックスコア",
    "Geminiの判断",
    "判断理由",
    "仮想損益",
]


def _get_worksheet() -> gspread.Worksheet | None:
    """Authenticate and return the first worksheet, or None on failure."""
    json_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")

    if not json_path or not spreadsheet_id:
        logger.warning(
            "GOOGLE_SERVICE_ACCOUNT_JSON or SPREADSHEET_ID is not set. "
            "Spreadsheet logging is disabled."
        )
        return None

    creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).sheet1

    # Ensure header row exists
    if not sheet.row_values(1):
        sheet.append_row(HEADERS)

    return sheet


def append_to_sheet(data_dict: dict) -> bool:
    """
    Append a single row of trade data to the Google Spreadsheet.

    Args:
        data_dict: Expected keys:
            - news_title (str)
            - panic_score (int)
            - decision (str): "BUY" or "SKIP"
            - reason (str)
            - virtual_pnl (float | int): defaults to 0

    Returns:
        True if the row was appended successfully, False otherwise.
    """
    try:
        ws = _get_worksheet()
        if ws is None:
            return False

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data_dict.get("news_title", ""),
            data_dict.get("panic_score", ""),
            data_dict.get("decision", ""),
            data_dict.get("reason", ""),
            data_dict.get("virtual_pnl", 0),
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Spreadsheet row appended: %s", data_dict.get("news_title", ""))
        return True

    except Exception as e:
        logger.error("Failed to append to spreadsheet: %s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sample = {
        "news_title": "テスト: 日経平均が急落",
        "panic_score": 85,
        "decision": "BUY",
        "reason": "過剰反応と判断",
        "virtual_pnl": 0,
    }
    append_to_sheet(sample)
