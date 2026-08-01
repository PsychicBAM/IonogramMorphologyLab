"""Translation loader — canonical scientific values remain English internally."""

from __future__ import annotations

import json
from pathlib import Path

_I18N_DIR = Path(__file__).resolve().parent


class I18n:
    def __init__(self, language: str = "en"):
        self.language = "ru" if language == "ru" else "en"
        self._data = self._load(self.language)

    def _load(self, lang: str) -> dict[str, str]:
        path = _I18N_DIR / f"{lang}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def set_language(self, language: str) -> None:
        self.language = "ru" if language == "ru" else "en"
        self._data = self._load(self.language)

    def t(self, key: str, default: str | None = None) -> str:
        return self._data.get(key, default if default is not None else key)

    def keys(self) -> list[str]:
        return sorted(self._data.keys())


_GLOBAL: I18n | None = None


def get_i18n(language: str | None = None) -> I18n:
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = I18n(language or "en")
    elif language is not None:
        _GLOBAL.set_language(language)
    return _GLOBAL
