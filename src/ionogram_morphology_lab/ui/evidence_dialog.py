"""Identity-bound non-modal Evidence dialog (Phase 4C.1c)."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ionogram_morphology_lab.morphology_candidate.presentation import (
    evidence_identity_header,
    evidence_stale_banner,
    format_ledger_rows,
    ledger_headers,
)
from ionogram_morphology_lab.morphology_candidate.reviews import ledger_hash


def evidence_identity_from_result(d: Mapping[str, Any]) -> dict[str, Any]:
    ledger = d.get("evidence_ledger") or []
    return {
        "source_sha256": str(d.get("source_sha256") or ""),
        "frame_index": int(d.get("frame_index") or 0),
        "interpreted_time": str(d.get("interpreted_time") or ""),
        "diagnostics_cache_id": str(d.get("diagnostics_cache_id") or ""),
        "candidate_result_hash": str(d.get("result_hash") or ""),
        "evidence_ledger_hash": str(d.get("evidence_ledger_hash") or ledger_hash(ledger)),
        "candidate_engine_version": str(d.get("candidate_engine_version") or ""),
        "ruleset_hash": str(d.get("ruleset_hash") or ""),
        "candidate_cache_schema_version": int(d.get("candidate_cache_schema_version") or 0),
    }


class EvidenceDialog(QDialog):
    """Non-modal evidence table bound to an immutable candidate identity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.identity: dict[str, Any] = {}
        self._follow_active = True
        self._lang = "en"
        self._on_closed: Callable[[], None] | None = None

        self._layout = QVBoxLayout(self)
        self.identity_label = QLabel()
        self.identity_label.setWordWrap(True)
        self._layout.addWidget(self.identity_label)
        self.stale_label = QLabel()
        self.stale_label.setWordWrap(True)
        self.stale_label.setStyleSheet("color: #a15c00;")
        self.stale_label.hide()
        self._layout.addWidget(self.stale_label)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self._layout.addWidget(self.note)
        row = QHBoxLayout()
        self.chk_tech = QCheckBox()
        self.chk_tech.toggled.connect(self._reload_table)
        row.addWidget(self.chk_tech)
        row.addStretch(1)
        self._layout.addLayout(row)
        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self._layout.addWidget(self.table)
        self._btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self._btn_box.rejected.connect(self.reject)
        self._btn_box.accepted.connect(self.accept)
        self._layout.addWidget(self._btn_box)
        self._ledger: list = []
        self.resize(960, 540)

    def set_closed_callback(self, cb: Callable[[], None] | None) -> None:
        self._on_closed = cb

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._on_closed:
            self._on_closed()
        super().closeEvent(event)

    def bind_result(self, d: Mapping[str, Any], lang: str, *, follow_active: bool = True) -> None:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.evidence.model_update"):
            self._lang = lang
            self._follow_active = follow_active
            self.identity = evidence_identity_from_result(d)
            self._ledger = list(d.get("evidence_ledger") or [])
            ru = lang == "ru"
            self.setWindowTitle("Журнал доказательств" if ru else "Evidence ledger")
            self.identity_label.setText(evidence_identity_header(d, lang))
            self.note.setText(
                "Локализованная таблица. Канонический JSON — в меню «Ещё…»."
                if ru
                else "Localized table. Canonical JSON is available under More…"
            )
            self.chk_tech.setText(
                "Показать технические ID" if ru else "Show technical IDs"
            )
            from ionogram_morphology_lab.ui.dialog_buttons import localize_dialog_buttons

            localize_dialog_buttons(self._btn_box, lang)
            self.stale_label.hide()
            self._reload_table()

    def mark_stale(self, lang: str) -> None:
        self._follow_active = False
        frame = int(self.identity.get("frame_index") or 0)
        self.stale_label.setText(evidence_stale_banner(frame, lang))
        self.stale_label.show()

    def matches_identity(self, d: Mapping[str, Any] | None) -> bool:
        if not d:
            return False
        other = evidence_identity_from_result(d)
        keys = (
            "source_sha256",
            "frame_index",
            "diagnostics_cache_id",
            "candidate_result_hash",
            "evidence_ledger_hash",
        )
        return all(other.get(k) == self.identity.get(k) for k in keys)

    def _reload_table(self) -> None:
        show_tech = self.chk_tech.isChecked()
        rows = format_ledger_rows(self._ledger, self._lang, show_technical_ids=show_tech)
        headers = ledger_headers(self._lang)
        keys = [
            "rule",
            "feature",
            "value",
            "unit",
            "condition",
            "data_validity",
            "result",
            "effect",
            "strength",
            "explanation",
        ]
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, k in enumerate(keys):
                self.table.setItem(i, j, QTableWidgetItem(str(r.get(k, ""))))
        # Avoid resizeColumnsToContents over all rows — set sensible defaults once
        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(2, 100)
        self.table.setSortingEnabled(True)
