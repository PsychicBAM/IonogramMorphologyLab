"""Method Comparison — Python / MATLAB / ML / expert side-by-side."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class MethodComparisonPage(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self._build()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        try:
            self.title.setText(self.i18n.t("compare.title"))
        except Exception:
            self.title.setText("Сравнение методов" if ru else "Method Comparison")
        self.note.setText(
            "Строки раздельно показывают слой, морфологию, помехи и неоднозначность. "
            "Ни один метод не объявляется автоматически правильным."
            if ru
            else "Rows keep layer, morphology, parameters, interference, and ambiguity separate. "
            "No automatic declaration that one method is correct."
        )

    def _build(self) -> None:
        root = QVBoxLayout(self)
        self.title = QLabel()
        self.note = QLabel()
        self.note.setWordWrap(True)
        root.addWidget(self.title)
        root.addWidget(self.note)
        self.retranslate()
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Method",
                "Layer",
                "Morphology",
                "Alternative",
                "Interference",
                "Ambiguity",
                "Quality",
                "Status",
            ]
        )
        root.addWidget(self.table, 1)
        btn = QPushButton("Refresh from last result")
        btn.clicked.connect(self.refresh)
        root.addWidget(btn)

    def refresh(self) -> None:
        rows: list[list[str]] = []
        run = getattr(self.session, "last_run_root", None)
        if run:
            pred_dir = Path(run) / "predictions"
            files = sorted(pred_dir.glob("*.json")) if pred_dir.exists() else []
            if files:
                data = json.loads(files[-1].read_text(encoding="utf-8"))
                sci = data.get("scientific_axes") or {}
                rows.append(
                    [
                        "Built-in rules (Python)",
                        str(sci.get("layer", data.get("layer", "indeterminate"))),
                        str(sci.get("morphology", data.get("candidate_morphology", "indeterminate"))),
                        str(data.get("top_alternative_1") or ""),
                        str(data.get("interference_status") or sci.get("interference_status", "")),
                        str(sci.get("ambiguity", "")),
                        str(sci.get("quality", data.get("data_quality_status", ""))),
                        str(data.get("final_auto_status", "proposed")),
                    ]
                )
                for m in sci.get("method_comparison") or data.get("method_comparison") or []:
                    rows.append(
                        [
                            str(m.get("method", "")),
                            str(m.get("layer", "")),
                            str(m.get("morphology", "")),
                            str(m.get("alternative", "")),
                            str(m.get("interference", "")),
                            str(m.get("ambiguity", "")),
                            str(m.get("quality", "")),
                            str(m.get("status", "")),
                        ]
                    )
                # expert slot if present
                human = data.get("human_decision") or {}
                if human:
                    rows.append(
                        [
                            "Expert",
                            str(human.get("layer", "")),
                            str(human.get("morphology", human.get("label", ""))),
                            str(human.get("alternative", "")),
                            str(human.get("interference", "")),
                            str(human.get("ambiguity", "")),
                            str(human.get("quality", "")),
                            "reviewed",
                        ]
                    )
        if not rows:
            rows = [
                [
                    "Built-in rules",
                    "indeterminate",
                    "indeterminate",
                    "",
                    "low",
                    "no_visible_ambiguity",
                    "not_assessable",
                    "no_result",
                ],
                [
                    "MATLAB method",
                    "—",
                    "—",
                    "",
                    "",
                    "",
                    "",
                    "not_run",
                ],
                [
                    "ML model",
                    "—",
                    "—",
                    "",
                    "",
                    "",
                    "",
                    "development",
                ],
                [
                    "Expert",
                    "—",
                    "—",
                    "",
                    "",
                    "",
                    "",
                    "pending",
                ],
            ]
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(val))
