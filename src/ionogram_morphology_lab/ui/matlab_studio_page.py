"""MATLAB Studio page — editor, library, run, results."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.matlab_studio.api_bridge import prepare_run_workspace, API_FUNCTIONS
from ionogram_morphology_lab.matlab_studio.backends import detect_backends, select_backend
from ionogram_morphology_lab.matlab_studio.builtin_library import (
    create_editable_copy,
    export_method_package,
    list_builtin_methods,
    read_builtin_source,
)
from ionogram_morphology_lab.matlab_studio.job_manager import MatlabJob, MatlabJobManager
from ionogram_morphology_lab.matlab_studio.library import ScriptLibrary
from ionogram_morphology_lab.matlab_studio.plugins import PluginRegistry
from ionogram_morphology_lab.matlab_studio.runner import MatlabRunRequest
from ionogram_morphology_lab.matlab_studio.method_contracts import (
    format_expected_output,
    get_method_contract,
)
from ionogram_morphology_lab.ui.matlab_results_panel import MatlabResultsPanel
from ionogram_morphology_lab.utils.paths import app_root
import numpy as np

MATLAB_TRUST_WARNING = (
    "MATLAB scripts run with your operating-system user permissions. Only run scripts you trust."
)


def file_sha256(path: Path | str) -> str:
    """Calculate a script digest without executing or importing it."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def requires_trust_confirmation(source: str, trust_status: str) -> bool:
    """Built-ins are trusted; every other script needs an explicit run decision."""
    return source != "builtin" or trust_status != "builtin"


class MatlabHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.kw = QTextCharFormat()
        self.kw.setForeground(QColor("#0000aa"))
        self.kw.setFontWeight(QFont.Weight.Bold)
        self.comment = QTextCharFormat()
        self.comment.setForeground(QColor("#008000"))
        self.keywords = [
            "function",
            "end",
            "if",
            "else",
            "elseif",
            "for",
            "while",
            "try",
            "catch",
            "return",
            "switch",
            "case",
            "otherwise",
        ]

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for kw in self.keywords:
            start = 0
            while True:
                idx = text.find(kw, start)
                if idx < 0:
                    break
                before_ok = idx == 0 or not text[idx - 1].isalnum()
                after = idx + len(kw)
                after_ok = after >= len(text) or not text[after].isalnum()
                if before_ok and after_ok:
                    self.setFormat(idx, len(kw), self.kw)
                start = idx + len(kw)
        if "%" in text:
            i = text.index("%")
            self.setFormat(i, len(text) - i, self.comment)


class _LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):  # noqa: N802
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):  # noqa: N802
        self.editor.paint_line_numbers(event)


