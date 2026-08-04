"""Model Lab UI — train/compare development models without writing Python."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.classifiers.model_lab import (
    MODEL_KINDS,
    ModelLab,
    ModelLabValidationError,
    is_foreign_model,
)
from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.synthetic.generator import generate_synthetic_case
from ionogram_morphology_lab.ui.empty_state import EmptyStatePanel


class ModelLabPage(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.lab = ModelLab()
        self.dataset = None
        self._build()
        self.refresh()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self.banner.setText(
            "Model Lab — только для разработки/исследований. "
            "Слепые метки статьи 3 не используются. Модели по умолчанию не прошли внешнюю валидацию."
            if ru
            else "Model Lab — development / research use only. "
            "Article 3 blinded labels are not used. Models are not externally validated by default."
        )
        self.btn_import.setText("Импорт размеченного CSV…" if ru else "Import labeled CSV…")
        self.btn_synth.setText(
            "Собрать синтетический набор для разработки"
            if ru
            else "Build synthetic development set"
        )
        self.form_labels["model"].setText("Модель" if ru else "Model")
        self.form_labels["split"].setText("Разбиение" if ru else "Split")
        self.form_labels["thr"].setText("Порог воздержания" if ru else "Abstention threshold")
        self.btn_train.setText("Обучить" if ru else "Train")
        self.btn_enable.setText(
            "Включить выбранную модель в анализ" if ru else "Enable selected model in analysis"
        )
        self.empty.configure(
            title="Лаборатория моделей" if ru else "Model Lab",
            why=(
                "Пока нет размеченного набора и обученных моделей."
                if ru
                else "No labeled dataset or trained models are available yet."
            ),
            prereq=(
                "Импортируйте CSV или соберите синтетический набор, затем нажмите «Обучить»."
                if ru
                else "Import a CSV or build a synthetic set, then click Train."
            ),
            after=(
                "После обучения здесь появятся карточки моделей и метрики разработки."
                if ru
                else "After training, model cards and development metrics appear here."
            ),
            action="Собрать синтетический набор" if ru else "Build synthetic set",
            nav_key="",
        )
        self.empty.action_btn.clicked.disconnect()
        self.empty.action_btn.clicked.connect(self._build_synth_set)
        self.empty.action_btn.setVisible(True)
        self.empty.setVisible(self.models.count() == 0 and self.dataset is None)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        lay.addWidget(self.banner)
        self.empty = EmptyStatePanel()
        lay.addWidget(self.empty)
        row = QHBoxLayout()
        self.btn_import = QPushButton()
        self.btn_import.clicked.connect(self._import_csv)
        self.btn_synth = QPushButton()
        self.btn_synth.clicked.connect(self._build_synth_set)
        row.addWidget(self.btn_import)
        row.addWidget(self.btn_synth)
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
        self.form_labels = {
            "model": QLabel(),
            "split": QLabel(),
            "thr": QLabel(),
        }
        form.addRow(self.form_labels["model"], self.kind)
        form.addRow(self.form_labels["split"], self.split)
        form.addRow(self.form_labels["thr"], self.thr)
        lay.addLayout(form)

        self.btn_train = QPushButton()
        self.btn_train.clicked.connect(self._train)
        lay.addWidget(self.btn_train)
        self.models = QListWidget()
        lay.addWidget(self.models, 1)
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        lay.addWidget(self.out, 1)
        self.btn_enable = QPushButton()
        self.btn_enable.clicked.connect(self._enable)
        lay.addWidget(self.btn_enable)
        self.retranslate()

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
        if hasattr(self, "empty"):
            self.empty.setVisible(self.models.count() == 0 and self.dataset is None)

    def _import_csv(self) -> None:
        ru = self.i18n.language == "ru"
        path, _ = QFileDialog.getOpenFileName(
            self, "Размеченный CSV" if ru else "Labeled CSV", "", "CSV (*.csv)"
        )
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
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            if isinstance(exc, ModelLabValidationError):
                message = exc.message_ru if ru else exc.message_en
            QMessageBox.warning(self, "Model Lab", message)

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
        ru = self.i18n.language == "ru"
        if not self.dataset:
            QMessageBox.information(
                self,
                "Model Lab",
                "Сначала импортируйте или соберите набор данных."
                if ru
                else "Import or build a dataset first.",
            )
            return
        try:
            self._run_training(allow_imputation=False)
        except ModelLabValidationError as exc:
            self._handle_validation_error(exc)
        except Exception as exc:  # noqa: BLE001
            self.out.setPlainText(
                ("Технические детали:\n" if ru else "Technical details:\n") + f"{exc!r}"
            )
            QMessageBox.warning(
                self,
                "Model Lab",
                "Обучение не завершено. См. технические детали в панели вывода."
                if ru
                else "Training could not be completed. See Technical details in the output panel.",
            )

    def _run_training(self, *, allow_imputation: bool) -> None:
        card = self.lab.train(
            self.dataset,
            kind=self.kind.currentText(),
            split_method="by_date" if self.split.currentText() == "by_date" else "random",
            abstention_threshold=self.thr.value(),
            allow_imputation=allow_imputation,
        )
        self.out.setPlainText(json.dumps(card.to_dict(), indent=2, ensure_ascii=False))
        self.refresh()

    def _handle_validation_error(self, exc: ModelLabValidationError) -> None:
        """Show a localized explanation first; raw technical text stays in the report."""
        report = {
            "validation_error": {
                "code": exc.code,
                "message_en": exc.message_en,
                "message_ru": exc.message_ru,
                "details": exc.details,
                "technical": exc.technical,
            }
        }
        self.out.setPlainText(
            "Dataset quality report\n" + json.dumps(report, indent=2, ensure_ascii=False, default=str)
        )
        message = exc.message_ru if self.i18n.language == "ru" else exc.message_en
        if exc.code != "missing_values_detected":
            QMessageBox.warning(self, "Model Lab", message)
            return
        prompt = (
            f"{message}\n\n"
            + (
                "Отчёт о качестве открыт в нижней панели. Применить документированную "
                "медианную импутацию с индикаторами пропусков?"
                if self.i18n.language == "ru"
                else "The quality report is open below. Apply documented median imputation "
                "with missing-value indicators?"
            )
        )
        answer = QMessageBox.question(
            self,
            "Model Lab",
            prompt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self._run_training(allow_imputation=True)
            except ModelLabValidationError as retry_error:
                self._handle_validation_error(retry_error)
            except Exception as retry_error:  # noqa: BLE001
                self.out.append(f"\nTechnical details:\n{retry_error!r}")
                QMessageBox.warning(
                    self,
                    "Model Lab",
                    "Training could not be completed. See Technical details in the quality report.",
                )

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
