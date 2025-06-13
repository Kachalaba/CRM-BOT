import asyncio
from unittest.mock import AsyncMock, MagicMock

import handlers


def test_stats_caching(monkeypatch):
    message = MagicMock()
    message.from_user.id = 42
    result = {}

    async def fake_answer(text):
        result.setdefault("texts", []).append(text)

    message.answer = AsyncMock(side_effect=fake_answer)

    records = [{"ID": "42", "К-сть тренувань": 3}]
    sheet = MagicMock(get_all_records=MagicMock(return_value=records))
    monkeypatch.setattr(handlers.sheets, "clients_sheet", sheet)

    now = [0.0]
    monkeypatch.setattr(handlers.time, "monotonic", lambda: now[0])

    handlers.STATS_CACHE.clear()

    asyncio.run(handlers.stats(message))
    assert result["texts"][-1] == "У тебя 3 оставшихся"
    assert sheet.get_all_records.call_count == 1

    now[0] += 10
    asyncio.run(handlers.stats(message))
    assert sheet.get_all_records.call_count == 1
    assert result["texts"][-1] == "У тебя 3 оставшихся"

    now[0] += 31
    records[0]["К-сть тренувань"] = 4
    asyncio.run(handlers.stats(message))
    assert sheet.get_all_records.call_count == 2
    assert result["texts"][-1] == "У тебя 4 оставшихся"
