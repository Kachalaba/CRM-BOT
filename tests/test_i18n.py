# isort:skip_file
import sys
from pathlib import Path
import asyncio
from unittest.mock import AsyncMock, MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import handlers  # noqa: E402
from utils import i18n  # noqa: E402


def test_help_ua(monkeypatch):
    user = MagicMock(language_code="uk", id=1)
    message = MagicMock(from_user=user)
    result = {}

    async def fake_answer(text):
        result["text"] = text

    message.answer = AsyncMock(side_effect=fake_answer)

    asyncio.run(handlers.send_help(message))

    assert result["text"] == i18n.t("/help", user=user)
