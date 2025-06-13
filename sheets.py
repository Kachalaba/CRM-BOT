import logging
import os

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

load_dotenv()

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "spreadsheet_id")

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


def safe_worksheet(sheet, *candidates):
    """Return the first existing worksheet from candidates or raise."""
    for name in candidates:
        try:
            ws = sheet.worksheet(name)
            return SafeWorksheet(ws)
        except WorksheetNotFound:
            continue
    logging.error("Worksheet not found: %s", ", ".join(candidates))
    raise WorksheetNotFound(f"No worksheet from candidates: {', '.join(candidates)}")


def validate_spreadsheet(spreadsheet_id: str) -> None:
    """Check that the spreadsheet exists and log the result."""
    try:
        client.open_by_key(spreadsheet_id)
    except APIError as err:
        if getattr(err.response, "status", None) == 404:
            logging.error("\ud83d\udeab Spreadsheet ID not found: %s", spreadsheet_id)
            logging.error(
                "https://docs.google.com/spreadsheets/d/%s/edit", spreadsheet_id
            )
        raise
    logging.info("\u2705 Spreadsheet ID OK")


def init_gspread(credentials_file: str) -> None:
    """Initialize Google Sheets connection."""
    global client, sheet, clients_sheet, history_sheet, groups_sheet
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"Файл {credentials_file} не знайдено.")
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPE)
    try:
        client = gspread.authorize(creds)
        validate_spreadsheet(SPREADSHEET_ID)
        sheet = client.open_by_key(SPREADSHEET_ID)
        clients_sheet = safe_worksheet(sheet, "Клиенты", "Клієнти")
        history_sheet = safe_worksheet(sheet, "История")
        groups_sheet = safe_worksheet(sheet, "Группа")
    except SpreadsheetNotFound as err:
        logging.error("Spreadsheet not found: %s", err, exc_info=True)
        raise RuntimeError("❗ Таблицю не знайдено.") from err
    except WorksheetNotFound as err:
        logging.error("Worksheet not found: %s", err, exc_info=True)
        raise RuntimeError("❗ Лист не знайдено.") from err
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
