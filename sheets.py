import json
import logging
import os
from typing import Any

from aiohttp import ClientError
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from gspread_asyncio import (
    AsyncioGspreadClientManager,
    AsyncioGspreadSpreadsheet,
    AsyncioGspreadWorksheet,
)

logger = logging.getLogger(__name__)

load_dotenv()

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

agcm: AsyncioGspreadClientManager | None = None
client: AsyncioGspreadSpreadsheet | None = None
sheet: AsyncioGspreadSpreadsheet | None = None
clients_sheet: "SafeWorksheet | None" = None
history_sheet: "SafeWorksheet | None" = None
groups_sheet: "SafeWorksheet | None" = None


def get_google_credentials() -> Credentials:
    """Return Google service account credentials from the environment."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("Змінна GOOGLE_CREDENTIALS_JSON не задана у файлі .env!")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict)
    return creds.with_scopes(SCOPE)


class SafeWorksheet:
    """Wrapper for AsyncioGspreadWorksheet that logs API errors."""

    def __init__(self, worksheet: AsyncioGspreadWorksheet) -> None:
        self._worksheet = worksheet

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._worksheet, name)
        if not callable(attr):
            return attr

        async def wrapper(*args: Any, **kwargs: Any):
            default = None
            try:
                return await attr(*args, **kwargs)
            except APIError as err:
                status = getattr(err.response, "status", None)
                if status in {403, 429}:
                    logger.warning("Sheets quota/permission error: %s", err)
                else:
                    logger.error("Sheets API error: %s", err, exc_info=True)
                return default
            except ClientError as err:
                logger.error("Sheets network error: %s", err, exc_info=True)
                return default
            except Exception as err:  # pragma: no cover - unexpected errors
                logger.error("Sheets unexpected error: %s", err, exc_info=True)
                return default

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
    logger.error("Worksheet not found: %s", ", ".join(candidates))
    raise WorksheetNotFound(f"No worksheet from candidates: {', '.join(candidates)}")


async def validate_spreadsheet(spreadsheet_id: str) -> None:
    """Check that the spreadsheet exists and log the result."""
    try:
        await client.open_by_key(spreadsheet_id)
    except APIError as err:
        if getattr(err.response, "status", None) == 404:
            logger.error("🚫 Spreadsheet ID not found: %s", spreadsheet_id)
            logger.error(
                "https://docs.google.com/spreadsheets/d/%s/edit", spreadsheet_id
            )
        raise
    logger.info("✅ Spreadsheet ID OK")


async def init_gspread(sheet_id: str) -> None:
    """Initialize Google Sheets connection."""
    global agcm, client, sheet, clients_sheet, history_sheet, groups_sheet

    creds = get_google_credentials()
    agcm = AsyncioGspreadClientManager(lambda: creds)
    try:
        client = await agcm.authorize()
        await validate_spreadsheet(sheet_id)
        sheet = await client.open_by_key(sheet_id)
        clients_sheet = await safe_worksheet(sheet, "Клиенты", "Клієнти")
        history_sheet = await safe_worksheet(sheet, "История")
        groups_sheet = await safe_worksheet(sheet, "Группа")
    except SpreadsheetNotFound as err:
        logger.error("Spreadsheet not found: %s", err, exc_info=True)
        raise RuntimeError("❗ Таблицю не знайдено.") from err
    except WorksheetNotFound as err:
        logger.error("Worksheet not found: %s", err, exc_info=True)
        raise RuntimeError("❗ Лист не знайдено.") from err
    except APIError as err:
        if getattr(err.response, "status", None) in {403, 429}:
            logger.warning("Sheets quota/permission error: %s", err)
            raise RuntimeError(
                "❗ Не вдалося зв’язатися з Google Sheets. Спробуйте пізніше."
            ) from err
        logger.error("Sheets API error: %s", err, exc_info=True)
        raise


def get_client_name(row: dict) -> str:
    return (
        row.get("Ім’я")
        or row.get("Імя")
        or row.get("Имя")
        or row.get("Имʼя")
        or "Клієнт"
    )
