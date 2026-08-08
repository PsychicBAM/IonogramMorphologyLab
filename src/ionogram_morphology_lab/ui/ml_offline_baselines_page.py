"""ML-C.1b Offline ML Baselines workspace — label integrity + live RU/EN."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.ml_dataset_manifests.store import MLDatasetManifestStore
from ionogram_morphology_lab.ml_offline_baselines import (
    ExperimentConfig,
    OfflineBaselineStore,
    run_experiment,
)
from ionogram_morphology_lab.ml_offline_baselines.baselines import list_baselines
from ionogram_morphology_lab.ml_offline_baselines.constants import (
    FEATURE_EXTRACTOR_VERSION,
    OFFLINE_BASELINE_PROTOCOL_VERSION,
    SUPPORTED_TASK,
)
from ionogram_morphology_lab.ml_offline_baselines.display_labels import (
    baseline_label,
    format_metric_value,
    format_optional_cell,
    morphology_display_name,
    sealed_short,
    state_label,
)
from ionogram_morphology_lab.ml_offline_baselines.label_integrity import (
    scan_prediction_rows_for_invalid_labels,

)
from ionogram_morphology_lab.ml_offline_baselines.source_resolve import (
    build_index_from_directory,
)
from ionogram_morphology_lab.ui.workspace_panels import (
    CollapsibleSection,
    ColumnVisibilityController,
)

_ROLE = Qt.ItemDataRole.UserRole

_STAGE_KEYS = {
    "Indexing project source files": "baselines.stage_index",
    "Loading train and development manifests": "baselines.stage_load",
    "Extracting single-frame features": "baselines.stage_features",
    "Fitting baseline": "baselines.stage_fit",
    "Predicting development set": "baselines.stage_predict",
    "Writing development artifacts": "baselines.stage_write",
    "Completed development-only baseline": "baselines.stage_done",
    "complete": "baselines.stage_done",
}


class BaselineWorker(QThread):
    """Worker with cancel ≠ success and success only after 100% progress."""

    progress = Signal(int, str)
    finished_ok = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    VALIDATE = "validate"
    RUN = "run"

    def __init__(
        self,
        mode: str,
        store: OfflineBaselineStore,
        manifest_store: MLDatasetManifestStore,
        experiment_id: str,
        project_root: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self.store = store
        self.manifest_store = manifest_store
        self.experiment_id = experiment_id
        self.project_root = project_root
        self._cancel = False
        self._terminal = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            self.progress.emit(3, "Indexing project source files")
            source_index = build_index_from_directory(self.project_root)
            if self._cancel:
                self.store.mark_cancelled(self.experiment_id)
                self._emit_cancelled()
                return
            if self.mode == self.VALIDATE:
                result = self.store.validate(
                    self.experiment_id, self.manifest_store, source_index
                )
            else:
                result = run_experiment(
                    self.store,
                    self.manifest_store,
                    self.experiment_id,
                    source_index,
                    progress_cb=lambda pct, msg: self.progress.emit(pct, msg),
                    cancel_cb=lambda: self._cancel,
                )
            if self._cancel or getattr(result, "state", "") == "cancelled":
                self._emit_cancelled()
                return
            self.progress.emit(100, "complete")
            self._terminal = True
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            if self._cancel:
                self._emit_cancelled()
            else:
                self._terminal = True
                self.failed.emit(str(exc))

    def _emit_cancelled(self) -> None:
        if not self._terminal:
            self._terminal = True
            self.cancelled.emit("cancelled")


class MLOfflineBaselinesPage(QWidget):
    """Readable Offline ML Baselines workspace (ML-C.1b)."""

    def __init__(self, session: Any, i18n: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self._store: OfflineBaselineStore | None = None
        self._manifest_store: MLDatasetManifestStore | None = None
        self._project_root: Path | None = None
        self._worker: BaselineWorker | None = None
        self._current_id = ""
        self._panel_visible = {
            "dataset": True,
            "features": True,
            "per_class": True,
            "errors": True,
            "provenance": True,
            "run_log": True,
            "technical": True,
        }
        self._build_ui()
        self.retranslate()

    def _t(self, key: str, fallback: str = "") -> str:
        try:
            return self.i18n.t(key, default=fallback or key)
        except Exception:  # noqa: BLE001
            return fallback or key

    def _lang(self) -> str:
        return "ru" if str(getattr(self.i18n, "language", "en")).startswith("ru") else "en"

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._status = QLabel()
        self._status.setObjectName("ml_baselines_status")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        self._holdout = QLabel()
        self._holdout.setObjectName("ml_baselines_holdout_sealed")
        self._holdout.setWordWrap(True)
        root.addWidget(self._holdout)

        self._immutable = QLabel()
        self._immutable.setObjectName("ml_baselines_immutable_banner")
        self._immutable.setWordWrap(True)
        self._immutable.hide()
        root.addWidget(self._immutable)

        self._dev_warning = QLabel()
        self._dev_warning.setObjectName("ml_baselines_development_warning")
        self._dev_warning.setWordWrap(True)
        self._dev_warning.hide()
        root.addWidget(self._dev_warning)

        actions = QHBoxLayout()
        self._btn_new = QPushButton()
        self._btn_validate = QPushButton()
        self._btn_run = QPushButton()
        self._btn_export = QPushButton()
        self._btn_cancel = QPushButton()
        self._btn_cancel.hide()
        self._more = QToolButton()
        self._more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._view = QToolButton()
        self._view.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        for btn in (
            self._btn_new,
            self._btn_validate,
            self._btn_run,
            self._btn_export,
            self._btn_cancel,
        ):
            actions.addWidget(btn)
        actions.addStretch(1)
        actions.addWidget(self._more)
        actions.addWidget(self._view)
        root.addLayout(actions)

        self._btn_new.clicked.connect(self._create_draft)
        self._btn_validate.clicked.connect(lambda: self._start(BaselineWorker.VALIDATE))
        self._btn_run.clicked.connect(lambda: self._start(BaselineWorker.RUN))
        self._btn_export.clicked.connect(self._export_summary)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._build_menus()

        self._main_split = QSplitter(Qt.Orientation.Vertical)
        top = QWidget()
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(0, 0, 0, 0)
        self._experiments = QListWidget()
        self._experiments.currentItemChanged.connect(self._on_selected)
        self._list_box = QGroupBox()
        box_l = QVBoxLayout(self._list_box)
        box_l.addWidget(self._experiments)
        top_l.addWidget(self._list_box, 1)

        self._setup = QWidget()
        setup_l = QFormLayout(self._setup)
        self._title = QLineEdit()
        self._analyst = QLineEdit()
        self._manifest = QComboBox()
        self._baseline = QComboBox()
        self._seed = QLineEdit()
        self._seed.setPlaceholderText("0")
        self._description = QLineEdit()
        self._setup_fields = (
            self._title,
            self._analyst,
            self._manifest,
            self._baseline,
            self._seed,
            self._description,
        )
        for widget in self._setup_fields:
            setup_l.addRow(QLabel(), widget)
        self._setup_labels = [
            setup_l.itemAt(i, QFormLayout.ItemRole.LabelRole).widget() for i in range(6)
        ]
        top_l.addWidget(self._setup, 2)
        self._main_split.addWidget(top)

        bottom = QWidget()
        bottom_l = QVBoxLayout(bottom)
        bottom_l.setContentsMargins(0, 0, 0, 0)
        self._progress = QProgressBar()
        self._progress.setMaximumHeight(18)
        bottom_l.addWidget(self._progress)
        self._tabs = QTabWidget()
        self._texts = [QTextEdit() for _ in range(6)]
        for text in self._texts:
            text.setReadOnly(True)
        self._confusion = QTableWidget()
        self._errors = QTableWidget()
        self._per_class = QTableWidget()
        for table in (self._confusion, self._errors, self._per_class):
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)
        self._error_headers = [
            "baselines.col_item",
            "baselines.col_group",
            "baselines.col_sequence",
            "baselines.col_date",
            "baselines.col_reference",
            "baselines.col_prediction",
            "baselines.col_correct",
        ]
        self._class_headers = [
            "baselines.col_class",
            "baselines.col_precision",
            "baselines.col_recall",
            "baselines.col_f1",
            "baselines.col_support",
        ]
        self._error_columns = ColumnVisibilityController(
            self._errors,
            ["Item", "Group", "Sequence", "Date", "Reference", "Prediction", "Correct?"],
            (0, 4, 5, 6),
        )
        self._class_columns = ColumnVisibilityController(
            self._per_class,
            ["Class", "Precision", "Recall", "F1", "Support"],
            (0,),
        )
        for _ in range(5):
            self._tabs.addTab(self._texts[_], "")
        evaluation = QWidget()
        evaluation_l = QVBoxLayout(evaluation)
        evaluation_l.setContentsMargins(4, 4, 4, 4)
        evaluation_l.addWidget(self._texts[5], 1)
        self._eval_split = QSplitter(Qt.Orientation.Horizontal)
        self._eval_split.addWidget(self._confusion)
        self._eval_split.addWidget(self._per_class)
        self._eval_split.setSizes([600, 400])
        evaluation_l.addWidget(self._eval_split, 2)
        self._tabs.addTab(evaluation, "")
        self._tabs.addTab(self._errors, "")
        self._summary = QTextEdit()
        self._summary.setReadOnly(True)
        self._tabs.addTab(self._summary, "")
        bottom_l.addWidget(self._tabs, 1)
        tech_body = QTextEdit()
        tech_body.setReadOnly(True)
        tech_body.setObjectName("ml_baselines_technical_body")
        self._tech_body = tech_body
        self._technical = CollapsibleSection(body=tech_body)
        tech_l = QVBoxLayout(self._technical)
        tech_l.addWidget(tech_body)
        self._technical.set_expanded(False)
        bottom_l.addWidget(self._technical)
        self._main_split.addWidget(bottom)
        self._main_split.setSizes([260, 620])
        root.addWidget(self._main_split, 1)

    def _build_menus(self) -> None:
        self._more_menu = QMenu(self)
        self._more_actions: dict[str, QAction] = {}
        for key, slot in (
            ("duplicate", self._duplicate),
            ("folder", self._open_folder),
            ("export_summary", self._export_summary),
            ("json", self._export_json),
            ("copy_id", self._copy_id),
            ("copy_manifest", self._copy_manifest),
            ("verify", self._verify_integrity),
            ("reset", self._reset_layout),
            ("technical", self._open_technical),
            ("archive", self._archive),
        ):
            action = self._more_menu.addAction("")
            action.triggered.connect(slot)
            self._more_actions[key] = action
        self._more.setMenu(self._more_menu)

        self._view_menu = QMenu(self)
        self._view_actions: dict[str, QAction] = {}
        for key in (
            "dataset",
            "features",
            "per_class",
            "errors",
            "provenance",
            "run_log",
            "technical",
        ):
            action = self._view_menu.addAction("")
            action.setCheckable(True)
            action.setChecked(self._panel_visible.get(key, True))
            action.toggled.connect(lambda shown, k=key: self._set_panel_visible(k, shown))
            self._view_actions[key] = action
        self._view_menu.addSeparator()
        self._view_all = self._view_menu.addAction("")
        self._view_all.triggered.connect(lambda: self._set_all_panels(True))
        self._view_secondary = self._view_menu.addAction("")
        self._view_secondary.triggered.connect(lambda: self._set_all_panels(False))
        self._view_reset = self._view_menu.addAction("")
        self._view_reset.triggered.connect(self._reset_layout)
        self._view.setMenu(self._view_menu)

    def retranslate(self) -> None:
        """Live RU/EN switch — preserve experiment/manifest/baseline/tab/layout."""
        lang = self._lang()
        keep_id = self._current_id
        keep_manifest = self._manifest.currentData()
        keep_baseline = self._baseline.currentData()
        keep_tab = self._tabs.currentIndex()
        keep_split = self._main_split.sizes()
        keep_eval = self._eval_split.sizes()
        keep_panels = dict(self._panel_visible)

        self._holdout.setText(
            self._t(
                "baselines.holdout_sealed",
                "Untouched Holdout: SEALED — not accessible in ML-C",
            )
        )
        self._dev_warning.setText(
            self._t(
                "baselines.development_note",
                "Development metrics are for model development only and are not independent validation.",
            )
        )
        self._immutable.setText(
            self._t(
                "baselines.immutable_banner",
                "Completed experiment — immutable.\n"
                "Create or duplicate an experiment to run another baseline.",
            )
        )
        self._btn_new.setText(self._t("baselines.new", "New Experiment"))
        self._btn_validate.setText(self._t("baselines.validate", "Validate Setup"))
        self._btn_run.setText(self._t("baselines.run", "Run Baseline"))
        self._btn_export.setText(self._t("baselines.export", "Export Summary"))
        self._btn_cancel.setText(self._t("baselines.cancel", "Cancel"))
        self._more.setText(self._t("baselines.more", "More ▾"))
        self._view.setText(self._t("baselines.view", "View"))
        self._list_box.setTitle(self._t("baselines.experiments", "Experiments"))

        for label, key, fallback in zip(
            self._setup_labels,
            (
                "baselines.title",
                "baselines.analyst",
                "baselines.frozen_manifest",
                "baselines.baseline",
                "baselines.seed",
                "baselines.description",
            ),
            ("Title", "Analyst", "Frozen Manifest", "Baseline", "Seed", "Description"),
        ):
            label.setText(self._t(key, fallback))

        for i in range(self._tabs.count()):
            self._tabs.setTabText(i, self._t(f"baselines.tab_{i}", f"Tab {i}"))
        self._technical.setTitle(self._t("baselines.technical", "Technical Details"))

        more_keys = {
            "duplicate": ("baselines.duplicate_as_new", "Duplicate as New"),
            "folder": ("baselines.open_folder", "Open Artifact Folder"),
            "export_summary": ("baselines.export", "Export Summary"),
            "json": ("baselines.export_json", "Export JSON"),
            "copy_id": ("baselines.copy_id", "Copy Experiment ID"),
            "copy_manifest": ("baselines.copy_manifest", "Copy Manifest ID"),
            "verify": ("baselines.verify_integrity", "Verify Integrity"),
            "reset": ("baselines.reset_layout", "Reset Layout"),
            "technical": ("baselines.open_technical", "Open Technical Details"),
            "archive": ("baselines.archive", "Archive Experiment"),
        }
        for key, (i18n_key, fallback) in more_keys.items():
            self._more_actions[key].setText(self._t(i18n_key, fallback))

        view_keys = {
            "dataset": ("baselines.view_dataset_details", "Dataset details"),
            "features": ("baselines.view_feature_details", "Feature details"),
            "per_class": ("baselines.view_per_class", "Per-class metrics"),
            "errors": ("baselines.view_errors", "Error explorer"),
            "provenance": ("baselines.view_provenance", "Provenance"),
            "run_log": ("baselines.view_run_log", "Run log"),
            "technical": ("baselines.view_technical", "Technical Details"),
        }
        for key, (i18n_key, fallback) in view_keys.items():
            self._view_actions[key].setText(self._t(i18n_key, fallback))
        self._view_all.setText(self._t("baselines.show_all", "Show all"))
        self._view_secondary.setText(
            self._t("baselines.hide_secondary", "Hide secondary panels")
        )
        self._view_reset.setText(self._t("baselines.reset_layout", "Reset Layout"))

        err_names = [self._t(k, k.split("_")[-1].title()) for k in self._error_headers]
        class_names = [self._t(k, k.split("_")[-1].title()) for k in self._class_headers]
        self._error_columns.set_names(err_names)
        self._class_columns.set_names(class_names)
        if self._errors.columnCount() == len(err_names):
            self._errors.setHorizontalHeaderLabels(err_names)
        if self._per_class.columnCount() == len(class_names):
            self._per_class.setHorizontalHeaderLabels(class_names)

        self._refresh_manifests(prefer=keep_manifest)
        self._refresh_baselines(prefer=keep_baseline)
        self._refresh_experiments(prefer=keep_id)
        if keep_id and self._store:
            try:
                self._load(keep_id, preserve_fields=False)
            except Exception:  # noqa: BLE001
                pass
        elif keep_manifest is not None:
            idx = self._manifest.findData(keep_manifest)
            if idx >= 0:
                self._manifest.setCurrentIndex(idx)
        if keep_baseline is not None:
            idx = self._baseline.findData(keep_baseline)
            if idx >= 0:
                self._baseline.setCurrentIndex(idx)
        self._tabs.setCurrentIndex(keep_tab)
        if keep_split:
            self._main_split.setSizes(keep_split)
        if keep_eval:
            self._eval_split.setSizes(keep_eval)
        for key, shown in keep_panels.items():
            self._panel_visible[key] = shown
            if key in self._view_actions:
                self._view_actions[key].blockSignals(True)
                self._view_actions[key].setChecked(shown)
                self._view_actions[key].blockSignals(False)
            self._apply_panel_visible(key, shown)
        self._refresh_actions()
        _ = lang  # language already applied via _t

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.on_project_changed()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._teardown(cancel=True)
        super().closeEvent(event)

    def on_project_changed(self) -> None:
        project = getattr(self.session, "project_path", None) or getattr(
            self.session, "active_project_path", None
        )
        if not project and getattr(self.session, "project", None):
            project = self.session.project.root
        if not project:
            self._store = self._manifest_store = None
            self._project_root = None
            self._current_id = ""
            self._status.setText(
                self._t("baselines.no_project", "Open a project to run offline baselines.")
            )
            self._refresh_actions()
            return
        self._project_root = Path(project)
        self._store = OfflineBaselineStore(self._project_root)
        self._manifest_store = MLDatasetManifestStore(self._project_root)
        self._refresh_manifests()
        self._refresh_baselines()
        self._refresh_experiments(prefer=self._current_id)

    def _refresh_manifests(self, prefer: Any = None) -> None:
        old = prefer if prefer is not None else self._manifest.currentData()
        self._manifest.blockSignals(True)
        self._manifest.clear()
        if self._manifest_store:
            for item in self._manifest_store.list_manifest_sets():
                if item.lifecycle_state == "frozen":
                    self._manifest.addItem(
                        f"{item.title} · {item.manifest_set_id}", item.manifest_set_id
                    )
        if old is not None:
            index = self._manifest.findData(old)
            if index >= 0:
                self._manifest.setCurrentIndex(index)
        self._manifest.blockSignals(False)

    def _refresh_baselines(self, prefer: Any = None) -> None:
        old = prefer if prefer is not None else self._baseline.currentData()
        self._baseline.blockSignals(True)
        self._baseline.clear()
        lang = self._lang()
        for baseline in list_baselines():
            version = baseline["version"]
            self._baseline.addItem(baseline_label(version, lang), version)
        if old is not None:
            index = self._baseline.findData(old)
            if index >= 0:
                self._baseline.setCurrentIndex(index)
        elif self._baseline.count():
            self._baseline.setCurrentIndex(0)
        self._baseline.blockSignals(False)

    def _refresh_experiments(self, prefer: str | None = None) -> None:
        target = prefer if prefer is not None else self._current_id
        self._experiments.blockSignals(True)
        self._experiments.clear()
        selected: QListWidgetItem | None = None
        if self._store:
            lang = self._lang()
            for record in sorted(
                self._store.list_experiments(), key=lambda r: r.updated_at, reverse=True
            ):
                row = QListWidgetItem(
                    f"{record.config.title} · {state_label(record.state, lang)}"
                )
                row.setData(_ROLE, record.experiment_id)
                self._experiments.addItem(row)
                if record.experiment_id == target:
                    selected = row
        if selected is not None:
            self._experiments.setCurrentItem(selected)
        self._experiments.blockSignals(False)
        if selected is None and not self._current_id:
            self._refresh_actions()
            self._update_status_compact(None)

    def _on_selected(self, item: QListWidgetItem | None, _old=None) -> None:
        if item:
            self._load(str(item.data(_ROLE)))

    def _load(self, experiment_id: str, *, preserve_fields: bool = True) -> None:
        if not self._store:
            return
        record = self._store.load_experiment(experiment_id)
        self._current_id = record.experiment_id
        c = record.config
        editable = record.state in {"draft", "failed", "cancelled", "validated"}
        for widget in self._setup_fields:
            widget.setEnabled(editable and record.state != "validated")
        if record.state == "validated":
            for widget in self._setup_fields:
                widget.setEnabled(False)
        self._title.setText(c.title)
        self._analyst.setText(c.analyst)
        self._description.setText(c.description)
        self._seed.setText(str(c.seed))
        idx = self._manifest.findData(c.manifest_set_id)
        if idx >= 0:
            self._manifest.setCurrentIndex(idx)
        elif c.manifest_set_id:
            self._manifest.addItem(c.manifest_set_id, c.manifest_set_id)
            self._manifest.setCurrentIndex(self._manifest.findData(c.manifest_set_id))
        idx = self._baseline.findData(c.baseline_version)
        if idx >= 0:
            self._baseline.setCurrentIndex(idx)
        _ = preserve_fields
        self._populate(record)
        self._refresh_actions()

    def _current_record(self) -> Any | None:
        if not self._store or not self._current_id:
            return None
        try:
            return self._store.load_experiment(self._current_id)
        except Exception:  # noqa: BLE001
            return None

    def _update_status_compact(self, record: Any | None) -> None:
        lang = self._lang()
        if record is None:
            if not self._manifest.count():
                self._status.setText(
                    self._t(
                        "baselines.no_frozen_manifest",
                        "A frozen leakage-safe ML-B manifest is required.",
                    )
                )
            else:
                self._status.setText(
                    self._t("baselines.status_idle", "Select or create an experiment.")
                )
            return
        state = state_label(record.state, lang)
        base = baseline_label(record.config.baseline_version, lang)
        n_dev = ""
        if record.state == "completed" and self._store:
            metrics = self._read_json(
                self._store.path_for(record.experiment_id) / "metrics_development.json"
            )
            n = metrics.get("item_count") or metrics.get("n") or metrics.get("n_items")
            if n is None:
                meta = self._read_json(
                    self._store.path_for(record.experiment_id) / "run_metadata.json"
                )
                n = meta.get("development_count")
            if n is not None:
                n_dev = f" · Development n={n}"
        hold = sealed_short(lang)
        short_manifest = (record.config.manifest_set_id or "")[:12]
        if record.state == "completed":
            self._status.setText(
                f"{state} · {base}{n_dev} · Holdout {hold}"
                if lang == "en"
                else f"{state} · {base}{n_dev} · Holdout {hold}"
            )
        elif record.state == "draft":
            self._status.setText(
                self._t(
                    "baselines.status_draft",
                    "Experiment draft · Manifest {mid} · Morphology · awaiting validation",
                ).format(mid=short_manifest or "—")
            )
        else:
            self._status.setText(f"{state} · {base} · Manifest {short_manifest}")

    def _populate(self, record: Any) -> None:
        lang = self._lang()
        base = self._store.path_for(record.experiment_id) if self._store else Path()
        train_n = dev_n = "—"
        meta = self._read_json(base / "run_metadata.json") if record.state == "completed" else {}
        if meta:
            train_n = str(meta.get("train_count", "—"))
            dev_n = str(meta.get("development_count", "—"))
        elif self._manifest_store and record.config.manifest_set_id:
            try:
                ms = self._manifest_store.load_manifest_set(record.config.manifest_set_id)
                counts = getattr(ms, "role_counts", {}) or {}
                train_n = str(counts.get("train", "—"))
                dev_n = str(counts.get("development", "—"))
            except Exception:  # noqa: BLE001
                pass

        # Setup tab — human-readable, never raw JSON
        if record.state == "completed":
            self._texts[0].setPlainText(
                "\n".join(
                    [
                        f"{self._t('baselines.state', 'State')}: {state_label(record.state, lang)}",
                        f"{self._t('baselines.baseline', 'Baseline')}: {baseline_label(record.config.baseline_version, lang)}",
                        f"{self._t('baselines.frozen_manifest', 'Frozen Manifest')}: {record.config.manifest_set_id}",
                        f"{self._t('baselines.train_count', 'Train items')}: {train_n}",
                        f"{self._t('baselines.dev_count', 'Development items')}: {dev_n}",
                        f"{self._t('baselines.holdout_unused', 'Untouched holdout: SEALED / UNUSED')}",
                        f"{self._t('baselines.completed_at', 'Completed')}: {record.completed_at or '—'}",
                    ]
                )
            )
        else:
            self._texts[0].setPlainText(
                "\n".join(
                    [
                        f"{self._t('baselines.title', 'Title')}: {record.config.title}",
                        f"{self._t('baselines.frozen_manifest', 'Frozen Manifest')}: {record.config.manifest_set_id or '—'}",
                        f"{self._t('baselines.task', 'Task')}: {self._t('baselines.task_morphology', 'Spread-F morphology classification')}",
                        f"{self._t('baselines.baseline', 'Baseline')}: {baseline_label(record.config.baseline_version, lang)}",
                        f"{self._t('baselines.extractor', 'Feature extractor')}: {record.config.feature_extractor_version}",
                        f"{self._t('baselines.train_count', 'Train items')}: {train_n}",
                        f"{self._t('baselines.dev_count', 'Development items')}: {dev_n}",
                        f"{self._t('baselines.holdout_short', 'Holdout')}: {sealed_short(lang)}",
                        f"{self._t('baselines.seed', 'Seed')}: {record.config.seed}",
                    ]
                )
            )

        self._texts[1].setPlainText(
            "\n".join(
                [
                    f"TRAIN: {train_n}",
                    f"DEVELOPMENT: {dev_n}",
                    f"UNTOUCHED HOLDOUT — {self._t('baselines.holdout_aggregate_only', 'aggregate only')}: {sealed_short(lang)}",
                    self._t(
                        "baselines.no_holdout_labels",
                        "No item-level holdout labels are available in ML-C.",
                    ),
                ]
            )
        )
        self._texts[2].setPlainText(
            "\n".join(
                [
                    f"{self._t('baselines.extractor', 'Feature extractor')}: {self._t('baselines.extractor_display', 'Single-frame pooled image 16×16')}",
                    f"{self._t('baselines.feature_count', 'Feature count')}: 256",
                    f"{self._t('baselines.uses_candidate', 'Uses candidate output')}: {self._t('baselines.no', 'No')}",
                    f"{self._t('baselines.uses_identity', 'Uses source/date IDs')}: {self._t('baselines.no', 'No')}",
                    f"{self._t('baselines.temporal', 'Temporal context')}: {self._t('baselines.no', 'No')}",
                ]
            )
        )
        self._texts[3].setPlainText(
            "\n".join(
                [
                    f"{baseline_label(record.config.baseline_version, lang)}",
                    f"{self._t('baselines.canonical_version', 'Canonical version')}: {record.config.baseline_version}",
                    f"{self._t('baselines.seed', 'Seed')}: {record.config.seed}",
                ]
            )
        )
        if record.validation_blockers:
            self._texts[4].setPlainText(
                self._t("baselines.validation_failed", "Validation blockers:")
                + "\n"
                + "\n".join(record.validation_blockers)
            )
        elif record.state == "validated":
            self._texts[4].setPlainText(self._t("baselines.ready_to_run", "Ready to run."))
        elif record.state == "completed":
            self._texts[4].setPlainText(
                self._t(
                    "baselines.run_completed_note",
                    "This experiment has completed. Create or duplicate to run again.",
                )
            )
        else:
            self._texts[4].setPlainText(
                self._t(
                    "baselines.validate_first",
                    "Validate setup before running.",
                )
            )

        self._summary.setPlainText(
            "\n".join(
                [
                    f"{self._t('baselines.experiment_id', 'Experiment ID')}: {record.experiment_id}",
                    f"{self._t('baselines.state', 'State')}: {state_label(record.state, lang)}",
                    f"{self._t('baselines.frozen_manifest', 'Frozen Manifest')}: {record.config.manifest_set_id}",
                    f"{self._t('baselines.task', 'Task')}: {self._t('baselines.task_morphology', 'Spread-F morphology classification')}",
                    f"{self._t('baselines.baseline', 'Baseline')}: {baseline_label(record.config.baseline_version, lang)}",
                    f"{self._t('baselines.extractor', 'Feature extractor')}: {record.config.feature_extractor_version}",
                    f"{self._t('baselines.train_count', 'Train items')}: {train_n}",
                    f"{self._t('baselines.dev_count', 'Development items')}: {dev_n}",
                    self._t("baselines.holdout_unused", "Untouched holdout: SEALED / UNUSED"),
                    self._t(
                        "baselines.limitations",
                        "Limitations: development-only agreement; not independent validation; holdout unused.",
                    ),
                ]
            )
        )

        tech_lines = [
            f"experiment_id={record.experiment_id}",
            f"state_canonical={record.state}",
            f"manifest_set_id={record.config.manifest_set_id}",
            f"baseline_version={record.config.baseline_version}",
            f"feature_extractor_version={record.config.feature_extractor_version}",
            f"protocol={record.protocol_version or OFFLINE_BASELINE_PROTOCOL_VERSION}",
            f"config_hash={record.config_hash}",
            f"artifact_dir={base}",
        ]
        if record.state == "completed":
            tech_lines.append(f"summary_path={base / 'experiment_summary.json'}")
            tech_lines.append(f"model_hash={record.model_hash}")
            tech_lines.append(f"metrics_hash={record.metrics_hash}")
        self._tech_body.setPlainText("\n".join(tech_lines))

        self._immutable.setVisible(record.state == "completed")
        if record.state == "completed":
            self._dev_warning.show()
            metrics = self._read_json(base / "metrics_development.json")
            lang = self._lang()
            overall = format_metric_value(metrics.get("overall_agreement"), lang)
            macro = format_metric_value(metrics.get("macro_f1"), lang)
            per_class = metrics.get("per_class", metrics.get("per_class_metrics", {}))
            classes = metrics.get("valid_target_classes") or (
                metrics.get("confusion_matrix", {}) or {}
            ).get("labels", [])
            support_lines = []
            if isinstance(per_class, list):
                for row in per_class:
                    if isinstance(row, dict):
                        support_lines.append(
                            f"  {row.get('class', '')}: {row.get('support', 0)}"
                        )
            elif isinstance(per_class, dict):
                for klass, values in per_class.items():
                    support = values.get("support", 0) if isinstance(values, dict) else 0
                    support_lines.append(f"  {klass}: {support}")
            groups = {
                str(row.get("atomic_group_id") or "")
                for row in self._read_jsonl(base / "predictions_development.jsonl")
                if row.get("atomic_group_id")
            }
            self._texts[5].setPlainText(
                "\n".join(
                    [
                        self._t(
                            "baselines.metrics_heading",
                            "Development-set agreement against selected expert reference labels",
                        ),
                        f"{self._t('baselines.dev_count', 'Development items')}: {dev_n}",
                        f"{self._t('baselines.dev_groups', 'Development atomic groups')}: {len(groups)}",
                        f"{self._t('baselines.overall_agreement', 'Overall agreement')}: {overall}",
                        f"{self._t('baselines.macro_f1', 'Macro F1')}: {macro}",
                        f"{self._t('baselines.valid_classes', 'Valid target classes')}: "
                        + (", ".join(str(c) for c in classes) if classes else "—"),
                        self._t("baselines.exact_supports", "Exact supports:"),
                        *(support_lines or ["  —"]),
                        self._t(
                            "baselines.development_note",
                            "Development metrics only — not independent validation.",
                        ),
                    ]
                )
            )
            self._fill_confusion(metrics.get("confusion_matrix", {}))
            self._fill_errors(base)
            self._fill_per_class(per_class)
        else:
            self._dev_warning.hide()
            self._texts[5].clear()
            self._confusion.clear()
            self._errors.clear()
            self._per_class.clear()
        self._update_status_compact(record)

    def _read_json(self, path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        try:
            return [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except Exception:
            return []

    def _fill_confusion(self, data: Any) -> None:
        if not isinstance(data, dict):
            self._confusion.clear()
            return
        lang = self._lang()
        labels = list(data.get("labels", []))
        matrix = data.get("matrix", data.get("values", []))
        display = [morphology_display_name(str(x), lang) for x in labels]
        self._confusion.setColumnCount(len(labels))
        self._confusion.setRowCount(len(labels))
        self._confusion.setHorizontalHeaderLabels(display)
        self._confusion.setVerticalHeaderLabels(display)
        for r, row in enumerate(matrix):
            for c, value in enumerate(row):
                self._confusion.setItem(r, c, QTableWidgetItem(str(value)))

    def _fill_errors(self, base: Path) -> None:
        """Prefer complete DEVELOPMENT predictions; fall back to error_cases aliases."""
        rows = self._read_jsonl(base / "predictions_development.jsonl")
        if not rows:
            raw = self._read_jsonl(base / "error_cases.jsonl")
            rows = []
            for row in raw:
                rows.append(
                    {
                        "item_id": row.get("item_id"),
                        "atomic_group_id": row.get("atomic_group_id"),
                        "sequence_id": row.get("sequence_id"),
                        "source_date": row.get("source_date"),
                        "expert_reference": row.get(
                            "expert_reference", row.get("expert_label")
                        ),
                        "prediction": row.get(
                            "prediction", row.get("predicted_label")
                        ),
                        "correct": row.get("correct", False),
                    }
                )
        headers = [self._t(k, k) for k in self._error_headers]
        self._errors.setColumnCount(len(headers))
        self._errors.setHorizontalHeaderLabels(headers)
        self._errors.setRowCount(len(rows))
        yes = self._t("baselines.yes", "Yes")
        no = self._t("baselines.no", "No")
        for r, row in enumerate(rows):
            correct = row.get("correct")
            if correct is None and row.get("expert_reference") is not None:
                correct = row.get("prediction") == row.get("expert_reference")
            correct_txt = (
                yes if correct is True else no if correct is False else format_optional_cell(None)
            )
            cells = (
                format_optional_cell(row.get("item_id")),
                format_optional_cell(row.get("atomic_group_id")),
                format_optional_cell(row.get("sequence_id")),
                format_optional_cell(row.get("source_date")),
                format_optional_cell(row.get("expert_reference", row.get("expert_label"))),
                format_optional_cell(row.get("prediction", row.get("predicted_label"))),
                correct_txt,
            )
            for c, value in enumerate(cells):
                self._errors.setItem(r, c, QTableWidgetItem(str(value)))

    def _fill_per_class(self, data: Any) -> None:
        headers = [self._t(k, k) for k in self._class_headers]
        self._per_class.setColumnCount(len(headers))
        self._per_class.setHorizontalHeaderLabels(headers)
        lang = self._lang()
        if isinstance(data, list):
            rows = [
                (
                    row.get("class", row.get("label", "")),
                    row,
                )
                for row in data
                if isinstance(row, dict)
            ]
        elif isinstance(data, dict):
            rows = list(data.items())
        else:
            rows = []
        self._per_class.setRowCount(len(rows))
        for r, (klass, values) in enumerate(rows):
            values = values if isinstance(values, dict) else {}
            cells = (
                morphology_display_name(str(klass), lang),
                format_metric_value(values.get("precision"), lang),
                format_metric_value(values.get("recall"), lang),
                format_metric_value(values.get("f1", values.get("f1_score")), lang),
                format_optional_cell(values.get("support")),
            )
            for c, value in enumerate(cells):
                self._per_class.setItem(r, c, QTableWidgetItem(str(value)))

    def _create_draft(self) -> None:
        if not self._store:
            return
        if not self._manifest.count() or not self._manifest.currentData():
            QMessageBox.information(
                self,
                self._t("baselines.blocked", "Baseline blocked"),
                self._t(
                    "baselines.no_frozen_manifest",
                    "A frozen leakage-safe ML-B manifest is required.",
                ),
            )
            self._refresh_actions()
            return
        if not self._baseline.count():
            self._refresh_baselines()
        prior_manifest = self._manifest.currentData()
        prior_baseline = self._baseline.currentData()
        prior_analyst = self._analyst.text().strip() or "analyst"
        try:
            seed = int(self._seed.text().strip() or "0")
        except ValueError:
            seed = 0
        title = self._t("baselines.default_title", "Offline baseline experiment")
        # Avoid keeping a completed title on the new draft
        record = self._store.create_draft(
            ExperimentConfig(
                title=title,
                analyst=prior_analyst,
                manifest_set_id=str(prior_manifest),
                task_contract=SUPPORTED_TASK,
                baseline_version=str(prior_baseline or self._baseline.itemData(0)),
                feature_extractor_version=FEATURE_EXTRACTOR_VERSION,
                seed=seed,
                description="",
            )
        )
        self._current_id = record.experiment_id
        self._refresh_experiments(prefer=record.experiment_id)
        self._load(record.experiment_id)
        self._tabs.setCurrentIndex(0)

    def _sync_draft_from_form(self) -> None:
        if not self._store or not self._current_id:
            return
        record = self._store.load_experiment(self._current_id)
        if record.state not in {"draft", "failed", "cancelled"}:
            return
        try:
            seed = int(self._seed.text().strip() or "0")
        except ValueError:
            seed = record.config.seed
        cfg = ExperimentConfig(
            title=self._title.text().strip()
            or self._t("baselines.default_title", "Offline baseline experiment"),
            analyst=self._analyst.text().strip(),
            manifest_set_id=str(self._manifest.currentData() or record.config.manifest_set_id),
            task_contract=SUPPORTED_TASK,
            baseline_version=str(
                self._baseline.currentData() or record.config.baseline_version
            ),
            feature_extractor_version=FEATURE_EXTRACTOR_VERSION,
            seed=seed,
            description=self._description.text().strip(),
        )
        self._store.save_draft(record, cfg)

    def _start(self, mode: str) -> None:
        if not self._store or not self._manifest_store or not self._project_root:
            return
        if not self._current_id:
            return
        record = self._store.load_experiment(self._current_id)
        if record.state == "completed":
            return
        if mode == BaselineWorker.VALIDATE:
            self._sync_draft_from_form()
        if mode == BaselineWorker.RUN and record.state != "validated":
            # Reload after possible sync
            record = self._store.load_experiment(self._current_id)
            if record.state != "validated":
                return
        self._teardown(cancel=True)
        self._progress.setValue(0)
        self._refresh_actions(running=True)
        self._worker = BaselineWorker(
            mode,
            self._store,
            self._manifest_store,
            self._current_id,
            self._project_root,
            self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._finished)
        self._worker.failed.connect(self._failed)
        self._worker.cancelled.connect(self._cancelled)
        self._worker.finished.connect(self._worker_finished)
        self._worker.start()

    def _on_progress(self, pct: int, message: str) -> None:
        self._progress.setValue(min(99, int(pct)))
        key = _STAGE_KEYS.get(message)
        self._status.setText(self._t(key, message) if key else message)

    def _finished(self, record: Any) -> None:
        self._progress.setValue(100)
        self._status.setText(self._t("baselines.success", "Operation completed."))
        self._refresh_experiments(prefer=record.experiment_id)
        self._load(record.experiment_id)
        if record.state == "completed":
            QMessageBox.information(
                self,
                self._t("baselines.completed", "Baseline completed"),
                self._t(
                    "baselines.completed_message",
                    "Experiment completed.\nUntouched holdout: SEALED and unused.",
                ),
            )
        elif record.state == "validated":
            QMessageBox.information(
                self,
                self._t("baselines.validated_title", "Validation passed"),
                self._t(
                    "baselines.validated_message",
                    "Setup validation passed. Run Baseline is now enabled.",
                ),
            )

    def _failed(self, message: str) -> None:
        self._status.setText(message)
        QMessageBox.warning(self, self._t("baselines.error", "Error"), message)
        if self._current_id:
            self._refresh_experiments(prefer=self._current_id)
            self._load(self._current_id)

    def _cancelled(self, _message: str) -> None:
        self._status.setText(self._t("baselines.cancelled", "Cancelled"))
        self._progress.setValue(min(self._progress.value(), 99))
        if self._current_id:
            self._refresh_experiments(prefer=self._current_id)
            self._load(self._current_id)

    def _worker_finished(self) -> None:
        self._worker = None
        self._refresh_actions()

    def _on_cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
            self._status.setText(
                self._t("baselines.cancel_requested", "Cancellation requested…")
            )

    def _teardown(self, cancel: bool = False) -> None:
        if self._worker and cancel and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        self._worker = None

    def _refresh_actions(self, *, running: bool = False) -> None:
        record = self._current_record()
        state = record.state if record else ""
        has_frozen = bool(self._manifest.count())
        is_running = running or state == "running" or self._worker is not None

        self._btn_cancel.setVisible(is_running)
        self._btn_cancel.setEnabled(is_running)

        self._btn_new.setVisible(True)
        self._btn_new.setEnabled(has_frozen and not is_running)

        if not has_frozen and not self._current_id:
            self._btn_validate.hide()
            self._btn_run.hide()
            self._btn_export.hide()
            self._immutable.hide()
            self._update_status_compact(None)
            self._set_more_visibility([])
            return

        if state in {"draft", "failed", "cancelled"}:
            self._btn_validate.show()
            self._btn_validate.setEnabled(not is_running)
            self._btn_run.show()
            self._btn_run.setEnabled(False)
            self._btn_export.hide()
            self._immutable.hide()
            more = [
                "duplicate",
                "folder",
                "copy_id",
                "copy_manifest",
                "reset",
                "technical",
                "archive",
            ]
        elif state == "validated":
            self._btn_validate.show()
            self._btn_validate.setEnabled(not is_running)
            self._btn_run.show()
            self._btn_run.setEnabled(not is_running)
            self._btn_export.hide()
            self._immutable.hide()
            more = [
                "duplicate",
                "folder",
                "copy_id",
                "copy_manifest",
                "reset",
                "technical",
                "archive",
            ]
        elif state == "running" or is_running:
            self._btn_validate.hide()
            self._btn_run.hide()
            self._btn_export.hide()
            self._immutable.hide()
            more = ["technical"]
        elif state == "completed":
            self._btn_validate.hide()
            self._btn_run.hide()
            self._btn_export.show()
            self._btn_export.setEnabled(True)
            self._immutable.show()
            more = [
                "duplicate",
                "folder",
                "export_summary",
                "json",
                "copy_id",
                "copy_manifest",
                "verify",
                "reset",
                "technical",
                "archive",
            ]
        elif state == "archived":
            self._btn_validate.hide()
            self._btn_run.hide()
            self._btn_export.show()
            self._immutable.show()
            more = ["folder", "json", "copy_id", "copy_manifest", "technical"]
        else:
            # No selection — encourage New Experiment
            self._btn_validate.hide()
            self._btn_run.hide()
            self._btn_export.hide()
            self._immutable.hide()
            more = ["reset", "technical"]
        self._set_more_visibility(more)

    def _set_more_visibility(self, keys: list[str]) -> None:
        allowed = set(keys)
        for key, action in self._more_actions.items():
            action.setVisible(key in allowed)

    def _set_panel_visible(self, key: str, shown: bool) -> None:
        self._panel_visible[key] = shown
        self._apply_panel_visible(key, shown)

    def _apply_panel_visible(self, key: str, shown: bool) -> None:
        if key == "dataset":
            self._list_box.setVisible(shown)
        elif key == "features":
            self._setup.setVisible(shown)
        elif key == "per_class":
            self._per_class.setVisible(shown)
        elif key == "errors":
            self._errors.setVisible(shown)
        elif key == "technical":
            # Critical holdout banner stays; technical panel may hide
            self._technical.setVisible(shown)
        elif key == "provenance":
            # Provenance is represented by summary/tech — keep holdout visible always
            pass
        elif key == "run_log":
            self._progress.setVisible(shown)

    def _set_all_panels(self, shown: bool) -> None:
        for key, action in self._view_actions.items():
            # Never allow permanently hiding holdout via View — holdout label is outside View
            action.blockSignals(True)
            action.setChecked(True if key == "technical" and not shown else shown)
            action.blockSignals(False)
            self._set_panel_visible(
                key, True if key == "technical" and not shown else shown
            )
        if not shown:
            # Hide secondary only — keep dataset list + setup visible for workflow
            for key in ("per_class", "errors", "provenance", "run_log", "technical"):
                if key in self._view_actions:
                    self._view_actions[key].blockSignals(True)
                    self._view_actions[key].setChecked(False)
                    self._view_actions[key].blockSignals(False)
                    self._set_panel_visible(key, False)
            for key in ("dataset", "features"):
                self._view_actions[key].blockSignals(True)
                self._view_actions[key].setChecked(True)
                self._view_actions[key].blockSignals(False)
                self._set_panel_visible(key, True)

    def _reset_layout(self) -> None:
        self._set_all_panels(True)
        self._technical.set_expanded(False)
        self._error_columns.reset()
        self._class_columns.reset()
        self._main_split.setSizes([260, 620])
        self._eval_split.setSizes([600, 400])

    def _open_technical(self) -> None:
        self._technical.setVisible(True)
        self._panel_visible["technical"] = True
        self._view_actions["technical"].blockSignals(True)
        self._view_actions["technical"].setChecked(True)
        self._view_actions["technical"].blockSignals(False)
        self._technical.set_expanded(True)

    def _verify_integrity(self) -> None:
        """Read-only integrity check — does not mutate completed artifacts."""
        if not self._store or not self._current_id:
            return
        record = self._store.load_experiment(self._current_id)
        path = self._store.path_for(record.experiment_id)
        report = self._read_json(path / "integrity_report.json")
        ok = bool(report.get("ok", False)) and record.state == "completed"
        missing = [
            name
            for name in (
                "experiment.json",
                "metrics_development.json",
                "predictions_development.jsonl",
            )
            if not (path / name).exists()
        ]
        if missing:
            ok = False
        bad_labels = scan_prediction_rows_for_invalid_labels(
            self._read_jsonl(path / "predictions_development.jsonl")
        )
        if bad_labels:
            ok = False
        title = self._t("baselines.verify_integrity", "Verify Integrity")
        body = (
            self._t("baselines.integrity_ok", "Integrity check passed (read-only).")
            if ok
            else self._t(
                "baselines.integrity_fail",
                "Integrity check reported problems (read-only; artifacts not modified).",
            )
        )
        if missing:
            body += "\n" + ", ".join(missing)
        if bad_labels:
            body += "\n" + self._t(
                "baselines.integrity_invalid_label",
                "Prediction artifact contains an invalid morphology label.",
            )
            body += " " + ", ".join(f"`{x}`" for x in bad_labels)
        QMessageBox.information(self, title, body)

    def _duplicate(self) -> None:
        if self._store and self._current_id:
            parent = self._store.load_experiment(self._current_id)
            record = self._store.create_revision(self._current_id)
            # Ensure new draft is selected and editable
            self._current_id = record.experiment_id
            self._refresh_experiments(prefer=record.experiment_id)
            self._load(record.experiment_id)
            self._tabs.setCurrentIndex(0)
            _ = parent

    def _archive(self) -> None:
        if self._store and self._current_id:
            self._store.archive(self._current_id)
            self._refresh_experiments(prefer=self._current_id)
            self._load(self._current_id)

    def _copy_id(self) -> None:
        if self._current_id:
            QApplication.clipboard().setText(self._current_id)

    def _copy_manifest(self) -> None:
        mid = self._manifest.currentData()
        if mid:
            QApplication.clipboard().setText(str(mid))

    def _open_folder(self) -> None:
        if self._store and self._current_id:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self._store.path_for(self._current_id)))
            )

    def _export_summary(self) -> None:
        """Export summary path goes to Technical Details / clipboard — not header."""
        if not self._store or not self._current_id:
            return
        path = self._store.path_for(self._current_id) / "experiment_summary.json"
        QApplication.clipboard().setText(str(path))
        body = self._tech_body.toPlainText()
        line = f"export_summary_path={path}"
        if line not in body:
            self._tech_body.setPlainText(body + ("\n" if body else "") + line)
        QMessageBox.information(
            self,
            self._t("baselines.export", "Export Summary"),
            self._t(
                "baselines.export_summary_copied",
                "Summary path copied to clipboard. Full path is listed under Technical Details.",
            ),
        )

    def _export_json(self) -> None:
        if not self._store or not self._current_id:
            return
        path = self._store.path_for(self._current_id) / "experiment.json"
        QApplication.clipboard().setText(str(path))
        body = self._tech_body.toPlainText()
        line = f"export_json_path={path}"
        if line not in body:
            self._tech_body.setPlainText(body + ("\n" if body else "") + line)
