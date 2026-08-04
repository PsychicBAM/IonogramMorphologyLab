"""Dialog: add current result to owner-review dataset with separate axes."""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from ionogram_morphology_lab.review_dataset.schema import MORPHOLOGY_VALUES, ReviewLabel
from ionogram_morphology_lab.review_dataset.store import (
    ReviewDatasetSourceError,
    ReviewDatasetStore,
)


class AddToReviewDatasetDialog(QDialog):
    def __init__(self, record: dict, session, i18n, parent=None):
        super().__init__(parent)
        self.record = record
        self.session = session
        self.i18n = i18n
        ru = i18n.language == "ru"
        self.setWindowTitle(
            "Добавить в набор экспертной проверки" if ru else "Add to review dataset"
        )
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        note = QLabel(
            "Решение владельца записывается отдельно по осям. "
            "Состояние по умолчанию — «Проверено владельцем», не «Подтверждено экспертом»."
            if ru
            else "Record separate owner decisions per axis. "
            "Default state is Owner-reviewed, not Expert-confirmed."
        )
        note.setWordWrap(True)
        lay.addWidget(note)
        form = QFormLayout()
        self.morph = QComboBox()
        self.morph.addItems(list(MORPHOLOGY_VALUES))
        sci = record.get("scientific_axes") or {}
        morph0 = sci.get("morphology") or record.get("candidate_morphology") or "indeterminate"
        if morph0 == "diffuse":
            morph0 = "diffuse_unspecified"
        idx = self.morph.findText(str(morph0))
        if idx >= 0:
            self.morph.setCurrentIndex(idx)
        self.layer = QLineEdit(str(sci.get("layer") or record.get("layer") or "indeterminate"))
        self.interference = QLineEdit(
            str(record.get("interference_status") or sci.get("interference") or "none")
        )
        self.ambiguity = QLineEdit(
            str(sci.get("ambiguity") or record.get("ambiguity") or "no_visible_ambiguity")
        )
        self.quality = QLineEdit(
            str(sci.get("quality") or record.get("data_quality_status") or "ok")
        )
        self.reviewer = QLineEdit("owner")
        self.explanation = QTextEdit()
        self.explanation.setMaximumHeight(80)
        form.addRow("Morphology / Морфология", self.morph)
        form.addRow("Layer / Слой", self.layer)
        form.addRow("Interference / Помехи", self.interference)
        form.addRow("Ambiguity / Неоднозначность", self.ambiguity)
        form.addRow("Quality / Качество", self.quality)
        form.addRow("Reviewer / Рецензент", self.reviewer)
        form.addRow("Explanation / Пояснение", self.explanation)
        lay.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _save(self) -> None:
        ru = self.i18n.language == "ru"
        rec = self.record
        source_file = str(
            rec.get("source_file")
            or rec.get("source_path")
            or (self.session.active_mat or "unknown")
        )
        sha = str(
            rec.get("source_mat_sha256")
            or rec.get("source_file_sha256")
            or "0" * 64
        )
        frame_id = str(rec.get("source_frame_id") or rec.get("frame_id") or "unknown")
        label = ReviewLabel(
            morphology=self.morph.currentText(),  # type: ignore[arg-type]
            layer=self.layer.text().strip() or "indeterminate",
            interference=self.interference.text().strip() or "none",
            ambiguity=self.ambiguity.text().strip() or "no_visible_ambiguity",
            quality=self.quality.text().strip() or "ok",
            reviewer=self.reviewer.text().strip() or "owner",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            source_frame_id=frame_id,
            source_file=source_file,
            source_sha256=sha if len(sha) == 64 else ("0" * 64),
            review_state="owner-reviewed",
            explanation=self.explanation.toPlainText().strip(),
        )
        try:
            store = ReviewDatasetStore()
            store.ensure_layout()
            store.add_label(label)
        except (ReviewDatasetSourceError, ValueError) as exc:
            QMessageBox.warning(self, "IML", str(exc))
            return
        QMessageBox.information(
            self,
            "IML",
            ("Метка сохранена как «Проверено владельцем»." if ru else "Label saved as Owner-reviewed."),
        )
        self.accept()
