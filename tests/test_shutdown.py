import asyncio
import logging
import signal
from unittest.mock import AsyncMock, MagicMock

import handlers
import main
import sheets


def test_shutdown(monkeypatch):
    called = {}

    async def fake_stop():
        called["stop"] = True

    monkeypatch.setattr(handlers.dp, "stop_polling", fake_stop)

    sheets.client = MagicMock()

    msgs = []
    monkeypatch.setattr(logging, "info", lambda msg: msgs.append(msg))

    asyncio.run(main.shutdown())

    assert called.get("stop")
    assert "Bot stopped" in msgs


def test_main_signal_shutdown(monkeypatch):
    loop = asyncio.new_event_loop()
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: loop)
    monkeypatch.setattr(asyncio, "run", lambda coro: loop.run_until_complete(coro))

    handlers_store = {}

    def add_sig(sig, cb):
        handlers_store[sig] = cb

    loop.add_signal_handler = add_sig

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", "c")
    monkeypatch.setenv("ADMIN_ID", "1")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet")

    monkeypatch.setattr(main.os.path, "exists", lambda path: True)

    async def fake_init(*_):
        return None

    monkeypatch.setattr(main, "init_gspread", fake_init)
    monkeypatch.setattr(handlers.dp, "start_polling", AsyncMock())

    stopped = {}

    async def fake_stop_polling():
        stopped["called"] = True

    monkeypatch.setattr(handlers.dp, "stop_polling", fake_stop_polling)

    sheets.client = MagicMock()

    msgs = []
    monkeypatch.setattr(logging, "info", lambda msg: msgs.append(msg))

    main.main()

    assert signal.SIGINT in handlers_store
    loop.call_soon(handlers_store[signal.SIGINT])
    loop.run_until_complete(asyncio.sleep(0))

    assert stopped.get("called")
    assert "Bot stopped" in msgs
