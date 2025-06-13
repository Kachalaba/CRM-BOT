import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from gspread.exceptions import APIError

import sheets


class Resp:
    def __init__(self, status: int):
        self.status = status
        self.reason = ""
        self.headers = {}
        self.text = "error"

    def json(self):
        return {"error": {"message": "test"}}


def make_error(status: int) -> APIError:
    return APIError(Resp(status))


@patch("sheets.os.path.exists", return_value=True)
@patch("sheets.Credentials")
@patch("sheets.AsyncioGspreadClientManager")
def test_quota_error(mock_mgr, mock_creds, mock_exists, caplog):
    mock_ws = MagicMock()
    mock_ws.get_all_records = AsyncMock(side_effect=make_error(429))
    mock_sheet = MagicMock()
    mock_sheet.worksheet = AsyncMock(return_value=mock_ws)
    mock_client = MagicMock()
    mock_client.open_by_key = AsyncMock(return_value=mock_sheet)
    mock_mgr.return_value.authorize = AsyncMock(return_value=mock_client)
    mock_creds.from_service_account_file.return_value = "creds"

    asyncio.run(sheets.init_gspread("creds.json"))

    with caplog.at_level(logging.WARNING):
        result = asyncio.run(sheets.clients_sheet.get_all_records())
    assert result is None
    assert any(rec.levelno == logging.WARNING for rec in caplog.records)


@patch("sheets.os.path.exists", return_value=True)
@patch("sheets.Credentials")
@patch("sheets.AsyncioGspreadClientManager")
def test_unknown_error(mock_mgr, mock_creds, mock_exists, caplog):
    mock_ws = MagicMock()
    mock_ws.get_all_records = AsyncMock(side_effect=make_error(500))
    mock_sheet = MagicMock()
    mock_sheet.worksheet = AsyncMock(return_value=mock_ws)
    mock_client = MagicMock()
    mock_client.open_by_key = AsyncMock(return_value=mock_sheet)
    mock_mgr.return_value.authorize = AsyncMock(return_value=mock_client)
    mock_creds.from_service_account_file.return_value = "creds"

    asyncio.run(sheets.init_gspread("creds.json"))

    with caplog.at_level(logging.ERROR):
        result = asyncio.run(sheets.clients_sheet.get_all_records())
    assert result is None
    assert any(rec.levelno == logging.ERROR for rec in caplog.records)
