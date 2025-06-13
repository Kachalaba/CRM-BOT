import logging
import os
from typing import Any

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from gspread_asyncio import (
    AsyncioGspreadClientManager,
    AsyncioGspreadSpreadsheet,
    AsyncioGspreadWorksheet,
)

load_dotenv()

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "spreadsheet_id")

agcm: AsyncioGspreadClientManager | None = None
client: AsyncioGspreadSpreadsheet | None = None
sheet: AsyncioGspreadSpreadsheet | None = None
clients_sheet: "SafeWorksheet | None" = None
history_sheet: "SafeWorksheet | None" = None
groups_sheet: "SafeWorksheet | None" = None


class SafeWorksheet:
    """Wrapper for AsyncioGspreadWorksheet that logs API errors."""

    def __init__(self, worksheet: AsyncioGspreadWorksheet) -> None:
        self._worksheet = worksheet

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._worksheet, name)
        if not callable(attr):
            return attr

        async def wrapper(*args: Any, **kwargs: Any):
            try:
                return await attr(*args, **kwargs)
            except APIError as err:
                if getattr(err.response, "status", None) in {403, 429}:
                    logging.warning("Sheets quota/permission error: %s", err)
                    raise RuntimeError(
                        "❗ Не вдалося зв’язатися з Google Sheets. Спробуйте пізніше."
                    ) from err
                logging.error("Sheets API error: %s", err, exc_info=True)
                raise

        return wrapper


async def safe_worksheet(
    sheet: AsyncioGspreadSpreadsheet, *candidates: str
) -> SafeWorksheet:
    """Return the first existing worksheet from candidates or raise."""
    for name in candidates:
        try:
            ws = await sheet.worksheet(name)
            return SafeWorksheet(ws)
        except WorksheetNotFound:
            continue
    logging.error("Worksheet not found: %s", ", ".join(candidates))
    raise WorksheetNotFound(f"No worksheet from candidates: {', '.join(candidates)}")


async def validate_spreadsheet(spreadsheet_id: str) -> None:
    """Check that the spreadsheet exists and log the result."""
    try:
        await client.open_by_key(spreadsheet_id)
    except APIError as err:
        if getattr(err.response, "status", None) == 404:
            logging.error("🚫 Spreadsheet ID not found: %s", spreadsheet_id)
            logging.error(
                "https://docs.google.com/spreadsheets/d/%s/edit", spreadsheet_id
            )
        raise
    logging.info("✅ Spreadsheet ID OK")


async def init_gspread(credentials_file: str) -> None:
    """Initialize Google Sheets connection."""
    global agcm, client, sheet, clients_sheet, history_sheet, groups_sheet

    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"Файл {credentials_file} не знайдено.")

    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPE)
    agcm = AsyncioGspreadClientManager(lambda: creds)
    try:
        client = await agcm.authorize()
        await validate_spreadsheet(SPREADSHEET_ID)
        sheet = await client.open_by_key(SPREADSHEET_ID)
        clients_sheet = await safe_worksheet(sheet, "Клиенты", "Клієнти")
        history_sheet = await safe_worksheet(sheet, "История")
        groups_sheet = await safe_worksheet(sheet, "Группа")
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


def get_client_name(row: dict) -> str:
    return (
        row.get("Ім’я")
        or row.get("Імя")
        or row.get("Имя")
        or row.get("Имʼя")
        or "Клієнт"
    )
