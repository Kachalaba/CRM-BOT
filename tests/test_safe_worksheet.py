import logging
from unittest.mock import MagicMock

import pytest
from gspread.exceptions import WorksheetNotFound

import sheets


def test_first_candidate():
    ws = MagicMock()
    sheet = MagicMock(worksheet=MagicMock(return_value=ws))
    result = sheets.safe_worksheet(sheet, "Клиенты", "Клієнти")
    assert isinstance(result, sheets.SafeWorksheet)
    sheet.worksheet.assert_called_once_with("Клиенты")
    assert result._worksheet is ws


def test_fallback_candidate():
    ws = MagicMock()
    sheet = MagicMock()
    sheet.worksheet.side_effect = [WorksheetNotFound("no"), ws]
    result = sheets.safe_worksheet(sheet, "Клиенты", "Клієнти")
    assert result._worksheet is ws
    assert sheet.worksheet.call_count == 2
    sheet.worksheet.assert_any_call("Клиенты")
    sheet.worksheet.assert_any_call("Клієнти")


def test_no_candidate(caplog):
    sheet = MagicMock()
    sheet.worksheet.side_effect = WorksheetNotFound("no")
    with caplog.at_level(logging.ERROR):
        with pytest.raises(WorksheetNotFound):
            sheets.safe_worksheet(sheet, "A", "B")
    assert any("Worksheet not found" in rec.message for rec in caplog.records)
