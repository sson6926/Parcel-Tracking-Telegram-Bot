from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class I18n:
    def __init__(self, translations_dir: Path | str | None = None) -> None:
        if translations_dir is None:
            translations_dir = Path(__file__).resolve().parent.parent / "i18n"
        self.translations_dir = Path(translations_dir)
        self._data: dict[str, dict[str, Any]] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self.translations_dir.exists():
            return
        for lang_file in self.translations_dir.glob("*.json"):
            lang_code = lang_file.stem
            try:
                content = json.loads(lang_file.read_text(encoding="utf-8"))
                self._data[lang_code] = content
            except Exception:
                pass

    def supported_languages(self) -> list[str]:
        return sorted(self._data.keys())

    def normalize_lang(self, lang_code: str | None) -> str:
        if not lang_code:
            return "vi"
        normalized = lang_code.lower()[:2]
        if normalized in self._data:
            return normalized
        return "vi"

    def language_name(self, lang_code: str, current_lang: str) -> str:
        normalized = self.normalize_lang(lang_code)
        data = self._data.get(normalized, {})
        meta = data.get("meta", {})
        if isinstance(meta, dict):
            return meta.get("name", normalized)
        return normalized

    def has_key(self, key: str, lang: str) -> bool:
        normalized_lang = self.normalize_lang(lang)
        data = self._data.get(normalized_lang, {})
        messages = data.get("messages", {})
        return key in messages

    def t(self, key: str, lang: str, **kwargs: Any) -> str:
        normalized_lang = self.normalize_lang(lang)
        data = self._data.get(normalized_lang, {})
        messages = data.get("messages", {})
        text = messages.get(key, key)

        for placeholder, value in kwargs.items():
            text = text.replace(f"{{{placeholder}}}", str(value))

        return text

    def status(self, status_code: str, lang: str) -> str:
        normalized_lang = self.normalize_lang(lang)
        data = self._data.get(normalized_lang, {})
        statuses = data.get("status", {})
        return statuses.get(status_code, status_code)
