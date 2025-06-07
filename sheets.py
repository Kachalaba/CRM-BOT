import os
import gspread
from google.oauth2.service_account import Credentials

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_NAME = "CRM_BOT"

client = None
sheet = None
clients_sheet = None
history_sheet = None
groups_sheet = None

def init_gspread(credentials_file: str) -> None:
    """Initialize Google Sheets connection."""
    global client, sheet, clients_sheet, history_sheet, groups_sheet
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"Файл {credentials_file} не знайдено.")
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME)
    clients_sheet = sheet.worksheet("Клієнти")
    history_sheet = sheet.worksheet("История")
    groups_sheet = sheet.worksheet("Группа")

def get_client_name(row):
    return (
        row.get("Ім’я")
        or row.get("Імя")
        or row.get("Имя")
        or row.get("Имʼя")
        or "Клієнт"
    )
