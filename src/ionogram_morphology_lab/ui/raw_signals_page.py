"""Expert-mode Raw Numeric Signals inspection (Phase 4A)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
from ionogram_morphology_lab.importers.mat_inventory import inventory_mat
from ionogram_morphology_lab.projects.time_mapping import format_hhmm, frame_to_minute, mapping_status
from ionogram_morphology_lab.scientific_outputs.formula_registry import explain_formula, list_formulas
from ionogram_morphology_lab.scientific_outputs.signal_contracts import (
    extract_frame_consistent,
    frame_stats,
    get_contract_by_variable,
    match_inventory_to_contracts,
    phase_interpretation_message,
)
from ionogram_morphology_lab.utils.hashing import sha256_bytes


class RawSignalsPage(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        lay = QVBoxLayout(self)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("padding:8px; border:1px solid #888;")
        lay.addWidget(self.banner)
        self.phase_warning = QLabel()
        self.phase_warning.setWordWrap(True)
        self.phase_warning.setStyleSheet("padding:6px; color:#a60;")
        self.phase_warning.hide()
        lay.addWidget(self.phase_warning)
        row = QHBoxLayout()
        self.btn_refresh = QPushButton()
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self.export_diagnostic_package)
        self.btn_formulas = QPushButton()
        self.btn_formulas.clicked.connect(self.show_formula_explanations)
        row.addWidget(self.btn_refresh)
        row.addWidget(self.btn_export)
        row.addWidget(self.btn_formulas)
        lay.addLayout(row)
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        lay.addWidget(self.view, 1)
        self.formula_view = QTextEdit()
        self.formula_view.setReadOnly(True)
        self.formula_view.setMaximumHeight(220)
        lay.addWidget(self.formula_view)
        self._last_payload: dict = {}
        self.retranslate()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self.banner.setText(
            "Исходные числовые данные — первичный научный вход. PNG — только визуализация матрицы."
            if ru
            else "Raw Numeric Signals — primary scientific input. A PNG is only a visualization of the matrix."
        )
        self.btn_refresh.setText("Обновить" if ru else "Refresh")
        self.btn_export.setText("Экспорт диагностического пакета" if ru else "Export diagnostic package")
        self.btn_formulas.setText("Пояснения формул" if ru else "Formula explanations")
        self.refresh()

    def _profile_dict(self) -> dict:
        prof = getattr(self.session, "profile", None) or {}
        if isinstance(prof, dict) and prof:
            return prof
        return {
            "profile_id": getattr(self.session, "profile_id", "kfu_cyclone_2013_2014"),
            "amplitude_variable_name": "Amp_all",
            "height_bins": 256,
            "frequency_bins": 400,
            "frequency_start_mhz": 1.5,
            "frequency_step_mhz": 0.019,
            "frequency_end_mhz": 9.081,
            "nominal_range_km_per_bin": 2.5,
            "time_mapping": "matlab_index_minus_1_minute",
            "status": "provisional",
        }

    def refresh(self) -> None:
        ru = self.i18n.language == "ru"
        if not getattr(self.session, "active_mat", None):
            self.view.setPlainText("Нет активного MAT." if ru else "No active MAT.")
            self._last_payload = {}
            return
        mat_path = Path(self.session.active_mat)
        inv = inventory_mat(mat_path)
        matches = match_inventory_to_contracts(inv.variables)
        if any(m["variable_name"] == "Phs_all" and m["present"] for m in matches):
            self.phase_warning.setText(phase_interpretation_message(self.i18n.language))
            self.phase_warning.show()
        else:
            self.phase_warning.hide()

        profile = self._profile_dict()
        frame_idx = int(getattr(self.session, "current_frame", 1) or 1)
        amp_name = profile.get("amplitude_variable_name", "Amp_all")
        contract = get_contract_by_variable(amp_name) or {}
        height_bins = int(profile.get("height_bins", 256))
        frequency_bins = int(profile.get("frequency_bins", 400))

        try:
            loaded = load_amplitude_matrix(mat_path, variable=amp_name)
            frame, rng = extract_frame_consistent(
                loaded.data, frame_idx, height_bins=height_bins, frequency_bins=frequency_bins
            )
            stats = frame_stats(frame)
            store_shape = None
            try:
                store = self.session.ensure_store()
                if store.status().valid:
                    store_shape = list(np.asarray(store.get_frame(frame_idx)).shape)
            except Exception:  # noqa: BLE001
                store_shape = None
        except Exception as exc:  # noqa: BLE001
            self.view.setPlainText(str(exc))
            self._last_payload = {"error": str(exc)}
            return

        tmap = mapping_status(profile.get("time_mapping"))
        minute = frame_to_minute(frame_idx) if tmap.available else None
        start = float(profile.get("frequency_start_mhz", 1.5))
        step = float(profile.get("frequency_step_mhz", 0.019))
        freq_ax = [start + i * step for i in range(frequency_bins)]
        scale = float(profile.get("nominal_range_km_per_bin", 2.5))
        range_ax = [i * scale for i in range(height_bins)]

        self._last_payload = {
            "contract_id": contract.get("contract_id"),
            "source_variable": amp_name,
            "mat_path": str(mat_path),
            "mat_sha256": inv.sha256,
            "frame_index": frame_idx,
            "source_row_range_0based": [rng.row_start, rng.row_end_exclusive],
            "source_row_range_matlab_1based": [rng.matlab_row_start_1based, rng.matlab_row_end_1based],
            "matrix_shape": stats["shape"],
            "dtype": stats["dtype"],
            "stats": stats,
            "frequency_axis_range_mhz": [float(freq_ax[0]), float(freq_ax[-1])],
            "nominal_height_axis_range_km": [float(range_ax[0]), float(range_ax[-1])],
            "time_mapping": {
                "available": tmap.available,
                "status": tmap.status,
                "hhmm": format_hhmm(minute) if minute is not None else None,
                "minute": minute,
            },
            "profile_id": profile.get("profile_id"),
            "profile_verification_status": profile.get("status") or "provisional",
            "viewer_batch_consistent_shape": store_shape,
            "inventory_matches": matches,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "frame_matrix": frame,
        }

        lines = [
            f"{'Переменная' if ru else 'Source variable'}: {amp_name}",
            f"{'Контракт' if ru else 'Signal contract'}: {contract.get('contract_id')}",
            f"{'Кадр' if ru else 'Frame'}: {frame_idx}",
            f"{'Строки источника (0-based Python)' if ru else 'Source rows (0-based Python)'}: "
            f"[{rng.row_start}, {rng.row_end_exclusive})",
            f"{'Строки источника (1-based MATLAB)' if ru else 'Source rows (1-based MATLAB)'}: "
            f"{rng.matlab_row_start_1based} … {rng.matlab_row_end_1based}",
            f"{'Форма исходной матрицы кадра' if ru else 'Source frame matrix shape'}: "
            f"{stats.get('source_shape', stats['shape'])}",
            (
                f"Тип исходной матрицы: {stats.get('source_dtype', stats['dtype'])}"
                if ru
                else f"Source matrix dtype: {stats.get('source_dtype', stats['dtype'])}"
            ),
            (
                f"Тип для расчёта статистики: {stats.get('analysis_dtype', 'float64')}"
                if ru
                else f"Analysis dtype for statistics: {stats.get('analysis_dtype', 'float64')}"
            ),
            f"min={stats['min']}  max={stats['max']}  median={stats['median']}",
            f"{'Доля конечных' if ru else 'Finite fraction'}: {stats['finite_fraction']:.6f}",
            f"NaN={stats['nan_count']}  Inf={stats['inf_count']}",
            f"{'Доля насыщения (эвристика)' if ru else 'Saturated fraction (heuristic)'}: "
            f"{stats['saturated_fraction_heuristic']:.6f}",
            (
                "Насыщение помечено как эвристика: уровень насыщения источника и поведение прибора не подтверждены."
                if ru
                else "Saturation is marked as a heuristic: source dtype saturation level and instrument behavior are not verified."
            ),
            f"{'Ось частоты МГц' if ru else 'Frequency-axis range MHz'}: "
            f"{self._last_payload['frequency_axis_range_mhz']}",
            f"{'Ось номинальной высоты км' if ru else 'Nominal-height-axis range km'}: "
            f"{self._last_payload['nominal_height_axis_range_km']}",
            f"{'Время' if ru else 'Time mapping'}: {self._last_payload['time_mapping']}",
            f"{'Статус профиля' if ru else 'Profile verification status'}: "
            f"{self._last_payload['profile_verification_status']}",
            f"{'Форма из FrameStore' if ru else 'FrameStore shape'}: {store_shape}",
            "",
            ("Сопоставление контрактов:" if ru else "Contract matches:"),
        ]
        for m in matches:
            lines.append(
                f"  • {m['variable_name']}: present={m['present']} shape={m['shape']} "
                f"ok={m['shape_ok']} status={m['verification_status']}"
            )
        self.view.setPlainText("\n".join(lines))

    def export_diagnostic_package(self) -> None:
        if not self._last_payload or "frame_matrix" not in self._last_payload:
            QMessageBox.warning(self, "IML", "Nothing to export — refresh first.")
            return
        dest = QFileDialog.getExistingDirectory(self, "Diagnostic package folder")
        if not dest:
            return
        out = Path(dest) / f"iml_raw_signals_{self._last_payload['frame_index']}"
        out.mkdir(parents=True, exist_ok=True)
        frame = self._last_payload["frame_matrix"]
        meta = {k: v for k, v in self._last_payload.items() if k != "frame_matrix"}
        (out / "metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        npz_path = out / "frame_matrix.npz"
        np.savez_compressed(npz_path, frame=frame)
        (out / "axes.json").write_text(
            json.dumps(
                {
                    "frequency_axis_range_mhz": meta.get("frequency_axis_range_mhz"),
                    "nominal_height_axis_range_km": meta.get("nominal_height_axis_range_km"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (out / "hashes.json").write_text(
            json.dumps(
                {
                    "source_mat_sha256": meta.get("mat_sha256"),
                    "frame_npz_sha256": sha256_bytes(npz_path.read_bytes()),
                    "signal_contract_id": meta.get("contract_id"),
                    "note": "Source MAT is not copied into the package.",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        QMessageBox.information(self, "IML", f"Wrote read-only package:\n{out}")

    def show_formula_explanations(self) -> None:
        lang = self.i18n.language
        blocks = [explain_formula(item["formula_id"], lang) for item in list_formulas() if item.get("formula_id")]
        self.formula_view.setPlainText(("\n" + ("-" * 40) + "\n").join(blocks) if blocks else "—")
