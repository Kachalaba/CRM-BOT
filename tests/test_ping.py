import asyncio
from unittest.mock import AsyncMock, MagicMock

import handlers


def test_ping_latency(monkeypatch):
    message = MagicMock()
    edited = {}

    async def fake_edit(text):
        edited["text"] = text

    msg = MagicMock(edit_text=AsyncMock(side_effect=fake_edit))

    async def fake_answer(text):
        assert text == "pong"
        return msg

    message.answer = AsyncMock(side_effect=fake_answer)

    ts = {"calls": 0}

    def fake_monotonic():
        ts["calls"] += 1
        return 1.0 if ts["calls"] == 1 else 1.1

    monkeypatch.setattr(handlers.time, "monotonic", fake_monotonic)

    asyncio.run(handlers.ping(message))

    assert message.answer.await_count == 1
    assert msg.edit_text.await_count == 1
    assert edited["text"].startswith("pong ")
    ms = int(edited["text"].split()[1])
    assert ms < 1500
