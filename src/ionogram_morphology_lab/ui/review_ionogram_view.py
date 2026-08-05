"""Embedded read-only ionogram for blind Expert Review (Phase 4C.2a)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from ionogram_morphology_lab.ui.active_source import paths_equal
from ionogram_morphology_lab.ui.fd_display import gray_to_qimage, scientific_to_display_gray

_LOG = logging.getLogger("iml.review_ionogram")


class ReviewIonogramView(QWidget):
    """Displays exactly one source SHA + frame; rejects stale identity mismatches."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.badge = QLabel()
        self.badge.setWordWrap(True)
        lay.addWidget(self.badge)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll.setWidget(self.image)
        lay.addWidget(self.scroll, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self._bound_sha = ""
        self._bound_frame = -1
        self._request_gen = 0

    def clear(self, message: str = "") -> None:
        self._bound_sha = ""
        self._bound_frame = -1
        self.image.clear()
        self.badge.setText("")
        self.status.setText(message)

    def show_identity_badge(
        self,
        *,
        display_name: str,
        frame_index: int,
        frame_time: str,
        source_sha256: str,
        lang: str = "en",
    ) -> None:
        short = (source_sha256 or "")[:12]
        if lang == "ru":
            self.badge.setText(
                f"Источник: {display_name} | кадр {frame_index} | "
                f"время {frame_time or '—'} | SHA {short}"
            )
        else:
            self.badge.setText(
                f"Source: {display_name} | frame {frame_index} | "
                f"time {frame_time or '—'} | SHA {short}"
            )

    def load_item(
        self,
        session: Any,
        *,
        source_sha256: str,
        frame_index: int,
        expected_path: Path | str | None = None,
        display_name: str = "",
        frame_time: str = "",
        lang: str = "en",
    ) -> bool:
        """Hydrate exact SHA/frame. Returns True if identity verified and image shown."""
        self._request_gen += 1
        gen = self._request_gen
        sha = (source_sha256 or "").lower()
        frame = int(frame_index)
        self.show_identity_badge(
            display_name=display_name or "—",
            frame_index=frame,
            frame_time=frame_time,
            source_sha256=sha,
            lang=lang,
        )
        try:
            store = None
            if hasattr(session, "ensure_store"):
                try:
                    store = session.ensure_store()
                except RuntimeError as exc:
                    self.clear(
                        "Источник недоступен."
                        if lang == "ru"
                        else f"Source unavailable: {exc}"
                    )
                    return False
            if store is None:
                self.clear("No frame store" if lang == "en" else "Нет кэша кадров")
                return False
            store_sha = (getattr(store, "source_sha256", "") or "").lower()
            if sha and store_sha and store_sha != sha:
                # Valid multi-source campaigns: resolve registered inventory path by SHA
                # and activate it. Genuine unregistered SHAs remain blocked.
                resolved = False
                try:
                    from ionogram_morphology_lab.morphology_review_campaign.project_sources import (
                        find_path_by_sha,
                    )

                    alt = find_path_by_sha(session, sha)
                    if alt is not None and hasattr(session, "set_active_mat"):
                        session.set_active_mat(alt)
                        if hasattr(session, "ensure_store"):
                            store = session.ensure_store()
                            store_sha = (getattr(store, "source_sha256", "") or "").lower()
                            if not store_sha and hasattr(session, "get_source_sha"):
                                store_sha = str(
                                    session.get_source_sha(allow_compute=True) or ""
                                ).lower()
                            resolved = bool(store_sha and store_sha == sha)
                except Exception:
                    resolved = False
                if not resolved:
                    _LOG.warning(
                        "review identity mismatch item_sha=%s store_sha=%s",
                        sha[:12],
                        store_sha[:12],
                    )
                    self.clear(
                        "Несовпадение SHA источника — отображение заблокировано."
                        if lang == "ru"
                        else "Source SHA mismatch — display blocked."
                    )
                    return False
            if expected_path is not None and not paths_equal(
                getattr(store, "source_path", None), expected_path
            ):
                # Soft check: path may differ by resolve; SHA is authoritative
                if not store_sha:
                    self.clear(
                        "Путь источника не совпадает."
                        if lang == "ru"
                        else "Source path mismatch."
                    )
                    return False
            if gen != self._request_gen:
                return False
            raw = np.asarray(store.get_frame(frame, prefetch=False))
            if gen != self._request_gen:
                return False
            u8 = scientific_to_display_gray(raw)
            pix = QPixmap.fromImage(gray_to_qimage(u8))
            self.image.setPixmap(pix)
            self._bound_sha = store_sha or sha
            self._bound_frame = frame
            self.status.setText(
                "Кандидат скрыт (слепой режим)."
                if lang == "ru"
                else "Candidate hidden (blind mode)."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("review ionogram load failed")
            self.clear(str(exc))
            return False

    def identity_matches(self, source_sha256: str, frame_index: int) -> bool:
        sha = (source_sha256 or "").lower()
        if self._bound_frame != int(frame_index):
            return False
        if sha and self._bound_sha and self._bound_sha != sha:
            return False
        return self._bound_frame >= 0
