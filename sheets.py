import logging
import os

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_NAME = "CRM_BOT"

client = None
sheet = None
clients_sheet = None
history_sheet = None
groups_sheet = None


class SafeWorksheet:
    """Wrapper for gspread Worksheet that logs API errors."""

    def __init__(self, worksheet):
        self._worksheet = worksheet

    def __getattr__(self, name):
        attr = getattr(self._worksheet, name)
        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            try:
                return attr(*args, **kwargs)
            except APIError as err:
                if getattr(err.response, "status", None) in {403, 429}:
                    logging.warning("Sheets quota/permission error: %s", err)
                    raise RuntimeError(
                        "❗ Не вдалося зв’язатися з Google Sheets. Спробуйте пізніше."
                    ) from err
                logging.error("Sheets API error: %s", err, exc_info=True)
                raise

        return wrapper


def init_gspread(credentials_file: str) -> None:
    """Initialize Google Sheets connection."""
    global client, sheet, clients_sheet, history_sheet, groups_sheet
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"Файл {credentials_file} не знайдено.")
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPE)
    try:
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME)
        clients_sheet = SafeWorksheet(sheet.worksheet("Клієнти"))
        history_sheet = SafeWorksheet(sheet.worksheet("История"))
        groups_sheet = SafeWorksheet(sheet.worksheet("Группа"))
    except APIError as err:
        if getattr(err.response, "status", None) in {403, 429}:
            logging.warning("Sheets quota/permission error: %s", err)
            raise RuntimeError(
                "❗ Не вдалося зв’язатися з Google Sheets. Спробуйте пізніше."
            ) from err
        logging.error("Sheets API error: %s", err, exc_info=True)
        raise


def get_client_name(row):
    return (
        row.get("Ім’я")
        or row.get("Імя")
        or row.get("Имя")
        or row.get("Имʼя")
        or "Клієнт"
    )
