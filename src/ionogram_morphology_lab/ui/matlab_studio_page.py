"""MATLAB Studio page — editor, library, run, results."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
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
from ionogram_morphology_lab.matlab_studio.library import ScriptLibrary
from ionogram_morphology_lab.matlab_studio.plugins import PluginRegistry
from ionogram_morphology_lab.matlab_studio.runner import MatlabRunRequest, run_matlab_job
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


class _RunWorker(QThread):
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, req: MatlabRunRequest):
        super().__init__()
        self.req = req

    def run(self) -> None:
        try:
            res = run_matlab_job(self.req)
            self.finished_ok.emit(res.to_dict())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class MatlabStudioPage(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.library = ScriptLibrary()
        self.plugins = PluginRegistry()
        self._worker: _RunWorker | None = None
        self._current_script_id = "untitled"
        self._builtin_readonly = False
        self._current_builtin_id = ""
        self._build()
        self.refresh_backends()
        self.refresh_library()
        self.refresh_builtin()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        self.backend_label = QLabel()
        root.addWidget(self.backend_label)
        self.trust_label = QLabel("No MATLAB script selected for execution.")
        self.trust_label.setWordWrap(True)
        root.addWidget(self.trust_label)
        split = QSplitter()
        left = QWidget()
        ll = QVBoxLayout(left)
        self.lib_list = QListWidget()
        self.lib_list.currentTextChanged.connect(self._open_from_library)
        ll.addWidget(QLabel("Script library"))
        ll.addWidget(self.lib_list, 1)
        ll.addWidget(QLabel("Built-in MATLAB methods (read-only)"))
        self.builtin_list = QListWidget()
        self.builtin_list.currentTextChanged.connect(self._open_builtin)
        ll.addWidget(self.builtin_list, 1)
        for text, slot in [
            ("New", self._new),
            ("Open…", self._open),
            ("Import folder…", self._import_folder),
            ("Save", self._save),
            ("History", self._history),
            ("Register plugin", self._register_plugin),
            ("Create editable copy", self._copy_builtin),
            ("Export built-in package", self._export_builtin),
            ("Open built-in docs", self._open_builtin_docs),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            ll.addWidget(b)
        split.addWidget(left)

        center = QWidget()
        cl = QVBoxLayout(center)
        self.editor_tabs = QTabWidget()
        self.editor = QPlainTextEdit()
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.editor.setFont(font)
        self._highlighter = MatlabHighlighter(self.editor.document())
        self.editor_tabs.addTab(self.editor, "untitled.m*")
        cl.addWidget(self.editor_tabs, 1)
        run_row = QHBoxLayout()
        self.run_target = QComboBox()
        self.run_target.addItems(
            ["current_frame", "selected_range", "one_file", "folder"]
        )
        self.btn_run = QPushButton("Run")
        self.btn_run.clicked.connect(self._run)
        self.allow_write = QCheckBox("Allow write to external folder (advanced)")
        run_row.addWidget(self.run_target)
        run_row.addWidget(self.btn_run)
        run_row.addWidget(self.allow_write)
        cl.addLayout(run_row)
        split.addWidget(center)

        right = QWidget()
        rl = QVBoxLayout(right)
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        rl.addWidget(QLabel("MATLAB Results"))
        rl.addWidget(self.results, 1)
        self.api_info = QPlainTextEdit()
        self.api_info.setReadOnly(True)
        self.api_info.setPlainText("API:\n" + "\n".join(API_FUNCTIONS))
        rl.addWidget(self.api_info)
        split.addWidget(right)
        split.setSizes([220, 600, 320])
        root.addWidget(split, 1)

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
        lines = [f"Active: {active.backend_id} ({active.status}) v={active.version}"]
        for b in backends:
            lines.append(f"- {b.backend_id}: available={b.available} {b.path} {'; '.join(b.warnings)}")
        self.backend_label.setText("\n".join(lines))
        self.btn_run.setEnabled(active.backend_id != "none" and active.available)
        if not self.btn_run.isEnabled():
            self.btn_run.setToolTip("No execution backend — editor still works.")

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
        self.results.setPlainText(json.dumps(hist, indent=2, ensure_ascii=False))

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
            f"target={self.run_target.currentText()}, "
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
        if not self.session.has_real_import() and self.run_target.currentText() == "current_frame":
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
        self.results.setPlainText(trust_details + "\n\nRunning…")
        self._worker = _RunWorker(req)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.failed.connect(lambda e: self.results.setPlainText(e))
        self._worker.start()

    def _on_done(self, payload: dict) -> None:
        self.results.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False))
        if payload.get("status") == "no_backend":
            QMessageBox.information(
                self,
                "MATLAB Studio",
                payload.get("error_message")
                or "No backend available. Editor and packaging still work.",
            )
