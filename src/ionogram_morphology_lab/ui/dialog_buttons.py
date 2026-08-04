"""Localize standard QDialogButtonBox buttons (Phase 4C.1d)."""

from __future__ import annotations

from PySide6.QtWidgets import QDialogButtonBox


_LABELS = {
    QDialogButtonBox.StandardButton.Close: {"ru": "Закрыть", "en": "Close"},
    QDialogButtonBox.StandardButton.Cancel: {"ru": "Отмена", "en": "Cancel"},
    QDialogButtonBox.StandardButton.Save: {"ru": "Сохранить", "en": "Save"},
    QDialogButtonBox.StandardButton.Ok: {"ru": "OK", "en": "OK"},
    QDialogButtonBox.StandardButton.Yes: {"ru": "Да", "en": "Yes"},
    QDialogButtonBox.StandardButton.No: {"ru": "Нет", "en": "No"},
}


def localize_dialog_buttons(box: QDialogButtonBox, lang: str) -> None:
    """Set RU/EN text on known standard buttons (no scientific side effects)."""
    for std, labels in _LABELS.items():
        btn = box.button(std)
        if btn is not None:
            btn.setText(labels.get(lang, labels["en"]))
