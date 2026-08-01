"""Ionogram Parameters / Параметры ионограммы — candidate estimates only."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.scientific_outputs.taxonomy import ParameterEstimate
from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

# Catalog of known parameters with honest implementation state (no unexplained empties).
PARAMETER_CATALOG = [
    {"name": "foE", "unit": "MHz", "state": "profile_dependent", "note_en": "Requires E-trace candidate + verified frequency axis.", "note_ru": "Нужен кандидат трассы E и проверенная ось частоты."},
    {"name": "h'E", "unit": "km (nominal virtual)", "state": "profile_dependent", "note_en": "Nominal virtual height only; not true height.", "note_ru": "Только номинальная виртуальная высота, не истинная."},
    {"name": "foEs", "unit": "MHz", "state": "profile_dependent", "note_en": "Es frequency candidate when Es detector fires.", "note_ru": "Кандидат частоты Es при срабатывании детектора Es."},
    {"name": "h'Es", "unit": "km (nominal virtual)", "state": "profile_dependent", "note_en": "Nominal virtual height candidate for Es.", "note_ru": "Кандидат номинальной виртуальной высоты Es."},
    {"name": "fbEs", "unit": "MHz", "state": "source_disabled", "note_en": "Blanketing-frequency candidate disabled until source-verified method is active.", "note_ru": "Кандидат частоты бланкетинга отключён до активации верифицированного метода."},
    {"name": "foF1", "unit": "MHz", "state": "profile_dependent", "note_en": "Only when F1 is separable; else F_unspecified.", "note_ru": "Только при отделении F1; иначе F_unspecified."},
    {"name": "h'F1", "unit": "km (nominal virtual)", "state": "profile_dependent", "note_en": "Nominal virtual height; profile-dependent.", "note_ru": "Номинальная виртуальная высота; зависит от профиля."},
    {"name": "foF2", "unit": "MHz", "state": "profile_dependent", "note_en": "Image-estimated candidate when F2 detector quality is sufficient.", "note_ru": "Кандидат по изображению при достаточном качестве детектора F2."},
    {"name": "fxF2", "unit": "MHz", "state": "source_disabled", "note_en": "Requires O/X-capable measurements; not confirmed from Amp_all alone.", "note_ru": "Требуются измерения с разделением O/X; Amp_all сам по себе недостаточен."},
    {"name": "h'F2", "unit": "km (nominal virtual)", "state": "profile_dependent", "note_en": "Nominal virtual height candidate for F2.", "note_ru": "Кандидат номинальной виртуальной высоты F2."},
]


class ParametersPage(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self._rows: list[ParameterEstimate] = []
        self._build()
        self.refresh_catalog()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        self.title = QLabel()
        self.blurb = QLabel()
        self.blurb.setWordWrap(True)
        root.addWidget(self.title)
        root.addWidget(self.blurb)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Parameter", "State", "Value", "Unit", "Method", "Calibration", "Expert", "Limitation"]
        )
        root.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.btn_load = QPushButton()
        self.btn_load.clicked.connect(self.load_from_result)
        self.btn_accept = QPushButton()
        self.btn_accept.clicked.connect(lambda: self._set_expert("accepted"))
        self.btn_reject = QPushButton()
        self.btn_reject.clicked.connect(lambda: self._set_expert("rejected"))
        self.btn_ind = QPushButton()
        self.btn_ind.clicked.connect(lambda: self._set_expert("indeterminate"))
        self.btn_save = QPushButton()
        self.btn_save.clicked.connect(self._save)
        for b in (self.btn_load, self.btn_accept, self.btn_reject, self.btn_ind, self.btn_save):
            row.addWidget(b)
        root.addLayout(row)
        self.retranslate()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self.title.setText("Параметры ионограммы" if ru else "Ionogram Parameters")
        self.blurb.setText(
            "Значения — кандидаты по изображению, не подтверждённые измерения ионозонда. "
            "Пустые поля без объяснения не показываются: у каждого параметра есть состояние реализации."
            if ru
            else "Values are image-estimated candidates, not confirmed ionosonde measurements. "
            "Empty unexplained fields are not shown; every parameter has an implementation state."
        )
        self.btn_load.setText("Загрузить из результата" if ru else "Load from last result")
        self.btn_accept.setText("Принять" if ru else "Accept")
        self.btn_reject.setText("Отклонить" if ru else "Reject")
        self.btn_ind.setText("Неопределённо" if ru else "Indeterminate")
        self.btn_save.setText("Сохранить решение эксперта" if ru else "Save expert edits")
        headers = (
            ["Параметр", "Состояние", "Значение", "Ед.", "Метод", "Калибровка", "Эксперт", "Ограничение"]
            if ru
            else ["Parameter", "State", "Value", "Unit", "Method", "Calibration", "Expert", "Limitation"]
        )
        for i, h in enumerate(headers):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(h))

    def refresh_catalog(self) -> None:
        """Show catalog with explicit states — never unexplained empties."""
        ru = self.i18n.language == "ru"
        estimates: list[ParameterEstimate] = []
        for item in PARAMETER_CATALOG:
            estimates.append(
                ParameterEstimate(
                    name=item["name"],
                    value=None,
                    unit=item["unit"],
                    estimation_method=item["state"],
                    profile=str((self.session.profile or {}).get("profile_id", "unknown")),
                    calibration_status="unavailable",
                    limitation=item["note_ru"] if ru else item["note_en"],
                    expert_status="pending",
                    metadata={"implementation_state": item["state"]},
                )
            )
        self._fill(estimates)

    def _fill(self, estimates: list[ParameterEstimate]) -> None:
        self._rows = estimates
        self.table.setRowCount(len(estimates))
        for i, p in enumerate(estimates):
            state = (p.metadata or {}).get("implementation_state", p.estimation_method or "unknown")
            vals = [
                p.name,
                state,
                "—" if p.value is None else str(p.value),
                p.unit,
                p.estimation_method,
                p.calibration_status,
                p.expert_status,
                p.limitation,
            ]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(v))

    def load_from_result(self) -> None:
        estimates: list[ParameterEstimate] = []
        run = getattr(self.session, "last_run_root", None)
        by_name: dict[str, dict] = {}
        if run:
            pred_dir = Path(run) / "predictions"
            if pred_dir.exists():
                files = sorted(pred_dir.glob("*.json"))
                if files:
                    data = json.loads(files[-1].read_text(encoding="utf-8"))
                    sci = data.get("scientific_axes") or {}
                    for p in sci.get("parameter_estimates") or []:
                        by_name[p.get("name", "")] = p
        ru = self.i18n.language == "ru"
        for item in PARAMETER_CATALOG:
            p = by_name.get(item["name"])
            if p and p.get("value") is not None:
                estimates.append(
                    ParameterEstimate(
                        name=item["name"],
                        value=p.get("value"),
                        unit=p.get("unit", item["unit"]),
                        estimation_method=p.get("estimation_method", "pipeline"),
                        profile=p.get("profile", ""),
                        calibration_status=p.get("calibration_status", "uncalibrated"),
                        confidence=p.get("confidence"),
                        uncertainty=p.get("uncertainty"),
                        source_rule=p.get("source_rule", ""),
                        source_page=p.get("source_page", ""),
                        limitation=p.get("limitation", item["note_ru"] if ru else item["note_en"]),
                        expert_status=p.get("expert_status", "pending"),
                        metadata={"implementation_state": "implemented"},
                    )
                )
            else:
                estimates.append(
                    ParameterEstimate(
                        name=item["name"],
                        value=None,
                        unit=item["unit"],
                        estimation_method=item["state"],
                        profile=str((self.session.profile or {}).get("profile_id", "unknown")),
                        calibration_status="unavailable",
                        limitation=item["note_ru"] if ru else item["note_en"],
                        expert_status="pending",
                        metadata={"implementation_state": item["state"]},
                    )
                )
        self._fill(estimates)

    def _set_expert(self, status: str) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            QMessageBox.information(
                self,
                "Parameters" if self.i18n.language != "ru" else "Параметры",
                "Select a parameter row." if self.i18n.language != "ru" else "Выберите строку параметра.",
            )
            return
        self._rows[row].expert_status = status
        self.table.setItem(row, 6, QTableWidgetItem(status))

    def _save(self) -> None:
        out = ensure_dir(app_root() / "workspaces" / "_parameters")
        path = out / "expert_parameters.json"
        path.write_text(
            json.dumps([p.to_dict() for p in self._rows], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        QMessageBox.information(self, "IML", f"Saved {path}")
