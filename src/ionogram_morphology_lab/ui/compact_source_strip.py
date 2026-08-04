"""Compact active-source strip for work pages (Phase 4B.2g)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.ui.active_source import ActiveSourceSnapshot, SourceStatus
from ionogram_morphology_lab.ui.theme import resolve_theme_name, source_card_tokens


class CompactSourceStrip(QWidget):
    """One-line source identity + Change / Import / Technical details."""

    action = Signal(str)

    def __init__(self, i18n, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self._snap = ActiveSourceSnapshot()
        self._theme_pref = "system"
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 2, 4, 2)
        root.setSpacing(2)
        row = QHBoxLayout()
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        row.addWidget(self.summary, 1)
        self.btn_change = QPushButton()
        self.btn_import = QPushButton()
        self.btn_tech = QToolButton()
        self.btn_tech.setCheckable(True)
        self.btn_change.clicked.connect(lambda: self.action.emit("pick_from_project"))
        self.btn_import.clicked.connect(lambda: self.action.emit("open_import"))
        self.btn_tech.toggled.connect(self._toggle_tech)
        for b in (self.btn_change, self.btn_import, self.btn_tech):
            row.addWidget(b)
        root.addLayout(row)
        self.tech = QLabel()
        self.tech.setWordWrap(True)
        self.tech.setVisible(False)
        root.addWidget(self.tech)
        self.retranslate()

    def apply_theme(self, preference: str | None = None) -> None:
        self._theme_pref = preference or self._theme_pref or "system"
        theme = resolve_theme_name(self._theme_pref)
        tokens = source_card_tokens(theme)
        self.setStyleSheet(
            f"background:{tokens['bg_alt']}; border:1px solid {tokens['border']};"
            f" color:{tokens['text']};"
        )

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self.btn_change.setText("Сменить" if ru else "Change")
        self.btn_import.setText("Открыть импорт" if ru else "Open Import")
        self.btn_tech.setText("Технические сведения" if ru else "Technical details")
        self.apply_snapshot(self._snap)

    def _toggle_tech(self, on: bool) -> None:
        self.tech.setVisible(on)

    def apply_snapshot(self, snap: ActiveSourceSnapshot) -> None:
        self._snap = snap
        ru = self.i18n.language == "ru"
        if not snap.project_open:
            self.summary.setText("Нет открытого проекта." if ru else "No project is open.")
            self.tech.clear()
            return
        if not snap.is_active or snap.mat_path is None:
            self.summary.setText(
                "Активный источник не выбран." if ru else "No active source selected."
            )
            self.tech.clear()
            return
        status = {
            SourceStatus.READY: ("источник готов" if ru else "source ready"),
            SourceStatus.MISSING: ("файл недоступен" if ru else "file missing"),
            SourceStatus.INCOMPATIBLE: ("несовместим" if ru else "incompatible"),
            SourceStatus.UNAVAILABLE: ("недоступен" if ru else "unavailable"),
        }.get(snap.status, snap.status.value)
        self.summary.setText(
            f"{snap.mat_filename} • "
            f"{'кадр' if ru else 'frame'} {snap.frame} • "
            f"{snap.interpreted_time or '—'} • {status}"
        )
        sha = (snap.source_sha256[:16] + "…") if snap.source_sha256 else "—"
        self.tech.setText(
            f"SHA: {sha} | {'Профиль' if ru else 'Profile'}: {snap.profile_id} | "
            f"contract: {snap.signal_contract_id} | path: {snap.mat_path}"
        )
