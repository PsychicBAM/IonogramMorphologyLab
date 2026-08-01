"""Model Lab UI — train/compare development models without writing Python."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.classifiers.model_lab import (
    MODEL_KINDS,
    ModelLab,
    is_foreign_model,
)
from ionogram_morphology_lab.synthetic.generator import generate_synthetic_case
from ionogram_morphology_lab.features.extract import extract_features
import numpy as np


class ModelLabPage(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.lab = ModelLab()
        self.dataset = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.addWidget(
            QLabel(
                "Model Lab — development / research use only. "
                "Article 3 blinded labels are not used. Models are not externally validated by default."
            )
        )
        row = QHBoxLayout()
        b1 = QPushButton("Import labeled CSV…")
        b1.clicked.connect(self._import_csv)
        b2 = QPushButton("Build synthetic development set")
        b2.clicked.connect(self._build_synth_set)
        row.addWidget(b1)
        row.addWidget(b2)
        lay.addLayout(row)

        form = QFormLayout()
        self.kind = QComboBox()
        self.kind.addItems(MODEL_KINDS)
        self.split = QComboBox()
        self.split.addItems(["by_date", "random_grouped_fallback"])
        self.thr = QDoubleSpinBox()
        self.thr.setRange(0.0, 1.0)
        self.thr.setSingleStep(0.05)
        self.thr.setValue(0.45)
        form.addRow("Model", self.kind)
        form.addRow("Split", self.split)
        form.addRow("Abstention threshold", self.thr)
        lay.addLayout(form)

        train = QPushButton("Train")
        train.clicked.connect(self._train)
        lay.addWidget(train)
        self.models = QListWidget()
        lay.addWidget(self.models, 1)
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        lay.addWidget(self.out, 1)
        en = QPushButton("Enable selected model in analysis")
        en.clicked.connect(self._enable)
        lay.addWidget(en)

    def refresh(self) -> None:
        self.models.clear()
        for m in self.lab.list_models():
            origin = m.get("origin", "imported")
            trust = m.get("trust_status", "unconfirmed")
            sha256 = m.get("sha256", "missing")
            self.models.addItem(
                f"{m['model_id']} | {m['kind']} | {m['status']} | "
                f"origin={origin} | trust={trust} | sha256={sha256} | "
                f"bal_acc={m.get('metrics', {}).get('balanced_accuracy', 'n/a')}"
            )

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Labeled CSV", "", "CSV (*.csv)")
        if not path:
            return
        try:
            self.dataset = self.lab.import_labeled_csv(path)
            self.out.setPlainText(
                json.dumps(
                    {k: v for k, v in self.dataset.items() if k not in ("X", "y")},
                    indent=2,
                )
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Model Lab", str(exc))

    def _build_synth_set(self) -> None:
        """Development-only synthetic labeled set (not scientific validation)."""
        import csv
        from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

        rows = []
        mapping = {
            "horizontally_diffuse": "frequency",
            "vertically_diffuse": "range",
            "mixed_diffuse": "mixed",
            "smooth_trace": "none",
            "vertical_interference": "artifact",
            "low_signal": "none",
        }
        for i, (kind, label) in enumerate(mapping.items()):
            feats = extract_features(generate_synthetic_case(kind, seed=i)).values
            row = {"date": f"synth-day-{i%3}", "label": label, **feats}
            rows.append(row)
        path = ensure_dir(app_root() / "model_lab" / "datasets") / "synthetic_dev.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        self.dataset = self.lab.import_labeled_csv(path)
        self.out.setPlainText(
            "Synthetic development set created (NOT scientific validation).\n"
            + json.dumps({k: v for k, v in self.dataset.items() if k not in ("X", "y")}, indent=2)
        )

    def _train(self) -> None:
        if not self.dataset:
            QMessageBox.information(self, "Model Lab", "Import or build a dataset first.")
            return
        try:
            card = self.lab.train(
                self.dataset,
                kind=self.kind.currentText(),
                split_method="by_date" if self.split.currentText() == "by_date" else "random",
                abstention_threshold=self.thr.value(),
            )
            self.out.setPlainText(json.dumps(card.to_dict(), indent=2, ensure_ascii=False))
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Model Lab", str(exc))

    def _enable(self) -> None:
        item = self.models.currentItem()
        if not item:
            return
        mid = item.text().split("|")[0].strip()
        card = next(
            (m for m in self.lab.list_models() if m.get("model_id") == mid),
            None,
        )
        if card is None:
            QMessageBox.warning(self, "Model Lab", "Model card is unavailable.")
            return
        if is_foreign_model(card) or self.lab.require_trust_confirmation(mid):
            warning = card.get("foreign_warning") or (
                "This model is imported or has not been confirmed. Loading a joblib "
                "model can execute code. Only enable it if you trust its source."
            )
            answer = QMessageBox.warning(
                self,
                "Model trust confirmation",
                warning,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.lab.confirm_trust(mid)
        ids = list(self.session.settings.get("models", "enabled_model_ids", []) or [])
        if mid not in ids:
            ids.append(mid)
        self.session.settings.set("models", "enabled_model_ids", ids)
        self.session.settings.set("analysis", "ml_models_enabled", True)
        self.session.settings.save()
        QMessageBox.information(self, "Model Lab", f"Enabled development model {mid}")
