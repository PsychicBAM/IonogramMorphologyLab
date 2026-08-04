"""Structured expert / owner decision dialog — no free-text canonical tokens."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)

MORPHOLOGY_CHOICES = (
    ("clean", "Явное рассеяние не обнаружено", "No visible spread"),
    ("diffuse_unspecified", "Наблюдается диффузная структура, тип не определён", "Diffuse structure visible; spread type undetermined"),
    ("frequency_spread", "Возможно частотное F-рассеяние", "Possible frequency Spread-F"),
    ("range_spread", "Возможно высотное F-рассеяние", "Possible range Spread-F"),
    ("mixed_spread", "Возможно смешанное F-рассеяние", "Possible mixed Spread-F"),
    ("not_assessable", "Кадр невозможно надёжно оценить", "Frame not reliably assessable"),
    ("indeterminate", "Неопределённо", "Indeterminate"),
    ("other_morphology", "Другая морфология", "Other morphology"),
)

REVIEW_STATES = (
    ("unverified", "Не проверено", "Unverified"),
    ("owner-reviewed", "Проверено владельцем", "Owner-reviewed"),
    ("expert-confirmed", "Подтверждено экспертом", "Expert-confirmed"),
)


class ExpertDecisionDialog(QDialog):
    def __init__(self, record: dict, i18n, parent=None):
        super().__init__(parent)
        self.record = record
        self.i18n = i18n
        ru = i18n.language == "ru"
        self.setWindowTitle("Решение эксперта / владельца" if ru else "Expert / owner decision")
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        note = QLabel(
            "Выберите канонические категории из списка. Произвольные токены недоступны. "
            "Статус «Подтверждено экспертом» назначается только вручную."
            if ru
            else "Choose canonical categories from the list. Free-text tokens are not allowed. "
            "Expert-confirmed is never assigned automatically."
        )
        note.setWordWrap(True)
        lay.addWidget(note)
        form = QFormLayout()
        sci = record.get("scientific_axes") or {}
        self.morph = QComboBox()
        for token, ru_lab, en_lab in MORPHOLOGY_CHOICES:
            self.morph.addItem(ru_lab if ru else en_lab, token)
        morph0 = sci.get("morphology") or record.get("candidate_morphology") or "indeterminate"
        if morph0 == "diffuse":
            morph0 = "diffuse_unspecified"
        idx = self.morph.findData(morph0)
        if idx >= 0:
            self.morph.setCurrentIndex(idx)
        inter_labels = {
            "none": ("нет", "none"),
            "present": ("присутствуют", "present"),
            "significant": ("значительные", "significant"),
            "dominant": ("доминируют", "dominant"),
            "prevents_assessment": ("мешают оценке", "prevents assessment"),
        }
        self.interference = QComboBox()
        for token, (ru_lab, en_lab) in inter_labels.items():
            self.interference.addItem(ru_lab if ru else en_lab, token)
        inter0 = record.get("interference_status") or "none"
        ii = self.interference.findData(inter0)
        if ii >= 0:
            self.interference.setCurrentIndex(ii)
        layer_labels = {
            "indeterminate": ("неопределён", "indeterminate"),
            "E": ("E", "E"),
            "Es": ("Es", "Es"),
            "F1": ("F1", "F1"),
            "F2": ("F2", "F2"),
            "F_unspecified": ("F (не уточнён)", "F unspecified"),
            "other": ("другой", "other"),
        }
        self.layer = QComboBox()
        for token, (ru_lab, en_lab) in layer_labels.items():
            self.layer.addItem(ru_lab if ru else en_lab, token)
        li = self.layer.findData(sci.get("layer") or "indeterminate")
        if li >= 0:
            self.layer.setCurrentIndex(li)
        amb_labels = {
            "no_visible_ambiguity": ("явной неоднозначности нет", "no visible ambiguity"),
            "possible_ox": ("возможна O/X", "possible O/X"),
            "layer_uncertain": ("слой неясен", "layer uncertain"),
            "other": ("другое", "other"),
        }
        self.ambiguity = QComboBox()
        for token, (ru_lab, en_lab) in amb_labels.items():
            self.ambiguity.addItem(ru_lab if ru else en_lab, token)
        ai = self.ambiguity.findData(sci.get("ambiguity") or "no_visible_ambiguity")
        if ai >= 0:
            self.ambiguity.setCurrentIndex(ai)
        qual_labels = {
            "valid": ("пригодно", "valid"),
            "warning": ("предупреждение", "warning"),
            "not_assessable": ("не оценивается", "not assessable"),
            "low_signal": ("слабый сигнал", "low signal"),
        }
        self.quality = QComboBox()
        for token, (ru_lab, en_lab) in qual_labels.items():
            self.quality.addItem(ru_lab if ru else en_lab, token)
        qi = self.quality.findData(sci.get("quality") or record.get("data_quality_status") or "valid")
        if qi >= 0:
            self.quality.setCurrentIndex(qi)
        self.review_state = QComboBox()
        for token, ru_lab, en_lab in REVIEW_STATES:
            self.review_state.addItem(ru_lab if ru else en_lab, token)
        # Default owner-reviewed — never auto expert-confirmed.
        self.review_state.setCurrentIndex(1)
        self.rationale = QTextEdit()
        self.rationale.setMaximumHeight(90)
        self.uncertainty = QTextEdit()
        self.uncertainty.setMaximumHeight(60)
        self.alternatives = QTextEdit()
        self.alternatives.setMaximumHeight(60)
        form.addRow("Морфология" if ru else "Morphology", self.morph)
        form.addRow("Помехи" if ru else "Interference", self.interference)
        form.addRow("Слой" if ru else "Layer", self.layer)
        form.addRow("Неоднозначность" if ru else "Ambiguity", self.ambiguity)
        form.addRow("Качество" if ru else "Quality", self.quality)
        form.addRow("Статус проверки" if ru else "Review status", self.review_state)
        form.addRow("Обоснование *" if ru else "Rationale *", self.rationale)
        form.addRow("Неопределённость" if ru else "Uncertainty", self.uncertainty)
        form.addRow("Альтернативы" if ru else "Alternatives", self.alternatives)
        lay.addLayout(form)
        tech = QGroupBox("Technical tokens" if not ru else "Технические токены")
        tech.setCheckable(True)
        tech.setChecked(False)
        tlay = QVBoxLayout(tech)
        self.tech_label = QLabel()
        self.tech_label.setWordWrap(True)
        tlay.addWidget(self.tech_label)
        lay.addWidget(tech)
        self.morph.currentIndexChanged.connect(self._refresh_tech)
        self._refresh_tech()
        self.error = QLabel()
        self.error.setStyleSheet("color:#a00;")
        lay.addWidget(self.error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _refresh_tech(self) -> None:
        self.tech_label.setText(
            f"morphology={self.morph.currentData()}\n"
            f"interference={self.interference.currentData()}\n"
            f"layer={self.layer.currentData()}\n"
            f"ambiguity={self.ambiguity.currentData()}\n"
            f"quality={self.quality.currentData()}\n"
            f"review_state={self.review_state.currentData()}"
        )

    def _accept(self) -> None:
        ru = self.i18n.language == "ru"
        if not self.rationale.toPlainText().strip():
            self.error.setText(
                "Обоснование обязательно." if ru else "Rationale is required."
            )
            return
        self.accept()

    def decision(self) -> dict:
        alts = [
            a.strip()
            for a in self.alternatives.toPlainText().replace(",", "\n").splitlines()
            if a.strip()
        ]
        return {
            "morphology": self.morph.currentData(),
            "interference": self.interference.currentData(),
            "layer": self.layer.currentData(),
            "ambiguity": self.ambiguity.currentData(),
            "quality": self.quality.currentData(),
            "review_state": self.review_state.currentData(),
            "rationale": self.rationale.toPlainText().strip(),
            "uncertainty": self.uncertainty.toPlainText().strip(),
            "alternatives": alts,
        }
