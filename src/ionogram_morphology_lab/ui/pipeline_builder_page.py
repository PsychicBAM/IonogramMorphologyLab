"""Pipeline Builder — compose analysis stages including layer/MATLAB/rules."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

STAGES = [
    ("import", "Import", True, []),
    ("profile", "Profile", True, ["import"]),
    ("cache", "Cache", True, ["profile"]),
    ("trace", "Trace extraction", True, ["cache"]),
    ("layer_e", "E-layer detector", True, ["trace"]),
    ("layer_es", "Es detector", True, ["trace"]),
    ("layer_f1", "F1 detector", True, ["trace"]),
    ("layer_f2", "F2 detector", True, ["trace"]),
    ("interference", "Interference detector", True, ["trace"]),
    ("spread_f", "Spread-F morphology", True, ["trace"]),
    ("ox_ambiguity", "O/X ambiguity detector", True, ["trace"]),
    ("parameters", "Parameter estimator", False, ["layer_e", "layer_es", "layer_f2"]),
    ("custom_rules", "User rule pack", False, ["trace"]),
    ("matlab", "MATLAB method", False, ["cache"]),
    ("ml", "ML model", False, ["trace"]),
    ("temporal", "Temporal analyzer", False, ["cache"]),
    ("human_review", "Human review", True, []),
    ("report", "Report", True, ["human_review"]),
]


class PipelineBuilderPage(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.checks: dict[str, QCheckBox] = {}
        self._build()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        try:
            self.title.setText(self.i18n.t("pipeline.title"))
        except Exception:
            self.title.setText("Конструктор конвейера" if ru else "Pipeline Builder")
        self.note.setText(
            "Проверяйте зависимости перед включением необязательных этапов."
            if ru
            else "Validate dependencies before enabling optional stages."
        )

    def _build(self) -> None:
        root = QVBoxLayout(self)
        self.title = QLabel()
        self.note = QLabel()
        self.note.setWordWrap(True)
        root.addWidget(self.title)
        root.addWidget(self.note)
        self.retranslate()
        for key, label, default, deps in STAGES:
            cb = QCheckBox(f"{label}  (deps: {', '.join(deps) or '—'})")
            cb.setChecked(default)
            self.checks[key] = cb
            root.addWidget(cb)
        self.msg = QLabel("")
        root.addWidget(self.msg)
        row = QHBoxLayout()
        for text, slot in [
            ("Validate", self.validate),
            ("Save pipeline", self.save),
            ("Load defaults", self.reset),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        root.addLayout(row)
        root.addStretch(1)

    def validate(self) -> bool:
        enabled = {k for k, cb in self.checks.items() if cb.isChecked()}
        errors = []
        for key, label, _default, deps in STAGES:
            if key not in enabled:
                continue
            for d in deps:
                if d and d not in enabled:
                    errors.append(f"{label} requires {d}")
        if errors:
            self.msg.setText("Validation failed:\n" + "\n".join(errors))
            return False
        self.msg.setText("Pipeline dependencies OK.")
        return True

    def save(self) -> None:
        if not self.validate():
            QMessageBox.warning(self, "Pipeline", self.msg.text())
            return
        cfg = {k: cb.isChecked() for k, cb in self.checks.items()}
        path = ensure_dir(app_root() / "config") / "pipeline_v11.json"
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        if hasattr(self.session, "pipeline_config"):
            self.session.pipeline_config = cfg
        QMessageBox.information(self, "Pipeline", f"Saved {path}")

    def reset(self) -> None:
        for key, _label, default, _deps in STAGES:
            self.checks[key].setChecked(default)
        self.validate()
