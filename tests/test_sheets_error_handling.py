import logging
from unittest.mock import MagicMock, patch

import pytest
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
@patch("sheets.gspread.authorize")
def test_quota_error(mock_auth, mock_creds, mock_exists, caplog):
    mock_ws = MagicMock()
    mock_ws.get_all_records.side_effect = make_error(429)
    mock_sheet = MagicMock()
    mock_sheet.worksheet.return_value = mock_ws
    mock_client = MagicMock(open_by_key=MagicMock(return_value=mock_sheet))
    mock_auth.return_value = mock_client
    mock_creds.from_service_account_file.return_value = "creds"

    sheets.init_gspread("creds.json")

    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError):
            sheets.clients_sheet.get_all_records()
    assert any(rec.levelno == logging.WARNING for rec in caplog.records)


@patch("sheets.os.path.exists", return_value=True)
@patch("sheets.Credentials")
@patch("sheets.gspread.authorize")
def test_unknown_error(mock_auth, mock_creds, mock_exists, caplog):
    mock_ws = MagicMock()
    mock_ws.get_all_records.side_effect = make_error(500)
    mock_sheet = MagicMock()
    mock_sheet.worksheet.return_value = mock_ws
    mock_client = MagicMock(open_by_key=MagicMock(return_value=mock_sheet))
    mock_auth.return_value = mock_client
    mock_creds.from_service_account_file.return_value = "creds"

    sheets.init_gspread("creds.json")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(APIError):
            sheets.clients_sheet.get_all_records()
    assert any(rec.levelno == logging.ERROR for rec in caplog.records)
