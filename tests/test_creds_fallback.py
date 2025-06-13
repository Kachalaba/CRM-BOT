import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

import main  # noqa: E402


def test_missing_credentials(monkeypatch, capsys):
    monkeypatch.delenv("GOOGLE_CREDENTIALS_JSON", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1:token")
    monkeypatch.setenv("ADMIN_ID", "1")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet")

    with pytest.raises(ValueError) as exc:
        main.main()
    assert "GOOGLE_CREDENTIALS_JSON" in str(exc.value)
