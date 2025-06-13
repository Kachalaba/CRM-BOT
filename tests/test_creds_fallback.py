import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

import main  # noqa: E402


def test_missing_credentials(monkeypatch, capsys):
    monkeypatch.delenv("CREDENTIALS_FILE", raising=False)
    monkeypatch.setenv("API_TOKEN", "1:token")
    monkeypatch.setenv("ADMIN_IDS", "1")

    called = {}

    async def fake_init(_):
        called["init"] = True

    monkeypatch.setattr(main, "init_gspread", fake_init)

    with pytest.raises(SystemExit) as exc:
        main.main()
    assert exc.value.code == 1
    assert not called
    err = capsys.readouterr().err
    assert "creds.json not found" in err