class MatlabCodeEditor(QPlainTextEdit):
    """Monospaced MATLAB editor with a local gutter and no wrapped lines."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = _LineNumberArea(self)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.setFont(font)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_area_width(0)

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self, _count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        rect = self.contentsRect()
        self.line_number_area.setGeometry(QRect(rect.left(), rect.top(), self.line_number_area_width(), rect.height()))

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))
        block = self.firstVisibleBlock()
        number = block.blockNumber() + 1
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#666"))
                painter.drawText(0, top, self.line_number_area.width() - 4, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, str(number))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            number += 1


class MatlabStudioPage(QWidget):
    def __init__(self, session, i18n, job_manager: MatlabJobManager | None = None, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.library = ScriptLibrary()
        self.plugins = PluginRegistry()
        self.job_manager = job_manager or MatlabJobManager(self)
        self._current_job_id: str | None = None
        self._last_result: dict | None = None
        self._current_script_id = "untitled"
        self._builtin_readonly = False
        self._current_builtin_id = ""
        self._build()
        self.job_manager.job_updated.connect(self._on_job_updated)
        self.job_manager.job_finished.connect(self._on_job_finished)
        self.retranslate()
        self.refresh_backends()
        self.refresh_library()
        self.refresh_builtin()

    def _build(self) -> None:
        from PySide6.QtWidgets import QGroupBox, QSizePolicy

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        self.backend_card = QGroupBox()
        self.backend_card.setObjectName("matlab_backend_card")
        bcl = QVBoxLayout(self.backend_card)
        self.backend_label = QLabel()
        self.backend_label.setWordWrap(True)
        self.backend_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bcl.addWidget(self.backend_label)
        root.addWidget(self.backend_card)
        self.trust_label = QLabel()
        self.trust_label.setWordWrap(True)
        root.addWidget(self.trust_label)
        split = QSplitter()
        split.setChildrenCollapsible(False)
        left = QWidget()
        left.setMinimumWidth(180)
        ll = QVBoxLayout(left)
        self.lib_list = QListWidget()
        self.lib_list.currentTextChanged.connect(self._open_from_library)
        self.script_library_label = QLabel()
        ll.addWidget(self.script_library_label)
        ll.addWidget(self.lib_list, 1)
        self.builtin_methods_label = QLabel()
        ll.addWidget(self.builtin_methods_label)
        self.builtin_list = QListWidget()
        self.builtin_list.currentTextChanged.connect(self._open_builtin)
        ll.addWidget(self.builtin_list, 1)
        # Primary library actions only — long secondary labels live in a menu.
        self.library_buttons = []
        for key, slot in [
            ("matlab.new", self._new),
            ("matlab.open", self._open),
            ("matlab.save", self._save),
        ]:
            b = QPushButton()
            b.setMinimumHeight(28)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.clicked.connect(slot)
            self.library_buttons.append((b, key))
            ll.addWidget(b)
        self.lib_more_btn = QToolButton()
        self.lib_more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.lib_more_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.lib_more_btn.setMinimumHeight(28)
        self.lib_more_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.lib_more_menu = QMenu(self)
        self.lib_more_btn.setMenu(self.lib_more_menu)
        self._lib_menu_actions: list[tuple[object, str]] = []
        for key, slot in [
            ("matlab.import_folder", self._import_folder),
            ("matlab.history", self._history),
            ("matlab.register_plugin", self._register_plugin),
            ("matlab.create_editable_copy", self._copy_builtin),
            ("matlab.export_builtin", self._export_builtin),
            ("matlab.open_builtin_docs", self._open_builtin_docs),
        ]:
            act = self.lib_more_menu.addAction(key)
            act.triggered.connect(slot)
            self._lib_menu_actions.append((act, key))
        ll.addWidget(self.lib_more_btn)
        split.addWidget(left)

        center = QWidget()
        center.setMinimumWidth(360)
        cl = QVBoxLayout(center)
        self.expected_output = QGroupBox()
        self.expected_output.setObjectName("matlab_expected_output")
        eol = QVBoxLayout(self.expected_output)
        self.expected_output_body = QLabel()
        self.expected_output_body.setWordWrap(True)
        eol.addWidget(self.expected_output_body)
        cl.addWidget(self.expected_output)
        self.validate_card = QLabel()
        self.validate_card.setObjectName("matlab_validate_card")
        self.validate_card.setWordWrap(True)
        self.validate_card.setStyleSheet("padding:6px; border:1px solid #888;")
        self.validate_card.hide()
        cl.addWidget(self.validate_card)
        self.editor_tabs = QTabWidget()
        self.editor = MatlabCodeEditor()
        self._highlighter = MatlabHighlighter(self.editor.document())
        self.editor_tabs.addTab(self.editor, "untitled.m*")
        cl.addWidget(self.editor_tabs, 1)
        # Vertical primary actions — full labels remain readable at 1366×768.
        self.run_target = QComboBox()
        for key in ("current_frame", "selected_range", "one_file", "folder"):
            self.run_target.addItem(key, key)
        self.btn_run = QPushButton()
        self.btn_run.setMinimumHeight(32)
        self.btn_run.setMinimumWidth(160)
        self.btn_run.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_run.clicked.connect(self._run)
        self.btn_cancel = QPushButton()
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setMinimumHeight(32)
        self.btn_cancel.setMinimumWidth(100)
        self.btn_cancel.clicked.connect(self._cancel_run)
        self.btn_validate = QPushButton()
        self.btn_validate.setMinimumHeight(32)
        self.btn_validate.setMinimumWidth(160)
        self.btn_validate.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_validate.clicked.connect(self._validate_code)
        target_row = QHBoxLayout()
        target_row.addWidget(self.run_target, 1)
        target_row.addWidget(self.btn_cancel)
        cl.addLayout(target_row)
        cl.addWidget(self.btn_run)
        cl.addWidget(self.btn_validate)
        self.editor_tools_btn = QToolButton()
        self.editor_tools_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.editor_tools_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.editor_tools_btn.setMinimumHeight(28)
        self.editor_tools_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.editor_tools_menu = QMenu(self)
        self.act_format = self.editor_tools_menu.addAction("Format")
        self.act_save_copy = self.editor_tools_menu.addAction("Save copy")
        self.act_compare_original = self.editor_tools_menu.addAction("Compare")
        self.act_format.triggered.connect(self._format_code)
        self.act_save_copy.triggered.connect(self._save_copy)
        self.act_compare_original.triggered.connect(self._compare_with_original)
        self.editor_tools_btn.setMenu(self.editor_tools_menu)
        # Keep aliases used by older tests / call sites.
        self.btn_format = self.editor_tools_btn
        self.btn_save_copy = self.editor_tools_btn
        self.btn_compare_original = self.editor_tools_btn
        self.allow_write = QCheckBox()
        tools_row = QHBoxLayout()
        tools_row.addWidget(self.editor_tools_btn, 1)
        tools_row.addWidget(self.allow_write, 2)
        cl.addLayout(tools_row)
        split.addWidget(center)

        right = QWidget()
        right.setMinimumWidth(280)
        rl = QVBoxLayout(right)
        self.results_label = QLabel()
        rl.addWidget(self.results_label)
        self.result_panel = MatlabResultsPanel()
        self.result_panel.run_again.connect(self._run)
        self.result_panel.add_to_comparison.connect(self._add_to_method_comparison)
        self.result_card = self.result_panel.card
        self.results = self.result_panel._text_views["Technical Log"]
        rl.addWidget(self.result_panel, 1)
        self.api_info = QPlainTextEdit()
        self.api_info.setReadOnly(True)
        self.api_info.setMaximumHeight(72)
        self.api_info.setPlainText("API:\n" + "\n".join(API_FUNCTIONS))
        rl.addWidget(self.api_info)
        # Cap expected-output / backend cards so the editor remains the largest central area.
        self.backend_card.setMaximumHeight(110)
        self.expected_output.setMaximumHeight(130)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)
        split.setStretchFactor(2, 2)
        split.setSizes([200, 640, 360])
        root.addWidget(split, 1)
        self._update_expected_output(self._current_script_id)

    def retranslate(self) -> None:
        self.trust_label.setText(self.i18n.t("matlab.no_script"))
        self.script_library_label.setText(self.i18n.t("matlab.script_library"))
        self.builtin_methods_label.setText(self.i18n.t("matlab.builtin_methods"))
        ru = self.i18n.language == "ru"
        self.backend_card.setTitle("Состояние исполнителя MATLAB" if ru else "MATLAB backend status")
        self.expected_output.setTitle("Ожидаемый результат метода" if ru else "Expected Method Output")
        self.btn_run.setText("Запустить в MATLAB" if ru else "Run in MATLAB")
        self.btn_run.setToolTip(self.btn_run.text())
        self.btn_run.setAccessibleName(self.btn_run.text())
        self.btn_cancel.setText("Остановить" if ru else "Cancel")
        self.btn_validate.setText("Проверить код без запуска" if ru else "Check Code Without Running")
        self.btn_validate.setToolTip(
            "Проверяется структура редактора и базовые требования IML. "
            "MATLAB не запускается, научный результат не вычисляется."
            if ru
            else "Checks editor structure and basic IML requirements. "
            "MATLAB is not started and no scientific result is computed."
        )
        self.btn_validate.setAccessibleName(self.btn_validate.text())
        self.editor_tools_btn.setText("Инструменты редактора…" if ru else "Editor tools…")
        self.editor_tools_btn.setToolTip(self.editor_tools_btn.text())
        self.act_format.setText("Форматировать код" if ru else "Format code")
        self.act_save_copy.setText("Сохранить копию" if ru else "Save copy")
        self.act_compare_original.setText("Сравнить с оригиналом" if ru else "Compare with original")
        self.allow_write.setText(self.i18n.t("matlab.allow_write"))
        # Short visible label; full phrase stays in tooltip/accessible name.
        self.lib_more_btn.setText("Ещё…" if ru else "More…")
        tip = "Дополнительные действия библиотеки" if ru else "More library actions"
        self.lib_more_btn.setToolTip(tip)
        self.lib_more_btn.setAccessibleName(tip)
        for act, key in self._lib_menu_actions:
            act.setText(self.i18n.t(key))
            act.setToolTip(act.text())
        self.results_label.setText(self.i18n.t("matlab.results"))
        # Keep stable itemData keys; only display labels change with language.
        target_labels = {
            "current_frame": "Текущий кадр" if ru else "Current frame",
            "selected_range": "Выбранный диапазон" if ru else "Selected range",
            "one_file": "Один файл" if ru else "One file",
            "folder": "Папка" if ru else "Folder",
        }
        cur = self.run_target.currentData() or "current_frame"
        self.run_target.blockSignals(True)
        self.run_target.clear()
        for key, label in target_labels.items():
            self.run_target.addItem(label, key)
        idx = self.run_target.findData(cur)
        self.run_target.setCurrentIndex(idx if idx >= 0 else 0)
        self.run_target.blockSignals(False)
        self.result_panel.set_table_headers(self.i18n.language)
        self.result_panel.set_action_labels({
            "open_folder": "Открыть папку результатов" if ru else "Open Results Folder",
            "open_file": "Открыть выбранный файл" if ru else "Open Selected File",
            "show_figures": "Показать созданные рисунки" if ru else "Show Generated Figures",
            "copy": "Копировать результат" if ru else "Copy Result",
            "export": "Экспортировать результат" if ru else "Export Result",
            "compare": "Добавить в сравнение методов" if ru else "Add to Method Comparison",
            "register": "Зарегистрировать как плагин MATLAB" if ru else "Register as MATLAB Plugin",
            "run_again": "Запустить снова" if ru else "Run Again",
            "tech_log": "Открыть технический журнал" if ru else "Open Technical Log",
            "more": "Дополнительно…" if ru else "More actions…",
        })
        self.result_panel.set_tab_labels({
            "Summary": "Сводка" if ru else "Summary",
            "Values": "Значения" if ru else "Values",
            "Registered Features": "Зарегистрированные признаки" if ru else "Registered Features",
            "Scientific Candidates": "Научные кандидаты" if ru else "Scientific Candidates",
            "Figures": "Рисунки" if ru else "Figures",
            "Tables": "Таблицы" if ru else "Tables",
            "Matrices": "Матрицы" if ru else "Matrices",
            "Created Files": "Созданные файлы" if ru else "Created Files",
            "Warnings and Errors": "Предупреждения и ошибки" if ru else "Warnings and Errors",
            "Technical Log": "Технический журнал" if ru else "Technical Log",
            "Provenance": "Происхождение" if ru else "Provenance",
        })
        if not self._last_result:
            self.result_panel.show_empty(self.i18n.language)
        else:
            self.result_panel.set_result(
                getattr(self, "_last_job_obj", None) or type("J", (), {"status": "completed"})(),
                self._last_result,
                self._current_script_id,
                language=self.i18n.language,
            )
        for button, key in self.library_buttons:
            button.setText(self.i18n.t(key))
            button.setToolTip(button.text())
        self._update_expected_output(self._current_script_id)
        self.refresh_backends()

    def _update_expected_output(self, method_id: str) -> None:
        contract = get_method_contract(method_id or "untitled")
        self.expected_output_body.setText(format_expected_output(contract, self.i18n.language))

    def refresh_backends(self) -> None:
        mats = self.session.settings
        backends = detect_backends(
            mats.get("matlab", "matlab_executable", ""),
            mats.get("matlab", "octave_executable", ""),
        )
        active = select_backend(
            mats.get("matlab", "active_backend", "auto"),
            mats.get("matlab", "matlab_executable", ""),
            mats.get("matlab", "octave_executable", ""),
        )
        ru = self.i18n.language == "ru"
        lines = [
            (
                f"Активный исполнитель: {active.backend_id} ({active.status}) v={active.version}"
                if ru
                else f"Active backend: {active.backend_id} ({active.status}) v={active.version}"
            )
        ]
        for b in backends:
            avail = "да" if (ru and b.available) else ("нет" if ru and not b.available else str(b.available))
            if not ru:
                avail = str(b.available)
            lines.append(
                f"• {b.backend_id}: {'доступен' if ru else 'available'}={avail}"
                + (f" — {'; '.join(b.warnings)}" if b.warnings else "")
            )
        if active.backend_id == "none" or not active.available:
            lines.append(
                "Исполнитель недоступен — редактор работает, запуск MATLAB отключён."
                if ru
                else "No execution backend — editor still works; Run in MATLAB is disabled."
            )
        self.backend_label.setText("\n".join(lines))
        self.btn_run.setEnabled(active.backend_id != "none" and active.available)
        if not self.btn_run.isEnabled():
            self.btn_run.setToolTip(
                "Нет исполнителя MATLAB/Octave — редактор доступен."
                if ru
                else "No execution backend — editor still works."
            )

    def refresh_library(self) -> None:
        self.lib_list.clear()
        # seed teaching examples into library index if empty
        teach = app_root() / "matlab_studio_library" / "teaching"
        if teach.exists() and not self.library.list_scripts():
            for d in teach.iterdir():
                if d.is_dir():
                    m = list(d.glob("*.m"))
                    if m:
                        try:
                            self.library.import_file(m[0], category="teaching", verification_status="teaching")
                        except Exception:
                            pass
        for rec in self.library.list_scripts():
            self.lib_list.addItem(f"{rec.category}/{rec.script_id} [{rec.verification_status}]")

    def refresh_builtin(self) -> None:
        self.builtin_list.clear()
        for rec in list_builtin_methods():
            self.builtin_list.addItem(f"{rec.category}/{rec.method_id}")

    def _open_builtin(self, text: str) -> None:
        if not text or "/" not in text:
            return
        mid = text.split("/", 1)[1]
        try:
            rec, src = read_builtin_source(mid)
        except FileNotFoundError:
            return
        self._builtin_readonly = True
        self._current_builtin_id = mid
        self._current_script_id = mid
        self.editor.setPlainText(src)
        self.editor.setReadOnly(True)
        self.editor_tabs.setTabText(0, f"{rec.path.name} [read-only]")
        self._update_expected_output(mid)

    def _copy_builtin(self) -> None:
        if not self._current_builtin_id:
            QMessageBox.information(self, "MATLAB Studio", "Select a built-in method first.")
            return
        project = getattr(self.session, "project_root", None) or getattr(self.session, "project", None)
        root = None
        if project is not None:
            root = getattr(project, "root", None) or getattr(project, "path", None)
        dest = create_editable_copy(self._current_builtin_id, project_root=root)
        self.library.import_file(dest, category="user", verification_status="user_copy")
        self._builtin_readonly = False
        self.editor.setReadOnly(False)
        self.editor.setPlainText(Path(dest).read_text(encoding="utf-8"))
        self._current_script_id = Path(dest).stem
        self.editor_tabs.setTabText(0, Path(dest).name)
        self.refresh_library()
        QMessageBox.information(self, "MATLAB Studio", f"Editable copy created:\n{dest}")

    def _export_builtin(self) -> None:
        if not self._current_builtin_id:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export method package", f"{self._current_builtin_id}.zip", "ZIP (*.zip)"
        )
        if path:
            export_method_package(self._current_builtin_id, path)
            QMessageBox.information(self, "MATLAB Studio", f"Exported {path}")

    def _open_builtin_docs(self) -> None:
        docs = app_root() / "docs" / "BUILTIN_MATLAB_IONOGRAM_METHODS_EN.md"
        ru = app_root() / "docs" / "BUILTIN_MATLAB_IONOGRAM_METHODS_RU.md"
        text = ""
        if docs.exists():
            text += docs.read_text(encoding="utf-8")[:8000]
        if ru.exists():
            text += "\n\n----\n\n" + ru.read_text(encoding="utf-8")[:8000]
        if not text:
            text = (
                "Built-in methods live under matlab_builtin/. "
                "See README_EN.md / README_RU.md in that folder. "
                "Candidate morphology only; not causal confirmation."
            )
        self.results.setPlainText(text)

    def _new(self) -> None:
        self._builtin_readonly = False
        self.editor.setReadOnly(False)
        self._current_script_id = "untitled"
        self.editor.setPlainText("% New MATLAB script for Ionogram Morphology Lab\n")
        self.editor_tabs.setTabText(0, "untitled.m*")

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open .m", "", "MATLAB (*.m)")
        if not path:
            return
        rec = self.library.import_file(path, category="imported")
        self.editor.setPlainText(Path(rec.source_file).read_text(encoding="utf-8"))
        self._current_script_id = rec.script_id
        self.editor_tabs.setTabText(0, Path(rec.source_file).name)
        self.refresh_library()

    def _import_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "MATLAB folder")
        if path:
            self.library.import_folder(path)
            self.refresh_library()

    def _save(self) -> None:
        if self._builtin_readonly:
            QMessageBox.warning(
                self,
                "MATLAB Studio",
                "Built-in methods are read-only. Use “Create editable copy” first.",
            )
            return
        name = self._current_script_id if self._current_script_id != "untitled" else "user_script"
        rec = self.library.save_text(name, self.editor.toPlainText(), category="user")
        self._current_script_id = rec.script_id
        self.editor_tabs.setTabText(0, Path(rec.source_file).name)
        self.refresh_library()
        QMessageBox.information(self, "MATLAB Studio", f"Saved {rec.source_file}")

    def _open_from_library(self, text: str) -> None:
        if not text or "/" not in text:
            return
        sid = text.split("/")[1].split(" ")[0]
        for rec in self.library.list_scripts():
            if rec.script_id == sid:
                self._builtin_readonly = False
                self.editor.setReadOnly(False)
                self.editor.setPlainText(Path(rec.source_file).read_text(encoding="utf-8"))
                self._current_script_id = sid
                self.editor_tabs.setTabText(0, Path(rec.source_file).name)
                break

    def _history(self) -> None:
        hist = self.library.history(self._current_script_id)
        self.result_panel._text_views["Technical Log"].setPlainText(
            json.dumps(hist, indent=2, ensure_ascii=False)
        )

    def _format_code(self) -> None:
        """Conservative whitespace-only formatter: no scientific or executable changes."""
        lines = self.editor.toPlainText().splitlines()
        indent = 0
        formatted = []
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()
            if lower.startswith(("end", "else", "elseif", "case", "otherwise", "catch")):
                indent = max(0, indent - 1)
            formatted.append(("    " * indent + stripped) if stripped else "")
            if lower.startswith(("function", "if ", "for ", "while ", "switch", "try", "else", "elseif", "catch")):
                indent += 1
        self.editor.setPlainText("\n".join(formatted) + ("\n" if lines else ""))

    def _validate_code(self) -> None:
        """Editor-structure check only — never executes MATLAB or computes science."""
        ru = self.i18n.language == "ru"
        source = self.editor.toPlainText()
        errors = []
        if not source.strip():
            errors.append("Скрипт пуст." if ru else "Script is empty.")
        if source.lower().count("function") > source.lower().count("end"):
            errors.append("Возможно отсутствует «end»." if ru else "Possible missing 'end'.")
        header = (
            "Проверяется структура редактора и базовые требования IML.\n"
            "MATLAB не запускается, научный результат не вычисляется.\n\n"
            if ru
            else "Checks editor structure and basic IML requirements.\n"
            "MATLAB is not started and no scientific result is computed.\n\n"
        )
        if errors:
            text = header + ("Ошибки:\n" if ru else "Issues:\n") + "\n".join(f"• {e}" for e in errors)
        else:
            text = header + (
                "Базовая проверка редактора пройдена. Это не запуск MATLAB."
                if ru
                else "Basic editor validation passed. This does not execute MATLAB."
            )
        self.validate_card.setText(text)
        self.validate_card.show()
        # Keep Technical Log in sync for accessibility; no modal required.
        self.result_panel._text_views["Technical Log"].setPlainText(text)

    def _save_copy(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save MATLAB copy", f"{self._current_script_id}.m", "MATLAB (*.m)")
        if path:
            Path(path).write_text(self.editor.toPlainText(), encoding="utf-8")

    def _compare_with_original(self) -> None:
        import difflib

        source = ""
        for rec in self.library.list_scripts():
            if rec.script_id == self._current_script_id:
                source = Path(rec.source_file).read_text(encoding="utf-8")
                break
        if not source:
            source = self.editor.toPlainText()
        diff = "\n".join(difflib.unified_diff(source.splitlines(), self.editor.toPlainText().splitlines(),
                                               fromfile="original", tofile="editor", lineterm=""))
        self.result_panel._text_views["Technical Log"].setPlainText(
            diff or "No changes from the saved original."
        )
        self.result_panel.tabs.setCurrentIndex(
            self.result_panel.TAB_KEYS.index("Technical Log")
        )

    def _add_to_method_comparison(self, candidates: object) -> None:
        """Explicit hand-off only; a MATLAB run never mutates main Results."""
        rows: list[dict] = []
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict):
                    rows.append(dict(item))
                else:
                    rows.append({"method": "MATLAB", "morphology": str(item), "status": "candidate"})
        elif candidates:
            rows.append({"method": "MATLAB", "morphology": str(candidates), "status": "candidate"})
        for row in rows:
            row.setdefault("method", "MATLAB Studio")
            row.setdefault("status", "matlab_candidate")
        self._pending_comparison_candidates = rows
        self.session.matlab_comparison_candidates = list(rows)
        ru = self.i18n.language == "ru"
        QMessageBox.information(
            self,
            "MATLAB Studio",
            (
                "Кандидаты подготовлены для «Сравнения методов». "
                "Страница «Результаты» не изменена."
                if ru
                else "Candidates were prepared for Method Comparison. "
                "Main Results were not changed."
            ),
        )
        # Optional MainWindow callback: navigate + refresh comparison page.
        callback = getattr(self, "on_candidates_for_comparison", None)
        if callable(callback):
            callback(rows)

    def _register_plugin(self) -> None:
        for rec in self.library.list_scripts():
            if rec.script_id == self._current_script_id and rec.manifest_path:
                try:
                    self.plugins.register(rec.manifest_path, role="feature")
                    QMessageBox.information(self, "MATLAB Studio", f"Registered plugin {rec.script_id}")
                except Exception as exc:  # noqa: BLE001
                    QMessageBox.warning(self, "MATLAB Studio", str(exc))
                return
        QMessageBox.information(self, "MATLAB Studio", "Save script first (needs manifest).")

    def _run(self) -> None:
        # Built-in methods run from original path without saving over them
        script_path = None
        entry = "main.m"
        source = "builtin"
        trust_status = "builtin"
        if self._builtin_readonly and self._current_builtin_id:
            rec_b, _ = read_builtin_source(self._current_builtin_id)
            script_path = rec_b.path
            entry = rec_b.path.name
        else:
            if not self._builtin_readonly:
                self._save()
            recs = [r for r in self.library.list_scripts() if r.script_id == self._current_script_id]
            if not recs:
                QMessageBox.warning(self, "MATLAB Studio", "Save a script first.")
                return
            rec = recs[0]
            script_path = Path(rec.source_file)
            entry = rec.entry_point
            source = (
                "user_copy"
                if rec.verification_status == "user_copy"
                else rec.category
            )
            trust_status = rec.verification_status or "unconfirmed"
        work = app_root() / "workspaces" / "_matlab_runs" / self._current_script_id
        active_backend = select_backend(
            self.session.settings.get("matlab", "active_backend", "auto"),
            self.session.settings.get("matlab", "matlab_executable", ""),
            self.session.settings.get("matlab", "octave_executable", ""),
        )
        requested_inputs = (
            f"target={self.run_target.currentData() or self.run_target.currentText()}, "
            f"frame_id={self.session.current_frame}, inputs=iml_current_frame"
        )
        trust_details = (
            f"Source: {source}\n"
            f"SHA-256: {file_sha256(script_path)}\n"
            f"Trust: {trust_status}\n"
            f"Backend: {active_backend.backend_id}\n"
            f"Output folder: {work}\n"
            f"Requested inputs: {requested_inputs}"
        )
        self.trust_label.setText(trust_details)
        self.results.setPlainText(trust_details)
        if requires_trust_confirmation(source, trust_status):
            answer = QMessageBox.warning(
                self,
                "MATLAB script trust",
                MATLAB_TRUST_WARNING,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            if not self.session.settings.get(
                "matlab", "first_trust_warning_ack", False
            ):
                self.session.settings.set(
                    "matlab", "first_trust_warning_ack", True
                )
                self.session.settings.save()
        elif not self.session.settings.get(
            "matlab", "builtin_trust_acknowledged", False
        ):
            self.session.settings.set(
                "matlab", "builtin_trust_acknowledged", True
            )
            self.session.settings.save()
        # unify below
        class _Tmp:
            pass

        rec = _Tmp()
        rec.source_file = script_path
        rec.entry_point = entry
        rec.script_id = self._current_script_id
        if not self.session.has_real_import() and (self.run_target.currentData() or self.run_target.currentText()) == "current_frame":
            # allow synthetic frame
            frame = np.zeros((256, 400))
        else:
            try:
                store = self.session.ensure_store()
                if not store.status().valid:
                    store.ensure_ready()
                frame = store.get_frame(self.session.current_frame)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(self, "MATLAB Studio", f"No frame available: {exc}")
                return
        prepare_run_workspace(
            work,
            current_frame=frame,
            frequency_axis=list(np.linspace(1.5, 9.081, frame.shape[1])),
            range_axis=[i * 2.5 for i in range(frame.shape[0])],
            profile=self.session.profile,
            metadata={"frame_id": self.session.current_frame},
            frame_ids=[self.session.current_frame],
        )
        # copy helpers onto path via work
        helpers = app_root() / "matlab_helpers"
        if helpers.exists():
            import shutil

            for p in helpers.glob("*.m"):
                shutil.copy2(p, work / p.name)
        req = MatlabRunRequest(
            script_path=rec.source_file,
            entrypoint=rec.entry_point,
            backend=self.session.settings.get("matlab", "active_backend", "auto"),
            matlab_executable=self.session.settings.get("matlab", "matlab_executable", ""),
            octave_executable=self.session.settings.get("matlab", "octave_executable", ""),
            timeout_s=int(self.session.settings.get("matlab", "default_timeout_s", 120)),
            work_dir=work,
            allow_external_write=self.allow_write.isChecked(),
            source_mat_paths=[str(self.session.active_mat)] if self.session.active_mat else [],
            inputs={"iml_current_frame": frame},
        )
        if req.backend == "auto":
            # prefer none-safe path: if no backend, show clear message without pretending
            pass
        if self.job_manager.has_active_jobs():
            ru = self.i18n.language == "ru"
            QMessageBox.information(
                self,
                "MATLAB Studio",
                "Задача MATLAB уже выполняется." if ru else "A MATLAB task is already running.",
            )
            return
        self.results.setPlainText(trust_details + ("\n\nВыполняется…" if self.i18n.language == "ru" else "\n\nRunning…"))
        self.result_card.setText(
            "Выполнение…" if self.i18n.language == "ru" else "Running…"
        )
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        try:
            job = self.job_manager.submit(
                req,
                script_id=self._current_script_id,
                trust_status=trust_status,
                requested_inputs=requested_inputs,
                active_frame=int(self.session.current_frame),
            )
            self._current_job_id = job.job_id
        except Exception as exc:  # noqa: BLE001
            self.btn_run.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self._show_failure_card(
                error_summary=str(exc),
                backend=str(req.backend),
                elapsed_s=0.0,
                work_dir=str(work),
                source_ok=True,
                technical={"exception": str(exc)},
            )

    def _cancel_run(self) -> None:
        if self._current_job_id:
            self.job_manager.cancel(self._current_job_id)

    def _on_job_updated(self, job: MatlabJob) -> None:
        if job.job_id != self._current_job_id:
            return
        ru = self.i18n.language == "ru"
        self.result_card.setText(
            f"{'Статус' if ru else 'Status'}: {job.status}\n"
            f"{'Процесс' if ru else 'Process'}: {job.process_state}"
        )

    def _on_job_finished(self, job: MatlabJob) -> None:
        if job.job_id != self._current_job_id:
            return
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        payload = job.result or job.to_dict()
        self._last_result = payload
        self._last_job_obj = job
        self.result_panel.set_result(
            job, payload, self._current_script_id, language=self.i18n.language
        )
        ok = job.status == "completed" and payload.get("status") == "ok"
        if ok:
            ru = self.i18n.language == "ru"
            if ru:
                integrity = (
                    "Исходный MAT не изменён (SHA-256 проверен)."
                    if job.source_mats_unchanged
                    else "ВНИМАНИЕ: контрольная сумма исходного MAT изменилась."
                )
                self.result_card.setText(
                    "Выполнение успешно завершено.\n"
                    f"Backend: {job.backend}\n"
                    f"Время: {job.elapsed_s}s\n"
                    f"{integrity}"
                )
            else:
                integrity = (
                    "Source MAT integrity: unchanged (SHA-256 verified)."
                    if job.source_mats_unchanged
                    else "WARNING: source MAT SHA-256 changed."
                )
                self.result_card.setText(
                    "Execution completed successfully.\n"
                    f"Backend: {job.backend}\nElapsed: {job.elapsed_s}s\n{integrity}\n\n"
                    "Results are organized in the tabs below; they are not automatically inserted into main Results."
                )
            return
        # Failure / timeout / cancel — never close the application
        summary = job.error_message or payload.get("error_message") or job.status
        line = ""
        for marker in ("line ", "Line ", "строк"):
            if marker.lower() in summary.lower():
                # best-effort extract
                import re

                m = re.search(r"(?:line|Line|строк[ае]?)\s*(\d+)", summary)
                if m:
                    line = m.group(1)
                break
        self._show_failure_card(
            error_summary=summary.splitlines()[0][:300] if summary else job.status,
            backend=job.backend,
            elapsed_s=job.elapsed_s,
            work_dir=job.output_directory,
            source_ok=job.source_mats_unchanged,
            technical=payload,
            script_line=line,
            status=job.status,
        )

    def _show_failure_card(
        self,
        *,
        error_summary: str,
        backend: str,
        elapsed_s: float,
        work_dir: str,
        source_ok: bool,
        technical: dict,
        script_line: str = "",
        status: str = "failed",
    ) -> None:
        ru = self.i18n.language == "ru"
        integrity = (
            ("Исходный MAT не изменён (SHA-256 проверен)." if source_ok else "Контрольная сумма исходного MAT изменилась.")
            if ru
            else (
                "Source MAT integrity: unchanged (SHA-256 verified)."
                if source_ok
                else "Source MAT integrity: SHA-256 changed."
            )
        )
        guided = str(self.session.settings.get("ux", "interface_mode", "guided")) == "guided"
        card = (
            f"{'Выполнение не удалось' if ru else 'Execution failed'} ({status}).\n"
            f"{'Кратко' if ru else 'MATLAB error summary'}: {error_summary}\n"
        )
        if script_line:
            card += f"{'Строка' if ru else 'Script line'}: {script_line}\n"
        card += (
            f"Backend: {backend}\n"
            f"{'Время' if ru else 'Elapsed'}: {elapsed_s}s\n"
            f"{integrity}\n"
            f"{'Папка вывода' if ru else 'Output folder'}: {work_dir}\n"
        )
        if guided:
            card += (
                "\nПодробный стек MATLAB скрыт в режиме Guided — откройте «Технические сведения»."
                if ru
                else "\nFull MATLAB stack is hidden in Guided mode — use Open technical details."
            )
        self.result_card.setText(card)
        self._last_result = technical
        payload = dict(technical)
        payload.setdefault("status", "error")
        payload.setdefault("work_dir", work_dir)
        payload.setdefault("error_message", error_summary)
        self.result_panel.set_result(
            type("FailedMatlabJob", (), {
                "status": status, "backend": backend, "elapsed_s": elapsed_s,
                "output_directory": work_dir, "source_mats_unchanged": source_ok,
                "source_path": "", "sha256": "", "active_frame": self.session.current_frame,
                "source_mat_paths": [], "requested_inputs": "",
            })(),
            payload,
            self._current_script_id,
            language=self.i18n.language,
        )
        self.result_card.setText(card + (
            "\nPartial outputs were retained. Next action: inspect Technical Log, then correct the script and run again."
            if not ru else
            "\nЧастичные выходные данные сохранены. Следующее действие: откройте технический журнал, исправьте скрипт и повторите запуск."
        ))

    def _open_technical_details(self) -> None:
        if not self._last_result:
            return
        self.result_panel._text_views["Technical Log"].setPlainText(
            json.dumps(self._last_result, indent=2, ensure_ascii=False)
        )
        self.result_panel.tabs.setCurrentIndex(
            self.result_panel.TAB_KEYS.index("Technical Log")
        )

    def _copy_error(self) -> None:
        text = self.result_card.text()
        if self._last_result:
            text += "\n\n" + json.dumps(self._last_result, indent=2, ensure_ascii=False)
        QApplication.clipboard().setText(text)

    def _open_log_folder(self) -> None:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        path = ""
        if self._last_result:
            path = str(self._last_result.get("work_dir") or "")
        if path and Path(path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
