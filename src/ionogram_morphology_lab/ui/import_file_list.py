"""Structured imported-MAT rows for the Import Data page (Phase 4B.2d)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.ui.source_roles import (
    SourceClassification,
    classify_mat_source,
    localize_badge,
    localize_role_message,
)
from ionogram_morphology_lab.ui.theme import refresh_themed_widget, resolve_theme_name, source_card_tokens


class ImportFileRow(QFrame):
    """One imported MAT with per-file actions."""

    action = Signal(str, str)  # action_key, path

    def __init__(self, path: Path, i18n, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.path = Path(path)
        self._cls: SourceClassification | None = None
        self._is_active = False
        self._theme_pref = "system"
        self.setObjectName("ImportFileRow")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        top = QHBoxLayout()
        self.name = QLabel()
        self.name.setStyleSheet("font-weight:700;")
        self.badge = QLabel()
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.name, 1)
        top.addWidget(self.badge)
        root.addLayout(top)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setVisible(False)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.details)
        row = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        for key in (
            "set_active",
            "unset_active",
            "open",
            "remove",
            "open_folder",
            "tech",
            "choose_compatible",
        ):
            b = QPushButton()
            b.clicked.connect(lambda _=False, k=key: self._on_click(k))
            self.buttons[key] = b
            row.addWidget(b)
        row.addStretch(1)
        root.addLayout(row)
        self.apply_theme("system")
        self.retranslate()

    def _on_click(self, key: str) -> None:
        if key == "tech":
            self.details.setVisible(not self.details.isVisible())
            return
        self.action.emit(key, str(self.path))

    def apply_theme(self, preference: str | None = None) -> None:
        self._theme_pref = preference or self._theme_pref or "system"
        refresh_themed_widget(self, "ImportFileRow", self._theme_pref)

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        labels = {
            "set_active": "Активировать для анализа" if ru else "Activate for Analysis",
            "unset_active": "Отключить от анализа" if ru else "Deactivate for Analysis",
            "open": "Открыть" if ru else "Open",
            "remove": "Убрать из проекта" if ru else "Remove from Project",
            "open_folder": "Открыть папку" if ru else "Open Folder",
            "tech": "Технические сведения" if ru else "Technical Details",
            "choose_compatible": localize_role_message("choose_compatible", self.i18n.language),
        }
        for k, b in self.buttons.items():
            b.setText(labels[k])
        if self._cls is not None:
            self.update_classification(self._cls, is_active=self._is_active)

    def update_classification(self, cls: SourceClassification, *, is_active: bool) -> None:
        self._cls = cls
        self._is_active = is_active
        ru = self.i18n.language == "ru"
        theme = resolve_theme_name(self._theme_pref)
        tokens = source_card_tokens(theme)
        missing = not self.path.is_file()
        badge_key = cls.badge_key(is_active=is_active, file_missing=missing)
        self.name.setText(self.path.name)
        self.badge.setText(localize_badge(badge_key, self.i18n.language))
        bg = {
            "active": tokens["badge_active_bg"],
            "inactive": tokens["badge_inactive_bg"],
            "auxiliary": tokens["badge_aux_bg"],
            "incompatible": tokens["badge_bad_bg"],
            "unavailable": tokens["badge_bad_bg"],
        }[badge_key]
        fg = {
            "active": tokens["badge_active_fg"],
            "inactive": tokens["badge_inactive_fg"],
            "auxiliary": tokens["badge_aux_fg"],
            "incompatible": tokens["badge_bad_fg"],
            "unavailable": tokens["badge_bad_fg"],
        }[badge_key]
        self.badge.setStyleSheet(
            f"background:{bg}; color:{fg}; padding:2px 8px; border-radius:3px; font-weight:600;"
        )
        vars_s = ", ".join(cls.variables[:8]) if cls.variables else "—"
        self.summary.setText(
            f"{'Тип' if ru else 'Product'}: {cls.product_type or '—'} | "
            f"{'Статус' if ru else 'Status'}: {cls.audit_status or '—'} | "
            f"{'Форма' if ru else 'Shape'}: {cls.shape or '—'}\n"
            f"{'Переменные' if ru else 'Variables'}: {vars_s}"
        )
        if not cls.can_activate and cls.reason_code == "missing_amp_all":
            self.summary.setText(
                self.summary.text()
                + "\n"
                + localize_role_message("missing_amp_all", self.i18n.language, variable=cls.primary_variable)
            )
        self.details.setText(
            f"path: {self.path}\n"
            f"role: {cls.role.value}\n"
            f"contract: {cls.contract_id or '—'} (ok={cls.contract_ok})\n"
            f"dtype: {cls.dtype or '—'} | can_activate={cls.can_activate}\n"
            f"reason: {cls.reason_code} {cls.reason_detail}"
        )
        # Action visibility
        self.buttons["set_active"].setVisible(cls.can_activate and not is_active and not missing)
        self.buttons["unset_active"].setVisible(is_active and not missing)
        self.buttons["open"].setVisible(cls.can_activate)
        self.buttons["choose_compatible"].setVisible(not cls.can_activate and not missing)
        self.buttons["remove"].setVisible(True)
        self.buttons["open_folder"].setVisible(True)


class ImportFileList(QWidget):
    """Scrollable list of ImportFileRow widgets."""

    action = Signal(str, str)

    def __init__(self, i18n, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self._theme_pref = "system"
        self._rows: dict[str, ImportFileRow] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.host = QWidget()
        self.host_lay = QVBoxLayout(self.host)
        self.host_lay.addStretch(1)
        self.scroll.setWidget(self.host)
        lay.addWidget(self.scroll, 1)
        self.retranslate()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self.hint.setText(
            "Импортированные MAT-файлы проекта. Действия доступны у каждой записи."
            if ru
            else "Imported project MAT files. Actions are available on each entry."
        )
        for row in self._rows.values():
            row.retranslate()

    def apply_theme(self, preference: str | None = None) -> None:
        self._theme_pref = preference or self._theme_pref or "system"
        for row in self._rows.values():
            row.apply_theme(self._theme_pref)

    def rebuild(self, paths: list[Path], profile: dict, active: Path | None) -> None:
        # Remove stale rows
        keep = {str(Path(p)) for p in paths}
        for key in list(self._rows):
            if key not in keep:
                w = self._rows.pop(key)
                self.host_lay.removeWidget(w)
                w.deleteLater()
        active_res = None
        if active is not None:
            try:
                active_res = Path(active).resolve()
            except OSError:
                active_res = Path(active)
        for path in paths:
            p = Path(path)
            key = str(p)
            if key not in self._rows:
                row = ImportFileRow(p, self.i18n)
                row.action.connect(self.action.emit)
                row.apply_theme(self._theme_pref)
                self._rows[key] = row
                self.host_lay.insertWidget(self.host_lay.count() - 1, row)
            cls = classify_mat_source(p, profile, try_frame=False)
            is_active = False
            if active is not None:
                try:
                    is_active = p.resolve() == active_res
                except OSError:
                    is_active = p == Path(active)
            self._rows[key].path = p
            self._rows[key].update_classification(cls, is_active=is_active)
