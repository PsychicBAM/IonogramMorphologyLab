"""Ionogram Parameters / Параметры ионограммы — candidate estimates only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.scientific_outputs.taxonomy import ParameterEstimate
from ionogram_morphology_lab.ui.display_values import display_status
from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

# Catalog of known parameters with honest implementation state (no unexplained empties).
PARAMETER_CATALOG = [
    {"name": "foE", "symbol": "foE", "full_en": "Critical frequency of the E layer", "full_ru": "Критическая частота слоя E", "meaning_en": "Highest frequency reflected from E", "meaning_ru": "Наивысшая частота отражения от E", "axis": "frequency", "trace": "E", "unit": "MHz", "state": "profile_dependent", "note_en": "Requires E-trace candidate + verified frequency axis.", "note_ru": "Нужен кандидат трассы E и проверенная ось частоты."},
    {"name": "h'E", "symbol": "h′E", "full_en": "Minimum virtual height of the E layer", "full_ru": "Минимальная виртуальная высота слоя E", "meaning_en": "Nominal virtual height (not true height)", "meaning_ru": "Номинальная виртуальная высота (не истинная)", "axis": "range/virtual-height", "trace": "E", "unit": "km (nominal virtual)", "state": "profile_dependent", "note_en": "Nominal virtual height only; not true height.", "note_ru": "Только номинальная виртуальная высота, не истинная."},
    {"name": "foEs", "symbol": "foEs", "full_en": "Ordinary-wave critical frequency of Es", "full_ru": "Критическая частота Es (обыкновенная)", "meaning_en": "Es frequency candidate", "meaning_ru": "Кандидат частоты Es", "axis": "frequency", "trace": "Es", "unit": "MHz", "state": "profile_dependent", "note_en": "Es frequency candidate when Es detector fires.", "note_ru": "Кандидат частоты Es при срабатывании детектора Es."},
    {"name": "h'Es", "symbol": "h′Es", "full_en": "Minimum virtual height of Es", "full_ru": "Минимальная виртуальная высота Es", "meaning_en": "Nominal virtual height for Es", "meaning_ru": "Номинальная виртуальная высота Es", "axis": "range/virtual-height", "trace": "Es", "unit": "km (nominal virtual)", "state": "profile_dependent", "note_en": "Nominal virtual height candidate for Es.", "note_ru": "Кандидат номинальной виртуальной высоты Es."},
    {"name": "fbEs", "symbol": "fbEs", "full_en": "Blanketing frequency of Es", "full_ru": "Частота бланкетинга Es", "meaning_en": "Blanketing-frequency candidate", "meaning_ru": "Кандидат частоты бланкетинга", "axis": "frequency", "trace": "Es", "unit": "MHz", "state": "source_disabled", "note_en": "Blanketing-frequency candidate disabled until source-verified method is active.", "note_ru": "Кандидат частоты бланкетинга отключён до активации верифицированного метода."},
    {"name": "foF1", "symbol": "foF1", "full_en": "Critical frequency of the F1 layer", "full_ru": "Критическая частота слоя F1", "meaning_en": "F1 frequency when separable", "meaning_ru": "Частота F1 при отделении", "axis": "frequency", "trace": "F1", "unit": "MHz", "state": "profile_dependent", "note_en": "Only when F1 is separable; else F_unspecified.", "note_ru": "Только при отделении F1; иначе F_unspecified."},
    {"name": "h'F1", "symbol": "h′F1", "full_en": "Minimum virtual height of F1", "full_ru": "Минимальная виртуальная высота F1", "meaning_en": "Nominal virtual height for F1", "meaning_ru": "Номинальная виртуальная высота F1", "axis": "range/virtual-height", "trace": "F1", "unit": "km (nominal virtual)", "state": "profile_dependent", "note_en": "Nominal virtual height; profile-dependent.", "note_ru": "Номинальная виртуальная высота; зависит от профиля."},
    {"name": "foF2", "symbol": "foF2", "full_en": "Critical frequency of the F2 layer", "full_ru": "Критическая частота слоя F2", "meaning_en": "Image-estimated F2 frequency candidate", "meaning_ru": "Кандидат частоты F2 по изображению", "axis": "frequency", "trace": "F2", "unit": "MHz", "state": "profile_dependent", "note_en": "Image-estimated candidate when F2 detector quality is sufficient.", "note_ru": "Кандидат по изображению при достаточном качестве детектора F2."},
    {"name": "fxF2", "symbol": "fxF2", "full_en": "Extraordinary-wave critical frequency of F2", "full_ru": "Критическая частота F2 (необыкновенная)", "meaning_en": "Requires O/X-capable data", "meaning_ru": "Нужны данные с разделением O/X", "axis": "frequency", "trace": "F2/X", "unit": "MHz", "state": "source_disabled", "note_en": "Requires O/X-capable measurements; not confirmed from Amp_all alone.", "note_ru": "Требуются измерения с разделением O/X; Amp_all сам по себе недостаточен."},
    {"name": "h'F2", "symbol": "h′F2", "full_en": "Minimum virtual height of F2", "full_ru": "Минимальная виртуальная высота F2", "meaning_en": "Nominal virtual height for F2", "meaning_ru": "Номинальная виртуальная высота F2", "axis": "range/virtual-height", "trace": "F2", "unit": "km (nominal virtual)", "state": "profile_dependent", "note_en": "Nominal virtual height candidate for F2.", "note_ru": "Кандидат номинальной виртуальной высоты F2."},
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
        self.table.itemSelectionChanged.connect(self._show_details)
        root.addWidget(self.table, 1)
        self.details = QLabel()
        self.details.setWordWrap(True)
        root.addWidget(self.details)
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
        headers = [
            self.i18n.t(key)
            for key in (
                "table.parameter", "table.state", "table.value", "table.unit",
                "table.method", "table.calibration", "table.expert", "table.limitation",
            )
        ]
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
                self._status_label(state),
                "—" if p.value is None else str(p.value),
                p.unit,
                self._status_label(p.estimation_method),
                self._status_label(p.calibration_status),
                self._status_label(p.expert_status),
                p.limitation,
            ]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(v))
        self._show_details()

    def _status_label(self, value: str | None) -> str:
        token = str(value or "")
        key = {
            "implemented": "params.state_impl",
            "not_yet_implemented": "params.state_nyi",
        }.get(token, "")
        return self.i18n.t(key) if key else display_status(token, self.i18n.language) or "—"

    def _catalog_item(self, name: str) -> dict:
        for item in PARAMETER_CATALOG:
            if item["name"] == name:
                return item
        return {"name": name}

    def _show_details(self) -> None:
        row = self.table.currentRow()
        ru = self.i18n.language == "ru"
        if row < 0 or row >= len(self._rows):
            self.details.setText(
                "Выберите параметр для объяснения статуса и ограничений."
                if ru else
                "Select a parameter to see its status, method, and limitations."
            )
            return
        p = self._rows[row]
        cat = self._catalog_item(p.name)
        meta = p.metadata or {}
        accepted = meta.get("accepted_provenance")
        why_missing = ""
        if p.value is None:
            why_missing = (
                "Значение недоступно: нет достаточных признаков трассы/слоя или калибровка недоступна."
                if ru
                else "Value unavailable: required trace/layer evidence is absent or calibration is unavailable."
            )
        lines = [
            f"{'Полное имя' if ru else 'Full name'}: {cat.get('full_ru' if ru else 'full_en', p.name)}",
            f"{'Символ' if ru else 'Symbol'}: {cat.get('symbol', p.name)}",
            f"{'Смысл' if ru else 'Physical meaning'}: {cat.get('meaning_ru' if ru else 'meaning_en', '')}",
            f"{'Единица' if ru else 'Unit'}: {p.unit}",
            f"{'Ось источника' if ru else 'Source axis'}: {cat.get('axis', '—')}",
            f"{'Метод оценки' if ru else 'Estimation method'}: {self._status_label(p.estimation_method)}",
            f"{'Нужная трасса/слой' if ru else 'Required trace/layer'}: {cat.get('trace', '—')}",
            f"{'Статус реализации' if ru else 'Implementation status'}: {self._status_label(meta.get('implementation_state', p.estimation_method))}",
            f"{'Калибровка' if ru else 'Calibration status'}: {self._status_label(p.calibration_status)}",
            f"{'Научный статус' if ru else 'Scientific status'}: "
            + ("кандидат по изображению, не подтверждённый скейлинг" if ru else "image-estimated candidate, not confirmed scaling"),
            f"{'Текущее значение' if ru else 'Current candidate value'}: {'—' if p.value is None else p.value}",
            why_missing,
            f"{'Ограничения' if ru else 'Limitations'}: {p.limitation}",
            (
                "Номинальная виртуальная высота — не истинная высота. "
                "Кандидат по изображению — не подтверждённый скейлинг ионозонда."
                if ru
                else "Nominal virtual height is not true height. "
                "An image-estimated candidate is not confirmed ionosonde scaling."
            ),
            f"{'Решение эксперта' if ru else 'Expert decision'}: {self._status_label(p.expert_status)}",
            (
                "Accept сохраняет кандидата с происхождением; Reject отклоняет; Indeterminate оставляет неопределённость."
                if ru
                else "Accept stores the candidate with provenance; Reject declines; Indeterminate keeps uncertainty."
            ),
        ]
        if accepted:
            lines.append(
                f"{'Принято' if ru else 'Accepted'}: {accepted.get('by')} @ {accepted.get('when')}; "
                f"{'значение' if ru else 'value'}={accepted.get('value')}; "
                f"{'метод' if ru else 'method'}={accepted.get('method')}; "
                f"{'в отчёты' if ru else 'enters reports'}={accepted.get('enters_reports')}"
            )
        self.details.setText("\n".join(line for line in lines if line))
        tip = cat.get("note_ru" if ru else "note_en", "")
        self.details.setToolTip(tip)

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
        ru = self.i18n.language == "ru"
        if row < 0 or row >= len(self._rows):
            QMessageBox.information(
                self,
                "Parameters" if not ru else "Параметры",
                "Select a parameter row." if not ru else "Выберите строку параметра.",
            )
            return
        p = self._rows[row]
        p.expert_status = status
        meta = dict(p.metadata or {})
        if status == "accepted":
            meta["accepted_provenance"] = {
                "by": "local_user",
                "when": datetime.now(timezone.utc).isoformat(),
                "value": p.value,
                "method": p.estimation_method,
                "enters_reports": True,
            }
        elif "accepted_provenance" in meta and status != "accepted":
            meta["accepted_provenance"]["enters_reports"] = False
            meta["accepted_provenance"]["changed_to"] = status
        p.metadata = meta
        self.table.setItem(row, 6, QTableWidgetItem(self._status_label(status)))
        self._show_details()
        if status == "accepted":
            QMessageBox.information(
                self,
                "IML",
                (
                    f"Принято: {p.name}={p.value} ({p.estimation_method}) пользователем local_user. "
                    "Можно изменить позже через Reject/Indeterminate. Значение может войти в отчёты."
                    if ru
                    else f"Accepted: {p.name}={p.value} ({p.estimation_method}) by local_user. "
                    "Use Reject/Indeterminate to change later. Value may enter reports."
                ),
            )

    def _save(self) -> None:
        out = ensure_dir(app_root() / "workspaces" / "_parameters")
        path = out / "expert_parameters.json"
        path.write_text(
            json.dumps([p.to_dict() for p in self._rows], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        QMessageBox.information(self, "IML", f"Saved {path}")
