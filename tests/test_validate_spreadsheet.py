import logging
from unittest.mock import MagicMock

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


def test_validate_ok(caplog):
    mock_client = MagicMock(open_by_key=MagicMock())
    sheets.client = mock_client
    with caplog.at_level(logging.INFO):
        sheets.validate_spreadsheet("abc")
    mock_client.open_by_key.assert_called_once_with("abc")
    assert any("Spreadsheet ID OK" in rec.message for rec in caplog.records)


def test_validate_not_found(caplog):
    mock_client = MagicMock(open_by_key=MagicMock(side_effect=make_error(404)))
    sheets.client = mock_client
    with caplog.at_level(logging.ERROR):
        with pytest.raises(APIError):
            sheets.validate_spreadsheet("abc")
    assert any("Spreadsheet ID not found" in rec.message for rec in caplog.records)
    assert any(
        "https://docs.google.com/spreadsheets/d/abc/edit" in rec.message
        for rec in caplog.records
    )
