"""Scientific status labels for automatic vs reviewed results."""

from __future__ import annotations

from typing import Any


def scientific_status_token(record: dict[str, Any], review_state: str | None = None) -> str:
    state = (review_state or record.get("review_state") or "").strip().lower()
    if state == "expert-confirmed":
        return "expert-confirmed"
    if state in ("owner-reviewed", "owner_reviewed"):
        return "owner-reviewed"
    return "automatic-candidate"


def scientific_status_label(token: str, lang: str = "en") -> str:
    ru = lang == "ru"
    if token == "expert-confirmed":
        return "Подтверждено экспертом" if ru else "Expert-confirmed"
    if token == "owner-reviewed":
        return "Проверено владельцем" if ru else "Owner-reviewed"
    return "Автоматический кандидат" if ru else "Automatic candidate"


def insufficient_examples_message(lang: str = "en") -> str:
    if lang == "ru":
        return "Для этой категории пока недостаточно проверенных реальных примеров."
    return "Insufficient reviewed real examples are available for this category."
