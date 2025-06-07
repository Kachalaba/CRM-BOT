"""Simple i18n utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aiogram import types

_LOCALES: dict[str, dict[str, str]] = {}
for file in Path("locales").glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        _LOCALES[file.stem] = json.load(f)

DEFAULT_LOCALE = "ua"


def get_locale(user_id: int | None = None, lang_code: str | None = None) -> str:
    """Return locale code based on telegram language."""
    if lang_code:
        lang = lang_code.lower()
        if lang.startswith("uk") or lang.startswith("ua"):
            return "ua"
        if lang in _LOCALES:
            return lang
    return DEFAULT_LOCALE


def t(key: str, *, user: types.User | None = None, locale: str | None = None, **kwargs: Any) -> str:
    """Translate message key for the given user or locale."""
    loc = locale or get_locale(getattr(user, "id", None), getattr(user, "language_code", None))
    data = _LOCALES.get(loc, _LOCALES[DEFAULT_LOCALE])
    text = data.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text
