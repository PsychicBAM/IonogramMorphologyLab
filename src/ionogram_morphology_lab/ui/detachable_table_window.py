"""Reusable non-modal detachable inspector table window (Phase 4C.1d)."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.ui.dialog_buttons import localize_dialog_buttons


class DetachableTableWindow(QMainWindow):
    """Resizable / maximizable host for Features or Sequence results.

    Does not own scientific data — caller supplies the central widget and
    updates it when identity changes.
    """

    closed = Signal()
    pin_changed = Signal(bool)
    open_selected = Signal()

    def __init__(
        self,
        *,
        kind: str,
        title: str,
        parent=None,
        settings_get: Callable[[str, Any], Any] | None = None,
        settings_set: Callable[[str, Any], None] | None = None,
    ):
        super().__init__(parent)
        self.kind = kind
        self._settings_get = settings_get
        self._settings_set = settings_set
        self._lang = "en"
        self._pinned = False
        self._identity: dict[str, Any] = {}
        self._follow = True
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowTitle(title)
        self.resize(900, 640)

        central = QWidget()
        self.setCentralWidget(central)
        self._root = QVBoxLayout(central)
        self._root.setContentsMargins(8, 8, 8, 8)

        self.identity_label = QLabel()
        self.identity_label.setWordWrap(True)
        self._root.addWidget(self.identity_label)

        self.stale_label = QLabel()
        self.stale_label.setWordWrap(True)
        self.stale_label.setStyleSheet("color: #a15c00;")
        self.stale_label.hide()
        self._root.addWidget(self.stale_label)

        toolbar = QHBoxLayout()
        self.chk_pin = QCheckBox()
        self.chk_pin.toggled.connect(self._on_pin_toggled)
        toolbar.addWidget(self.chk_pin)
        self.btn_follow = QToolButton()
        self.btn_follow.setCheckable(True)
        self.btn_follow.setChecked(True)
        self.btn_follow.toggled.connect(self._on_follow_toggled)
        toolbar.addWidget(self.btn_follow)
        toolbar.addStretch(1)
        self._root.addLayout(toolbar)

        self.body_host = QVBoxLayout()
        self._root.addLayout(self.body_host, 1)

        self._btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self._btn_box.rejected.connect(self.close)
        self._root.addWidget(self._btn_box)

        # Persistent attribute — Escape closes this non-modal window when focused.
        self._esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._esc_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._esc_shortcut.activated.connect(self.close)

        self._restore_geometry()
        self.retranslate("en")

    def set_body_widget(self, widget: QWidget) -> None:
        while self.body_host.count():
            item = self.body_host.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self.body_host.addWidget(widget, 1)

    def set_identity(self, identity: dict[str, Any], lang: str) -> None:
        self._identity = dict(identity or {})
        self._lang = lang
        self._refresh_identity_text()

    def mark_stale(self, lang: str, message: str) -> None:
        self._lang = lang
        self.stale_label.setText(message)
        self.stale_label.show()

    def clear_stale(self) -> None:
        self.stale_label.hide()
        self.stale_label.clear()

    @property
    def pinned(self) -> bool:
        return self._pinned

    @property
    def follow_active(self) -> bool:
        return self._follow and not self._pinned

    def retranslate(self, lang: str) -> None:
        self._lang = lang
        ru = lang == "ru"
        self.chk_pin.setText("Закрепить на этом кадре" if ru else "Pin to this frame")
        self.btn_follow.setText("Следовать за кадром" if ru else "Follow current frame")
        localize_dialog_buttons(self._btn_box, lang)
        self._refresh_identity_text()

    def _refresh_identity_text(self) -> None:
        ru = self._lang == "ru"
        src = str(self._identity.get("mat_filename") or "").strip()
        if not src:
            src = str(self._identity.get("source_sha256") or "")[:12] or "—"
        frame = self._identity.get("frame_index", "—")
        time_s = str(self._identity.get("interpreted_time") or "—")
        if "T" in time_s:
            time_s = time_s.split("T", 1)[1][:5]
        ver = str(self._identity.get("feature_version") or "").strip()
        ver_s = f" · {ver}" if ver else ""
        pin = (" · закреплено" if ru else " · pinned") if self._pinned else ""
        if ru:
            self.identity_label.setText(
                f"Источник: {src} · Кадр: {frame} · Время: {time_s}{ver_s}{pin}"
            )
        else:
            self.identity_label.setText(
                f"Source: {src} · Frame: {frame} · Time: {time_s}{ver_s}{pin}"
            )

    def _on_pin_toggled(self, on: bool) -> None:
        self._pinned = bool(on)
        if on:
            self.btn_follow.setChecked(False)
            self._follow = False
        self._refresh_identity_text()
        self.pin_changed.emit(self._pinned)

    def _on_follow_toggled(self, on: bool) -> None:
        self._follow = bool(on)
        if on:
            self.chk_pin.setChecked(False)
            self._pinned = False
            self.clear_stale()
        self._refresh_identity_text()

    def _geom_key(self) -> str:
        return f"fd_detach_{self.kind}_geometry"

    def _restore_geometry(self) -> None:
        if self._settings_get is None:
            return
        raw = self._settings_get(self._geom_key(), "")
        if not raw:
            return
        try:
            self.restoreGeometry(QByteArray.fromBase64(str(raw).encode("ascii")))
        except Exception:
            pass

    def _persist_geometry(self) -> None:
        if self._settings_set is None:
            return
        try:
            self._settings_set(
                self._geom_key(),
                bytes(self.saveGeometry().toBase64()).decode("ascii"),
            )
        except Exception:
            pass

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist_geometry()
        self.closed.emit()
        super().closeEvent(event)
