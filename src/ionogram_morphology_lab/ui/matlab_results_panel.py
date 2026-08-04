"""Readable MATLAB Studio result presentation; deliberately separate from main results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.matlab_studio.manifest import ScriptManifest, save_manifest
from ionogram_morphology_lab.matlab_studio.method_contracts import classify_scientific_run_status


def _as_lines(value: Any) -> str:
    if isinstance(value, dict):
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    if isinstance(value, (list, tuple)):
        return "\n".join(str(item) for item in value) or "—"
    return str(value or "—")


def classify_output_files(paths: list[str]) -> dict[str, list[str]]:
    grouped = {"figures": [], "tables": [], "matrices": [], "other": []}
    for path in dict.fromkeys(paths):
        suffix = Path(path).suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".svg", ".fig", ".pdf"}:
            grouped["figures"].append(path)
        elif suffix in {".csv", ".tsv", ".xlsx"}:
            grouped["tables"].append(path)
        elif suffix == ".mat":
            grouped["matrices"].append(path)
        else:
            grouped["other"].append(path)
    return grouped


_STATUS_LABELS = {
    "completed_with_registered_output": (
        "Выполнение завершено с зарегистрированным выходом",
        "Execution completed with registered output",
    ),
    "completed_with_files_only": (
        "Выполнение завершено: созданы только файлы",
        "Execution completed with files only",
    ),
    "completed_with_no_registered_output": (
        "MATLAB завершил работу без ошибки, но метод не зарегистрировал результаты и не создал выходные файлы.",
        "MATLAB finished without error, but the method registered no results and created no output files.",
    ),
    "execution_failed": ("Выполнение завершилось ошибкой", "Execution failed"),
    "execution_cancelled": ("Выполнение отменено", "Execution cancelled"),
    "execution_timed_out": ("Превышено время ожидания", "Execution timed out"),
}


def build_result_sections(job: Any, payload: dict[str, Any], lang: str = "en") -> dict[str, str]:
    """Turn a completed or failed job into explicit, non-empty Studio sections."""
    ru = lang == "ru"
    provenance = dict(payload.get("provenance") or {})
    outputs = dict(payload.get("outputs") or {})
    files = list(payload.get("output_files") or [])
    grouped = classify_output_files(files)
    integrity_ok = getattr(job, "source_mats_unchanged", payload.get("source_mats_unchanged", True))
    integrity = (
        ("Целостность исходного MAT: без изменений (SHA-256 проверен)." if ru else "Source MAT integrity: unchanged (SHA-256 verified).")
        if integrity_ok
        else ("ПРЕДУПРЕЖДЕНИЕ: SHA-256 исходного MAT изменился." if ru else "WARNING: source MAT SHA-256 changed.")
    )
    error = payload.get("error_message") or getattr(job, "error_message", "")
    job_status = str(getattr(job, "status", payload.get("status", "unknown")))
    sci_status = classify_scientific_run_status(job_status=job_status, payload=payload)
    status_label = _STATUS_LABELS.get(sci_status, (sci_status, sci_status))[0 if ru else 1]
    features = outputs.get("registered_features", outputs.get("features", []))
    candidates = outputs.get("scientific_candidates", outputs.get("candidates", []))
    values = outputs.get("values") or outputs.get("scalars") or []
    work = payload.get("work_dir") or getattr(job, "output_directory", "—")
    method = getattr(job, "source_path", provenance.get("script", "—"))
    what_calc = []
    if values:
        what_calc.append("значения" if ru else "values")
    if features:
        what_calc.append("признаки" if ru else "features")
    if candidates:
        what_calc.append("кандидаты" if ru else "candidates")
    if not what_calc:
        what_calc.append("—" if not files else ("только файлы" if ru else "files only"))
    summary = (
        f"{'Что выполнено' if ru else 'What was executed'}: {method}\n"
        f"{'Статус' if ru else 'Status'}: {status_label}\n"
        f"{'Backend' if not ru else 'Исполнитель'}: {getattr(job, 'backend', payload.get('backend', '—'))}\n"
        f"{'Время' if ru else 'Elapsed'}: {getattr(job, 'elapsed_s', payload.get('elapsed_s', 0))} s\n"
        f"{'Кадр' if ru else 'Frame'}: {getattr(job, 'active_frame', '—')}\n"
        f"{'Что вычислено' if ru else 'What was calculated'}: {', '.join(what_calc)}\n"
        f"{'Что создано' if ru else 'What was created'}: "
        f"{len(grouped['figures'])} {('рисунков' if ru else 'figures')}, "
        f"{len(grouped['tables'])} {('таблиц' if ru else 'tables')}, "
        f"{len(grouped['matrices'])} {('матриц' if ru else 'matrices')}, "
        f"{len(files)} {('файлов' if ru else 'files')}\n"
        f"{'Где сохранено' if ru else 'Where stored'}: {work}\n"
        f"{integrity}\n\n"
        + (
            "Обычный текст остаётся в MATLAB Studio. Файлы — в папке этого запуска. "
            "Результат не попадает автоматически на страницу «Результаты»."
            if ru
            else "Ordinary text remains in MATLAB Studio. Files remain in this run-specific folder. "
            "MATLAB results are not automatically inserted into main Results; only a registered and "
            "enabled compatible pipeline stage may create one."
        )
    )
    if sci_status == "completed_with_no_registered_output":
        summary = status_label + "\n\n" + summary
    return {
        "Summary": summary,
        "Values": _as_lines(values) if values else (
            "Нет зарегистрированных скалярных значений." if ru else "No registered scalar values."
        ),
        "Registered Features": _as_lines(features),
        "Scientific Candidates": (
            _as_lines(candidates)
            + (
                "\n\nКандидаты можно добавить в сравнение методов; в основные Результаты они не попадают автоматически."
                if ru
                else "\n\nCandidates can be added to Method Comparison; they do not enter main Results automatically."
            )
        ),
        "Figures": _as_lines(grouped["figures"]) or ("Рисунки не созданы." if ru else "No figures created."),
        "Tables": _as_lines(grouped["tables"]) or ("Таблицы не созданы." if ru else "No tables created."),
        "Matrices": _as_lines(grouped["matrices"]) or ("Матрицы не созданы." if ru else "No matrices created."),
        "Created Files": _as_lines(files) or ("Файлы не созданы." if ru else "No files created."),
        "Warnings and Errors": _as_lines(
            error or payload.get("stderr") or (
                "Предупреждений и ошибок нет." if ru else "No warnings or errors reported."
            )
        ),
        "Technical Log": "\n\n".join(
            part
            for part in (
                _as_lines(payload.get("stdout")),
                _as_lines(payload.get("stderr")),
                _as_lines(payload.get("diary")),
                _as_lines(payload.get("stack")),
            )
            if part != "—"
        )
        or ("Технический журнал пуст." if ru else "No technical log was captured."),
        "Provenance": (
            f"Method ID: {provenance.get('method_id', getattr(job, 'script_id', '—'))}\n"
            f"Script: {method}\n"
            f"SHA-256: {getattr(job, 'sha256', '—')}\n"
            f"MAT SHA-256: {_as_lines(getattr(job, 'source_mat_sha256', provenance.get('source_mat_sha256', [])))}\n"
            f"Backend: {getattr(job, 'backend', payload.get('backend', '—'))}\n"
            f"Status: {status_label}\n"
            f"Frame: {getattr(job, 'active_frame', '—')}\n"
            f"Time: {getattr(job, 'start_time', provenance.get('created_at', '—'))}\n"
            f"Inputs: {getattr(job, 'requested_inputs', '—')}\n"
            f"Shapes: {_as_lines(provenance.get('input_shapes', {}))}\n"
            f"Parameters: {_as_lines(provenance.get('parameters', {}))}\n"
            f"Output folder: {work}\n{integrity}"
        ),
        "_sci_status": sci_status,
        "_grouped": grouped,  # type: ignore[dict-item]
        "_files": files,  # type: ignore[dict-item]
        "_values": values,  # type: ignore[dict-item]
    }


class PluginRegistrationDialog(QDialog):
    """Wizard intentionally requires a successful, complete run."""

    def __init__(self, result: dict[str, Any] | None, script_id: str, parent=None, language: str = "en"):
        super().__init__(parent)
        self.result = result or {}
        self.script_id = script_id
        ru = language == "ru"
        self.setWindowTitle(
            "Зарегистрировать как плагин MATLAB" if ru else "Register as MATLAB Plugin"
        )
        layout = QVBoxLayout(self)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        form = QFormLayout()
        self.plugin_id = QLineEdit(script_id)
        self.name_en = QLineEdit(script_id.replace("_", " ").title())
        self.name_ru = QLineEdit()
        self.role = QLineEdit("feature")
        self.version = QLineEdit("0.1.0")
        self.author = QLineEdit()
        self.entry_point = QLineEdit("run")
        self.required_inputs = QLineEdit("frame, Amp_all")
        self.produced_outputs = QLineEdit("registered_features, scientific_candidates")
        self.supported_profiles = QLineEdit("kfu_cyclone_2013_2014")
        self.scientific_status = QLineEdit("development_candidate")
        self.citation = QLineEdit()
        self.limitations = QLineEdit(
            "Not externally validated; does not auto-enter main Results."
        )
        self.timeout = QLineEdit("120")
        self.trust_status = QLineEdit("unconfirmed")
        fields = (
            (("ID плагина", "Plugin ID"), self.plugin_id),
            (("Имя (EN)", "Name (EN)"), self.name_en),
            (("Имя (RU)", "Name (RU)"), self.name_ru),
            (("Точка входа", "Entry point"), self.entry_point),
            (("Входы", "Required inputs"), self.required_inputs),
            (("Выходы", "Produced outputs"), self.produced_outputs),
            (("Профили", "Supported profiles"), self.supported_profiles),
            (("Научный статус", "Scientific status"), self.scientific_status),
            (("Роль", "Role"), self.role),
            (("Версия", "Version"), self.version),
            (("Автор", "Author"), self.author),
            (("Ссылки", "Source references"), self.citation),
            (("Ограничения", "Limitations"), self.limitations),
            (("Таймаут (с)", "Timeout (s)"), self.timeout),
            (("Доверие", "Trust status"), self.trust_status),
        )
        for labels, field in fields:
            form.addRow(labels[0 if ru else 1], field)
        layout.addLayout(form)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        sci = classify_scientific_run_status(
            job_status=str(self.result.get("status", "")),
            payload=self.result,
        )
        ok = self.result.get("status") == "ok" and bool(self.result.get("work_dir")) and sci.startswith(
            "completed_with"
        ) and sci != "completed_with_no_registered_output"
        # Allow files-only or registered; refuse failed/empty/incomplete.
        ok = (
            self.result.get("status") == "ok"
            and bool(self.result.get("work_dir"))
            and sci
            in (
                "completed_with_registered_output",
                "completed_with_files_only",
            )
        )
        self.notice.setText(
            (
                "Плагин можно зарегистрировать только после успешного полного запуска с выходом."
                if not ok
                else "Регистрация включает совместимый этап конвейера; результат не вставляется в «Результаты» автоматически."
            )
            if ru
            else (
                "A plugin may be registered only from a successful, complete run with output."
                if not ok
                else "Registration enables a compatible pipeline stage; it does not insert this MATLAB result into main Results."
            )
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)

    def manifest(self, destination: Path) -> Path:
        return save_manifest(
            ScriptManifest(
                plugin_id=self.plugin_id.text().strip(),
                name_en=self.name_en.text().strip(),
                name_ru=self.name_ru.text().strip() or self.name_en.text().strip(),
                version=self.version.text().strip() or "0.1.0",
                author=self.author.text().strip(),
                citation=self.citation.text().strip(),
                script_type="feature_extraction",
                entrypoint=self.entry_point.text().strip() or "run",
                limitations_en=self.limitations.text().strip(),
                limitations_ru=self.limitations.text().strip(),
            ),
            destination,
        )


class MatlabResultsPanel(QWidget):
    """Tabbed results panel with wrapping primary actions and a More menu."""

    add_to_comparison = Signal(object)
    run_again = Signal()

    TAB_KEYS = (
        "Summary",
        "Values",
        "Registered Features",
        "Scientific Candidates",
        "Figures",
        "Tables",
        "Matrices",
        "Created Files",
        "Warnings and Errors",
        "Technical Log",
        "Provenance",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._payload: dict[str, Any] = {}
        self._job: Any = None
        self._script_id = "matlab_method"
        self._language = "en"
        self._action_keys: dict[str, QPushButton | QToolButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.card = QLabel()
        self.card.setWordWrap(True)
        self.card.setObjectName("matlab_result_card")
        self.card.setStyleSheet("padding:8px; border:1px solid #888; border-radius:4px;")
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addWidget(self.card)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        self.tabs.setUsesScrollButtons(True)
        self.views: dict[str, QWidget] = {}
        self._text_views: dict[str, QTextEdit] = {}
        for name in self.TAB_KEYS:
            if name == "Values":
                page = QWidget()
                vlay = QVBoxLayout(page)
                self.values_table = QTableWidget(0, 5)
                self.values_table.setHorizontalHeaderLabels(
                    ["Output", "Value", "Unit", "Status", "Limitation"]
                )
                self.values_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                vlay.addWidget(self.values_table)
                self.views[name] = page
                self.tabs.addTab(page, name)
            elif name == "Created Files":
                page = QWidget()
                vlay = QVBoxLayout(page)
                self.files_table = QTableWidget(0, 4)
                self.files_table.setHorizontalHeaderLabels(["File", "Type", "Size", "Open"])
                self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                vlay.addWidget(self.files_table)
                self.views[name] = page
                self.tabs.addTab(page, name)
            elif name == "Figures":
                page = QWidget()
                vlay = QVBoxLayout(page)
                self.figures_host = QVBoxLayout()
                wrap = QWidget()
                wrap.setLayout(self.figures_host)
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                scroll.setWidget(wrap)
                vlay.addWidget(scroll)
                self.figures_note = QTextEdit()
                self.figures_note.setReadOnly(True)
                self.figures_note.setMaximumHeight(80)
                vlay.addWidget(self.figures_note)
                self.views[name] = page
                self.tabs.addTab(page, name)
            else:
                view = QTextEdit()
                view.setReadOnly(True)
                self._text_views[name] = view
                self.views[name] = view
                self.tabs.addTab(view, name)
        layout.addWidget(self.tabs, 1)

        # Vertical action list — never one clipped horizontal row of long RU labels.
        actions_frame = QFrame()
        actions_frame.setObjectName("matlab_actions")
        self.actions_lay = QVBoxLayout(actions_frame)
        self.actions_lay.setContentsMargins(0, 4, 0, 0)
        self.actions_lay.setSpacing(4)
        layout.addWidget(actions_frame)

        self._build_actions()
        self.show_empty()

    def _mk_btn(self, key: str, slot) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName(f"matlab_action_{key}")
        btn.setMinimumHeight(30)
        btn.setMinimumWidth(160)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet("text-align: left; padding-left: 10px;")
        btn.clicked.connect(slot)
        self._action_keys[key] = btn
        self.actions_lay.addWidget(btn)
        return btn

    def _build_actions(self) -> None:
        self._mk_btn("open_folder", self.open_results_folder)
        self._mk_btn("run_again", self.run_again.emit)
        self._mk_btn("tech_log", lambda: self.tabs.setCurrentIndex(self.TAB_KEYS.index("Technical Log")))
        self.more_btn = QToolButton()
        self.more_btn.setObjectName("matlab_action_more")
        self.more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.more_btn.setMinimumHeight(30)
        self.more_btn.setMinimumWidth(160)
        self.more_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.more_btn.setStyleSheet("text-align: left; padding-left: 10px;")
        self.more_menu = QMenu(self)
        self.more_btn.setMenu(self.more_menu)
        self.actions_lay.addWidget(self.more_btn)
        self._action_keys["more"] = self.more_btn

        menu_items = [
            ("open_file", self.open_selected_file),
            ("show_figures", self.show_generated_figures),
            ("copy", self.copy_result),
            ("export", self.export_result),
            ("compare", self._add_to_comparison),
            ("register", self.register_plugin),
        ]
        self._menu_actions: dict[str, Any] = {}
        for key, slot in menu_items:
            act = self.more_menu.addAction(key)
            act.triggered.connect(slot)
            self._menu_actions[key] = act

    def set_action_labels(self, labels: dict[str, str]) -> None:
        """labels keys use stable ids: open_folder, open_file, ... more"""
        mapping = {
            "open_folder": "open_folder",
            "Open Results Folder": "open_folder",
            "open_file": "open_file",
            "Open Selected File": "open_file",
            "show_figures": "show_figures",
            "Show Generated Figures": "show_figures",
            "copy": "copy",
            "Copy Result": "copy",
            "export": "export",
            "Export Result": "export",
            "compare": "compare",
            "Add to Method Comparison": "compare",
            "register": "register",
            "Register as MATLAB Plugin": "register",
            "run_again": "run_again",
            "Run Again": "run_again",
            "tech_log": "tech_log",
            "Open Technical Log": "tech_log",
            "more": "more",
            "More actions": "more",
        }
        for raw, text in labels.items():
            key = mapping.get(raw, raw)
            widget = self._action_keys.get(key)
            if isinstance(widget, QPushButton):
                widget.setText(text)
                widget.setToolTip(text)
                widget.setAccessibleName(text)
            elif isinstance(widget, QToolButton) and key == "more":
                widget.setText(text)
                widget.setToolTip(text)
                widget.setAccessibleName(text)
            act = self._menu_actions.get(key)
            if act is not None:
                act.setText(text)
                act.setToolTip(text)

    def set_tab_labels(self, labels: dict[str, str]) -> None:
        for i, key in enumerate(self.TAB_KEYS):
            if key in labels and i < self.tabs.count():
                self.tabs.setTabText(i, labels[key])
                self.tabs.setTabToolTip(i, labels[key])

    def set_table_headers(self, language: str = "en") -> None:
        ru = language == "ru"
        self.values_table.setHorizontalHeaderLabels(
            ["Выход", "Значение", "Ед.", "Статус", "Ограничение"]
            if ru
            else ["Output", "Value", "Unit", "Status", "Limitation"]
        )
        self.files_table.setHorizontalHeaderLabels(
            ["Файл", "Тип", "Размер", "Открыть"]
            if ru
            else ["File", "Type", "Size", "Open"]
        )

    def show_empty(self, language: str = "en") -> None:
        self._language = language
        if language == "ru":
            text = (
                "Результатов MATLAB пока нет. Выберите скрипт, данные и нажмите «Запустить в MATLAB». "
                "После выполнения здесь появятся зарегистрированные признаки, научные кандидаты, "
                "графики и созданные файлы.\n\n"
                "Результат MATLAB не попадает автоматически на страницу «Результаты»."
            )
        else:
            text = (
                "No MATLAB results yet. Select a script and data, then click Run in MATLAB. "
                "After execution, registered features, scientific candidates, figures, "
                "and created files appear here.\n\n"
                "A MATLAB result is not automatically inserted into the main Results page."
            )
        self.card.setText(text)
        for view in self._text_views.values():
            view.setPlainText(text)
        self.values_table.setRowCount(0)
        self.files_table.setRowCount(0)
        self._clear_figures()
        self.figures_note.setPlainText(text)

    def set_result(self, job: Any, payload: dict[str, Any], script_id: str, language: str | None = None) -> None:
        self._job, self._payload, self._script_id = job, payload, script_id
        if language:
            self._language = language
        sections = build_result_sections(job, payload, self._language)
        for name, text in sections.items():
            if name.startswith("_"):
                continue
            if name in self._text_views:
                self._text_views[name].setPlainText(str(text))
        self.card.setText(str(sections["Summary"]))
        self._fill_values(sections.get("_values") or (payload.get("outputs") or {}).get("values") or [])
        self._fill_files(list(sections.get("_files") or payload.get("output_files") or []))
        self._fill_figures(list((sections.get("_grouped") or {}).get("figures") or []))

    def _fill_values(self, values: Any) -> None:
        rows: list[dict[str, Any]] = []
        if isinstance(values, dict):
            for k, v in values.items():
                if isinstance(v, dict):
                    rows.append({"output": k, **v})
                else:
                    rows.append({"output": k, "value": v, "unit": "", "status": "ok", "limitation": ""})
        elif isinstance(values, list):
            for item in values:
                if isinstance(item, dict):
                    rows.append(item)
                else:
                    rows.append({"output": str(item), "value": item, "unit": "", "status": "ok", "limitation": ""})
        self.values_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, key in enumerate(("output", "value", "unit", "status", "limitation")):
                self.values_table.setItem(i, j, QTableWidgetItem(str(row.get(key, "—"))))

    def _fill_files(self, files: list[str]) -> None:
        self.files_table.setRowCount(len(files))
        for i, path_str in enumerate(files):
            path = Path(path_str)
            size = path.stat().st_size if path.exists() else 0
            kind = path.suffix.lower().lstrip(".") or "file"
            self.files_table.setItem(i, 0, QTableWidgetItem(path.name))
            self.files_table.setItem(i, 1, QTableWidgetItem(kind))
            self.files_table.setItem(i, 2, QTableWidgetItem(str(size)))
            btn = QPushButton("Open" if self._language != "ru" else "Открыть")
            btn.clicked.connect(lambda _=False, p=path: QDesktopServices.openUrl(QUrl.fromLocalFile(str(p))))
            self.files_table.setCellWidget(i, 3, btn)

    def _clear_figures(self) -> None:
        while self.figures_host.count():
            item = self.figures_host.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _fill_figures(self, figures: list[str]) -> None:
        self._clear_figures()
        if not figures:
            self.figures_note.setPlainText(
                "Рисунки не созданы. Не каждый метод создаёт изображение."
                if self._language == "ru"
                else "No figures created. Not every method produces an image."
            )
            return
        self.figures_note.setPlainText(
            f"{len(figures)} " + ("рисунок(ов)." if self._language == "ru" else "figure(s).")
        )
        for path_str in figures:
            path = Path(path_str)
            box = QFrame()
            box.setFrameShape(QFrame.Shape.StyledPanel)
            lay = QVBoxLayout(box)
            title = QLabel(path.name)
            title.setWordWrap(True)
            lay.addWidget(title)
            img = QLabel()
            img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if path.exists() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                pix = QPixmap(str(path))
                if not pix.isNull():
                    img.setPixmap(
                        pix.scaled(QSize(360, 240), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    )
            lay.addWidget(img)
            row = QHBoxLayout()
            for label, slot in (
                ("Open" if self._language != "ru" else "Открыть", lambda p=path: QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))),
                ("Save copy" if self._language != "ru" else "Сохранить копию", lambda p=path: self._save_copy_file(p)),
            ):
                b = QPushButton(label)
                b.clicked.connect(slot)
                row.addWidget(b)
            lay.addLayout(row)
            self.figures_host.addWidget(box)

    def _save_copy_file(self, path: Path) -> None:
        dest, _ = QFileDialog.getSaveFileName(self, "Save copy", path.name)
        if dest:
            Path(dest).write_bytes(path.read_bytes())

    def _work_dir(self) -> Path | None:
        value = self._payload.get("work_dir") or getattr(self._job, "output_directory", "")
        return Path(value) if value else None

    def open_results_folder(self) -> bool:
        work = self._work_dir()
        if not work or not work.exists():
            return False
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(work)))

    def _selected_file(self) -> Path | None:
        files = self._payload.get("output_files") or []
        return Path(files[0]) if files else None

    def open_selected_file(self) -> bool:
        path = self._selected_file()
        return bool(path and path.exists() and QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))))

    def show_generated_figures(self) -> None:
        self.tabs.setCurrentIndex(self.TAB_KEYS.index("Figures"))

    def copy_result(self) -> None:
        QGuiApplication.clipboard().setText(
            json.dumps(self._payload, indent=2, ensure_ascii=False, default=str)
        )

    def export_result(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export MATLAB result", "matlab_result.json", "JSON (*.json)"
        )
        if path:
            Path(path).write_text(
                json.dumps(self._payload, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )

    def _add_to_comparison(self) -> None:
        candidates = (self._payload.get("outputs") or {}).get(
            "scientific_candidates",
            (self._payload.get("outputs") or {}).get("candidates", []),
        )
        if candidates:
            self.add_to_comparison.emit(candidates)
        else:
            QMessageBox.information(
                self,
                "MATLAB Studio",
                "Нет научных кандидатов для сравнения."
                if self._language == "ru"
                else "This run has no scientific candidates to compare.",
            )

    def register_plugin(self) -> None:
        dialog = PluginRegistrationDialog(
            self._payload, self._script_id, self, language=self._language
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        work = self._work_dir()
        if not work:
            return
        manifest = dialog.manifest(work / f"{dialog.plugin_id.text().strip()}.iml-matlab.yaml")
        QMessageBox.information(self, "MATLAB Studio", f"Plugin manifest created:\n{manifest}")

    def primary_action_min_widths(self) -> list[int]:
        """Test helper: widths of visible primary action buttons."""
        widths = []
        for key in ("open_folder", "run_again", "tech_log", "more"):
            w = self._action_keys.get(key)
            if w is not None:
                widths.append(w.minimumWidth())
        return widths
