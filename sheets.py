import os
import gspread
from google.oauth2.service_account import Credentials

client = None
clients_sheet = None
history_sheet = None
groups_sheet = None

DEFAULT_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_NAME = "CRM_BOT"


def init_gspread(credentials_file: str, scope: list[str] | None = None) -> None:
    """Initialize Google Sheets connection."""
    global client, clients_sheet, history_sheet, groups_sheet
    if scope is None:
        scope = DEFAULT_SCOPE
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"Файл {credentials_file} не знайдено.")
    creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME)
    clients_sheet = sheet.worksheet("Клієнти")
    history_sheet = sheet.worksheet("История")
    groups_sheet = sheet.worksheet("Группа")

