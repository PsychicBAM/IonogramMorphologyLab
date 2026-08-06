"""IML-2 bilingual research shell: real viewer, batch UX, help, settings."""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import shutil
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import QSignalBlocker, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

_LOG = logging.getLogger(__name__)

from ionogram_morphology_lab import __version__
from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.cache.frame_store import FrameStore
from ionogram_morphology_lab.database.project_db import ProjectDatabase
from ionogram_morphology_lab.help.content import HELP_SECTIONS, search_help
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.importers.audit import audit_mat_path
from ionogram_morphology_lab.importers.mat_inventory import list_mat_files
from ionogram_morphology_lab.instrument_profiles.schema import (
    frequency_axis_from_profile,
    load_profile,
    range_axis_from_profile,
)
from ionogram_morphology_lab.instrument_profiles.wizard import ProfileWizardState
from ionogram_morphology_lab.projects.batch_selection import (
    DEFAULT_KFU_INTERVAL_MINUTES,
    estimate_resources,
    select_contact_sequence,
    select_custom_list,
    select_frame_range,
    select_full_day,
    select_single,
    select_time_range,
)
from ionogram_morphology_lab.projects.model import AnalysisProject, create_project
from ionogram_morphology_lab.ui.active_source import (
    ActiveSourceCard,
    confirm_imported_active,
    confirm_set_active,
    confirm_switch_active,
    open_file_folder,
    resolve_active_source,
)
from ionogram_morphology_lab.ui.compact_source_strip import CompactSourceStrip
from ionogram_morphology_lab.ui.import_file_list import ImportFileList
from ionogram_morphology_lab.ui.source_roles import (
    classify_mat_source,
    format_missing_variable_user_message,
    localize_role_message,
)
from ionogram_morphology_lab.ui.theme import apply_app_theme

from ionogram_morphology_lab.projects.pipeline import BatchController, batch_analyze
from ionogram_morphology_lab.projects.time_mapping import (
    format_hhmm,
    frame_to_minute,
    mapping_status,
    minute_to_frame,
    parse_hhmm,
)
from ionogram_morphology_lab.reference_atlas.atlas import load_atlas
from ionogram_morphology_lab.rendering.ionogram_render import RenderSpec, render_contact_sheet, render_raw_ionogram
from ionogram_morphology_lab.reports.export_reports import export_run_reports
from ionogram_morphology_lab.security import ForbiddenPathError, default_blocklist
from ionogram_morphology_lab.segmentation.trace_interference import segment_frame
from ionogram_morphology_lab.synthetic.generator import generate_synthetic_case
from ionogram_morphology_lab.ui.presenters import (
    audit_card,
    confidence_explanation,
    explain_result,
    morphology_label,
    profile_card,
)
from ionogram_morphology_lab.ui.display_values import display_status
from ionogram_morphology_lab.ui.analysis_pipeline_panel import AnalysisPipelinePanel
from ionogram_morphology_lab.ui.diffuse_explanation import explain_diffuse_unspecified
from ionogram_morphology_lab.ui.empty_state import EmptyStatePanel
from ionogram_morphology_lab.ui.scientific_status import (
    insufficient_examples_message,
    scientific_status_label,
    scientific_status_token,
)
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.utils.paths import app_root, ensure_dir
from ionogram_morphology_lab.review_dataset.store import ReviewDatasetStore

# Default Results columns (extra fields live in the details panel).
RESULTS_DEFAULT_COLUMNS = ("time", "morphology", "interference", "status", "scientific_status")
RESULTS_OPTIONAL_COLUMNS = (
    "frame",
    "layer",
    "quality",
    "ambiguity",
    "confidence",
    "ox",
)


NAV_KEYS = [
    ("home", "nav.home"),
    ("projects", "nav.projects"),
    ("import", "nav.import"),
    ("profile", "nav.profile"),
    ("audit", "nav.audit"),
    ("viewer", "nav.viewer"),
    ("sequences", "nav.sequences"),
    ("batch", "nav.batch"),
    ("results", "nav.results"),
    ("parameters", "nav.parameters"),
    ("campaigns", "nav.campaigns"),
    ("expert", "nav.expert"),
    ("disagreement", "nav.disagreement"),
    ("atlas", "nav.atlas"),
    ("science", "nav.science"),
    ("raw_signals", "nav.raw_signals"),
    ("feature_diagnostics", "nav.feature_diagnostics"),
    ("matlab", "nav.matlab"),
    ("rules", "nav.rules"),
    ("rule_test", "nav.rule_test"),
    ("compare", "nav.compare"),
    ("pipeline", "nav.pipeline"),
    ("models", "nav.models"),
    ("ml_readiness", "nav.ml_readiness"),
    ("reports", "nav.reports"),
    ("settings", "nav.settings"),
    ("help", "nav.help"),
]

NAV_GROUPS = [
    ("start", "nav_group.start", ("home", "projects", "import")),
    ("data", "nav_group.data", ("profile", "audit", "viewer", "sequences")),
    ("analysis", "nav_group.analysis", ("batch", "results", "parameters", "campaigns", "expert", "disagreement")),
    ("reports", "nav_group.reports", ("reports",)),
    ("methods", "nav_group.methods", ("matlab", "rules", "rule_test", "compare", "pipeline", "models", "ml_readiness")),
    ("resources", "nav_group.resources", ("atlas", "science", "raw_signals", "feature_diagnostics", "settings", "help")),
]
NAV_LABELS = dict(NAV_KEYS)
GUIDED_NAV_KEYS = {
    "home", "projects", "import", "profile", "audit", "viewer", "sequences",
    "batch", "results", "parameters", "campaigns", "expert", "disagreement",
    "ml_readiness", "reports", "settings", "help",
}


def tip_button(text_key: str, i18n) -> QToolButton:
    b = QToolButton()
    b.setText("?")
    b.setFixedWidth(22)
    b.setToolTip(i18n.t(text_key))
    b.setObjectName(f"tip_{text_key}")
    return b


class CacheBuildWorker(QThread):
    progress = Signal(dict)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, store: FrameStore):
        super().__init__()
        self.store = store

    def run(self) -> None:
        try:
            st = self.store.build_cache(progress_cb=lambda d: self.progress.emit(d))
            self.finished_ok.emit({"valid": st.valid, "path": st.path, "reason": st.reason})
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, language: str = "en") -> None:
        super().__init__()
        self.settings = SettingsStore()
        if language:
            self.settings.set("general", "language", language)
        self.i18n = get_i18n(self.settings.get("general", "language", language))
        self.session = AppSession(settings=self.settings)
        self.wizard = ProfileWizardState()
        self.batch_controller = BatchController()
        from ionogram_morphology_lab.matlab_studio.job_manager import MatlabJobManager

        self.matlab_jobs = MatlabJobManager(self)
        self.matlab_page = None
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._playback_tick)
        self._cache_worker: CacheBuildWorker | None = None
        self._syncing_time = False
        self._viewer_nav_busy = False
        self._viewer_ready = False
        self._viewer_n_frames = 0
        self._results_displayed_identity: dict | None = None
        self._viewer_render_timer = QTimer(self)
        self._viewer_render_timer.setSingleShot(True)
        self._viewer_render_timer.setInterval(80)
        self._viewer_render_timer.timeout.connect(self._render_current_frame_safe)
        # Phase 4B.2h page lifecycle counters
        self._page_builders: dict[str, Any] = {}
        self._page_materialized: dict[str, bool] = {}
        self.page_instance_created_count: dict[str, int] = {}
        self.page_activation_count: dict[str, int] = {}
        self.registry_reload_count = 0
        self.cache_scan_count = 0
        self.language_switch_io_count = 0
        self._retranslate_only = False
        self._lang_switch_t0 = 0.0
        self._page_language_dirty: dict[str, bool] = {}
        self._build_ui()
        self._bind_shortcuts()
        self._apply_theme()
        self.retranslate()
        self._set_viewer_controls_enabled(False)
        self._set_viewer_status("not_loaded")
        self._update_status_bar()
        self._start_packaged_profiler_if_enabled()
        try:
            from ionogram_morphology_lab.ui.build_identity import warm_executable_sha_async
            from ionogram_morphology_lab.ui.cancel_crash_audit import install_exception_hooks

            install_exception_hooks()
            warm_executable_sha_async()
        except Exception:  # noqa: BLE001
            pass
        # Warm persistent V2 worker after UI is idle — never blocks first paint.
        QTimer.singleShot(1500, self._warm_v2_worker)
        # Never auto-open modal onboarding under offscreen/CI (blocks pytest).
        import os

        if (
            self.settings.get("general", "show_onboarding", True)
            and os.environ.get("QT_QPA_PLATFORM", "").lower() != "offscreen"
            and os.environ.get("IML_DISABLE_ONBOARDING", "") != "1"
        ):
            QTimer.singleShot(300, self._maybe_onboarding)

    def t(self, key: str) -> str:
        return self.i18n.t(key)

    def _build_ui(self) -> None:
        self.setMinimumSize(1200, 780)
        try:
            from PySide6.QtGui import QIcon

            icon_path = app_root() / "assets" / "IonogramMorphologyLab.ico"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:  # noqa: BLE001
            pass
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        self.nav = QTreeWidget()
        self.nav.setFixedWidth(230)
        self.nav.setHeaderHidden(True)
        self.nav.setRootIsDecorated(True)
        self.nav.itemClicked.connect(self._on_nav_item)
        root.addWidget(self.nav)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.pages: dict[str, QWidget] = {}
        builders = {
            "home": self._page_home,
            "projects": self._page_project,
            "import": self._page_import,
            "profile": self._page_profile,
            "audit": self._page_audit,
            "viewer": self._page_viewer,
            "sequences": self._page_sequences,
            "batch": self._page_batch,
            "results": self._page_results,
            "parameters": self._page_parameters,
            "campaigns": self._page_campaigns,
            "expert": self._page_expert,
            "disagreement": self._page_disagreement,
            "atlas": self._page_atlas,
            "science": self._page_science,
            "raw_signals": self._page_raw_signals,
            "feature_diagnostics": self._page_feature_diagnostics,
            "matlab": self._page_matlab,
            "rules": self._page_rules,
            "rule_test": self._page_rule_test,
            "compare": self._page_compare,
            "pipeline": self._page_pipeline,
            "models": self._page_models,
            "ml_readiness": self._page_ml_readiness,
            "reports": self._page_reports,
            "settings": self._page_settings,
            "help": self._page_help,
        }
        from ionogram_morphology_lab.ui.page_intros import attach_intro

        # Heavy pages: create once on first visit (persistent thereafter).
        # Batch/MATLAB stay eager — other MainWindow wiring and acceptance tests
        # reference their controls immediately after construction.
        self._lazy_page_keys = {
            "feature_diagnostics",
            "raw_signals",
            "atlas",
            "compare",
            "pipeline",
            "models",
            "ml_readiness",
            "rule_test",
            "expert",
            "disagreement",
        }
        self._page_builders = dict(builders)
        self.intro_panels: dict[str, object] = {}
        for key, _ in NAV_KEYS:
            page = QWidget()
            layout = QVBoxLayout(page)
            title = QLabel(key)
            title.setObjectName(f"title_{key}")
            title.setStyleSheet("font-size: 18px; font-weight: 600;")
            layout.addWidget(title)
            # Skip bulky intro banner on Feature Diagnostics (page has its own compact help).
            if key != "feature_diagnostics":
                panel = attach_intro(key, layout, self.i18n, self.settings)
                if panel is not None:
                    self.intro_panels[key] = panel
            if key in self._lazy_page_keys:
                placeholder = QLabel("…")
                placeholder.setObjectName(f"lazy_placeholder_{key}")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(placeholder, 1)
                self._page_materialized[key] = False
                self.page_instance_created_count[key] = 0
            else:
                body = builders[key]()
                body.setObjectName(f"page_body_{key}")
                layout.addWidget(body, 1)
                self._page_materialized[key] = True
                self.page_instance_created_count[key] = 1
            self.page_activation_count[key] = 0
            self.pages[key] = page
            self.stack.addWidget(page)

        self._build_navigation()
        self._build_menus()

        tb = QToolBar(self.t("toolbar.title"), self)
        tb.setObjectName("main_toolbar")
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(tb)
        self.btn_collapse_nav = QPushButton("☰")
        self.btn_collapse_nav.setFixedWidth(36)
        self.btn_collapse_nav.clicked.connect(self._toggle_nav)
        tb.addWidget(self.btn_collapse_nav)
        for action_name in (
            "new_project", "open_project", "import_file", "import_folder",
            "save_project", "viewer", "run", "cancel",
        ):
            tb.addAction(self.actions[action_name])
        self.setStatusBar(QStatusBar())
        self.status_project = QLabel("")
        self.status_file = QLabel("")
        self.status_profile = QLabel("")
        self.status_cache = QLabel("")
        self.status_frame = QLabel("")
        self.status_task = QLabel("")
        for w in (
            self.status_project,
            self.status_file,
            self.status_profile,
            self.status_cache,
            self.status_frame,
            self.status_task,
        ):
            self.statusBar().addPermanentWidget(w)
        self._navigate_key("home")
        if self.settings.get("general", "nav_collapsed", False):
            self.nav.setVisible(False)

    def _build_navigation(self) -> None:
        self.nav_groups: dict[str, QTreeWidgetItem] = {}
        self.nav_items: dict[str, QTreeWidgetItem] = {}
        expanded = self.settings.get("ux", "nav_groups_expanded", {}) or {}
        for group_key, label_key, keys in NAV_GROUPS:
            group = QTreeWidgetItem([self.t(label_key)])
            group.setData(0, Qt.ItemDataRole.UserRole, None)
            group.setToolTip(0, self.t(label_key))
            group.setData(0, Qt.ItemDataRole.AccessibleTextRole, self.t(label_key))
            self.nav.addTopLevelItem(group)
            self.nav_groups[group_key] = group
            for key in keys:
                item = QTreeWidgetItem([self.t(NAV_LABELS[key])])
                item.setData(0, Qt.ItemDataRole.UserRole, key)
                item.setToolTip(0, self.t(NAV_LABELS[key]))
                item.setData(0, Qt.ItemDataRole.AccessibleTextRole, self.t(NAV_LABELS[key]))
                group.addChild(item)
                self.nav_items[key] = item
            default_expanded = group_key != "methods"
            group.setExpanded(bool(expanded.get(group_key, default_expanded)))
        self.nav.itemExpanded.connect(self._save_nav_group_state)
        self.nav.itemCollapsed.connect(self._save_nav_group_state)
        self._apply_ux_mode()

    def _save_nav_group_state(self, _item: QTreeWidgetItem) -> None:
        expanded = {
            key: item.isExpanded()
            for key, item in self.nav_groups.items()
        }
        self.settings.set("ux", "nav_groups_expanded", expanded)
        self.settings.save()

    def _apply_ux_mode(self) -> None:
        mode = self.settings.get("ux", "interface_mode", "guided")
        visible_keys = GUIDED_NAV_KEYS if mode == "guided" else set(NAV_LABELS)
        for key, item in self.nav_items.items():
            item.setHidden(key not in visible_keys)
        for group_key, _label_key, keys in NAV_GROUPS:
            group = self.nav_groups[group_key]
            group.setHidden(not any(key in visible_keys for key in keys))
            if mode == "research" and group_key == "methods":
                group.setExpanded(False)

    def _build_menus(self) -> None:
        self.actions: dict[str, QAction] = {}

        def add_action(name: str, text_key: str, slot, icon: QStyle.StandardPixmap | None = None) -> QAction:
            action = QAction(self)
            action.setObjectName(f"action_{name}")
            action.setData(text_key)
            action.triggered.connect(slot)
            if icon is not None:
                action.setIcon(self.style().standardIcon(icon))
            self.actions[name] = action
            return action

        add_action("new_project", "menu.new_project", lambda: self._navigate_key("projects"), QStyle.StandardPixmap.SP_FileIcon)
        add_action("open_project", "menu.open_project", self._open_project, QStyle.StandardPixmap.SP_DialogOpenButton)
        add_action("import_file", "menu.import_mat", self._import_file, QStyle.StandardPixmap.SP_FileIcon)
        add_action("import_folder", "menu.import_folder", self._import_folder, QStyle.StandardPixmap.SP_DirOpenIcon)
        add_action("save_project", "menu.save", self._save_project, QStyle.StandardPixmap.SP_DialogSaveButton)
        add_action("export", "menu.export", self._export_reports)
        add_action("exit", "menu.exit", self.close)
        add_action("viewer", "menu.viewer", lambda: self._navigate_key("viewer"), QStyle.StandardPixmap.SP_DesktopIcon)
        add_action("batch", "menu.batch", lambda: self._navigate_key("batch"))
        add_action("results", "menu.results", lambda: self._navigate_key("results"))
        add_action("run", "menu.run", self._batch_start, QStyle.StandardPixmap.SP_MediaPlay)
        add_action("cancel", "menu.cancel", lambda: self.batch_controller.cancel(), QStyle.StandardPixmap.SP_MediaStop)
        for name, key in (
            ("matlab", "matlab"), ("rules", "rules"), ("pipeline", "pipeline"),
            ("models", "models"), ("quick_start", "home"), ("help", "help"),
        ):
            add_action(name, f"menu.{name}", lambda _checked=False, nav_key=key: self._navigate_key(nav_key))
        add_action("about", "menu.about", self._show_about)
        add_action("build_identity", "menu.build_identity", self._show_build_identity)

        menus = self.menuBar()
        self.file_menu = menus.addMenu("")
        for name in ("new_project", "open_project", "import_file", "import_folder", "save_project", "export"):
            self.file_menu.addAction(self.actions[name])
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.actions["exit"])
        self.project_menu = menus.addMenu("")
        self.project_menu.addAction(self.actions["viewer"])
        self.analysis_menu = menus.addMenu("")
        for name in ("batch", "results", "run", "cancel"):
            self.analysis_menu.addAction(self.actions[name])
        self.tools_menu = menus.addMenu("")
        for name in ("matlab", "rules", "pipeline", "models"):
            self.tools_menu.addAction(self.actions[name])
        self.help_menu = menus.addMenu("")
        for name in ("quick_start", "help", "about", "build_identity"):
            self.help_menu.addAction(self.actions[name])

    def _toggle_nav(self) -> None:
        visible = not self.nav.isVisible()
        self.nav.setVisible(visible)
        self.settings.set("general", "nav_collapsed", not visible)
        self.settings.save()

    def _page_sequences(self) -> QWidget:
        # Temporal sequences — reuse contact-sheet / playback controls summary
        w = QWidget()
        lay = QVBoxLayout(w)
        self.seq_info = QLabel()
        self.seq_info.setWordWrap(True)
        btn = QPushButton()
        btn.setObjectName("btn_seq_contact")
        btn.clicked.connect(self._make_contact_sheet)
        lay.addWidget(self.seq_info)
        lay.addWidget(btn)
        lay.addStretch(1)
        return w

    def _page_campaigns(self) -> QWidget:
        from ionogram_morphology_lab.ui.expert_review_campaign_page import (
            ExpertReviewCampaignPage,
        )

        page = ExpertReviewCampaignPage(self.session, self.i18n, main_window=self)
        self._expert_review_campaign_page = page
        return page

    def _page_expert(self) -> QWidget:
        from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage

        page = ExpertReviewCorpusPage(self.session, self.i18n)
        self._expert_review_corpus_page = page
        return page

    def _page_disagreement(self) -> QWidget:
        from ionogram_morphology_lab.ui.disagreement_analysis_page import (
            DisagreementAnalysisPage,
        )

        page = DisagreementAnalysisPage(self.session, self.i18n)
        self._disagreement_analysis_page = page
        return page

    def _page_ml_readiness(self) -> QWidget:
        from ionogram_morphology_lab.ui.ml_data_readiness_page import MLDataReadinessPage

        page = MLDataReadinessPage(self.session, self.i18n)
        self._ml_data_readiness_page = page
        return page

    def _page_matlab(self) -> QWidget:
        from ionogram_morphology_lab.ui.matlab_studio_page import MatlabStudioPage

        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        self.matlab_source_card = CompactSourceStrip(self.i18n)
        self.matlab_source_card.action.connect(self._handle_source_action)
        lay.addWidget(self.matlab_source_card)
        self.matlab_page = MatlabStudioPage(
            self.session, self.i18n, job_manager=self.matlab_jobs
        )
        self.matlab_page.on_candidates_for_comparison = self._on_matlab_candidates_for_comparison
        lay.addWidget(self.matlab_page, 1)
        return wrap

    def _on_matlab_candidates_for_comparison(self, _candidates: object) -> None:
        """Open Method Comparison after an explicit MATLAB Studio hand-off."""
        self._navigate_key("compare")
        page = self.pages.get("compare")
        if page is None:
            return
        from ionogram_morphology_lab.ui.method_comparison_page import MethodComparisonPage

        body = page.findChild(MethodComparisonPage)
        if body is not None:
            body.refresh()

    def _page_parameters(self) -> QWidget:
        from ionogram_morphology_lab.ui.parameters_page import ParametersPage

        return ParametersPage(self.session, self.i18n)

    def _page_raw_signals(self) -> QWidget:
        from ionogram_morphology_lab.ui.raw_signals_page import RawSignalsPage

        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        self.raw_signals_source_card = CompactSourceStrip(self.i18n)
        self.raw_signals_source_card.action.connect(self._handle_source_action)
        lay.addWidget(self.raw_signals_source_card)
        page = RawSignalsPage(self.session, self.i18n)
        self._raw_signals_page = page
        lay.addWidget(page, 1)
        return wrap

    def _page_feature_diagnostics(self) -> QWidget:
        from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.page_ctor"):
            page = FeatureDiagnosticsPage(self.session, self.i18n)
        with span_timer("fd.page_connect"):
            page.navigate_requested.connect(self._navigate_key)
            page.source_action.connect(self._handle_source_action)
            page.open_in_viewer_requested.connect(lambda: self._navigate_key("viewer"))
            page.frame_sync_to_viewer.connect(self._on_fd_frame_sync)
            self._feature_diagnostics_page = page
        return page

    def _on_fd_frame_sync(self, frame: int) -> None:
        """Apply Feature Diagnostics frame to Viewer without modal spam."""
        self.session.set_current_frame(int(frame), emit=True)
        if self._viewer_ready:
            try:
                self.go_to_frame(int(frame), render=True)
            except Exception:  # noqa: BLE001
                pass

    def _page_rules(self) -> QWidget:
        from ionogram_morphology_lab.ui.rule_builder_page import RuleBuilderPage

        return RuleBuilderPage(self.session, self.i18n, self.settings)

    def _page_rule_test(self) -> QWidget:
        from ionogram_morphology_lab.ui.rule_testing_page import RuleTestingPage

        return RuleTestingPage(self.session, self.i18n)

    def _page_compare(self) -> QWidget:
        from ionogram_morphology_lab.ui.method_comparison_page import MethodComparisonPage

        return MethodComparisonPage(self.session, self.i18n)

    def _page_pipeline(self) -> QWidget:
        from ionogram_morphology_lab.ui.pipeline_builder_page import PipelineBuilderPage

        return PipelineBuilderPage(self.session, self.i18n)

    def _page_models(self) -> QWidget:
        from ionogram_morphology_lab.ui.model_lab_page import ModelLabPage

        return ModelLabPage(self.session, self.i18n)

    def _labeled(self, key: str, widget: QWidget, tip_key: str | None = None) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(self.t(key))
        lab.setObjectName(f"lab_{key}")
        lay.addWidget(lab)
        if tip_key:
            lay.addWidget(tip_button(tip_key, self.i18n))
        lay.addWidget(widget, 1)
        return row

    # ----- pages -----
    def _page_home(self) -> QWidget:
        from ionogram_morphology_lab.ui.home_dashboard import HomeDashboard

        self.home_dashboard = HomeDashboard(self.session, self.i18n, self.settings)
        self.home_dashboard.navigate_to.connect(self._navigate_key)
        self.home_dashboard.interface_mode_changed.connect(self._apply_ux_mode)
        # Keep legacy labels for retranslate compatibility (hidden)
        self.home_welcome = QLabel()
        self.home_welcome.hide()
        self.home_disclaimer = QLabel()
        self.home_disclaimer.hide()
        return self.home_dashboard

    def _page_project(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        cl = QVBoxLayout(content)

        self.proj_current_box = QGroupBox()
        cur_lay = QVBoxLayout(self.proj_current_box)
        self.proj_current_info = QLabel()
        self.proj_current_info.setWordWrap(True)
        cur_lay.addWidget(self.proj_current_info)
        cl.addWidget(self.proj_current_box)

        self.proj_open_box = QGroupBox()
        open_lay = QVBoxLayout(self.proj_open_box)
        row_open = QHBoxLayout()
        self.btn_open_project = QPushButton()
        self.btn_open_project.setObjectName("btn_open_project_page")
        self.btn_open_project.clicked.connect(self._open_project)
        self.btn_browse_project_folder = QPushButton()
        self.btn_browse_project_folder.clicked.connect(self._open_project_folder)
        self.btn_open_recent = QPushButton()
        self.btn_open_recent.clicked.connect(self._open_selected_recent_project)
        for b in (self.btn_open_project, self.btn_browse_project_folder, self.btn_open_recent):
            row_open.addWidget(b)
        open_lay.addLayout(row_open)
        self.recent_projects_table = QTableWidget(0, 5)
        self.recent_projects_table.setHorizontalHeaderLabels(
            ["name", "path", "last_opened", "availability", "actions"]
        )
        self.recent_projects_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        open_lay.addWidget(self.recent_projects_table)
        cl.addWidget(self.proj_open_box)

        self.proj_create_box = QGroupBox()
        create_lay = QVBoxLayout(self.proj_create_box)
        self.proj_name = QLineEdit("IML_Project")
        btn = QPushButton()
        btn.setObjectName("btn_create_project")
        btn.clicked.connect(self._create_project)
        self.proj_status = QLabel("")
        self.proj_status.setWordWrap(True)
        create_lay.addWidget(self._labeled("project.name", self.proj_name))
        create_lay.addWidget(btn)
        create_lay.addWidget(self.proj_status)
        cl.addWidget(self.proj_create_box)
        cl.addStretch(1)
        scroll.setWidget(content)
        lay.addWidget(scroll)
        self._refresh_projects_page()
        return w

    def _page_import(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.import_source_card = ActiveSourceCard(self.i18n)
        self.import_source_card.action.connect(self._handle_source_action)
        lay.addWidget(self.import_source_card)
        row = QHBoxLayout()
        b1 = QPushButton()
        b1.setObjectName("btn_import_file")
        b2 = QPushButton()
        b2.setObjectName("btn_import_folder")
        b1.clicked.connect(self._import_file)
        b2.clicked.connect(self._import_folder)
        row.addWidget(b1)
        row.addWidget(b2)
        lay.addLayout(row)
        self.import_file_list = ImportFileList(self.i18n)
        self.import_file_list.action.connect(self._handle_import_file_action)
        lay.addWidget(self.import_file_list, 3)
        # Legacy audit text retained as collapsed technical dump
        self.import_cards = QTextEdit()
        self.import_cards.setReadOnly(True)
        self.import_cards.setMaximumHeight(120)
        self.import_cards.setVisible(False)
        self.import_tech = QPlainTextEdit()
        self.import_tech.setReadOnly(True)
        self.import_tech.setVisible(False)
        tech_btn = QPushButton()
        tech_btn.setObjectName("btn_import_tech")
        tech_btn.clicked.connect(lambda: self.import_tech.setVisible(not self.import_tech.isVisible()))
        lay.addWidget(tech_btn)
        lay.addWidget(self.import_tech, 1)
        lay.addWidget(self.import_cards)
        return w

    def _page_profile(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        b1 = QPushButton()
        b1.setObjectName("btn_load_kfu")
        b1.clicked.connect(self._load_kfu_profile)
        b2 = QPushButton()
        b2.setObjectName("btn_wizard")
        b2.clicked.connect(self._wizard_advance)
        why = QPushButton()
        why.setObjectName("btn_why_profile")
        why.clicked.connect(self._why_provisional_profile)
        self.profile_card_view = QTextEdit()
        self.profile_card_view.setReadOnly(True)
        self.profile_raw = QPlainTextEdit()
        self.profile_raw.setReadOnly(True)
        self.profile_raw.setVisible(False)
        raw_btn = QPushButton()
        raw_btn.setObjectName("btn_profile_raw")
        raw_btn.clicked.connect(lambda: self.profile_raw.setVisible(not self.profile_raw.isVisible()))
        lay.addWidget(b1)
        lay.addWidget(b2)
        lay.addWidget(why)
        lay.addWidget(self.profile_card_view, 2)
        lay.addWidget(raw_btn)
        lay.addWidget(self.profile_raw, 1)
        return w

    def _page_audit(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        btn = QPushButton()
        btn.setObjectName("btn_audit")
        btn.clicked.connect(self._run_audit)
        self.audit_cards = QTextEdit()
        self.audit_cards.setReadOnly(True)
        self.audit_tech = QPlainTextEdit()
        self.audit_tech.setReadOnly(True)
        self.audit_tech.setVisible(False)
        tech = QPushButton()
        tech.setObjectName("btn_audit_tech")
        tech.clicked.connect(lambda: self.audit_tech.setVisible(not self.audit_tech.isVisible()))
        lay.addWidget(btn)
        lay.addWidget(self.audit_cards, 2)
        lay.addWidget(tech)
        lay.addWidget(self.audit_tech, 1)
        return w

    def _page_viewer(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        # Page itself must not force horizontal scrolling; long values use wrap/tooltips.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        self.viewer_source_card = CompactSourceStrip(self.i18n)
        self.viewer_source_card.action.connect(self._handle_source_action)
        lay.addWidget(self.viewer_source_card)

        self.viewer_summary = QGroupBox()
        self.viewer_summary.setObjectName("viewer_summary")
        self.viewer_summary.setCheckable(True)
        self.viewer_summary.setChecked(True)
        self.viewer_summary.setFlat(False)
        summary_lay = QVBoxLayout(self.viewer_summary)
        self.viewer_meta = QLabel()
        self.viewer_meta.setWordWrap(True)
        self.viewer_meta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        summary_lay.addWidget(self.viewer_meta)
        self.viewer_summary.toggled.connect(self.viewer_meta.setVisible)
        lay.addWidget(self.viewer_summary)
        self.viewer_status = QLabel()
        self.viewer_status.setObjectName("viewer_status")
        self.viewer_status.setWordWrap(True)
        self.viewer_status.setStyleSheet("padding:4px; font-weight:600;")
        lay.addWidget(self.viewer_status)

        ctrl = QHBoxLayout()
        self.frame_spin = QSpinBox()
        self.frame_spin.setRange(1, 1)
        self.frame_spin.setEnabled(False)
        self.frame_spin.valueChanged.connect(self._on_frame_spin)
        self.time_edit = QLineEdit("00:00")
        self.time_edit.setFixedWidth(64)
        self.time_edit.setEnabled(False)
        self.time_edit.editingFinished.connect(self._on_time_edit)
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setRange(1, 1)
        self.frame_slider.setEnabled(False)
        # Live drag only updates index; expensive render runs on release / debounce.
        self.frame_slider.valueChanged.connect(self._on_frame_slider_moved)
        self.frame_slider.sliderReleased.connect(self._on_frame_slider_released)
        ctrl.addWidget(tip_button("tip.frame_index", self.i18n))
        ctrl.addWidget(self.frame_spin)
        ctrl.addWidget(tip_button("tip.interpreted_time", self.i18n))
        ctrl.addWidget(self.time_edit)
        ctrl.addWidget(self.frame_slider, 1)
        lay.addLayout(ctrl)

        jump_default = int(
            self.settings.get("viewer", "navigation_jump_minutes", DEFAULT_KFU_INTERVAL_MINUTES)
        )
        speed_default = float(self.settings.get("viewer", "playback_speed", 2.0))

        self.jump_combo = QComboBox()
        self.jump_combo.addItems(["1", "5", "10", "15", "30", "60"])
        self.jump_combo.setCurrentText(str(jump_default))
        self.jump_combo.currentTextChanged.connect(self._on_jump_interval_changed)
        self.jump_label = QLabel()
        self.jump_label.setObjectName("viewer_jump_label")
        self.jump_unit = QLabel()
        self.jump_unit.setObjectName("viewer_jump_unit")

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5", "1", "2", "5", "10"])
        speed_text = self._format_playback_speed(speed_default)
        if self.speed_combo.findText(speed_text) >= 0:
            self.speed_combo.setCurrentText(speed_text)
        self.speed_combo.currentTextChanged.connect(self._on_playback_speed_changed)
        self.speed_label = QLabel()
        self.speed_label.setObjectName("viewer_speed_label")
        self.speed_unit = QLabel()
        self.speed_unit.setObjectName("viewer_speed_unit")

        self.loop_chk = QCheckBox()
        self.viewer_group_nav = QGroupBox()
        self.viewer_group_jump = QGroupBox()
        self.viewer_group_playback = QGroupBox()
        self.viewer_group_render = QGroupBox()

        self.view_mode = QComboBox()
        self.view_mode.addItems(["raw", "trace", "interference", "components", "overlay"])
        self.view_mode.currentTextChanged.connect(lambda _=None: self._schedule_viewer_render())
        self.preview_mode = QComboBox()
        self.preview_mode.addItems(["auto", "fast", "full"])
        self.preview_mode.currentTextChanged.connect(lambda _=None: self._schedule_viewer_render())
        self.view_mode_label = QLabel()
        self.preview_mode_label = QLabel()

        self.btn_first = QPushButton()
        self.btn_prev = QPushButton()
        self.btn_next = QPushButton()
        self.btn_last = QPushButton()
        self.btn_back = QPushButton()
        self.btn_fwd = QPushButton()
        self.btn_play = QPushButton()
        self.btn_pause = QPushButton()
        self.btn_cache = QPushButton()
        self.btn_contact = QPushButton()
        self.btn_save_img = QPushButton()
        for b in (
            self.btn_first,
            self.btn_prev,
            self.btn_next,
            self.btn_last,
            self.btn_back,
            self.btn_fwd,
            self.btn_play,
            self.btn_pause,
            self.btn_contact,
            self.btn_save_img,
            self.jump_combo,
            self.speed_combo,
            self.loop_chk,
        ):
            b.setEnabled(False)
        for b, slot in [
            (self.btn_first, lambda: self.go_to_frame(1, render=True)),
            (self.btn_prev, lambda: self.go_to_frame(self.session.current_frame - 1, render=True)),
            (self.btn_next, lambda: self.go_to_frame(self.session.current_frame + 1, render=True)),
            (self.btn_last, lambda: self.go_to_frame(self._viewer_n_frames or 1, render=True)),
            (self.btn_back, self._jump_back),
            (self.btn_fwd, self._jump_fwd),
            (self.btn_play, self._play),
            (self.btn_pause, self._pause_play),
            (self.btn_cache, self._build_cache_async),
            (self.btn_contact, self._make_contact_sheet),
            (self.btn_save_img, self._save_current_image),
        ]:
            b.clicked.connect(slot)
            b.setMinimumHeight(28)
            b.setMinimumWidth(72)

        nav_layout = QHBoxLayout(self.viewer_group_nav)
        for b in (self.btn_first, self.btn_prev, self.btn_next, self.btn_last):
            nav_layout.addWidget(b)

        jump_layout = QHBoxLayout(self.viewer_group_jump)
        jump_layout.addWidget(self.btn_back)
        jump_layout.addWidget(self.btn_fwd)
        jump_layout.addWidget(self.jump_label)
        jump_layout.addWidget(self.jump_combo)
        jump_layout.addWidget(self.jump_unit)

        playback_layout = QHBoxLayout(self.viewer_group_playback)
        playback_layout.addWidget(self.btn_play)
        playback_layout.addWidget(self.btn_pause)
        playback_layout.addWidget(self.loop_chk)
        playback_layout.addWidget(self.speed_label)
        playback_layout.addWidget(self.speed_combo)
        playback_layout.addWidget(self.speed_unit)

        self.btn_add_to_corpus = QPushButton()
        self.btn_add_to_corpus.setObjectName("btn_add_to_corpus")
        self.btn_add_to_corpus.clicked.connect(self._viewer_add_current_to_corpus)
        render_layout = QHBoxLayout(self.viewer_group_render)
        for b in (self.btn_cache, self.btn_contact, self.btn_save_img, self.btn_add_to_corpus):
            render_layout.addWidget(b)
        render_layout.addWidget(self.view_mode_label)
        render_layout.addWidget(self.view_mode)
        render_layout.addWidget(self.preview_mode_label)
        render_layout.addWidget(self.preview_mode)

        # 2×2 grid keeps Navigation/Jump/Playback/Display visible at 1366×768.
        groups_grid = QHBoxLayout()
        left_groups = QVBoxLayout()
        right_groups = QVBoxLayout()
        left_groups.addWidget(self.viewer_group_nav)
        left_groups.addWidget(self.viewer_group_jump)
        right_groups.addWidget(self.viewer_group_playback)
        right_groups.addWidget(self.viewer_group_render)
        groups_grid.addLayout(left_groups, 1)
        groups_grid.addLayout(right_groups, 1)
        lay.addLayout(groups_grid)

        self.viewer_image = QLabel()
        self.viewer_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer_image.setMinimumHeight(280)
        self.viewer_image.setMinimumWidth(320)
        self.viewer_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.viewer_image.setStyleSheet("background:#111;color:#ddd;")
        self.viewer_view_label = QLabel()
        self.viewer_view_label.setWordWrap(True)
        image_box = QWidget()
        image_lay = QVBoxLayout(image_box)
        image_lay.setContentsMargins(0, 0, 0, 0)
        image_lay.addWidget(self.viewer_view_label)
        image_lay.addWidget(self.viewer_image, 1)
        self.cache_progress = QProgressBar()
        self.cache_progress.setVisible(False)
        image_lay.addWidget(self.cache_progress)
        self.viewer_open_btn = QPushButton()
        self.viewer_open_btn.setObjectName("btn_open_real")
        self.viewer_open_btn.clicked.connect(self._open_real_viewer)
        image_lay.addWidget(self.viewer_open_btn)
        lay.addWidget(image_box, 1)

        scroll.setWidget(content)
        outer.addWidget(scroll)
        return w

    def _page_synth(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel()
        note.setObjectName("synth_note")
        note.setWordWrap(True)
        btn = QPushButton("SYNTHETIC")
        btn.setObjectName("btn_synth")
        btn.clicked.connect(self._synth_demo)
        self.synth_image = QLabel()
        self.synth_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.synth_image.setMinimumHeight(360)
        self.synth_image.setStyleSheet("background:#222;color:#ccc;")
        lay.addWidget(note)
        lay.addWidget(btn)
        lay.addWidget(self.synth_image, 1)
        return w

    def _page_batch(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.batch_source_card = CompactSourceStrip(self.i18n)
        self.batch_source_card.action.connect(self._handle_source_action)
        lay.addWidget(self.batch_source_card)
        self.batch_step_title = QLabel()
        self.batch_step_title.setStyleSheet("font-weight:600;")
        lay.addWidget(self.batch_step_title)
        self.batch_mode = QComboBox()
        # Stable selection-mode tokens remain in item data; users see workflow language.
        self.batch_mode.addItem("Current frame", "current_frame")
        self.batch_mode.addItem("Selected frames", "selected")
        self.batch_mode.addItem("Frame range", "frame_range")
        self.batch_mode.addItem("Time range", "time_range")
        self.batch_mode.addItem("Every N minutes", "every_n")
        self.batch_mode.addItem("Entire file", "entire_file")
        self.batch_mode.addItem("Custom list", "custom_list")
        self.batch_mode.currentIndexChanged.connect(self._refresh_batch_preview)
        self.batch_preset = QComboBox()
        self.batch_preset.addItem("", "fast_preview")
        self.batch_preset.addItem("", "standard")
        self.batch_preset.addItem("", "scientific_strict")
        self.batch_preset.addItem("", "custom")
        self.batch_preset.setCurrentIndex(max(0, self.batch_preset.findData(self.settings.analysis_mode())))
        self.batch_preset.currentIndexChanged.connect(self._refresh_batch_preview)
        form = QFormLayout()
        self.b_start = QSpinBox()
        self.b_start.setRange(1, 1440)
        self.b_start.setValue(1)
        self.b_end = QSpinBox()
        self.b_end.setRange(1, 1440)
        self.b_end.setValue(1440)
        self.b_step = QSpinBox()
        self.b_step.setRange(1, 1440)
        self.b_step.setValue(DEFAULT_KFU_INTERVAL_MINUTES)
        self.b_t0 = QLineEdit("00:00")
        self.b_t1 = QLineEdit("23:59")
        self.b_custom = QLineEdit("1, 10, 50, 100")
        self.b_day_interval = QComboBox()
        self.b_day_interval.addItems(["1", "5", "10", "15", "30", "60"])
        self.b_day_interval.setCurrentText("10")
        for wdg in (
            self.b_start,
            self.b_end,
            self.b_step,
            self.b_t0,
            self.b_t1,
            self.b_custom,
            self.b_day_interval,
        ):
            if hasattr(wdg, "valueChanged"):
                wdg.valueChanged.connect(self._refresh_batch_preview)
            elif hasattr(wdg, "currentTextChanged"):
                wdg.currentTextChanged.connect(self._refresh_batch_preview)
            else:
                wdg.textChanged.connect(self._refresh_batch_preview)
        self.batch_form_rows = {
            "start": (QLabel(), self.b_start),
            "end": (QLabel(), self.b_end),
            "step": (QLabel(), self.b_step),
            "t0": (QLabel(), self.b_t0),
            "t1": (QLabel(), self.b_t1),
            "day_interval": (QLabel(), self.b_day_interval),
            "custom": (QLabel(), self.b_custom),
        }
        form.addRow(QLabel(), self.batch_mode)
        self.batch_preset_label = QLabel()
        form.addRow(self.batch_preset_label, self.batch_preset)
        for label, field in self.batch_form_rows.values():
            form.addRow(label, field)
        lay.addLayout(form)

        ops_box = QGroupBox()
        ops_box.setObjectName("batch_ops_box")
        ops_lay = QVBoxLayout(ops_box)
        self.op_checks: dict[str, QCheckBox] = {}
        self.op_descriptions = {
            "audit": "check data quality",
            "build_cache": "build a derived read-only cache",
            "render": "render diagnostic images",
            "features": "measure image features",
            "rules": "apply candidate morphology rules",
            "references": "compare reference metadata",
            "export_reports": "write reproducible reports",
            "full_pipeline": "run the recommended complete pipeline",
        }
        for op in self.op_descriptions:
            c = QCheckBox()
            c.setToolTip(self.op_descriptions[op])
            c.stateChanged.connect(self._refresh_batch_preview)
            self.op_checks[op] = c
            ops_lay.addWidget(c)
        self.op_checks["full_pipeline"].setChecked(True)
        lay.addWidget(ops_box)

        self.batch_preview = QTextEdit()
        self.batch_preview.setReadOnly(True)
        self.batch_preview.setMaximumHeight(140)
        lay.addWidget(self.batch_preview)

        row = QHBoxLayout()
        self.btn_batch_start = QPushButton()
        self.btn_batch_pause = QPushButton()
        self.btn_batch_resume = QPushButton()
        self.btn_batch_cancel = QPushButton()
        self.btn_batch_start.setObjectName("btn_batch_start")
        self.btn_batch_pause.setObjectName("btn_batch_pause")
        self.btn_batch_resume.setObjectName("btn_batch_resume")
        self.btn_batch_cancel.setObjectName("btn_batch_cancel")
        self.btn_batch_start.clicked.connect(self._batch_start)
        self.btn_batch_pause.clicked.connect(lambda: self.batch_controller.pause())
        self.btn_batch_resume.clicked.connect(lambda: self.batch_controller.resume())
        self.btn_batch_cancel.clicked.connect(lambda: self.batch_controller.cancel())
        for b in (
            self.btn_batch_start,
            self.btn_batch_pause,
            self.btn_batch_resume,
            self.btn_batch_cancel,
        ):
            row.addWidget(b)
        lay.addLayout(row)

        self.batch_progress = QProgressBar()
        self.batch_status = QLabel("")
        lay.addWidget(self.batch_progress)
        lay.addWidget(self.batch_status)
        self.batch_tech = QPlainTextEdit()
        self.batch_tech.setReadOnly(True)
        self.batch_tech.setVisible(False)
        tech = QPushButton()
        tech.setObjectName("btn_batch_tech")
        tech.clicked.connect(lambda: self.batch_tech.setVisible(not self.batch_tech.isVisible()))
        lay.addWidget(tech)
        lay.addWidget(self.batch_tech, 1)
        self._refresh_batch_preview()
        return w

    def _page_results(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        self.results_empty = QLabel()
        self.results_empty.setWordWrap(True)
        lay.addWidget(self.results_empty)
        self.analysis_pipeline_panel = AnalysisPipelinePanel()
        self.analysis_pipeline_panel.setMaximumHeight(220)
        lay.addWidget(self.analysis_pipeline_panel)
        self.review_counts_label = QLabel()
        self.review_counts_label.setObjectName("review_counts_label")
        self.review_counts_label.setWordWrap(True)
        lay.addWidget(self.review_counts_label)
        toolbar = QHBoxLayout()
        self.results_run_selector = QComboBox()
        self.results_filter = QComboBox()
        self.results_filter.addItems(["All", "Needs review", "Abstained", "Warnings"])
        self.results_filter.currentIndexChanged.connect(self._load_results_table)
        self.results_columns = QComboBox()
        self.results_columns.addItem("Default columns", "default")
        self.results_columns.addItem("Compact + layer/quality", "extended")
        self.results_columns.addItem("All detail columns", "all")
        self.results_columns.currentIndexChanged.connect(self._load_results_table)
        self.btn_results_export = QPushButton()
        self.btn_results_export.clicked.connect(self._export_reports)
        self.btn_add_review = QPushButton()
        self.btn_add_review.setObjectName("btn_add_review")
        self.btn_add_review.clicked.connect(self._add_to_review_dataset)
        toolbar.addWidget(self.results_run_selector)
        toolbar.addWidget(self.results_filter)
        toolbar.addWidget(self.results_columns)
        toolbar.addWidget(self.btn_results_export)
        toolbar.addWidget(self.btn_add_review)
        toolbar.addStretch(1)
        lay.addLayout(toolbar)
        split = QSplitter(Qt.Orientation.Horizontal)
        self._results_active_columns = list(RESULTS_DEFAULT_COLUMNS)
        self.results_table = QTableWidget(0, len(self._results_active_columns))
        self.results_table.setHorizontalHeaderLabels(list(self._results_active_columns))
        self.results_table.itemSelectionChanged.connect(self._show_selected_result)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.results_table.setWordWrap(True)
        self.results_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setMouseTracking(True)
        self.results_table.setMinimumWidth(280)
        self.results_tabs = QTabWidget()
        self.res_overview = QTextEdit()
        self.res_overview.setReadOnly(True)
        self.res_evidence = QTextEdit()
        self.res_evidence.setReadOnly(True)
        self.res_details = QTextEdit()
        self.res_details.setReadOnly(True)
        self.res_features = QTextEdit()
        self.res_features.setReadOnly(True)
        self.res_rules = QTextEdit()
        self.res_rules.setReadOnly(True)
        self.res_alts = QTextEdit()
        self.res_alts.setReadOnly(True)
        self.res_refs = QTextEdit()
        self.res_refs.setReadOnly(True)
        self.res_expert = QTextEdit()
        self.res_expert.setReadOnly(True)
        self.res_tech = QPlainTextEdit()
        self.res_tech.setReadOnly(True)
        raw_page = QWidget()
        raw_layout = QVBoxLayout(raw_page)
        raw_layout.setContentsMargins(0, 0, 0, 0)
        self.results_identity_line = QLabel()
        self.results_identity_line.setObjectName("results_identity_line")
        self.results_identity_line.setWordWrap(True)
        self.results_identity_line.setStyleSheet("font-weight:600; padding:4px;")
        self.res_image = QLabel()
        self.res_image.setMinimumHeight(200)
        self.res_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.res_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        raw_layout.addWidget(self.results_identity_line)
        raw_layout.addWidget(self.res_image, 1)
        for name, widget in [
            ("overview", self.res_overview),
            ("evidence", self.res_evidence),
            ("details", self.res_details),
            ("raw", raw_page),
            ("features", self.res_features),
            ("rules", self.res_rules),
            ("alternatives", self.res_alts),
            ("references", self.res_refs),
            ("expert", self.res_expert),
            ("technical", self.res_tech),
        ]:
            self.results_tabs.addTab(widget, name)
        split.addWidget(self.results_table)
        split.addWidget(self.results_tabs)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        split.setSizes([420, 640])
        lay.addWidget(split, 1)
        row = QHBoxLayout()
        self.btn_accept = QPushButton()
        self.btn_change = QPushButton()
        self.btn_uncertain = QPushButton()
        self.btn_na = QPushButton()
        self.btn_save_human = QPushButton()
        self.btn_accept.setObjectName("btn_accept")
        self.btn_change.setObjectName("btn_change")
        self.btn_uncertain.setObjectName("btn_uncertain")
        self.btn_na.setObjectName("btn_na")
        self.btn_save_human.setObjectName("btn_save_human")
        self.btn_accept.clicked.connect(lambda: self._human_decision("accept"))
        self.btn_change.clicked.connect(lambda: self._human_decision("change"))
        self.btn_uncertain.clicked.connect(lambda: self._human_decision("uncertain"))
        self.btn_na.clicked.connect(lambda: self._human_decision("not_assessable"))
        self.btn_save_human.clicked.connect(lambda: self._human_decision("save"))
        for b in (
            self.btn_accept,
            self.btn_change,
            self.btn_uncertain,
            self.btn_na,
            self.btn_save_human,
        ):
            row.addWidget(b)
        lay.addLayout(row)
        return w

    def _page_atlas(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        filt = QHBoxLayout()
        self.atlas_filter = QComboBox()
        self.atlas_filter.addItems(
            ["all", "frequency", "range", "mixed", "other", "indeterminate"]
        )
        self.atlas_filter.currentTextChanged.connect(self._load_atlas)
        filt.addWidget(self.atlas_filter)
        btn = QPushButton("Refresh")
        btn.setObjectName("btn_atlas")
        btn.clicked.connect(self._load_atlas)
        filt.addWidget(btn)
        lay.addLayout(filt)
        self.atlas_view = QTextEdit()
        self.atlas_view.setReadOnly(True)
        lay.addWidget(self.atlas_view, 1)
        return w

    def _page_science(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        btn = QPushButton("Refresh")
        btn.setObjectName("btn_science")
        btn.clicked.connect(self._load_science)
        methods = QPushButton("Analysis Methods / Методы анализа")
        methods.setObjectName("btn_analysis_methods")
        methods.clicked.connect(self._show_analysis_methods)
        self.science_view = QTextEdit()
        self.science_view.setReadOnly(True)
        tech = QPushButton()
        tech.setObjectName("btn_science_tech")
        self.science_tech = QPlainTextEdit()
        self.science_tech.setReadOnly(True)
        self.science_tech.setVisible(False)
        tech.clicked.connect(lambda: self.science_tech.setVisible(not self.science_tech.isVisible()))
        lay.addWidget(btn)
        lay.addWidget(methods)
        lay.addWidget(self.science_view, 2)
        lay.addWidget(tech)
        lay.addWidget(self.science_tech, 1)
        return w

    def _page_reports(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.reports_empty = EmptyStatePanel()
        self.reports_empty.action_requested.connect(self._navigate_key)
        lay.addWidget(self.reports_empty)
        btn = QPushButton()
        btn.setObjectName("btn_export")
        btn.clicked.connect(self._export_reports)
        self.report_log = QTextEdit()
        self.report_log.setReadOnly(True)
        lay.addWidget(btn)
        lay.addWidget(self.report_log, 1)
        return w

    def _page_settings(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.settings_tabs = QTabWidget()
        self._settings_widgets: dict[str, Any] = {}

        def add_tab(name_key: str, fields: list[tuple[str, str, str]]):
            tab = QWidget()
            form = QFormLayout(tab)
            for section, key, kind in fields:
                if kind == "lang":
                    wid = QComboBox()
                    wid.addItem("English", "en")
                    wid.addItem("Русский", "ru")
                    cur = self.settings.get(section, key, "en")
                    wid.setCurrentIndex(0 if cur == "en" else 1)
                    wid.currentIndexChanged.connect(
                        lambda _i, w=wid: self.set_language(w.currentData())
                    )
                elif kind == "scale":
                    wid = QComboBox()
                    wid.addItem(self.t("settings.interface_scale_auto"), "auto")
                    for percent in ("90", "100", "110", "125", "150"):
                        wid.addItem(f"{percent}%", percent)
                    current = str(self.settings.get(section, key, "auto"))
                    wid.setCurrentIndex(max(0, wid.findData(current)))
                elif kind == "bool":
                    wid = QCheckBox()
                    wid.setChecked(bool(self.settings.get(section, key, False)))
                elif kind == "int":
                    wid = QSpinBox()
                    wid.setRange(1, 128)
                    wid.setValue(int(self.settings.get(section, key, 1)))
                elif kind == "float":
                    wid = QDoubleSpinBox()
                    wid.setRange(0.1, 60)
                    wid.setValue(float(self.settings.get(section, key, 1)))
                else:
                    wid = QLineEdit(str(self.settings.get(section, key, "")))
                self._settings_widgets[f"{section}.{key}"] = (section, key, kind, wid)
                label = self.t("settings.interface_scale") if key == "interface_scale" else f"{section}.{key}"
                form.addRow(label, wid)
            self.settings_tabs.addTab(tab, name_key)

        add_tab(
            "general",
            [
                ("general", "language", "lang"),
                ("general", "theme", "str"),
                ("general", "interface_scale", "scale"),
                ("general", "workspace_dir", "str"),
                ("general", "restore_last_project", "bool"),
                ("general", "confirm_before_closing", "bool"),
                ("general", "show_onboarding", "bool"),
            ],
        )
        add_tab(
            "data",
            [
                ("data", "default_profile_id", "str"),
                ("data", "recursive_folder_scan", "bool"),
                ("data", "calculate_source_sha", "bool"),
                ("data", "strict_source_readonly", "bool"),
            ],
        )
        add_tab(
            "viewer",
            [
                ("viewer", "default_frame_step_minutes", "int"),
                ("viewer", "navigation_jump_minutes", "int"),
                ("viewer", "playback_speed", "float"),
                ("viewer", "contact_interval_minutes", "int"),
                ("viewer", "prefetch_count", "int"),
                ("viewer", "preview_mode", "str"),
            ],
        )
        add_tab(
            "performance",
            [
                ("performance", "worker_count", "int"),
                ("performance", "max_ram_mb", "int"),
                ("performance", "automatic_cache_creation", "bool"),
                ("performance", "background_prefetch", "bool"),
                ("performance", "lru_capacity", "int"),
            ],
        )
        add_tab(
            "analysis",
            [
                ("analysis", "mode", "str"),
                ("analysis", "rule_engine", "bool"),
                ("analysis", "abstention", "bool"),
                ("analysis", "feature_extraction", "bool"),
                ("analysis", "ml_models_enabled", "bool"),
                ("analysis", "scientific_formula_pipeline_enabled", "bool"),
                ("analysis", "scientific_feature_pipeline_v2_enabled", "bool"),
            ],
        )
        add_tab(
            "matlab",
            [
                ("matlab", "active_backend", "str"),
                ("matlab", "matlab_executable", "str"),
                ("matlab", "octave_executable", "str"),
                ("matlab", "working_directory", "str"),
                ("matlab", "default_timeout_s", "int"),
                ("matlab", "max_execution_s", "int"),
                ("matlab", "auto_detect", "bool"),
                ("matlab", "reuse_engine_session", "bool"),
            ],
        )
        add_tab(
            "models",
            [
                ("models", "default_split", "str"),
                ("models", "abstention_threshold", "float"),
            ],
        )
        add_tab(
            "reports",
            [
                ("reports", "language", "str"),
                ("reports", "include_bibliography", "bool"),
                ("reports", "include_reproducibility_manifest", "bool"),
            ],
        )
        storage = QWidget()
        storage_form = QFormLayout(storage)
        self.storage_paths: dict[str, QLineEdit] = {}
        self.storage_path_labels: dict[str, QLabel] = {}
        self.storage_browse_buttons: list[QPushButton] = []
        self.storage_open_buttons: list[QPushButton] = []
        for key in (
            "project_dir",
            "workspace_dir",
            "cache_location",
            "reports_dir",
            "models_dir",
            "matlab_workspace",
            "temp_dir",
        ):
            section = "performance" if key == "cache_location" else ("general" if key == "workspace_dir" else "storage")
            edit = QLineEdit(str(self.settings.get(section, key, "")))
            browse = QPushButton()
            browse.clicked.connect(lambda _=False, e=edit: self._browse_storage_folder(e))
            open_btn = QPushButton()
            open_btn.clicked.connect(lambda _=False, e=edit: self._open_storage_folder(e.text()))
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.addWidget(edit, 1)
            row_lay.addWidget(browse)
            row_lay.addWidget(open_btn)
            lab = QLabel()
            storage_form.addRow(lab, row)
            self.storage_paths[key] = edit
            self.storage_path_labels[key] = lab
            self.storage_browse_buttons.append(browse)
            self.storage_open_buttons.append(open_btn)
        self.storage_info = QLabel()
        self.storage_info.setWordWrap(True)
        self.storage_status_label = QLabel()
        storage_form.addRow(self.storage_status_label, self.storage_info)
        cache_actions = QWidget()
        cache_actions_lay = QHBoxLayout(cache_actions)
        cache_actions_lay.setContentsMargins(0, 0, 0, 0)
        migrate = QPushButton()
        migrate.setObjectName("btn_migrate_cache")
        migrate.clicked.connect(self._migrate_cache)
        clear_cache = QPushButton()
        clear_cache.setObjectName("btn_clear_cache")
        clear_cache.clicked.connect(self._clear_cache)
        restore_defaults = QPushButton()
        restore_defaults.setObjectName("btn_storage_defaults")
        restore_defaults.clicked.connect(self._restore_storage_defaults)
        for b in (migrate, clear_cache, restore_defaults):
            cache_actions_lay.addWidget(b)
        self._storage_action_buttons = {
            "migrate": migrate,
            "clear": clear_cache,
            "defaults": restore_defaults,
        }
        storage_form.addRow(cache_actions)
        self.settings_tabs.addTab(storage, "Storage")
        ref = QWidget()
        rv = QVBoxLayout(ref)
        self.refpacks_label = QLabel(
            "Reference packs are loaded from knowledge_base / atlas metadata. "
            "Copyrighted figures require explicit permission."
        )
        self.refpacks_label.setWordWrap(True)
        rv.addWidget(self.refpacks_label)
        rv.addStretch(1)
        self.settings_tabs.addTab(ref, "reference")
        priv = QWidget()
        pv = QVBoxLayout(priv)
        self.privacy_label = QLabel()
        self.privacy_label.setWordWrap(True)
        self.chk_protected = QCheckBox("Protected Scientific Study mode")
        self.chk_protected.setChecked(
            bool(self.settings.get("privacy", "protected_study_enabled", False))
        )
        self.chk_protected.stateChanged.connect(
            lambda s: self.settings.set("privacy", "protected_study_enabled", bool(s))
        )
        pv.addWidget(self.privacy_label)
        pv.addWidget(self.chk_protected)
        self.settings_tabs.addTab(priv, "privacy")
        adv = QWidget()
        av = QVBoxLayout(adv)
        self.advanced_label = QLabel()
        av.addWidget(self.advanced_label)
        self.build_identity_view = QPlainTextEdit()
        self.build_identity_view.setReadOnly(True)
        self.build_identity_view.setObjectName("build_identity_view")
        self.btn_refresh_build_identity = QPushButton()
        self.btn_refresh_build_identity.clicked.connect(self._refresh_build_identity_panel)
        self.btn_copy_build_identity = QPushButton()
        self.btn_copy_build_identity.clicked.connect(
            lambda: QApplication.clipboard().setText(self.build_identity_view.toPlainText())
        )
        id_row = QHBoxLayout()
        id_row.addWidget(self.btn_refresh_build_identity)
        id_row.addWidget(self.btn_copy_build_identity)
        id_row.addStretch(1)
        av.addLayout(id_row)
        av.addWidget(self.build_identity_view, 1)
        self.chk_packaged_profiler = QCheckBox()
        self.chk_packaged_profiler.setChecked(
            bool(self.settings.get("performance", "packaged_exe_profiler", False))
        )
        self.chk_packaged_profiler.stateChanged.connect(
            lambda s: self.settings.set("performance", "packaged_exe_profiler", bool(s))
        )
        av.addWidget(self.chk_packaged_profiler)
        self.settings_tabs.addTab(adv, "advanced")
        self._refresh_build_identity_panel()

        lay.addWidget(self.settings_tabs, 1)
        row = QHBoxLayout()
        save = QPushButton()
        save.setObjectName("btn_settings_save")
        save.clicked.connect(self._save_settings)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("btn_settings_cancel")
        cancel.clicked.connect(lambda: self.settings.load() or self.retranslate())
        reset = QPushButton()
        reset.setObjectName("btn_settings_reset")
        reset.clicked.connect(self._reset_settings)
        exp = QPushButton("Export Settings")
        exp.clicked.connect(self._export_settings)
        imp = QPushButton("Import Settings")
        imp.clicked.connect(self._import_settings)
        for b in (save, cancel, reset, exp, imp):
            row.addWidget(b)
        shortcut = QPushButton("Create Desktop Shortcut")
        shortcut.clicked.connect(self._create_desktop_shortcut)
        row.addWidget(shortcut)
        lay.addLayout(row)
        self._refresh_storage_info()
        return w

    def _page_help(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        restore = QPushButton()
        restore.setObjectName("btn_restore_intros")
        restore.clicked.connect(self._restore_intros)
        root.addWidget(restore)
        inner = QWidget()
        lay = QHBoxLayout(inner)
        left = QVBoxLayout()
        self.help_search = QLineEdit()
        self.help_search.textChanged.connect(self._filter_help)
        self.help_nav = QListWidget()
        self.help_nav.currentRowChanged.connect(self._show_help_section)
        left.addWidget(self.help_search)
        left.addWidget(self.help_nav, 1)
        self.help_body = QTextEdit()
        self.help_body.setReadOnly(True)
        wrap = QWidget()
        wrap.setLayout(left)
        wrap.setFixedWidth(280)
        lay.addWidget(wrap)
        lay.addWidget(self.help_body, 1)
        root.addWidget(inner, 1)
        self._populate_help()
        return w

    # ----- language / status -----
    def retranslate(self) -> None:
        t = self.t
        self.setWindowTitle(f"{t('app.name')} v{__version__}")
        if hasattr(self, "actions"):
            for action in self.actions.values():
                action.setText(t(action.data()))
            self.file_menu.setTitle(t("menu.file"))
            self.project_menu.setTitle(t("menu.project"))
            self.analysis_menu.setTitle(t("menu.analysis"))
            self.tools_menu.setTitle(t("menu.tools"))
            self.help_menu.setTitle(t("menu.help"))
            self._apply_ux_mode()
        # Retranslate materialized child pages only (never force data reload).
        for key in (
            "parameters", "rules", "rule_test", "compare", "pipeline", "matlab", "models",
            "raw_signals", "feature_diagnostics",
        ):
            if not self._page_materialized.get(key, True):
                continue
            page = self.pages.get(key)
            if page is None:
                continue
            lay = page.layout()
            if lay and lay.count() >= 2:
                w = lay.itemAt(lay.count() - 1).widget()
                if w is not None and hasattr(w, "retranslate"):
                    if hasattr(w, "retranslate_ui"):
                        w.retranslate_ui()
                    else:
                        w.retranslate()
        self._refresh_source_cards(light=True)
        for panel in getattr(self, "intro_panels", {}).values():
            if hasattr(panel, "retranslate"):
                panel.retranslate()
        for key, nav_key in NAV_KEYS:
            full_title = t(nav_key)
            self.nav_items[key].setText(0, full_title)
            self.nav_items[key].setToolTip(0, full_title)
            self.nav_items[key].setData(0, Qt.ItemDataRole.AccessibleTextRole, full_title)
            title = self.pages[key].findChild(QLabel, f"title_{key}")
            if title:
                title.setText(t(nav_key))
        for group_key, label_key, _keys in NAV_GROUPS:
            full_title = t(label_key)
            self.nav_groups[group_key].setText(0, full_title)
            self.nav_groups[group_key].setToolTip(0, full_title)
            self.nav_groups[group_key].setData(0, Qt.ItemDataRole.AccessibleTextRole, full_title)
        if hasattr(self, "home_welcome"):
            self.home_welcome.setText(t("home.welcome"))
        if hasattr(self, "home_disclaimer"):
            self.home_disclaimer.setText(t("home.disclaimer"))
        if hasattr(self, "home_dashboard"):
            self.home_dashboard.retranslate()
            if not self._retranslate_only:
                self.home_dashboard.refresh()
        if hasattr(self, "proj_current_info"):
            self._refresh_projects_page()
        if hasattr(self, "seq_info"):
            self.seq_info.setText(t("sequences.help"))
        expert = self.findChild(QLabel, "expert_help")
        if expert:
            expert.setText(t("expert.help"))
        ru = self.i18n.language == "ru"
        if hasattr(self, "expert_empty"):
            self.expert_empty.configure(
                title="Экспертная проверка" if ru else "Expert Review",
                why=(
                    "Страница пуста, потому что проверка выполняется из результатов анализа."
                    if ru
                    else "This page is empty because review actions start from analysis results."
                ),
                prereq=(
                    "Нужен завершённый пакетный анализ и выбранный результат."
                    if ru
                    else "A completed batch analysis and a selected result are required."
                ),
                after=(
                    "После проверки появятся метки владельца/эксперта и счётчики классов."
                    if ru
                    else "After review, owner/expert labels and class counts appear."
                ),
                action="Открыть Результаты" if ru else "Open Results",
                nav_key="results",
            )
        if hasattr(self, "reports_empty"):
            has_run = bool(self.session.last_run_root)
            self.reports_empty.setVisible(not has_run)
            self.reports_empty.configure(
                title="Отчёты" if ru else "Reports",
                why=(
                    "Отчёт нельзя сформировать, пока нет запуска анализа."
                    if ru
                    else "No report can be written until an analysis run exists."
                ),
                prereq=(
                    "Сначала выполните «Пакетный анализ»."
                    if ru
                    else "Run Batch Analysis first."
                ),
                after=(
                    "После экспорта здесь появится журнал путей к HTML/CSV/JSON."
                    if ru
                    else "After export, this page lists HTML/CSV/JSON report paths."
                ),
                action="Открыть Пакетный анализ" if ru else "Open Batch Analysis",
                nav_key="batch",
            )
        mapping = {
            "btn_onboarding": "home.start",
            "btn_create_project": "project.create",
            "btn_import_file": "import.select_file",
            "btn_import_folder": "import.select_folder",
            "btn_import_tech": "import.technical",
            "btn_load_kfu": "profile.load_kfu",
            "btn_wizard": "profile.wizard",
            "btn_why_profile": "profile.why_provisional",
            "btn_profile_raw": "profile.advanced_raw",
            "btn_audit": "import.audit",
            "btn_audit_tech": "import.technical",
            "btn_open_real": "viewer.open_real",
            "btn_batch_start": "batch.start",
            "btn_batch_pause": "batch.pause",
            "btn_batch_resume": "batch.resume",
            "btn_batch_cancel": "batch.cancel",
            "btn_batch_tech": "batch.technical_log",
            "btn_export": "reports.export",
            "btn_settings_save": "settings.save",
            "btn_settings_reset": "settings.reset",
            "btn_accept": "results.accept",
            "btn_change": "results.change",
            "btn_uncertain": "results.uncertain",
            "btn_na": "results.not_assessable",
            "btn_save_human": "results.save_human",
            "btn_seq_contact": "viewer.contact",
            "btn_goto_results": "nav.results",
            "btn_restore_intros": "help.restore_intros",
        }
        for oid, key in mapping.items():
            btn = self.findChild(QPushButton, oid)
            if btn:
                btn.setText(t(key))
        if hasattr(self, "_storage_action_buttons"):
            self._storage_action_buttons["migrate"].setText(t("storage.migrate_cache"))
            self._storage_action_buttons["clear"].setText(t("storage.clear_cache"))
            self._storage_action_buttons["defaults"].setText(t("storage.restore_defaults"))
        if hasattr(self, "storage_path_labels"):
            for key, lab in self.storage_path_labels.items():
                lab.setText(t(f"storage.{key}"))
            for btn in getattr(self, "storage_browse_buttons", []):
                btn.setText(t("storage.browse"))
            for btn in getattr(self, "storage_open_buttons", []):
                btn.setText(t("storage.open_folder"))
            if hasattr(self, "storage_status_label"):
                self.storage_status_label.setText(t("storage.status"))
            self._refresh_storage_info()
        # viewer buttons (short labels + full tooltips so RU text stays readable)
        viewer_btn_map = [
            (self.btn_first, "viewer.first"),
            (self.btn_prev, "viewer.prev"),
            (self.btn_next, "viewer.next"),
            (self.btn_last, "viewer.last"),
            (self.btn_back, "viewer.jump_back"),
            (self.btn_fwd, "viewer.jump_forward"),
            (self.btn_play, "viewer.play"),
            (self.btn_pause, "viewer.pause"),
            (self.btn_cache, "viewer.build_cache"),
            (self.btn_contact, "viewer.contact"),
            (self.btn_save_img, "viewer.save_image"),
            (self.btn_add_to_corpus, "expert_corpus.add_to_corpus"),
        ]
        for btn, key in viewer_btn_map:
            btn.setText(t(key))
            btn.setToolTip(t(key))
        self._update_jump_button_labels()
        self.loop_chk.setText(t("viewer.loop_playback"))
        self.loop_chk.setToolTip(t("viewer.loop_tooltip"))
        self.viewer_group_nav.setTitle(t("viewer.group_nav"))
        self.viewer_group_jump.setTitle(t("viewer.group_jump"))
        self.viewer_group_playback.setTitle(t("viewer.group_playback"))
        self.viewer_group_render.setTitle(t("viewer.group_render"))
        self.jump_label.setText(t("viewer.jump_interval"))
        self.jump_label.setAccessibleName(t("viewer.jump_interval"))
        self.jump_unit.setText(t("viewer.jump_unit"))
        self.jump_unit.setAccessibleName(t("viewer.jump_unit"))
        self.speed_label.setText(t("viewer.playback_speed"))
        self.speed_label.setAccessibleName(t("viewer.playback_speed"))
        self.speed_unit.setText(t("viewer.playback_unit"))
        self.speed_unit.setAccessibleName(t("viewer.playback_unit"))
        self.jump_combo.setToolTip(t("viewer.jump_interval_tip"))
        self.jump_combo.setAccessibleName(t("viewer.jump_interval"))
        self.speed_combo.setToolTip(t("viewer.playback_speed_tip"))
        self.speed_combo.setAccessibleName(t("viewer.playback_speed"))
        ru = self.i18n.language == "ru"
        self.view_mode_label.setText("Вид" if ru else "View")
        self.preview_mode_label.setText("Предпросмотр" if ru else "Preview")
        if hasattr(self, "batch_step_title"):
            self.batch_step_title.setText(
                "Шаг 1. Что анализировать → 2. Детали → 3. Предустановка → 4. Этапы → 5. Подтверждение"
                if ru else
                "Step 1. What to analyse → 2. Details → 3. Preset → 4. Stages → 5. Confirm"
            )
            labels = {
                "start": "Первый кадр" if ru else "First frame",
                "end": "Последний кадр" if ru else "Last frame",
                "step": "Шаг кадров / минут" if ru else "Frame / minute step",
                "t0": "Начало времени" if ru else "Start time",
                "t1": "Конец времени" if ru else "End time",
                "day_interval": "Интервал (мин)" if ru else "Interval (min)",
                "custom": "Кадры или время через запятую" if ru else "Comma-separated frames or times",
            }
            for key, (label, _field) in self.batch_form_rows.items():
                label.setText(labels[key])
            self.batch_preset_label.setText("Предустановка анализа" if ru else "Analysis preset")
            for i, key in enumerate(("batch.preset.quick", "batch.preset.standard", "batch.preset.scientific_strict", "batch.preset.custom")):
                self.batch_preset.setItemText(i, t(key))
            modes = [
                "Текущий кадр", "Выбранные кадры", "Диапазон кадров", "Диапазон времени",
                "Каждые N минут", "Весь файл", "Произвольный список",
            ] if ru else [
                "Current frame", "Selected frames", "Frame range", "Time range",
                "Every N minutes", "Entire file", "Custom list",
            ]
            for i, label in enumerate(modes):
                self.batch_mode.setItemText(i, label)
            stage_names = {
                "audit": "Проверить качество данных" if ru else "Check data quality",
                "build_cache": "Создать производный кэш" if ru else "Build derived cache",
                "render": "Создать диагностические изображения" if ru else "Render diagnostic images",
                "features": "Измерить признаки изображения" if ru else "Measure image features",
                "rules": "Применить правила-кандидаты" if ru else "Apply candidate rules",
                "references": "Сопоставить с эталонами" if ru else "Compare reference metadata",
                "export_reports": "Сформировать воспроизводимый отчёт" if ru else "Write reproducible report",
                "full_pipeline": "Полный рекомендуемый конвейер" if ru else "Recommended complete pipeline",
            }
            for key, check in self.op_checks.items():
                check.setText(stage_names[key])
        if hasattr(self, "results_empty"):
            self.results_empty.setText(
                "Результатов пока нет. Выберите кадры в «Пакетном анализе» и запустите конвейер."
                if ru else
                "No results yet. Select frames in Batch Analysis and run the pipeline."
            )
            self.btn_results_export.setText("Экспорт" if ru else "Export")
            if hasattr(self, "btn_add_review"):
                self.btn_add_review.setText(
                    "Добавить в набор экспертной проверки" if ru else "Add to review dataset"
                )
            self.results_filter.setItemText(0, "Все" if ru else "All")
            self.results_filter.setItemText(1, "Требуют проверки" if ru else "Needs review")
            self.results_filter.setItemText(2, "Воздержание" if ru else "Abstained")
            self.results_filter.setItemText(3, "Предупреждения" if ru else "Warnings")
            if hasattr(self, "results_columns"):
                self.results_columns.setItemText(0, "Столбцы по умолчанию" if ru else "Default columns")
                self.results_columns.setItemText(1, "Компактно + слой/качество" if ru else "Compact + layer/quality")
                self.results_columns.setItemText(2, "Все столбцы деталей" if ru else "All detail columns")
            if hasattr(self, "analysis_pipeline_panel"):
                self.analysis_pipeline_panel.retranslate(self.i18n.language)
            self._apply_results_headers()
            if not self._results_displayed_identity:
                self.results_identity_line.setText(
                    "Выберите строку результата, чтобы показать точный кадр-источник."
                    if ru else
                    "Select a result row to display its exact source frame."
                )
            self._refresh_review_counts()
        for i, key in enumerate(
            [
                "results.overview",
                "results.evidence",
                "results.details",
                "results.raw",
                "results.features",
                "results.rules",
                "results.alternatives",
                "results.references",
                "results.expert",
                "results.technical",
            ]
        ):
            if i < self.results_tabs.count():
                try:
                    self.results_tabs.setTabText(i, t(key))
                except Exception:
                    labels = (
                        ["Обзор", "Доказательства", "Детали", "Кадр", "Признаки", "Правила",
                         "Альтернативы", "Эталоны", "Эксперт", "Техническое"]
                        if ru else
                        ["Overview", "Evidence", "Details", "Frame", "Features", "Rules",
                         "Alternatives", "References", "Expert", "Technical"]
                    )
                    if i < len(labels):
                        self.results_tabs.setTabText(i, labels[i])
        # settings tab titles
        for i, key in enumerate(
            [
                "settings.general",
                "settings.data",
                "settings.viewer",
                "settings.performance",
                "settings.analysis",
                "settings.matlab",
                "settings.models",
                "settings.reports",
                "settings.storage",
                "settings.reference_packs",
                "settings.privacy",
                "settings.advanced",
            ]
        ):
            if i < self.settings_tabs.count():
                self.settings_tabs.setTabText(i, t(key))
        scale_entry = getattr(self, "_settings_widgets", {}).get("general.interface_scale")
        if scale_entry:
            scale_widget = scale_entry[3]
            scale_widget.setItemText(0, t("settings.interface_scale_auto"))
        if ru:
            self.privacy_label.setText(
                f"{t('settings.telemetry')}\n{t('settings.network')}\n"
                f"{t('settings.protected_study')}\n"
                f"Исходные MAT: только чтение по умолчанию\n"
                f"Режим анализа: {self.settings.analysis_mode()}"
            )
            self.advanced_label.setText(
                f"Пакет правил={self.settings.get('advanced','rule_pack_version')}\n"
                f"Пакет эталонов={self.settings.get('advanced','reference_pack_version')}\n"
                f"Режим анализа={self.settings.analysis_mode()}\n"
                f"Идентификация сборки (ниже):"
            )
        else:
            self.privacy_label.setText(
                f"{t('settings.telemetry')}\n{t('settings.network')}\n"
                f"{t('settings.protected_study')}\n"
                f"Source MAT: read-only by default\n"
                f"Analysis mode: {self.settings.analysis_mode()}"
            )
            self.advanced_label.setText(
                f"rule_pack={self.settings.get('advanced','rule_pack_version')}\n"
                f"reference_pack={self.settings.get('advanced','reference_pack_version')}\n"
                f"analysis_mode={self.settings.analysis_mode()}\n"
                f"Build Identity (below):"
            )
        if hasattr(self, "btn_refresh_build_identity"):
            self.btn_refresh_build_identity.setText(
                "Обновить идентификацию" if ru else "Refresh Build Identity"
            )
            self.btn_copy_build_identity.setText("Копировать" if ru else "Copy")
            self.chk_packaged_profiler.setText(
                "Профилировщик упакованного EXE (IML_PACKAGED_PERF)"
                if ru
                else "Packaged EXE profiler (IML_PACKAGED_PERF)"
            )
            if not self._retranslate_only:
                self._refresh_build_identity_panel()
        self.help_search.setPlaceholderText(t("help.search"))
        # sync settings language combo (visible labels; internal values en/ru)
        lang_wid = self._settings_widgets.get("general.language")
        if lang_wid:
            _, _, _, wid = lang_wid
            wid.blockSignals(True)
            wid.setCurrentIndex(0 if self.i18n.language == "en" else 1)
            wid.blockSignals(False)
        if self.settings_tabs.count():
            form = self.settings_tabs.widget(0).layout()
            if isinstance(form, QFormLayout) and form.rowCount():
                lab_item = form.itemAt(0, QFormLayout.ItemRole.LabelRole)
                if lab_item and lab_item.widget():
                    lab_item.widget().setText(t("settings.interface_language"))
        # tip tooltips
        for tip in self.findChildren(QToolButton):
            oid = tip.objectName() or ""
            if oid.startswith("tip_"):
                tip.setToolTip(t(oid[4:]))
        self._populate_help()
        if not self._retranslate_only:
            self._refresh_viewer_meta()
            self._refresh_batch_preview()
        if hasattr(self, "import_file_list"):
            self.import_file_list.retranslate()
            if not self._retranslate_only:
                self._refresh_import_file_list()

    def set_language(self, language: str) -> None:
        import time

        from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler, span_timer

        lang = "ru" if language == "ru" else "en"
        self._lang_switch_t0 = time.perf_counter()
        self._retranslate_only = True
        self.language_switch_io_count = 0
        with span_timer("language_switch"):
            with span_timer("lang.settings_update"):
                self.i18n.set_language(lang)
                self.settings.set("general", "language", lang)
                # Persist asynchronously — never block UI on disk during switch
                QTimer.singleShot(0, self.settings.save)
            with span_timer("lang.chrome"):
                self._retranslate_chrome()
            with span_timer("lang.visible_page"):
                self._retranslate_visible_page_only()
            with span_timer("lang.mark_hidden_dirty"):
                self._mark_hidden_pages_language_dirty()
            with span_timer("lang.status_bar"):
                self._update_status_bar()
            # Do NOT apply theme, rebuild help Markdown, or walk hidden pages.
        self._retranslate_only = False
        elapsed = time.perf_counter() - self._lang_switch_t0
        prof = get_profiler()
        if prof is not None:
            prof.event(
                "language_switch_done",
                duration_s=elapsed,
                io_count=self.language_switch_io_count,
                dirty_pages=sum(1 for v in self._page_language_dirty.values() if v),
            )

    def _current_page_key(self) -> str | None:
        keys = [k for k, _ in NAV_KEYS]
        try:
            idx = self.stack.currentIndex()
            if 0 <= idx < len(keys):
                return keys[idx]
        except Exception:
            return None
        return None

    def _retranslate_chrome(self) -> None:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        t = self.t
        with span_timer("lang.window_title"):
            self.setWindowTitle(f"{t('app.name')} v{__version__}")
        with span_timer("lang.menus"):
            if hasattr(self, "actions"):
                for action in self.actions.values():
                    action.setText(t(action.data()))
                self.file_menu.setTitle(t("menu.file"))
                self.project_menu.setTitle(t("menu.project"))
                self.analysis_menu.setTitle(t("menu.analysis"))
                self.tools_menu.setTitle(t("menu.tools"))
                self.help_menu.setTitle(t("menu.help"))
        with span_timer("lang.navigation_tree"):
            for key, nav_key in NAV_KEYS:
                full_title = t(nav_key)
                self.nav_items[key].setText(0, full_title)
                self.nav_items[key].setToolTip(0, full_title)
                # Always refresh page-level title labels (including Feature Diagnostics).
                page = self.pages.get(key)
                if page is not None:
                    title = page.findChild(QLabel, f"title_{key}")
                    if title is not None:
                        title.setText(full_title)
            for group_key, label_key, _keys in NAV_GROUPS:
                full_title = t(label_key)
                self.nav_groups[group_key].setText(0, full_title)
                self.nav_groups[group_key].setToolTip(0, full_title)

    def _retranslate_page_body(self, key: str) -> None:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        page = self.pages.get(key)
        if page is None:
            return
        with span_timer(f"lang.page.{key}"):
            title = page.findChild(QLabel, f"title_{key}")
            if title:
                title.setText(self.t(dict(NAV_KEYS).get(key, f"nav.{key}")))
            # Intro panel for this page only
            panel = getattr(self, "intro_panels", {}).get(key)
            if panel is not None and hasattr(panel, "retranslate"):
                panel.retranslate()
            lay = page.layout()
            if lay and lay.count() >= 1:
                w = lay.itemAt(lay.count() - 1).widget()
                if w is not None:
                    if hasattr(w, "retranslate_ui"):
                        w.retranslate_ui()
                    elif hasattr(w, "retranslate"):
                        w.retranslate()
            self._page_language_dirty[key] = False

    def _retranslate_visible_page_only(self) -> None:
        key = self._current_page_key()
        if key:
            self._retranslate_page_body(key)
        # Compact source strips on visible work pages only
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("lang.source_strips_visible"):
            # Labels only — never resolve/open/stat MAT during language switch.
            self._retranslate_source_strips_only()

    def _mark_hidden_pages_language_dirty(self) -> None:
        cur = self._current_page_key()
        for key, _ in NAV_KEYS:
            if key == cur:
                continue
            if self._page_materialized.get(key, False):
                self._page_language_dirty[key] = True

    def _show_about(self) -> None:
        body = self.t("about.body").replace("{version}", __version__)
        QMessageBox.about(self, self.t("about.title"), body)

    def _refresh_build_identity_panel(self) -> None:
        from ionogram_morphology_lab.ui.build_identity import collect_build_identity, format_build_identity
        from ionogram_morphology_lab.utils.paths import app_root

        if not hasattr(self, "build_identity_view"):
            return
        # Prefer cached SHA; compute only if still pending (background warmer usually fills it).
        cache_path = self.settings.cache_dir()
        ident = collect_build_identity(
            cache_root=cache_path,
            workspace_root=app_root() / "workspaces",
            active_project_path=getattr(self.session.project, "root", None) if self.session.project else None,
            compute_sha=not self._retranslate_only,
            cache_root_info=self.settings.cache_root_info(),
        )
        self._build_identity = ident
        self.build_identity_view.setPlainText(format_build_identity(ident, self.i18n.language))
        warn = ident.get("cache_root_warning") or ""
        if warn and getattr(self, "advanced_label", None) is not None:
            # Surface once in Advanced settings
            pass

    def _show_build_identity(self) -> None:
        self._refresh_build_identity_panel()
        text = getattr(self, "build_identity_view", None)
        body = text.toPlainText() if text is not None else ""
        if not body:
            from ionogram_morphology_lab.ui.build_identity import collect_build_identity, format_build_identity
            from ionogram_morphology_lab.utils.paths import app_root

            body = format_build_identity(
                collect_build_identity(
                    cache_root=self.settings.cache_dir(),
                    workspace_root=app_root() / "workspaces",
                    active_project_path=getattr(self.session.project, "root", None)
                    if self.session.project
                    else None,
                ),
                self.i18n.language,
            )
        dlg = QDialog(self)
        dlg.setWindowTitle("Build Identity" if self.i18n.language != "ru" else "Идентификация сборки")
        lay = QVBoxLayout(dlg)
        edit = QPlainTextEdit()
        edit.setReadOnly(True)
        edit.setPlainText(body)
        lay.addWidget(edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        try:
            from ionogram_morphology_lab.ui.dialog_buttons import localize_dialog_buttons

            localize_dialog_buttons(buttons, self.i18n.language)
        except Exception:
            pass
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        btn_copy = QPushButton("Copy" if self.i18n.language != "ru" else "Копировать")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(body))
        buttons.addButton(btn_copy, QDialogButtonBox.ButtonRole.ActionRole)
        lay.addWidget(buttons)
        dlg.resize(640, 420)
        dlg.exec()

    def _start_packaged_profiler_if_enabled(self) -> None:
        from ionogram_morphology_lab.ui.build_identity import collect_build_identity
        from ionogram_morphology_lab.ui.packaged_exe_profiler import profiler_enabled, start_profiler
        from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

        if not profiler_enabled(self.settings):
            return
        out = ensure_dir(app_root() / "workspaces" / "_packaged_exe_perf")
        # Session subfolder
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        session_dir = ensure_dir(out / stamp)
        ident = collect_build_identity(
            cache_root=self.settings.cache_dir(),
            workspace_root=app_root() / "workspaces",
            active_project_path=getattr(self.session.project, "root", None) if self.session.project else None,
        )
        start_profiler(session_dir, identity=ident)
        self._perf_heartbeat = QTimer(self)
        self._perf_heartbeat.setInterval(250)

        def _tick() -> None:
            from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler

            p = get_profiler()
            if p is not None:
                p.heartbeat_tick()

        self._perf_heartbeat.timeout.connect(_tick)
        self._perf_heartbeat.start()

    def _ensure_page_materialized(self, key: str) -> None:
        """Create heavy page body once; later activations reuse the same instance."""
        if self._page_materialized.get(key, True):
            return
        page = self.pages.get(key)
        builder = self._page_builders.get(key)
        if page is None or builder is None:
            return
        from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler, span_timer

        with span_timer("page_creation", page=key):
            lay = page.layout()
            if lay is None:
                return
            with span_timer("page_creation.remove_placeholder", page=key):
                for i in range(lay.count() - 1, -1, -1):
                    item = lay.itemAt(i)
                    w = item.widget() if item else None
                    if w is not None and (w.objectName() or "").startswith("lazy_placeholder_"):
                        lay.removeWidget(w)
                        w.deleteLater()
                        break
            with span_timer("page_creation.builder", page=key):
                body = builder()
                body.setObjectName(f"page_body_{key}")
            with span_timer("page_creation.addWidget", page=key):
                lay.addWidget(body, 1)
            self._page_materialized[key] = True
            self.page_instance_created_count[key] = int(self.page_instance_created_count.get(key, 0)) + 1
            # Language already current — only apply if dirty; skip full retranslate
            with span_timer("page_creation.initial_labels", page=key):
                if hasattr(body, "retranslate_ui"):
                    body.retranslate_ui()
                elif hasattr(body, "retranslate"):
                    body.retranslate()
            self._page_language_dirty[key] = False
            prof = get_profiler()
            if prof is not None:
                prof.bump("page_instance_created_count")
                prof.event("page_materialized", page=key)

    def _why_provisional_profile(self) -> None:
        from ionogram_morphology_lab.ui.why_links import why_text

        QMessageBox.information(
            self,
            "Why?",
            why_text("provisional_profile", self.i18n.language)
            + "\n\n"
            + why_text("nominal_virtual_height", self.i18n.language),
        )

    def _restore_intros(self) -> None:
        for panel in getattr(self, "intro_panels", {}).values():
            if hasattr(panel, "restore"):
                panel.restore()
        if hasattr(self, "home_dashboard") and hasattr(self.home_dashboard, "intro"):
            self.home_dashboard.intro.restore()
        rules_page = None
        page = self.pages.get("rules")
        if page and page.layout() and page.layout().count() >= 2:
            rules_page = page.layout().itemAt(1).widget()
        if rules_page is not None and hasattr(rules_page, "intro"):
            rules_page.intro.restore()
        QMessageBox.information(
            self,
            "Help",
            "Page introductions restored." if self.i18n.language != "ru" else "Введения страниц восстановлены.",
        )

    def _update_status_bar(self) -> None:
        t = self.t
        p = self.session.project.name if self.session.project else "—"
        f = self.session.active_mat.name if self.session.active_mat else "—"
        cache = "—"
        if self.session.frame_store:
            st = self.session.frame_store.status()
            cache = "ready" if st.valid else (st.reason or "missing")
        tm = mapping_status(self.session.profile.get("time_mapping"))
        time_s = (
            format_hhmm(frame_to_minute(self.session.current_frame))
            if tm.available
            else "n/a"
        )
        self.status_project.setText(f"{t('status.project')}: {p}")
        self.status_file.setText(f"{t('status.file')}: {f}")
        self.status_profile.setText(
            f"{t('status.profile')}: {self.session.profile_id} ({self.session.profile.get('profile_verification_status')})"
        )
        self.status_cache.setText(f"{t('status.cache')}: {cache}")
        self.status_frame.setText(
            f"{t('status.frame')}: {self.session.current_frame} | {t('status.time')}: {time_s}"
        )
        self.status_task.setText(
            f"{t('status.task')}: {self.session.background_task or '—'} | {t('status.mode')}"
        )

    def _on_nav(self, row: int) -> None:
        keys = [k for k, _ in NAV_KEYS]
        if 0 <= row < len(keys):
            self._navigate_key(keys[row])

    def _on_nav_item(self, item: QTreeWidgetItem, _column: int) -> None:
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if key:
            self._navigate_key(key)

    def _warm_v2_worker(self) -> None:
        try:
            from ionogram_morphology_lab.ui.v2_process_worker import shared_pool

            shared_pool().start_async()
        except Exception:  # noqa: BLE001
            pass

    def _navigate_key(self, key: str) -> None:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler, span_timer

        keys = [k for k, _ in NAV_KEYS]
        if key in keys:
            with span_timer("page_activation", page=key):
                prev = None
                try:
                    prev = keys[self.stack.currentIndex()]
                except Exception:
                    prev = None
                with span_timer("nav.deactivate_prev", page=prev or ""):
                    if prev == "feature_diagnostics" and key != "feature_diagnostics":
                        prof = get_profiler()
                        if prof is not None:
                            prof.event("page_deactivate", page="feature_diagnostics", wait=False)
                with span_timer("nav.ensure_materialized", page=key):
                    self._ensure_page_materialized(key)
                with span_timer("nav.set_current_widget", page=key):
                    self.stack.setCurrentIndex(keys.index(key))
                with span_timer("nav.update_selection", page=key):
                    item = self.nav_items[key]
                    self.nav.setCurrentItem(item)
                    item.parent().setExpanded(True)
                self.page_activation_count[key] = int(self.page_activation_count.get(key, 0)) + 1
                prof = get_profiler()
                if prof is not None:
                    prof.bump("page_activation_count")
                # Lazy language apply for dirty pages — never global retranslate/theme.
                with span_timer("nav.lazy_language", page=key):
                    if self._page_language_dirty.get(key):
                        self._retranslate_page_body(key)
                with span_timer("nav.source_strip_light", page=key):
                    self._refresh_source_cards(light=True)
                with span_timer("nav.activate_page", page=key):
                    if key == "home" and hasattr(self, "home_dashboard") and not self._retranslate_only:
                        # Defer home refresh — do not block switch paint
                        QTimer.singleShot(0, self.home_dashboard.refresh)
                    if key == "feature_diagnostics" and hasattr(self, "_feature_diagnostics_page"):
                        page = self._feature_diagnostics_page
                        if hasattr(page, "activate"):
                            page.activate(force_load=False)
                    if key == "raw_signals" and hasattr(self, "_raw_signals_page"):
                        if hasattr(self._raw_signals_page, "activate"):
                            self._raw_signals_page.activate()

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, lambda: self._goto_frame(self.session.current_frame - 1))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, lambda: self._goto_frame(self.session.current_frame + 1))
        QShortcut(QKeySequence(Qt.Key.Key_Home), self, lambda: self._goto_frame(1))
        QShortcut(QKeySequence(Qt.Key.Key_End), self, lambda: self._goto_frame(self.frame_spin.maximum()))
        QShortcut(QKeySequence(Qt.Key.Key_PageUp), self, self._jump_back)
        QShortcut(QKeySequence(Qt.Key.Key_PageDown), self, self._jump_fwd)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._toggle_play)
        QShortcut(QKeySequence("Ctrl+G"), self, self._goto_dialog)

    # ----- actions -----
    def _recent_projects(self) -> list[dict]:
        raw = self.settings.get("general", "recent_projects", []) or []
        return [r for r in raw if isinstance(r, dict) and r.get("path")]

    def _remember_project(self, project: AnalysisProject) -> None:
        entry = {
            "name": project.name,
            "path": str(Path(project.root) / "project.json"),
            "root": str(project.root),
            "last_opened": datetime.now(timezone.utc).isoformat(),
        }
        items = [entry] + [r for r in self._recent_projects() if r.get("path") != entry["path"]]
        self.settings.set("general", "recent_projects", items[:12])
        self.settings.save()

    def _refresh_projects_page(self) -> None:
        if not hasattr(self, "proj_current_info"):
            return
        ru = self.i18n.language == "ru"
        self.proj_current_box.setTitle("Текущий проект" if ru else "Current project")
        self.proj_open_box.setTitle("Открыть проект" if ru else "Open project")
        self.proj_create_box.setTitle("Создать проект" if ru else "Create project")
        if hasattr(self, "btn_open_project"):
            self.btn_open_project.setText("Открыть проект" if ru else "Open project")
            self.btn_browse_project_folder.setText(
                "Выбрать папку проекта" if ru else "Choose project folder"
            )
            self.btn_open_recent.setText(
                "Открыть недавний проект" if ru else "Open recent project"
            )
        p = self.session.project
        if p is None:
            self.proj_current_info.setText(
                "Проект не открыт." if ru else "No project is open."
            )
        else:
            active = self.session.active_mat.name if self.session.active_mat else "—"
            run = str(self.session.last_run_root) if self.session.last_run_root else "—"
            self.proj_current_info.setText(
                f"{'Имя' if ru else 'Name'}: {p.name}\n"
                f"{'Путь' if ru else 'Path'}: {p.root}\n"
                f"{'Создан' if ru else 'Created'}: {getattr(p, 'created_at', '—')}\n"
                f"{'Активный файл' if ru else 'Active source file'}: {active}\n"
                f"{'Активный запуск' if ru else 'Active run'}: {run}\n"
                f"{'Несохранённые правки' if ru else 'Unsaved changes'}: "
                f"{'да (сохраните проект при необходимости)' if ru else 'possible — save project if needed'}"
            )
        headers = (
            ["Имя", "Путь", "Открыт", "Доступность", "Действия"]
            if ru
            else ["Name", "Path", "Last opened", "Availability", "Actions"]
        )
        self.recent_projects_table.setHorizontalHeaderLabels(headers)
        recent = self._recent_projects()
        self.recent_projects_table.setRowCount(len(recent))
        for i, item in enumerate(recent):
            path = Path(str(item.get("path") or ""))
            available = path.exists()
            self.recent_projects_table.setItem(i, 0, QTableWidgetItem(str(item.get("name", ""))))
            self.recent_projects_table.setItem(i, 1, QTableWidgetItem(str(item.get("path", ""))))
            self.recent_projects_table.setItem(i, 2, QTableWidgetItem(str(item.get("last_opened", ""))))
            self.recent_projects_table.setItem(
                i, 3, QTableWidgetItem("доступен" if (ru and available) else ("available" if available else ("нет" if ru else "missing")))
            )
            cell = QWidget()
            hl = QHBoxLayout(cell)
            hl.setContentsMargins(0, 0, 0, 0)
            open_b = QPushButton("Open" if not ru else "Открыть")
            open_b.clicked.connect(lambda _=False, p=str(path): self._switch_to_project_json(p))
            rem_b = QPushButton("Remove" if not ru else "Убрать")
            rem_b.clicked.connect(lambda _=False, p=str(path): self._remove_recent_project(p))
            hl.addWidget(open_b)
            hl.addWidget(rem_b)
            self.recent_projects_table.setCellWidget(i, 4, cell)

    def _remove_recent_project(self, path: str) -> None:
        items = [r for r in self._recent_projects() if r.get("path") != path]
        self.settings.set("general", "recent_projects", items)
        self.settings.save()
        self._refresh_projects_page()

    def _open_selected_recent_project(self) -> None:
        rows = self.recent_projects_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(
                self,
                "IML",
                "Выберите проект в списке." if self.i18n.language == "ru" else "Select a project in the list.",
            )
            return
        path_item = self.recent_projects_table.item(rows[0].row(), 1)
        if path_item:
            self._switch_to_project_json(path_item.text())

    def _open_project_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Project folder" if self.i18n.language != "ru" else "Папка проекта"
        )
        if not folder:
            return
        candidate = Path(folder) / "project.json"
        if not candidate.exists():
            QMessageBox.warning(
                self,
                "IML",
                "В папке нет project.json." if self.i18n.language == "ru" else "No project.json in that folder.",
            )
            return
        self._switch_to_project_json(str(candidate))

    def _confirm_project_switch(self) -> bool:
        ru = self.i18n.language == "ru"
        if self.matlab_jobs is not None and hasattr(self.matlab_jobs, "has_running_jobs"):
            try:
                if self.matlab_jobs.has_running_jobs():
                    QMessageBox.warning(
                        self,
                        "IML",
                        "Сначала остановите активные задания MATLAB."
                        if ru
                        else "Stop active MATLAB jobs before switching projects.",
                    )
                    return False
            except Exception:  # noqa: BLE001
                pass
        if self.session.project is None:
            return True
        answer = QMessageBox.question(
            self,
            "IML",
            (
                "Сменить проект? Несохранённые правки могут быть потеряны. "
                "Результаты текущего проекта не будут смешаны с новым."
                if ru
                else "Switch project? Unsaved edits may be lost. "
                "Results from the current project will not be mixed with the next one."
            ),
        )
        return answer == QMessageBox.StandardButton.Yes

    def _clear_project_ui_state(self) -> None:
        self.session.last_run_root = None
        self.session.last_results = []
        self.session.matlab_comparison_candidates = []
        self.session.selected_mats = []
        self.session.set_active_mat(None)
        if hasattr(self, "_feature_diagnostics_page"):
            self._feature_diagnostics_page.clear_results()
        if hasattr(self, "results_table"):
            self.results_table.setRowCount(0)
        self.session.events.project_changed.emit()

    def _switch_to_project_json(self, path: str) -> None:
        if not self._confirm_project_switch():
            return
        try:
            project = AnalysisProject.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
            self._clear_project_ui_state()
            self.session.project = project
            self.session.restore_inventory_from_project()
            self.proj_name.setText(project.name)
            self._remember_project(project)
            self.proj_status.setText(f"{self.t('project.opened')}: {project.root}")
            self._refresh_projects_page()
            self._refresh_source_cards()
            self._update_status_bar()
            self.session.events.project_changed.emit()
            self.session.events.active_mat_changed.emit()
            self._navigate_key("projects")
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._error_dialog(str(exc), traceback.format_exc())

    def _create_project(self) -> None:
        if self.session.project is not None and not self._confirm_project_switch():
            return
        name = self.proj_name.text().strip() or "IML_Project"
        ws = self.settings.get("general", "workspace_dir") or None
        self._clear_project_ui_state()
        self.session.project = create_project(
            name,
            language=self.i18n.language,
            workspace_parent=ws,
            profile_id=self.session.profile_id,
        )
        self._remember_project(self.session.project)
        self.proj_status.setText(f"{self.t('project.created')}: {self.session.project.root}")
        self._refresh_projects_page()
        self._refresh_source_cards()
        self._update_status_bar()
        self.session.events.project_changed.emit()

    def _open_project(self) -> None:
        path = QFileDialog.getOpenFileName(
            self, self.t("menu.open_project"), "", "IML project (project.json)"
        )[0]
        if not path:
            return
        self._switch_to_project_json(path)

    def _save_project(self) -> None:
        if self.session.project is None:
            self._navigate_key("projects")
            QMessageBox.information(self, "IML", self.t("menu.new_project"))
            return
        project = self.session.project
        project.source_paths = [str(path) for path in self.session.selected_mats]
        project.active_source_path = str(self.session.active_mat) if self.session.active_mat else None
        (project.path / "project.json").write_text(
            json.dumps(project.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.proj_status.setText(f"{self.t('project.saved')}: {project.root}")

    def _import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "MAT", "", "MAT (*.mat)")
        if path:
            self._add_mat(Path(path), make_active=True)

    def _import_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "MAT folder")
        if not path:
            return
        try:
            files = list_mat_files(path, recursive=bool(self.settings.get("data", "recursive_folder_scan", True)))
        except ForbiddenPathError:
            QMessageBox.critical(self, "IML", self.t("import.blocked"))
            return
        for i, f in enumerate(files):
            self._add_mat(f, make_active=(i == len(files) - 1), confirm=(i == len(files) - 1))

    def _add_mat(self, path: Path, *, make_active: bool = True, confirm: bool = True) -> None:
        try:
            default_blocklist().assert_allowed(path)
        except ForbiddenPathError:
            QMessageBox.critical(self, "IML", self.t("import.blocked"))
            return
        cls = classify_mat_source(path, self.session.profile, try_frame=True)
        activate = bool(make_active and cls.can_activate)
        if activate and not self._confirm_safe_source_switch(path):
            self.session.add_to_inventory(path, make_active=False)
            self._refresh_import_file_list()
            self._refresh_source_cards()
            return
        # Never replace a valid Am_all active source with an incompatible file
        if make_active and not cls.can_activate:
            activate = False
        self.session.add_to_inventory(path, make_active=activate)
        if activate:
            self._apply_source_switch_cleanup()
        audit = audit_mat_path(path, self.session.profile)
        self.session.last_audits.append(audit.to_dict())
        lang = self.i18n.language
        cards = [audit_card(a, lang) for a in self.session.last_audits[-20:]]
        if hasattr(self, "import_cards"):
            self.import_cards.setPlainText("\n\n———\n\n".join(cards))
        self.import_tech.setPlainText(json.dumps(audit.to_dict(), indent=2, ensure_ascii=False))
        self._refresh_import_file_list()
        self._refresh_viewer_meta()
        self._refresh_source_cards()
        self._update_status_bar()
        if activate and confirm:
            confirm_imported_active(self, self.i18n.language, path.name)
        elif make_active and not cls.can_activate:
            QMessageBox.information(
                self,
                "IML",
                localize_role_message(
                    "imported_auxiliary", self.i18n.language, variable=cls.primary_variable
                )
                + f"\n{path.name}",
            )
        if activate:
            self._navigate_key("viewer")
        else:
            self._navigate_key("import")

    def _refresh_import_file_list(self) -> None:
        if not hasattr(self, "import_file_list"):
            return
        self.import_file_list.rebuild(
            list(self.session.selected_mats),
            self.session.profile,
            self.session.active_mat,
        )

    def _apply_theme(self) -> None:
        pref = str(self.settings.get("general", "theme", "system") or "system")
        app = QApplication.instance()
        apply_app_theme(app, pref)
        for attr in (
            "import_source_card",
            "viewer_source_card",
            "batch_source_card",
            "raw_signals_source_card",
            "matlab_source_card",
        ):
            card = getattr(self, attr, None)
            if card is not None and hasattr(card, "apply_theme"):
                card.apply_theme(pref)
        if hasattr(self, "import_file_list"):
            self.import_file_list.apply_theme(pref)
        if hasattr(self, "_feature_diagnostics_page"):
            self._feature_diagnostics_page.apply_theme(pref)
            self._feature_diagnostics_page.source_card.apply_theme(pref)

    def _retranslate_source_strips_only(self) -> None:
        """Language path: retranslate strip/card labels from cached snapshots — zero MAT I/O."""
        for attr in (
            "import_source_card",
            "viewer_source_card",
            "batch_source_card",
            "raw_signals_source_card",
            "matlab_source_card",
        ):
            card = getattr(self, attr, None)
            if card is not None and hasattr(card, "retranslate"):
                card.retranslate()
        if hasattr(self, "_feature_diagnostics_page"):
            sc = getattr(self._feature_diagnostics_page, "source_card", None)
            if sc is not None and hasattr(sc, "retranslate"):
                sc.retranslate()

    def _refresh_source_cards(self, *, light: bool = False) -> None:
        # light=True (nav/lang): use cached snapshot only — never force MAT rebuild.
        snap = resolve_active_source(self.session, force_rebuild=False)
        for attr in (
            "import_source_card",
            "viewer_source_card",
            "batch_source_card",
            "raw_signals_source_card",
            "matlab_source_card",
        ):
            card = getattr(self, attr, None)
            if card is not None:
                card.apply_snapshot(snap)
        if hasattr(self, "_feature_diagnostics_page"):
            self._feature_diagnostics_page.source_card.apply_snapshot(snap)
        # Full import-list rebuild can be expensive; skip on language/page light refresh.
        if not light and not self._retranslate_only:
            self._refresh_import_file_list()

    def _source_blockers(self) -> list[str]:
        """Return human-readable blockers that make an unsafe source switch."""
        ru = self.i18n.language == "ru"
        blockers: list[str] = []
        if getattr(self, "_play_timer", None) is not None and self._play_timer.isActive():
            blockers.append(
                "Воспроизведение в Viewer активно." if ru else "Viewer playback is active."
            )
        if getattr(self.session, "background_task", ""):
            blockers.append(
                "Выполняется пакетный анализ." if ru else "A batch analysis job is running."
            )
        if self.matlab_jobs is not None:
            try:
                running = False
                if hasattr(self.matlab_jobs, "has_running_jobs"):
                    running = bool(self.matlab_jobs.has_running_jobs())
                elif hasattr(self.matlab_jobs, "has_active_jobs"):
                    running = bool(self.matlab_jobs.has_active_jobs())
                if running:
                    blockers.append(
                        "Выполняется задание MATLAB." if ru else "A MATLAB job is running."
                    )
            except Exception:  # noqa: BLE001
                pass
        if hasattr(self, "_feature_diagnostics_page") and self._feature_diagnostics_page.is_job_running():
            blockers.append(
                "Выполняется Feature Pipeline V2."
                if ru
                else "A Feature Pipeline V2 job is running."
            )
        elif getattr(self.session, "v2_job_status", "") == "running":
            blockers.append(
                "Выполняется Feature Pipeline V2."
                if ru
                else "A Feature Pipeline V2 job is running."
            )
        return blockers

    def _confirm_safe_source_switch(self, new_path: Path | None) -> bool:
        """Ask/stop when switching or detaching would mix contexts or interrupt jobs."""
        current = self.session.active_mat
        if new_path is not None and current is not None:
            try:
                if Path(current).resolve() == Path(new_path).resolve():
                    return True
            except OSError:
                if Path(current) == Path(new_path):
                    return True
        if current is None and new_path is not None:
            return True

        ru = self.i18n.language == "ru"
        blockers = self._source_blockers()
        if blockers:
            # Hard-block active V2 / MATLAB / batch; allow stopping playback.
            hard = [
                b
                for b in blockers
                if ("V2" in b or "MATLAB" in b or "пакетн" in b.lower() or "batch" in b.lower())
            ]
            if hard:
                QMessageBox.warning(
                    self,
                    "IML",
                    (
                        "Нельзя сменить источник, пока выполняется задача:\n- "
                        + "\n- ".join(hard)
                        if ru
                        else "Cannot switch source while a job is running:\n- " + "\n- ".join(hard)
                    ),
                )
                return False
            if getattr(self, "_play_timer", None) is not None and self._play_timer.isActive():
                ans = QMessageBox.question(
                    self,
                    "IML",
                    (
                        "Остановить воспроизведение Viewer и сменить источник?"
                        if ru
                        else "Stop Viewer playback and switch source?"
                    ),
                )
                if ans != QMessageBox.StandardButton.Yes:
                    return False
                self._play_timer.stop()

        if current is not None and new_path is None:
            msg = (
                "Отключить от анализа? Файл останется в проекте и на компьютере. "
                "Его можно снова активировать для анализа."
                if ru
                else "Deactivate for Analysis? The file remains in the project and on disk. "
                "You can activate it again for analysis."
            )
            ans = QMessageBox.question(self, "IML", msg)
            return ans == QMessageBox.StandardButton.Yes
        if current is not None and new_path is not None:
            return confirm_switch_active(
                self, self.i18n.language, Path(current).name, Path(new_path).name
            )
        return True

    def _apply_source_switch_cleanup(self) -> None:
        """Clear stale per-source UI after MAT switch/detach — never mix MAT A/B results."""
        if getattr(self, "_play_timer", None) is not None:
            self._play_timer.stop()
        self._viewer_ready = False
        self._viewer_n_frames = 0
        self._set_viewer_controls_enabled(False)
        self._set_viewer_status("not_loaded")
        if hasattr(self, "viewer_view_label"):
            self.viewer_view_label.clear()
        self.session.matlab_comparison_candidates = []
        if hasattr(self, "matlab_page") and hasattr(self.matlab_page, "clear_execution_context"):
            try:
                self.matlab_page.clear_execution_context()
            except Exception:  # noqa: BLE001
                pass
        if hasattr(self, "_feature_diagnostics_page"):
            self._feature_diagnostics_page.clear_results()
        self._refresh_viewer_meta()
        self._refresh_source_cards()
        if hasattr(self, "_feature_diagnostics_page"):
            self._feature_diagnostics_page.refresh()
        if hasattr(self, "_raw_signals_page"):
            self._raw_signals_page.refresh()
        self._update_status_bar()

    def _activate_mat_validated(self, path: Path, *, confirm_msg: bool = True) -> bool:
        """Validate and activate a compatible MAT. On failure keep previous active source."""
        previous = self.session.active_mat
        cls = classify_mat_source(path, self.session.profile, try_frame=True)
        if not path.is_file() or not cls.can_activate:
            QMessageBox.warning(
                self,
                "IML",
                localize_role_message(
                    cls.reason_code or "missing_amp_all",
                    self.i18n.language,
                    variable=cls.primary_variable,
                ),
            )
            return False
        if not self._confirm_safe_source_switch(path):
            return False
        try:
            self.session.set_active_mat(path)
            self._apply_source_switch_cleanup()
            self._save_project_quiet()
            if confirm_msg:
                confirm_set_active(self, self.i18n.language, path.name)
            return True
        except Exception as exc:  # noqa: BLE001
            # Roll back — never leave half-switched state
            self.session.set_active_mat(previous)
            self._apply_source_switch_cleanup()
            user, tech = format_missing_variable_user_message(exc, self.i18n.language)
            self._error_dialog(user, tech)
            return False

    def _save_project_quiet(self) -> None:
        if self.session.project is None:
            return
        project = self.session.project
        project.source_paths = [str(path) for path in self.session.selected_mats]
        project.active_source_path = str(self.session.active_mat) if self.session.active_mat else None
        try:
            (project.path / "project.json").write_text(
                json.dumps(project.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _pick_active_from_project(self) -> None:
        ru = self.i18n.language == "ru"
        compatible: list[Path] = []
        for p in self.session.selected_mats:
            cls = classify_mat_source(p, self.session.profile, try_frame=False)
            if cls.can_activate:
                compatible.append(Path(p))
        if not compatible:
            QMessageBox.information(
                self,
                "IML",
                "В проекте нет совместимых Am_all-файлов."
                if ru
                else "No compatible Am_all files in the project.",
            )
            return
        names = [p.name for p in compatible]
        choice, ok = QInputDialog.getItem(
            self,
            localize_role_message("pick_from_project", self.i18n.language),
            localize_role_message("no_active_selected", self.i18n.language),
            names,
            0,
            False,
        )
        if not ok or not choice:
            return
        path = next(p for p in compatible if p.name == choice)
        self._activate_mat_validated(path)

    def _handle_import_file_action(self, action: str, path_str: str) -> None:
        path = Path(path_str)
        if action == "set_active":
            self._activate_mat_validated(path)
            return
        if action == "unset_active":
            self._handle_source_action("detach")
            return
        if action == "open":
            if self._activate_mat_validated(path, confirm_msg=False):
                self._navigate_key("viewer")
            return
        if action == "remove":
            self._remove_inventory_path(path)
            return
        if action == "open_folder":
            open_file_folder(path)
            return
        if action == "choose_compatible":
            self._pick_active_from_project()
            return

    def _remove_inventory_path(self, target: Path) -> None:
        ru = self.i18n.language == "ru"
        ans = QMessageBox.question(
            self,
            "IML",
            (
                f"Убрать из проекта?\n{target.name}\n\n"
                "Запись исчезнет из проекта. Файл на компьютере удалён не будет."
                if ru
                else f"Remove from project?\n{target.name}\n\n"
                "The entry will disappear from the project. The file on disk will not be deleted."
            ),
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        existed = target.exists()
        self.session.remove_inventory_entry(target)
        self._apply_source_switch_cleanup()
        self._save_project_quiet()
        self._refresh_import_file_list()
        if existed and not target.exists():
            QMessageBox.critical(
                self,
                "IML",
                "Ошибка: файл исчез с диска." if ru else "Error: file disappeared from disk.",
            )

    def _handle_source_action(self, action: str) -> None:
        ru = self.i18n.language == "ru"
        if action == "refresh":
            # Explicit Refresh Source — intentional MAT inspect / snapshot rebuild.
            try:
                self.session.refresh_active_source_snapshot()
            except Exception:
                resolve_active_source(self.session, force_rebuild=True)
            self._refresh_source_cards()
            if hasattr(self, "_feature_diagnostics_page"):
                self._feature_diagnostics_page.refresh()
            if hasattr(self, "_raw_signals_page"):
                self._raw_signals_page.refresh()
            return
        snap = resolve_active_source(self.session, force_rebuild=False)

        if action == "open_import":
            self._navigate_key("import")
            return
        if action == "open_folder":
            if snap.mat_path is not None:
                open_file_folder(Path(snap.mat_path))
            return
        if action == "choose_mat":
            path, _ = QFileDialog.getOpenFileName(self, "MAT", "", "MAT (*.mat)")
            if path:
                self._add_mat(Path(path), make_active=True, confirm=True)
            return
        if action == "pick_from_project":
            self._pick_active_from_project()
            return
        if action == "set_active":
            self._pick_active_from_project()
            return
        if action == "detach":
            if self.session.active_mat is None:
                return
            if not self._confirm_safe_source_switch(None):
                return
            self.session.detach_active_mat()
            self._apply_source_switch_cleanup()
            self._save_project_quiet()
            return
        if action == "remove_entry":
            target = snap.mat_path or (self.session.selected_mats[0] if self.session.selected_mats else None)
            if target is None:
                return
            self._remove_inventory_path(Path(target))
            return

    def _load_kfu_profile(self) -> None:
        self.session.load_profile("kfu_cyclone_2013_2014")
        lang = self.i18n.language
        self.profile_card_view.setPlainText(profile_card(self.session.profile, lang))
        self.profile_raw.setPlainText(json.dumps(self.session.profile, indent=2, ensure_ascii=False))
        self._update_status_bar()

    def _wizard_advance(self) -> None:
        if not self.wizard.sample_mat:
            if self.session.active_mat:
                self.wizard.load_sample(self.session.active_mat)
            else:
                QMessageBox.information(self, "IML", self.t("viewer.no_import"))
                return
        step = self.wizard.next_step()
        if step == "save_profile":
            path = self.wizard.save()
            self.profile_card_view.append(f"Saved: {path}")
        if step == "run_validation":
            self.profile_card_view.append("; ".join(self.wizard.validate()))
        self.profile_card_view.append(f"Wizard: {self.wizard.current_step()}")

    def _run_audit(self) -> None:
        mats = self.session.selected_mats or list((app_root() / "synthetic_data").glob("*.mat"))
        cards = []
        tech = []
        for path in mats:
            try:
                res = audit_mat_path(path, self.session.profile)
                cards.append(audit_card(res.to_dict(), self.i18n.language))
                tech.append(res.to_dict())
            except Exception as exc:  # noqa: BLE001
                self._error_dialog(str(exc), traceback.format_exc())
        self.audit_cards.setPlainText("\n\n———\n\n".join(cards))
        self.audit_tech.setPlainText(json.dumps(tech, indent=2, ensure_ascii=False))

    def _open_real_viewer(self) -> None:
        if not self.session.has_real_import():
            QMessageBox.information(self, "IML", self.t("viewer.no_import"))
            self._set_viewer_status("not_loaded")
            return
        if self.settings.get("performance", "automatic_cache_creation", True):
            self._build_cache_async()
        else:
            self._activate_viewer_if_ready(render=True)

    def _cache_build_running(self) -> bool:
        return bool(self._cache_worker is not None and self._cache_worker.isRunning())

    def _build_cache_async(self) -> None:
        if not self.session.has_real_import():
            QMessageBox.information(self, "IML", self.t("viewer.no_import"))
            return
        if self._cache_build_running():
            _LOG.info("viewer: cache build already running; ignore duplicate start")
            self._set_viewer_status("cache_building")
            return
        store = self.session.ensure_store()
        if store.status().valid:
            self._activate_viewer_if_ready(render=True)
            return
        self._viewer_ready = False
        self._set_viewer_controls_enabled(False)
        self._viewer_render_timer.stop()
        self.cache_progress.setVisible(True)
        self.cache_progress.setValue(0)
        self.session.background_task = "cache"
        self._set_viewer_status("cache_building")
        self._update_status_bar()
        self._cache_worker = CacheBuildWorker(store)
        self._cache_worker.progress.connect(self._on_cache_progress)
        self._cache_worker.finished_ok.connect(self._on_cache_ready)
        self._cache_worker.failed.connect(self._on_cache_failed)
        self._cache_worker.start()

    def _on_cache_progress(self, info: dict) -> None:
        if "percent" in info:
            self.cache_progress.setValue(int(info["percent"]))
        self.session.background_task = info.get("event", "cache")
        self._set_viewer_status("cache_building")
        self._update_status_bar()

    def _on_cache_ready(self, info: dict) -> None:
        self.cache_progress.setVisible(False)
        self.session.background_task = ""
        self._activate_viewer_if_ready(render=True)
        self._refresh_source_cards()
        self.session.events.cache_rebuilt.emit()
        self._update_status_bar()

    def _on_cache_failed(self, message: str) -> None:
        self.cache_progress.setVisible(False)
        self.session.background_task = ""
        self._viewer_ready = False
        self._set_viewer_controls_enabled(False)
        self._set_viewer_status("render_error", detail=message)
        _LOG.error("viewer cache build failed: %s", message)
        self._error_dialog(message, message)

    def _refresh_viewer_meta(self) -> None:
        lang = self.i18n.language
        ru = lang == "ru"
        tm = mapping_status(self.session.profile.get("time_mapping"))
        mat = self.session.active_mat.name if self.session.active_mat else "—"
        cache = "—"
        if self.session.frame_store:
            st = self.session.frame_store.status()
            cache = "ready" if st.valid else (st.reason or "missing")
        warn = tm.warning_ru if ru else tm.warning_en
        if hasattr(self, "viewer_summary"):
            self.viewer_summary.setTitle(
                "Сводка просмотра (проект / файл / профиль / оси / время / кэш)"
                if ru
                else "Viewer summary (project / file / profile / axes / time / cache)"
            )
        lines = [
            f"{self.t('common.project')}: {self.session.project.name if self.session.project else '—'}",
            f"{self.t('common.mat')}: {mat}",
            f"{self.t('common.variable')}: {self.session.profile.get('amplitude_variable_name')}",
            f"{self.t('common.profile')}: {self.session.profile_id} [{self.session.profile.get('profile_verification_status')}]",
            f"{self.t('common.cache')}: {cache}",
            f"{self.t('common.frequency_axis')}: {self.session.profile.get('frequency_variable_name') or self.t('common.profile').lower()}",
            f"{self.t('common.range_axis')}: {self.session.profile.get('range_axis_label_ru') if ru else self.session.profile.get('range_axis_label_en')}",
            f"{self.t('common.time_mapping')}: {tm.status}",
            warn,
        ]
        text = "\n".join(line for line in lines if line)
        self.viewer_meta.setText(text)
        self.viewer_meta.setToolTip(text)
        if hasattr(self, "time_edit"):
            self.time_edit.setEnabled(bool(self._viewer_ready and tm.available))
        if hasattr(self, "viewer_open_btn"):
            self.viewer_open_btn.setVisible(not self.session.has_real_import())

    def _set_viewer_status(self, kind: str, detail: str = "") -> None:
        if not hasattr(self, "viewer_status"):
            return
        ru = self.i18n.language == "ru"
        n = int(self._viewer_n_frames or 0)
        cur = int(self.session.current_frame or 1)
        if kind == "not_loaded":
            text = "Данные не загружены" if ru else "Data not loaded"
        elif kind == "cache_building":
            text = "Создание кэша…" if ru else "Cache building…"
        elif kind == "ready":
            text = (f"Готово: кадр {cur} из {n}" if ru else f"Ready: frame {cur} of {n}")
        elif kind == "render_error":
            detail_txt = detail or ""
            if "missing_variable" in detail_txt:
                detail_txt, _tech = format_missing_variable_user_message(detail_txt, self.i18n.language)
            text = ("Ошибка отрисовки" if ru else "Render error") + (f": {detail_txt}" if detail_txt else "")
        else:
            text = kind
        self.viewer_status.setText(text)

    def _set_viewer_controls_enabled(self, enabled: bool) -> None:
        for w in (
            getattr(self, "frame_spin", None),
            getattr(self, "frame_slider", None),
            getattr(self, "btn_first", None),
            getattr(self, "btn_prev", None),
            getattr(self, "btn_next", None),
            getattr(self, "btn_last", None),
            getattr(self, "btn_back", None),
            getattr(self, "btn_fwd", None),
            getattr(self, "btn_play", None),
            getattr(self, "btn_pause", None),
            getattr(self, "btn_contact", None),
            getattr(self, "btn_save_img", None),
            getattr(self, "jump_combo", None),
            getattr(self, "speed_combo", None),
            getattr(self, "loop_chk", None),
        ):
            if w is not None:
                w.setEnabled(enabled)
        tm_ok = mapping_status(self.session.profile.get("time_mapping")).available
        if hasattr(self, "time_edit"):
            self.time_edit.setEnabled(bool(enabled and tm_ok))
        # Cache button stays available whenever a MAT is imported.
        if hasattr(self, "btn_cache"):
            self.btn_cache.setEnabled(bool(self.session.has_real_import()))

    def _sync_viewer_range_controls(self, n_frames: int, frame_id: int) -> None:
        n = max(1, int(n_frames))
        frame_id = max(1, min(int(frame_id), n))
        self._viewer_n_frames = n
        blockers = [
            QSignalBlocker(self.frame_spin),
            QSignalBlocker(self.frame_slider),
        ]
        self.frame_spin.setRange(1, n)
        self.frame_slider.setRange(1, n)
        self.frame_spin.setValue(frame_id)
        self.frame_slider.setValue(frame_id)
        del blockers
        if mapping_status(self.session.profile.get("time_mapping")).available:
            with QSignalBlocker(self.time_edit):
                self.time_edit.setText(format_hhmm(frame_to_minute(frame_id)))

    def _activate_viewer_if_ready(self, *, render: bool = True) -> bool:
        if not self.session.has_real_import():
            self._viewer_ready = False
            self._set_viewer_controls_enabled(False)
            self._set_viewer_status("not_loaded")
            return False
        try:
            store = self.session.ensure_store()
            st = store.status()
            if not st.valid:
                self._viewer_ready = False
                self._set_viewer_controls_enabled(False)
                if self.settings.get("performance", "automatic_cache_creation", True):
                    self._build_cache_async()
                else:
                    self._set_viewer_status("not_loaded")
                return False
            n = int(store.n_frames())
            self._viewer_ready = True
            self._set_viewer_controls_enabled(True)
            return self.go_to_frame(self.session.current_frame or 1, render=render)
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("viewer activate failed")
            self._viewer_ready = False
            self._set_viewer_controls_enabled(False)
            self._set_viewer_status("render_error", detail=str(exc))
            return False

    def go_to_frame(self, frame_id: int, *, render: bool = True) -> bool:
        """Single validated navigation path for slider/spin/buttons/time/shortcuts."""
        return self.set_current_frame_from_ui(frame_id, render=render)

    def set_current_frame_from_ui(self, frame_id: int, *, render: bool = True) -> bool:
        if self._viewer_nav_busy:
            return False
        if not self.session.has_real_import():
            self._set_viewer_status("not_loaded")
            return False
        if self._cache_build_running() or not self._viewer_ready:
            # Never start another cache build from slider spam.
            self._set_viewer_status("cache_building" if self._cache_build_running() else "not_loaded")
            return False
        self._viewer_nav_busy = True
        self._syncing_time = True
        try:
            store = self.session.ensure_store()
            st = store.status()
            if not st.valid:
                self._viewer_ready = False
                self._set_viewer_controls_enabled(False)
                self._set_viewer_status("not_loaded")
                return False
            n = int(store.n_frames())
            if n < 1:
                self._set_viewer_status("render_error", detail="n_frames<1")
                return False
            clamped = max(1, min(int(frame_id), n))
            self.session.set_current_frame(clamped, emit=True)
            self._sync_viewer_range_controls(n, clamped)
            self._set_viewer_status("ready")
            self._refresh_viewer_meta()
            self._refresh_source_cards()
            self._update_status_bar()
            if render:
                return self._render_current_frame_safe()
            return True
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("viewer navigation failed frame=%s", frame_id)
            self._set_viewer_status("render_error", detail=str(exc))
            # Visible controlled error — do not abort the process.
            self.viewer_view_label.setText(str(exc))
            return False
        finally:
            self._syncing_time = False
            self._viewer_nav_busy = False

    def _schedule_viewer_render(self) -> None:
        if self._viewer_ready and not self._cache_build_running():
            self._viewer_render_timer.start()

    def _on_frame_spin(self, v: int) -> None:
        if self._syncing_time or self._viewer_nav_busy:
            return
        self.go_to_frame(v, render=True)

    def _on_frame_slider_moved(self, v: int) -> None:
        if self._syncing_time or self._viewer_nav_busy:
            return
        if not self._viewer_ready:
            return
        # Lightweight index sync while dragging; defer heavy render.
        self.go_to_frame(v, render=False)
        self._schedule_viewer_render()

    def _on_frame_slider_released(self) -> None:
        if self._syncing_time or self._viewer_nav_busy:
            return
        if not self._viewer_ready:
            return
        self.go_to_frame(self.frame_slider.value(), render=True)

    def _on_time_edit(self) -> None:
        if self._syncing_time or self._viewer_nav_busy:
            return
        m = parse_hhmm(self.time_edit.text())
        if m is None:
            return
        self.go_to_frame(minute_to_frame(m), render=True)

    def _format_playback_speed(self, fps: float) -> str:
        for item in ("0.5", "1", "2", "5", "10"):
            if abs(float(item) - fps) < 1e-6:
                return item
        return str(fps)

    def _playback_interval_ms(self) -> int:
        fps = float(self.speed_combo.currentText())
        return int(1000 / max(fps, 0.1))

    def _update_jump_button_labels(self) -> None:
        if not hasattr(self, "btn_back"):
            return
        n = self._jump_minutes()
        for btn, key in (
            (self.btn_back, "viewer.jump_back"),
            (self.btn_fwd, "viewer.jump_forward"),
        ):
            text = self.t(key).replace("N", str(n))
            btn.setText(text)
            btn.setToolTip(text)

    def _on_jump_interval_changed(self, text: str) -> None:
        try:
            minutes = int(text)
        except ValueError:
            return
        self.settings.set("viewer", "navigation_jump_minutes", minutes)
        self.settings.save()
        self._update_jump_button_labels()

    def _on_playback_speed_changed(self, text: str) -> None:
        try:
            fps = float(text)
        except ValueError:
            return
        self.settings.set("viewer", "playback_speed", fps)
        self.settings.save()
        if self._play_timer.isActive():
            self._play_timer.start(self._playback_interval_ms())

    def _jump_minutes(self) -> int:
        return int(self.jump_combo.currentText())

    def _jump_back(self) -> None:
        self.go_to_frame(self.session.current_frame - self._jump_minutes(), render=True)

    def _jump_fwd(self) -> None:
        self.go_to_frame(self.session.current_frame + self._jump_minutes(), render=True)

    def _play(self) -> None:
        if not self._viewer_ready:
            return
        self._play_timer.start(self._playback_interval_ms())

    def _pause_play(self) -> None:
        self._play_timer.stop()

    def _toggle_play(self) -> None:
        if self._play_timer.isActive():
            self._pause_play()
        else:
            self._play()

    def _playback_tick(self) -> None:
        if not self._viewer_ready:
            self._pause_play()
            return
        nxt = self.session.current_frame + 1
        max_f = self._viewer_n_frames or self.frame_spin.maximum()
        if nxt > max_f:
            if self.loop_chk.isChecked():
                nxt = 1
            else:
                self._pause_play()
                return
        self.go_to_frame(nxt, render=True)

    def _goto_dialog(self) -> None:
        text, ok = QInputDialog.getText(self, "Go to", "Frame or HH:MM")
        if not ok:
            return
        if ":" in text:
            m = parse_hhmm(text)
            if m is not None:
                self.go_to_frame(minute_to_frame(m), render=True)
        else:
            try:
                self.go_to_frame(int(text), render=True)
            except ValueError:
                pass

    def _goto_frame(self, frame_id: int) -> None:
        """Compatibility wrapper — all callers use the validated navigation path."""
        self.go_to_frame(frame_id, render=True)

    def _render_current_frame_safe(self) -> bool:
        try:
            self._render_current_frame()
            self._set_viewer_status("ready")
            return True
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("viewer render failed frame=%s", self.session.current_frame)
            self._set_viewer_status("render_error", detail=str(exc))
            self.viewer_view_label.setText(str(exc))
            return False

    def _render_current_frame(self) -> None:
        if not self.session.has_real_import() or not self._viewer_ready:
            raise RuntimeError("viewer_not_ready")
        store = self.session.ensure_store()
        if not store.status().valid:
            raise RuntimeError("cache_not_ready")
        frame = store.get_frame(self.session.current_frame, prefetch=True)
        original = np.array(frame, copy=True)
        mode = self.view_mode.currentText()
        preview = self.preview_mode.currentText()
        display = frame
        label = self.t("viewer.raw")
        if mode != "raw":
            seg = segment_frame(frame)
            label = self.t("viewer.derived")
            if mode == "trace":
                display = seg.trace_mask.astype(float)
            elif mode == "interference":
                display = seg.interference_mask.astype(float)
            elif mode == "components":
                display = seg.component_map.astype(float)
            else:
                display = np.asarray(frame) * seg.trace_mask
        if preview == "fast" or (preview == "auto" and mode == "raw"):
            display = display[::2, ::2]
            label = f"{label} | {self.t('viewer.fast_preview')}"
        if not np.array_equal(frame, original):
            _LOG.error("viewer: raw frame mutated during render; restoring integrity flag")
            raise RuntimeError("raw_frame_mutated_during_render")
        prof = load_profile(app_root() / "config/instrument_profiles" / f"{self.session.profile_id}.yaml")
        if display.shape != frame.shape:
            freq = list(range(display.shape[1]))
            rng = list(range(display.shape[0]))
        else:
            freq = frequency_axis_from_profile(prof)
            rng = range_axis_from_profile(prof)
            # Clamp axes length to frame shape to avoid renderer mismatches.
            if len(freq) != display.shape[1]:
                freq = list(range(display.shape[1]))
            if len(rng) != display.shape[0]:
                rng = list(range(display.shape[0]))
        out = ensure_dir(app_root() / "workspaces" / "_viewer") / "current.png"
        spec = RenderSpec(
            view_kind="raw" if mode == "raw" else "derived_diagnostic",
            scaling_method="none" if mode == "raw" else "percentile_display",
            profile_source=self.session.profile_id,
            range_label_en=self.session.profile.get("range_axis_label_en", "Nominal virtual height"),
            warnings=[
                "nominal virtual-height axis",
                "not true physical height",
                "archive time interpretation may be provisional",
            ],
        )
        title = f"f{self.session.current_frame:04d}"
        if mapping_status(self.session.profile.get("time_mapping")).available:
            title += f" ≈ {format_hhmm(frame_to_minute(self.session.current_frame))} (provisional)"
        render_raw_ionogram(display, freq, rng, out, spec=spec, title=title)
        self.viewer_view_label.setText(label)
        pix = QPixmap(str(out))
        sz = self.viewer_image.size()
        if sz.width() < 2 or sz.height() < 2:
            self.viewer_image.setPixmap(pix)
        else:
            self.viewer_image.setPixmap(
                pix.scaled(
                    sz,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def _save_current_image(self) -> None:
        src = app_root() / "workspaces" / "_viewer" / "current.png"
        if not src.exists():
            return
        path, _ = QFileDialog.getSaveFileName(self, "PNG", "ionogram.png", "PNG (*.png)")
        if path:
            Path(path).write_bytes(src.read_bytes())

    def _make_contact_sheet(self) -> None:
        if not self.session.has_real_import():
            return
        sel = select_contact_sequence(
            self.session.current_frame,
            5,
            5,
            int(self.settings.get("viewer", "contact_interval_minutes", 10)),
            n_frames=self.session.ensure_store().n_frames(),
        )
        msg = sel.explanation_ru if self.i18n.language == "ru" else sel.explanation_en
        if QMessageBox.question(self, "IML", msg) != QMessageBox.StandardButton.Yes:
            return
        store = self.session.ensure_store()
        frames = [store.get_frame(i) for i in sel.frame_ids]
        prof = load_profile(app_root() / "config/instrument_profiles" / f"{self.session.profile_id}.yaml")
        out = ensure_dir(app_root() / "workspaces" / "_viewer") / "contact.png"
        render_contact_sheet(
            frames,
            frequency_axis_from_profile(prof),
            range_axis_from_profile(prof),
            out,
            labels=[f"f{i:04d}" for i in sel.frame_ids],
            rows=5,
            cols=5,
        )
        self.viewer_image.setPixmap(QPixmap(str(out)).scaledToWidth(900))

    def _synth_demo(self) -> None:
        frame = generate_synthetic_case("horizontally_diffuse")
        out = ensure_dir(app_root() / "workspaces" / "_viewer") / "synth.png"
        render_raw_ionogram(
            frame,
            list(np.linspace(1.5, 9.081, 400)),
            [i * 2.5 for i in range(256)],
            out,
            spec=RenderSpec(view_kind="raw"),
            title="SYNTHETIC teaching demo — not scientific validation",
        )
        self.synth_image.setPixmap(QPixmap(str(out)).scaledToWidth(800))

    def _current_selection(self):
        n = 1440
        if self.session.frame_store and self.session.frame_store.status().valid:
            n = self.session.frame_store.n_frames()
        mode = self.batch_mode.currentData()
        if mode in ("current_frame", "selected"):
            frame = self.session.current_frame if mode == "current_frame" else self.b_start.value()
            return select_single(frame, n)
        if mode == "frame_range":
            return select_frame_range(self.b_start.value(), self.b_end.value(), self.b_step.value(), n)
        if mode == "time_range":
            return select_time_range(self.b_t0.text(), self.b_t1.text(), self.b_step.value(), n)
        if mode in ("every_n", "entire_file"):
            return select_full_day(int(self.b_day_interval.currentText()) if mode == "every_n" else 1, n)
        if mode == "full_day":
            return select_full_day(int(self.b_day_interval.currentText()), n)
        if mode == "custom_list":
            return select_custom_list([x.strip() for x in self.b_custom.text().replace(";", ",").split(",")], n)
        return select_contact_sequence(self.b_start.value(), 5, 5, self.b_step.value(), n)

    def _refresh_batch_preview(self) -> None:
        # Signals can fire while the batch page is still constructing widgets.
        required = (
            "btn_batch_start",
            "batch_preview",
            "batch_form_rows",
            "op_checks",
            "batch_preset",
        )
        if any(not hasattr(self, name) for name in required):
            return
        try:
            sel = self._current_selection()
            est = estimate_resources(sel)
            expl = sel.explanation_ru if self.i18n.language == "ru" else sel.explanation_en
            mode = self.batch_mode.currentData()
            visible = {
                "current_frame": {"start"},
                "selected": {"start", "custom"},
                "frame_range": {"start", "end", "step"},
                "time_range": {"t0", "t1", "step"},
                "every_n": {"day_interval"},
                "entire_file": set(),
                "custom_list": {"custom"},
            }.get(mode, set())
            for key, (label, field) in self.batch_form_rows.items():
                label.setVisible(key in visible)
                field.setVisible(key in visible)
            from ionogram_morphology_lab.ui.active_source_authority import (
                active_source_label,
                authoritative_active_source,
                batch_mats_from_active,
            )

            auth = authoritative_active_source(self.session)
            mats, batch_err = batch_mats_from_active(self.session)
            self.btn_batch_start.setEnabled(
                bool(sel.frame_ids)
                and self.session.project is not None
                and bool(mats)
                and not batch_err
            )
            project = getattr(self.session.project, "name", "—") if self.session.project else "—"
            profile = self.session.profile_id or "—"
            stages = ", ".join(c.text() for c in self.op_checks.values() if c.isChecked()) or "—"
            ru = self.i18n.language == "ru"
            lang = "ru" if ru else "en"
            mat_line = active_source_label(auth, lang)
            if auth.is_active and auth.short_sha:
                mat_line += f" | SHA {auth.short_sha}"
            self.batch_preview.setPlainText(
                f"{expl}\n\n"
                f"{self.t('batch.confirm_title')}\n"
                f"{self.t('batch.summary_project')}: {project}\n"
                f"{self.t('batch.summary_mat')}: {mat_line}\n"
                f"{self.t('batch.summary_profile')}: {profile}\n"
                f"{self.t('batch.expected')}: {est['expected_frames']}\n"
                f"{self.t('batch.summary_frames_time')}: "
                f"{sel.frame_ids[0] if sel.frame_ids else '—'}…{sel.frame_ids[-1] if sel.frame_ids else '—'}\n"
                f"{self.t('batch.summary_stages')}: {stages}\n"
                f"{self.t('batch.summary_preset')}: {self.batch_preset.currentText()}\n"
                f"{self.t('batch.summary_output')}: {getattr(self.session.project, 'root', '—')}\n"
                f"{self.t('batch.summary_memory')} ~ {est['estimated_memory_mb']} MB\n"
                f"{self.t('batch.summary_cache')} ~ {est['estimated_cache_mb']} MB\n"
                f"{self.t('batch.summary_render')} ~ {est['estimated_render_seconds']} s | "
                f"{self.t('batch.summary_analysis')} ~ {est['estimated_analysis_seconds']} s\n"
                f"{self.t('batch.summary_frame_interval')}: {sel.frame_interval} | "
                f"{self.t('batch.summary_time_interval')}: {sel.time_interval_minutes}"
            )
        except Exception as exc:  # noqa: BLE001
            if hasattr(self, "batch_preview"):
                self.batch_preview.setPlainText(str(exc))

    def _viewer_add_current_to_corpus(self) -> None:
        """Viewer: Add current frame to Expert Review Corpus (explicit action)."""
        from ionogram_morphology_lab.morphology_review_corpus.project_items import (
            current_viewer_frame_item,
        )

        try:
            self._ensure_page_materialized("expert")
            page = getattr(self, "_expert_review_corpus_page", None)
            if page is None:
                QMessageBox.warning(self, "IML", self.t("expert_corpus.empty_no_project"))
                return
            item = current_viewer_frame_item(self.session)
            result = page.add_items_to_current_or_new([item])
            QMessageBox.information(
                self,
                "IML",
                f"{self.t('expert_corpus.add_to_corpus')}\n"
                f"cohort={result.get('cohort_id')} added={result.get('added')}",
            )
            self._navigate_key("expert")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "IML", str(exc))

    def _batch_start(self) -> None:
        from ionogram_morphology_lab.ui.active_source_authority import (
            active_source_label,
            authoritative_active_source,
            batch_mats_from_active,
            freeze_batch_source_snapshot,
        )

        if self.session.project is None:
            QMessageBox.warning(self, "IML", self.t("nav.new_project"))
            return
        mats, batch_err = batch_mats_from_active(self.session)
        lang = "ru" if self.i18n.language == "ru" else "en"
        auth = authoritative_active_source(self.session)
        if batch_err or not mats:
            if batch_err == "active_source_unavailable":
                msg = (
                    f"{active_source_label(auth, lang)}\n"
                    + (
                        "Выполнение заблокировано: активный источник недоступен."
                        if lang == "ru"
                        else "Blocked: active source is unavailable."
                    )
                )
            elif batch_err == "active_source_required":
                msg = (
                    "Выберите активный MAT-источник. Пакетный анализ не использует "
                    "первый файл из списка автоматически."
                    if lang == "ru"
                    else "Select an active MAT source. Batch Analysis does not "
                    "silently use the first inventory file."
                )
            else:
                msg = self.t("viewer.no_import")
            QMessageBox.information(self, "IML", msg)
            return
        sel = self._current_selection()
        # This selects the existing analysis profile; it does not alter rule thresholds.
        self.settings.set("analysis", "mode", self.batch_preset.currentData())
        self.settings.save()
        ops = [k for k, c in self.op_checks.items() if c.isChecked()] or ["full_pipeline"]
        expl = sel.explanation_ru if self.i18n.language == "ru" else sel.explanation_en
        frozen = freeze_batch_source_snapshot(self.session)
        self._batch_frozen_source = frozen
        confirm_extra = (
            f"\n\n{active_source_label(auth, lang)}"
            f"\nSHA: {auth.source_sha256 or '—'}"
            f"\nFrames: {sel.frame_ids[0] if sel.frame_ids else '—'}…"
            f"{sel.frame_ids[-1] if sel.frame_ids else '—'}"
        )
        if (
            QMessageBox.question(
                self, "IML", expl + confirm_extra + "\n\n" + self.t("batch.confirm")
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.batch_controller = BatchController()
        self.batch_progress.setValue(0)
        self.batch_status.setText(
            f"{frozen.get('display_name', '')} | rev={frozen.get('activation_revision')}"
        )

        def factory(path, profile):
            return FrameStore(
                path,
                profile,
                cache_root=self.settings.cache_dir(),
                prefetch_radius=int(self.settings.get("viewer", "prefetch_count", 2)),
                lru_capacity=int(self.settings.get("performance", "lru_capacity", 16)),
                source_sha256=frozen.get("source_sha256") or None,
            )

        def progress(info: dict) -> None:
            self.batch_tech.appendPlainText(json.dumps(info, ensure_ascii=False))
            if info.get("event") == "progress":
                self.batch_progress.setValue(int(info.get("percent", 0)))
                self.batch_status.setText(
                    f"[frozen:{frozen.get('display_name')}] "
                    f"{info.get('file')} f{info.get('frame')} | "
                    f"{info.get('completed')}/{info.get('total')} | "
                    f"ETA {info.get('eta_s')}s | op={info.get('operation')} | "
                    f"cache hit/miss {info.get('cache_hits')}/{info.get('cache_misses')}"
                )
            self.session.background_task = info.get("operation", "")
            self._update_status_bar()

        # Frozen mats list — active source only; never full inventory order
        summary = batch_analyze(
            self.session.project,
            mats,
            frame_indices=sel.frame_ids,
            frame_step=sel.frame_interval or DEFAULT_KFU_INTERVAL_MINUTES,
            progress_cb=progress,
            controller=self.batch_controller,
            operations=ops,
            frame_store_factory=factory,
            explanation=expl,
        )
        self.session.last_run_root = Path(summary["run_root"])
        self.session.background_task = ""
        self._load_results_table()
        self.batch_status.setText(
            f"Done: {summary['n_results']} results, {summary['n_errors']} errors. {expl}"
        )
        self._update_status_bar()

    def _results_column_keys(self) -> list[str]:
        mode = "default"
        if hasattr(self, "results_columns"):
            mode = self.results_columns.currentData() or "default"
        if mode == "all":
            return list(RESULTS_DEFAULT_COLUMNS) + list(RESULTS_OPTIONAL_COLUMNS)
        if mode == "extended":
            return list(RESULTS_DEFAULT_COLUMNS) + ["layer", "quality"]
        return list(RESULTS_DEFAULT_COLUMNS)

    def _apply_results_headers(self) -> None:
        if not hasattr(self, "results_table"):
            return
        keys = getattr(self, "_results_active_columns", list(RESULTS_DEFAULT_COLUMNS))
        ru = self.i18n.language == "ru"
        mapping = {
            "time": ("Время", "Time"),
            "morphology": ("Морфология", "Morphology"),
            "interference": ("Помехи", "Interference"),
            "status": ("Статус результата", "Result status"),
            "scientific_status": ("Научный статус", "Scientific status"),
            "frame": ("Кадр", "Frame"),
            "layer": ("Слой", "Layer"),
            "quality": ("Качество", "Quality"),
            "ambiguity": ("Неоднозначность", "Ambiguity"),
            "confidence": ("Уверенность", "Confidence"),
            "ox": ("O/X", "O/X"),
        }
        headers = [mapping.get(k, (k, k))[0 if ru else 1] for k in keys]
        self.results_table.setColumnCount(len(keys))
        self.results_table.setHorizontalHeaderLabels(headers)

    def _result_column_value(self, key: str, rec: dict, identity: dict, lang: str) -> tuple[str, Any]:
        sci = rec.get("scientific_axes") or {}
        morph = sci.get("morphology") or rec.get("morphology") or rec.get("candidate_morphology", "")
        fid = self._result_frame_number(identity, rec) or 0
        review_state = self._review_state_for_record(rec)
        sci_token = scientific_status_token(rec, review_state)
        interference = (
            rec.get("interference_status")
            or sci.get("interference")
            or (rec.get("rule_result") or {}).get("interference_assessment")
            or "none"
        )
        if key == "time":
            raw = identity.get("interpreted_time") or (format_hhmm(frame_to_minute(int(fid))) if fid else "—")
            return str(raw), raw
        if key == "morphology":
            return morphology_label(morph, lang), morph
        if key == "interference":
            return display_status(interference, lang), interference
        if key == "status":
            raw = rec.get("final_auto_status")
            return display_status(raw, lang), raw
        if key == "scientific_status":
            return scientific_status_label(sci_token, lang), sci_token
        if key == "frame":
            raw = identity.get("source_frame_id") or identity.get("frame_id") or "—"
            return str(raw), raw
        if key == "layer":
            raw = sci.get("layer") or rec.get("layer") or "indeterminate"
            return display_status(raw, lang), raw
        if key == "quality":
            raw = sci.get("quality") or rec.get("data_quality_status")
            return display_status(raw, lang), raw
        if key == "ambiguity":
            raw = sci.get("ambiguity") or rec.get("ambiguity") or "no_visible_ambiguity"
            return display_status(raw, lang), raw
        if key == "confidence":
            raw = rec.get("confidence_score")
            if raw is None:
                return display_status("uncalibrated", lang), None
            return str(raw), raw
        if key == "ox":
            raw = bool(rec.get("possible_ox_confusion"))
            return display_status("yes" if raw else "no", lang), raw
        return "—", None

    def _review_state_for_record(self, rec: dict) -> str | None:
        if rec.get("review_state"):
            return str(rec.get("review_state"))
        try:
            store = ReviewDatasetStore()
            sha = str(rec.get("source_mat_sha256") or rec.get("source_file_sha256") or "")
            frame = str(rec.get("source_frame_id") or rec.get("frame_id") or "")
            if not sha or not frame:
                return None
            labels = store.load_by_source(sha, frame)
            if not labels:
                return None
            # Prefer expert-confirmed when present.
            states = {lab.review_state for lab in labels}
            if "expert-confirmed" in states:
                return "expert-confirmed"
            if "owner-reviewed" in states:
                return "owner-reviewed"
            return "unverified"
        except Exception:  # noqa: BLE001
            return None

    def _refresh_review_counts(self) -> None:
        if not hasattr(self, "review_counts_label"):
            return
        ru = self.i18n.language == "ru"
        try:
            store = ReviewDatasetStore()
            labels = store.list_labels()
        except Exception:  # noqa: BLE001
            labels = []
        from collections import Counter

        morph_counts = Counter(lab.morphology for lab in labels)
        state_counts = Counter(lab.review_state for lab in labels)
        needed = ("clean", "frequency_spread", "range_spread", "mixed_spread")
        missing = [m for m in needed if morph_counts.get(m, 0) == 0]
        lines = [
            ("Набор проверки: " if ru else "Review dataset: ")
            + f"unverified={state_counts.get('unverified', 0)}, "
            + f"owner-reviewed={state_counts.get('owner-reviewed', 0)}, "
            + f"expert-confirmed={state_counts.get('expert-confirmed', 0)}",
            ("По классам: " if ru else "By class: ")
            + ", ".join(f"{k}={morph_counts.get(k, 0)}" for k in needed),
        ]
        if missing:
            lines.append(
                ("Недостаточно примеров для: " if ru else "Missing examples for: ")
                + ", ".join(missing)
                + ". "
                + (
                    "Автоматическую эффективность нельзя рассчитать, пока нет нескольких проверенных классов."
                    if ru
                    else "Automatic performance cannot be calculated until multiple reviewed classes exist."
                )
            )
        self.review_counts_label.setText("\n".join(lines))

    def _add_to_review_dataset(self) -> None:
        if not self.session.last_results:
            return
        rows = self.results_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(
                self,
                "IML",
                "Выберите строку результата." if self.i18n.language == "ru" else "Select a result row.",
            )
            return
        rec = self.session.last_results[rows[0].row()]
        from ionogram_morphology_lab.ui.review_dataset_dialog import AddToReviewDatasetDialog

        dlg = AddToReviewDatasetDialog(rec, self.session, self.i18n, self)
        if dlg.exec():
            self._refresh_review_counts()
            self._load_results_table()

    def _load_results_table(self) -> None:
        self.session.last_results = []
        self._results_displayed_identity = None
        self.results_table.setRowCount(0)
        self.res_image.clear()
        if not self.session.last_run_root:
            self.results_empty.setVisible(True)
            self._refresh_review_counts()
            return
        for p in sorted((self.session.last_run_root / "predictions").glob("*.json")):
            rec = json.loads(p.read_text(encoding="utf-8"))
            rec.setdefault("result_id", p.stem)
            self.session.last_results.append(rec)
        filt = self.results_filter.currentText() if hasattr(self, "results_filter") else "All"
        if filt in ("Needs review", "Требуют проверки"):
            self.session.last_results = [r for r in self.session.last_results if r.get("final_auto_status") not in ("accepted", "ok")]
        elif filt in ("Abstained", "Воздержание"):
            self.session.last_results = [r for r in self.session.last_results if "abstain" in str(r.get("final_auto_status", "")) or r.get("candidate_morphology") == "abstain"]
        elif filt in ("Warnings", "Предупреждения"):
            self.session.last_results = [r for r in self.session.last_results if "warning" in str((r.get("scientific_axes") or {}).get("quality", ""))]
        self.results_empty.setVisible(not self.session.last_results)
        self._results_active_columns = self._results_column_keys()
        self._apply_results_headers()
        self.results_table.setRowCount(len(self.session.last_results))
        lang = self.i18n.language
        for r, rec in enumerate(self.session.last_results):
            identity = self._result_identity(rec)
            for c, key in enumerate(self._results_active_columns):
                text, raw_value = self._result_column_value(key, rec, identity, lang)
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, identity)
                item.setToolTip(
                    json.dumps(raw_value, ensure_ascii=False, indent=2)
                    if isinstance(raw_value, (dict, list))
                    else str(raw_value if raw_value is not None else "—")
                )
                self.results_table.setItem(r, c, item)
        self._refresh_review_counts()

    def _result_identity(self, rec: dict) -> dict:
        run_id = rec.get("analysis_run_id") or rec.get("run_id")
        source_frame_id = rec.get("source_frame_id") or rec.get("frame_id") or rec.get("frame_index")
        frame_id = rec.get("frame_id") or source_frame_id
        sequence_position = rec.get("sequence_position")
        if sequence_position is None:
            sequence_position = rec.get("frame_index")
        frame_number = self._result_frame_number(
            {"source_frame_id": source_frame_id, "frame_id": frame_id, "sequence_position": sequence_position},
            rec,
        )
        interpreted_time = rec.get("interpreted_time")
        if not interpreted_time and frame_number:
            interpreted_time = format_hhmm(frame_to_minute(frame_number))
        return {
            "project_id": rec.get("project_id"),
            "analysis_run_id": run_id,
            "run_id": rec.get("run_id") or run_id,
            "source_mat_sha256": (
                rec.get("source_mat_sha256")
                or rec.get("source_file_sha256")
                or rec.get("source_path_hash")
            ),
            "source_file": rec.get("source_file") or rec.get("source_path"),
            "source_variable": rec.get("source_variable"),
            "source_frame_id": source_frame_id,
            "frame_id": frame_id,
            "sequence_position": sequence_position,
            "interpreted_time": interpreted_time,
            "profile_version": rec.get("profile_version") or rec.get("profile_verification_status"),
            "feature_vector_version": rec.get("feature_vector_version") or rec.get("processing_version"),
            "rule_pack_version": rec.get("rule_pack_version"),
            "result_id": rec.get("result_id"),
        }

    @staticmethod
    def _result_frame_number(identity: dict, rec: dict) -> int | None:
        for value in (
            identity.get("sequence_position"),
            rec.get("frame_index"),
            identity.get("source_frame_id"),
            identity.get("frame_id"),
        ):
            if isinstance(value, int) and value > 0:
                return value
            text = str(value or "")
            if text.isdigit() and int(text) > 0:
                return int(text)
            match = re.search(r"(?:^|_)f(\d+)$", text, re.IGNORECASE)
            if match and int(match.group(1)) > 0:
                return int(match.group(1))
        return None

    @staticmethod
    def _raw_path_matches_identity(path: Path, identity: dict, frame_number: int) -> bool:
        stem = path.stem
        named_ids = {
            str(value) for value in (identity.get("source_frame_id"), identity.get("frame_id"))
            if value not in (None, "")
        }
        if stem in named_ids:
            return True
        match = re.search(r"(?:^|_)f(\d+)$", stem, re.IGNORECASE)
        return bool(match and int(match.group(1)) == frame_number and all(v.isdigit() for v in named_ids))

    def _render_selected_result_frame(self, rec: dict, identity: dict) -> tuple[Path | None, dict | None]:
        frame_number = self._result_frame_number(identity, rec)
        if not frame_number:
            return None, None
        try:
            store = self.session.ensure_store() if self.session.has_real_import() else None
            if store is not None and store.status().valid:
                expected_hash = str(identity.get("source_mat_sha256") or "")
                hash_matches = not expected_hash or store.source_sha256.startswith(expected_hash) or expected_hash.startswith(store.source_sha256)
                expected_file = str(identity.get("source_file") or "")
                file_matches = not expected_file or Path(expected_file).name == store.source_path.name
                expected_variable = str(identity.get("source_variable") or "")
                variable_matches = not expected_variable or expected_variable == store.variable_name
                if hash_matches and file_matches and variable_matches:
                    frame = store.get_frame(frame_number, prefetch=False)
                    profile = load_profile(app_root() / "config/instrument_profiles" / f"{self.session.profile_id}.yaml")
                    freq = frequency_axis_from_profile(profile)
                    rng = range_axis_from_profile(profile)
                    if len(freq) != frame.shape[1]:
                        freq = list(range(frame.shape[1]))
                    if len(rng) != frame.shape[0]:
                        rng = list(range(frame.shape[0]))
                    safe_result_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(identity.get("result_id") or "result"))
                    out = ensure_dir(app_root() / "workspaces" / "_results_preview") / f"{safe_result_id}_f{frame_number:04d}.png"
                    render_raw_ionogram(
                        frame,
                        freq,
                        rng,
                        out,
                        spec=RenderSpec(
                            view_kind="raw",
                            scaling_method="none",
                            profile_source=self.session.profile_id,
                            range_label_en=self.session.profile.get("range_axis_label_en", "Nominal virtual height"),
                        ),
                        title=str(identity.get("frame_id") or f"f{frame_number:04d}"),
                    )
                    return out, dict(identity)
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("results: exact FrameStore render failed for %s: %s", identity, exc)
        raw_path = rec.get("raw_render_path")
        if raw_path:
            path = Path(raw_path)
            if path.exists() and self._raw_path_matches_identity(path, identity, frame_number):
                return path, dict(identity)
        return None, None

    def _show_selected_result(self) -> None:
        rows = self.results_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        rec = self.session.last_results[row]
        identity_item = self.results_table.item(row, 0)
        identity = identity_item.data(Qt.ItemDataRole.UserRole) if identity_item else None
        if not isinstance(identity, dict):
            identity = self._result_identity(rec)
        lang = self.i18n.language
        image_path, displayed_identity = self._render_selected_result_frame(rec, identity)
        # When no image can be rendered, still bind panels to the selected row identity.
        # Missing imagery is not an identity mismatch by itself.
        if displayed_identity is None:
            displayed_identity = dict(identity)
            self._results_displayed_identity = displayed_identity
            image_available = False
        else:
            self._results_displayed_identity = displayed_identity
            image_available = image_path is not None
        self.res_image.clear()
        if image_path:
            pixmap = QPixmap(str(image_path))
            target = self.res_image.size()
            if target.width() > 2 and target.height() > 2:
                pixmap = pixmap.scaled(
                    target,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self.res_image.setPixmap(pixmap)
        selected_frame = self._result_frame_number(identity, rec)
        displayed_frame = self._result_frame_number(displayed_identity, rec)
        mismatch = bool(
            image_available
            and selected_frame is not None
            and displayed_frame is not None
            and selected_frame != displayed_frame
        )
        if (
            not mismatch
            and image_available
            and identity.get("result_id")
            and displayed_identity.get("result_id")
        ):
            mismatch = identity["result_id"] != displayed_identity["result_id"]
        total_frames = int(self.session.profile.get("frames_per_file", 0) or 0)
        if self.session.frame_store is not None:
            try:
                total_frames = self.session.frame_store.n_frames()
            except Exception:  # noqa: BLE001
                pass
        time_text = identity.get("interpreted_time") or "—"
        run_text = identity.get("analysis_run_id") or identity.get("run_id") or "—"
        if lang == "ru":
            self.results_identity_line.setText(
                f"Кадр источника: {selected_frame or '—'} из {total_frames or '—'} · "
                f"Время: {time_text} · Запуск анализа: {run_text}"
            )
            mismatch_message = "Несоответствие данных результата. Обновите или повторите анализ."
        else:
            self.results_identity_line.setText(
                f"Source frame: {selected_frame or '—'} of {total_frames or '—'} · "
                f"Time: {time_text} · Analysis run: {run_text}"
            )
            mismatch_message = "Result data mismatch. Refresh or re-run analysis."
        if mismatch:
            _LOG.error(
                "results identity mismatch: selected=%s displayed=%s image=%s",
                identity,
                displayed_identity,
                image_path,
            )
        sci = rec.get("scientific_axes") or {}
        layer = sci.get("layer", rec.get("layer", "indeterminate"))
        morphology = sci.get("morphology", rec.get("candidate_morphology", "indeterminate"))
        ambiguity = sci.get("ambiguity", rec.get("ambiguity", "no_visible_ambiguity"))
        quality = sci.get("quality", rec.get("data_quality_status", ""))
        review_state = self._review_state_for_record(rec)
        sci_token = scientific_status_token(rec, review_state)
        sci_label = scientific_status_label(sci_token, lang)
        axes = (
            f"{'Научный статус' if lang == 'ru' else 'Scientific status'}: {sci_label}\n"
            f"Layer / Слой: {display_status(layer, lang)}\n"
            f"Morphology / Морфология: {morphology_label(morphology, lang)}\n"
            f"Ambiguity / Неоднозначность: {display_status(ambiguity, lang)}\n"
            f"Quality / Качество: {display_status(quality, lang)}\n"
            + (
                "Оси хранятся раздельно — никогда как один перегруженный тип ионограммы.\n\n"
                if lang == "ru"
                else "These axes are stored separately — never as one overloaded ionogram type.\n\n"
            )
        )
        diffuse_why = explain_diffuse_unspecified(rec, lang)
        overview_body = axes + explain_result(rec, lang)
        if diffuse_why:
            overview_body = axes + diffuse_why + "\n\n" + explain_result(rec, lang)
        if sci_token == "automatic-candidate":
            overview_body += "\n\n" + (
                "Автоматический кандидат — не подтверждённая классификация."
                if lang == "ru"
                else "Automatic candidate — not a confirmed classification."
            )
        try:
            store = ReviewDatasetStore()
            morph_key = (
                "diffuse_unspecified"
                if morphology in ("diffuse", "diffuse_unspecified")
                else str(morphology)
            )
            reviewed = [
                lab
                for lab in store.list_labels()
                if lab.morphology == morph_key
                and lab.review_state in ("owner-reviewed", "expert-confirmed")
            ]
            if not reviewed:
                overview_body += "\n\n" + insufficient_examples_message(lang)
        except Exception:  # noqa: BLE001
            pass
        self.res_overview.setPlainText(mismatch_message if mismatch else overview_body)
        evidence = rec.get("rule_result") or rec.get("evidence") or {}
        labels = (
            [
                ("Научный статус", sci_label),
                ("Предлагаемый слой", display_status(layer, "ru")),
                ("Морфология", morphology_label(morphology, "ru")),
                ("Качество", display_status(quality, "ru")),
                ("Неоднозначность", display_status(ambiguity, "ru")),
                ("Помеха", display_status(rec.get("interference_status", evidence.get("interference", "—")), "ru")),
                ("Статус результата", display_status(rec.get("final_auto_status", "—"), "ru")),
                ("Подтверждающие признаки", evidence.get("supporting_features", rec.get("supporting_features", "—"))),
                ("Противоречащие признаки", evidence.get("contradicting_features", rec.get("contradicting_features", "—"))),
                ("Сработавшие правила", rec.get("activated_rules", evidence.get("rules_fired", "—"))),
                ("Правила почти у порога", rec.get("near_threshold_rules", "—")),
                ("Альтернативы", rec.get("alternative_interpretations", "—")),
                ("Причина воздержания", evidence.get("abstention_reason", rec.get("abstention_reason", "—"))),
                ("Ограничения", rec.get("limitations", evidence.get("limitations", "—"))),
            ] if lang == "ru" else [
                ("Scientific status", sci_label),
                ("Proposed layer", display_status(layer, "en")),
                ("Morphology", morphology_label(morphology, "en")),
                ("Quality", display_status(quality, "en")),
                ("Ambiguity", display_status(ambiguity, "en")),
                ("Interference", display_status(rec.get("interference_status", evidence.get("interference", "—")), "en")),
                ("Result status", display_status(rec.get("final_auto_status", "—"), "en")),
                ("Supporting features", evidence.get("supporting_features", rec.get("supporting_features", "—"))),
                ("Contradicting features", evidence.get("contradicting_features", rec.get("contradicting_features", "—"))),
                ("Rules fired", rec.get("activated_rules", evidence.get("rules_fired", "—"))),
                ("Near-threshold rules", rec.get("near_threshold_rules", "—")),
                ("Alternatives", rec.get("alternative_interpretations", "—")),
                ("Abstention reason", evidence.get("abstention_reason", rec.get("abstention_reason", "—"))),
                ("Limitations", rec.get("limitations", evidence.get("limitations", "—"))),
            ]
        )
        if morphology in ("mixed_spread", "mixed"):
            labels.extend(
                [
                    ("Ось частоты / Frequency axis", evidence.get("frequency_evidence", "—")),
                    ("Ось высоты / Range axis", evidence.get("range_evidence", "—")),
                    ("Пороги / Thresholds", evidence.get("thresholds", "—")),
                    ("Исключение помех / Interference exclusion", evidence.get("interference_exclusion", "—")),
                ]
            )
        if diffuse_why:
            labels.insert(
                2,
                ("Почему тип не определён" if lang == "ru" else "Why type is undetermined", diffuse_why),
            )
        self.res_evidence.setPlainText(
            mismatch_message
            if mismatch else
            "\n\n".join(
                f"{label}\n{json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else value}"
                for label, value in labels
            )
        )
        if hasattr(self, "res_details"):
            self.res_details.setPlainText(
                mismatch_message
                if mismatch
                else json.dumps(
                    {
                        "layer": layer,
                        "quality": quality,
                        "ambiguity": ambiguity,
                        "confidence": rec.get("confidence_score"),
                        "possible_ox_confusion": rec.get("possible_ox_confusion"),
                        "scientific_status": sci_token,
                        "evidence": evidence,
                        "measured_features": rec.get("measured_features"),
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        # Overlay legend (color + linestyle + pattern)
        from ionogram_morphology_lab.rendering.overlays import overlay_legend

        self.res_alts.setPlainText(
            "Overlays / Оверлеи:\n"
            + json.dumps(overlay_legend(lang), indent=2, ensure_ascii=False)
            + "\n\nAlternatives:\n"
            + json.dumps(rec.get("alternative_interpretations"), indent=2, ensure_ascii=False)
        )
        self.res_features.setPlainText(json.dumps(rec.get("measured_features"), indent=2, ensure_ascii=False))
        self.res_rules.setPlainText(
            f"Activated: {rec.get('activated_rules')}\nContradicted: {rec.get('contradicted_rules')}\n"
            f"Sources: {list(zip(rec.get('source_ids') or [], rec.get('source_pages') or []))}"
        )
        refs = rec.get("nearest_references") or []
        self.res_refs.setPlainText(
            "\n\n".join(
                f"{r.get('wording_ru' if lang=='ru' else 'wording_en')} {r.get('citation')}\n{r.get('limitations')}"
                for r in refs
            )
            or "—"
        )
        self.res_expert.setPlainText(self.t("results.human") + "\n(pending)")
        self.res_tech.setPlainText(json.dumps(rec, indent=2, ensure_ascii=False))

    def _human_decision(self, kind: str) -> None:
        if not self.session.project or not self.session.last_results:
            return
        rows = self.results_table.selectionModel().selectedRows()
        if not rows:
            return
        rec = self.session.last_results[rows[0].row()]
        from ionogram_morphology_lab.ui.expert_decision_dialog import ExpertDecisionDialog

        # Structured editor for change / save; accept/uncertain/na prefill rationale.
        dlg = ExpertDecisionDialog(rec, self.i18n, self)
        if kind == "accept":
            dlg.rationale.setPlainText("accepted proposed category")
        elif kind in ("uncertain", "not_assessable"):
            # Taxonomy code for the morphology combo (not an API credential).
            morph_code = "indeterminate" if kind == "uncertain" else "not_assessable"
            idx = dlg.morph.findData(morph_code)
            if idx >= 0:
                dlg.morph.setCurrentIndex(idx)
            dlg.rationale.setPlainText(kind)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        decision = dlg.decision()
        human = {
            "decision": kind,
            "category": decision["morphology"],
            "morphology": decision["morphology"],
            "interference": decision["interference"],
            "layer": decision["layer"],
            "ambiguity": decision["ambiguity"],
            "quality": decision["quality"],
            "review_state": decision["review_state"],
            "reason": decision["rationale"],
            "uncertainty": decision["uncertainty"],
            "alternatives": decision["alternatives"],
            "ts": datetime.now(timezone.utc).isoformat(),
            "reviewer": "local_user",
        }
        db = ProjectDatabase(Path(self.session.project.root) / "project.sqlite")
        db.update_human_decision(rec["frame_id"], human)
        db.append_audit(human["ts"], "human_decision", {"frame_id": rec["frame_id"], **human})
        self.res_expert.setPlainText(json.dumps(human, indent=2, ensure_ascii=False))
        self.res_overview.setPlainText(
            explain_result(rec, self.i18n.language)
            + "\n\n"
            + self.t("results.auto")
            + f": {rec.get('candidate_morphology')}\n"
            + self.t("results.human")
            + f": {decision['morphology']} ({decision['review_state']})"
        )

    def _load_atlas(self) -> None:
        cases = load_atlas()
        filt = self.atlas_filter.currentText()
        if filt != "all":
            cases = [c for c in cases if c.canonical_terminology == filt]
        lang = self.i18n.language
        blocks = []
        for c in cases:
            img_note = (
                self.t("atlas.image_unavailable")
                if c.internal_image_availability != "available"
                else "Image available in optional local pack"
            )
            blocks.append(
                f"{c.reference_case_id}\n"
                f"{c.authors} ({c.year})\n{c.title}\n"
                f"Page: {c.exact_page} | Figure: {c.figure}\n"
                f"Source term: {c.original_terminology}\n"
                f"Canonical: {c.canonical_terminology}\n"
                f"Regime: {c.station_regime}\n"
                f"Rights: {c.rights_status}\n"
                f"{img_note}\n"
                f"Limitations: {c.limitations}\n"
                f"{self.t('science.wording_similar')}"
            )
        self.atlas_view.setPlainText("\n\n———\n\n".join(blocks))

    def _load_science(self) -> None:
        kb = app_root() / "knowledge_base"
        lang = self.i18n.language
        cards = []
        with open(kb / "VERIFIED_FORMULA_REGISTRY.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("iml_status") == "disabled" or row.get("verification_status") == "candidate_not_ready":
                    status = self.t("science.disabled_formula")
                else:
                    status = row.get("verification_status")
                cards.append(
                    f"{row.get('formula_id')}: {row.get('formula_name_en')}\n"
                    f"{row.get('equation_latex')}\n"
                    f"Source {row.get('source_id')} p.{row.get('printed_page')} (PDF {row.get('pdf_page')})\n"
                    f"Status: {status}\nDomain: {row.get('validity_domain')}\n"
                    f"Notes: {row.get('notes')}"
                )
        with open(kb / "SCIENTIFIC_CLAIM_REGISTRY.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                claim = row.get("claim_ru") if lang == "ru" else row.get("claim_en")
                cards.append(
                    f"{row.get('claim_id')}: {claim}\n"
                    f"Allowed: {row.get('allowed_wording_en')}\n"
                    f"Prohibited: {row.get('prohibited_wording_en')}"
                )
        self.science_view.setPlainText("\n\n———\n\n".join(cards))
        self.science_tech.setPlainText((kb / "VERIFIED_FORMULA_REGISTRY.csv").read_text(encoding="utf-8")[:8000])

    def _show_analysis_methods(self) -> None:
        """Readable Analysis Methods page — not a compiled black box."""
        root = app_root() / "src" / "ionogram_morphology_lab"
        lang = self.i18n.language
        modules = [
            ("features", root / "features"),
            ("rules", root / "rules"),
            ("similarity", root / "similarity"),
            ("segmentation", root / "segmentation"),
            ("rendering", root / "rendering"),
            ("classifiers", root / "classifiers"),
            ("projects/pipeline", root / "projects" / "pipeline.py"),
        ]
        lines = [
            "Analysis Methods / Методы анализа" if lang == "en" else "Методы анализа / Analysis Methods",
            "",
            "Inspect definitions, parameters, and source locations. "
            "Create a MATLAB equivalent template from MATLAB Studio when needed.",
            "Results remain candidate morphology unless externally validated.",
            "",
        ]
        for name, path in modules:
            exists = Path(path).exists()
            lines.append(f"• {name}")
            lines.append(f"  source: {path}")
            lines.append(f"  present: {exists}")
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                doc = ""
                if '"""' in text:
                    doc = text.split('"""', 2)[1].strip().splitlines()[0] if text.count('"""') >= 2 else ""
                if doc:
                    lines.append(f"  summary: {doc}")
            lines.append("")
        feat_reg = app_root() / "docs" / "IML1_FEATURE_REGISTRY_EN.md"
        if feat_reg.exists():
            lines.append("Feature registry documentation:")
            lines.append(str(feat_reg))
        self.science_view.setPlainText("\n".join(lines))

    def _export_reports(self) -> None:
        if not self.session.last_run_root:
            self.report_log.setPlainText("No run yet")
            return
        paths = export_run_reports(self.session.last_run_root, language=self.i18n.language)
        paths2 = export_run_reports(
            self.session.last_run_root, language="ru" if self.i18n.language == "en" else "en"
        )
        self.report_log.setPlainText(
            "Reports exported.\n" + "\n".join(f"{k}: {v}" for k, v in {**paths, **paths2}.items())
        )

    def _save_settings(self) -> None:
        for key, edit in getattr(self, "storage_paths", {}).items():
            section = "performance" if key == "cache_location" else ("general" if key == "workspace_dir" else "storage")
            self.settings.set(section, key, edit.text().strip())
        for section, key, kind, wid in self._settings_widgets.values():
            if kind == "bool":
                val = wid.isChecked()
            elif kind == "int":
                val = wid.value()
            elif kind == "float":
                val = wid.value()
            elif kind == "lang":
                val = wid.currentData() or wid.currentText()
                val = "ru" if val == "ru" else "en"
            elif kind == "scale":
                val = str(wid.currentData() or "auto")
            else:
                val = wid.text()
            self.settings.set(section, key, val)
        # Apply optional protected study mode from privacy flag
        from ionogram_morphology_lab.security import ProtectedStudyConfig, set_active_protection

        enabled = bool(self.settings.get("privacy", "protected_study_enabled", False))
        set_active_protection(ProtectedStudyConfig(enabled=enabled))
        self.settings.save()
        self._apply_interface_scale()
        self._apply_theme()
        self.set_language(self.settings.get("general", "language", "en"))
        self._refresh_storage_info()
        QMessageBox.information(self, "IML", self.t("settings.save"))

    def _apply_interface_scale(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        base_size = getattr(app, "_iml_base_font_point_size", None)
        if not base_size:
            base_size = app.font().pointSizeF()
            if base_size <= 0:
                base_size = 9.0
            app._iml_base_font_point_size = base_size
        value = str(self.settings.get("general", "interface_scale", "auto"))
        factor = 1.0 if value == "auto" else int(value) / 100.0
        font = app.font()
        font.setPointSizeF(float(base_size) * factor)
        app.setFont(font)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._apply_interface_scale()
        super().showEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Never destroy active MATLAB/cache workers while still running."""
        import os

        from PySide6.QtWidgets import QMessageBox

        active_matlab = self.matlab_jobs.has_active_jobs()
        cache_running = bool(self._cache_worker is not None and self._cache_worker.isRunning())
        headless = (
            os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen"
            or os.environ.get("IML_HEADLESS", "") == "1"
        )

        def _stop_workers(wait_ms: int) -> None:
            self.matlab_jobs.shutdown_all(wait_ms=wait_ms)
            if self._cache_worker is not None and self._cache_worker.isRunning():
                # Best-effort; never block forever on a stuck/fake worker.
                self._cache_worker.wait(min(wait_ms, 5000))

        if active_matlab or cache_running:
            if headless:
                _stop_workers(2000)
            else:
                ru = self.i18n.language == "ru"
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Icon.Warning)
                box.setWindowTitle("Ionogram Morphology Lab")
                box.setText(
                    "Выполняется задача MATLAB. Остановить её и закрыть приложение?"
                    if ru and active_matlab
                    else (
                        "A MATLAB task is running. Stop it and close the application?"
                        if active_matlab
                        else (
                            "Выполняется фоновая задача. Остановить и закрыть приложение?"
                            if ru
                            else "A background task is running. Stop it and close the application?"
                        )
                    )
                )
                cancel_btn = box.addButton(
                    "Отмена" if ru else "Cancel close", QMessageBox.ButtonRole.RejectRole
                )
                box.addButton(
                    "Остановить и закрыть" if ru else "Stop task and close",
                    QMessageBox.ButtonRole.DestructiveRole,
                )
                wait_btn = box.addButton(
                    "Ждать" if ru else "Wait", QMessageBox.ButtonRole.ActionRole
                )
                box.exec()
                clicked = box.clickedButton()
                if clicked is cancel_btn:
                    event.ignore()
                    return
                if clicked is wait_btn:
                    _stop_workers(15000)
                    if self.matlab_jobs.has_active_jobs() or (
                        self._cache_worker is not None and self._cache_worker.isRunning()
                    ):
                        event.ignore()
                        return
                else:
                    _stop_workers(5000)
        else:
            _stop_workers(500)
        # Clear fake/stuck cache worker reference so Qt teardown cannot wait forever.
        if self._cache_worker is not None and self._cache_worker.isRunning():
            self._cache_worker = None
        # Controlled V2 worker shutdown — never used for Cancel or page switch.
        try:
            from ionogram_morphology_lab.ui.v2_process_worker import shared_pool

            shared_pool().shutdown()
        except Exception:  # noqa: BLE001
            pass
        try:
            from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler, stop_profiler

            p = get_profiler()
            if p is not None:
                p.write_summary()
            stop_profiler()
        except Exception:  # noqa: BLE001
            pass
        event.accept()
        super().closeEvent(event)

    def _browse_storage_folder(self, edit: QLineEdit) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose folder", edit.text() or str(app_root()))
        if selected:
            edit.setText(str(Path(selected)))
            self._refresh_storage_info()

    def _open_storage_folder(self, value: str) -> None:
        if value:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(ensure_dir(Path(value)))))

    def _refresh_storage_info(self) -> None:
        entries = []
        for key, edit in getattr(self, "storage_paths", {}).items():
            if not (raw := edit.text().strip()):
                continue
            try:
                path = ensure_dir(Path(raw))
                usage = shutil.disk_usage(path)
                size = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
                writable = "writable" if os.access(path, os.W_OK) else "not writable"
                entries.append(f"{key}: {writable}; {size / 1048576:.1f} MB; {usage.free / 1073741824:.1f} GB free")
            except OSError as exc:
                entries.append(f"{key}: unavailable ({exc})")
        if hasattr(self, "storage_info"):
            self.storage_info.setText("\n".join(entries) or self.t("storage.info_empty"))

    def _migrate_cache(self) -> None:
        target_text = self.storage_paths["cache_location"].text().strip()
        if not target_text:
            QMessageBox.information(self, "IML", self.t("storage.migrate_need_target"))
            return
        source, target = self.settings.cache_dir(), Path(target_text)
        if source.resolve() == target.resolve():
            return
        if (
            QMessageBox.question(self, "IML", self.t("storage.migrate_confirm"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        staging = target.with_name(target.name + ".iml-migrating")
        try:
            if staging.exists():
                shutil.rmtree(staging)
            shutil.copytree(source, staging)
            if target.exists():
                rollback = target.with_name(target.name + ".iml-rollback")
                if rollback.exists():
                    shutil.rmtree(rollback)
                target.replace(rollback)
                try:
                    staging.replace(target)
                except Exception:
                    rollback.replace(target)
                    raise
                shutil.rmtree(rollback, ignore_errors=True)
            else:
                staging.replace(target)
            self.settings.set("performance", "cache_location", str(target))
            self.settings.save()
            QMessageBox.information(self, "IML", self.t("storage.migrate_done"))
        except OSError as exc:
            shutil.rmtree(staging, ignore_errors=True)
            QMessageBox.warning(
                self, "IML", self.t("storage.migrate_rollback").format(error=exc)
            )
        self._refresh_storage_info()

    def _clear_cache(self) -> None:
        """Remove derived cache contents only. Never deletes source MAT files."""
        cache = self.settings.cache_dir()
        if not cache.exists():
            QMessageBox.information(self, "IML", self.t("storage.clear_empty"))
            return
        if (
            QMessageBox.question(self, "IML", self.t("storage.clear_confirm"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        removed = 0
        skipped_mat = 0
        try:
            for path in sorted(cache.rglob("*"), reverse=True):
                # Absolute safety: never delete .mat even if placed under cache.
                if path.is_file() and path.suffix.lower() == ".mat":
                    skipped_mat += 1
                    continue
                if path.is_file() or path.is_symlink():
                    path.unlink(missing_ok=True)
                    removed += 1
                elif path.is_dir():
                    try:
                        path.rmdir()
                        removed += 1
                    except OSError:
                        pass
            msg = self.t("storage.clear_done")
            if skipped_mat:
                msg += f"\n(.mat preserved: {skipped_mat})"
            QMessageBox.information(self, "IML", msg)
        except OSError as exc:
            QMessageBox.warning(self, "IML", str(exc))
        self._refresh_storage_info()

    def _restore_storage_defaults(self) -> None:
        from ionogram_morphology_lab.app.settings_store import DEFAULT_SETTINGS

        defaults = DEFAULT_SETTINGS.get("storage", {})
        self.settings.set("storage", "project_dir", defaults.get("project_dir", ""))
        self.settings.set("storage", "reports_dir", defaults.get("reports_dir", ""))
        self.settings.set("storage", "models_dir", defaults.get("models_dir", ""))
        self.settings.set("storage", "matlab_workspace", defaults.get("matlab_workspace", ""))
        self.settings.set("storage", "temp_dir", defaults.get("temp_dir", ""))
        self.settings.set("general", "workspace_dir", DEFAULT_SETTINGS["general"].get("workspace_dir", ""))
        self.settings.set("performance", "cache_location", DEFAULT_SETTINGS["performance"].get("cache_location", ""))
        self.settings.save()
        for key, edit in getattr(self, "storage_paths", {}).items():
            section = (
                "performance"
                if key == "cache_location"
                else ("general" if key == "workspace_dir" else "storage")
            )
            edit.setText(str(self.settings.get(section, key, "")))
        QMessageBox.information(self, "IML", self.t("storage.defaults_done"))
        self._refresh_storage_info()

    def _create_desktop_shortcut(self) -> None:
        if (
            QMessageBox.question(self, "IML", self.t("storage.shortcut_confirm"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(app_root() / "scripts" / "create_desktop_shortcut.ps1"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        QMessageBox.information(
            self,
            "IML",
            result.stdout.strip()
            or (self.t("storage.shortcut_done") if not result.returncode else result.stderr),
        )

    def _reset_settings(self) -> None:
        self.settings.reset()
        QMessageBox.information(self, "IML", self.t("settings.reset"))
        self.set_language(self.settings.get("general", "language", "en"))

    def _export_settings(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Settings", "iml_settings.json", "JSON (*.json)")
        if path:
            self.settings.export_to(path)

    def _import_settings(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "JSON (*.json)")
        if path:
            self.settings.import_from(path)
            self.set_language(self.settings.get("general", "language", "en"))
            self.retranslate()

    def _populate_help(self) -> None:
        self.help_nav.clear()
        lang = self.i18n.language
        for s in HELP_SECTIONS:
            self.help_nav.addItem(s["title_ru"] if lang == "ru" else s["title_en"])
        if self.help_nav.count():
            self.help_nav.setCurrentRow(0)

    def _filter_help(self, text: str) -> None:
        hits = search_help(text, self.i18n.language)
        self.help_nav.clear()
        self._help_hits = hits
        for s in hits:
            self.help_nav.addItem(s["title_ru"] if self.i18n.language == "ru" else s["title_en"])

    def _show_help_section(self, row: int) -> None:
        hits = getattr(self, "_help_hits", HELP_SECTIONS)
        if row < 0 or row >= len(hits):
            return
        s = hits[row]
        body = s["body_ru"] if self.i18n.language == "ru" else s["body_en"]
        title = s["title_ru"] if self.i18n.language == "ru" else s["title_en"]
        self.help_body.setPlainText(f"{title}\n\n{body}")

    def _maybe_onboarding(self) -> None:
        if self.settings.get("general", "show_onboarding", True):
            self._run_onboarding()

    def _run_onboarding(self) -> None:
        steps = [
            ("Language / Язык", "Choose language at first launch or in Settings → General. Settings stay synchronized."),
            ("Project", self.t("nav.new_project")),
            ("Import", self.t("nav.import")),
            ("Audit", self.t("nav.audit")),
            ("Profile", self.t("profile.kfu")),
            ("Cache", self.t("tip.cache")),
            ("Viewer", self.t("nav.viewer")),
            ("Batch", self.t("batch.expected")),
            ("Results", self.t("results.overview")),
            ("Export", self.t("reports.export")),
        ]
        for title, body in steps:
            box = QMessageBox(self)
            box.setWindowTitle(title)
            box.setText(body)
            skip = box.addButton(self.t("onboarding.skip"), QMessageBox.ButtonRole.RejectRole)
            nxt = box.addButton(self.t("onboarding.next"), QMessageBox.ButtonRole.AcceptRole)
            never = box.addButton(self.t("onboarding.dont_show"), QMessageBox.ButtonRole.DestructiveRole)
            box.exec()
            clicked = box.clickedButton()
            if clicked == skip:
                break
            if clicked == never:
                self.settings.set("general", "show_onboarding", False)
                self.settings.save()
                break

    def _error_dialog(self, summary: str, technical: str) -> None:
        ru = self.i18n.language == "ru"
        user = summary
        tech = technical
        if "missing_variable" in (summary + technical):
            user, tech = format_missing_variable_user_message(
                technical or summary, self.i18n.language
            )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(self.t("error.generic"))
        box.setText(user)
        box.setInformativeText(
            "Исходные MAT-файлы не изменялись.\n"
            "Полное сообщение — в «Технические сведения»."
            if ru
            else "Source MAT files were not modified.\n"
            "Use Technical details for the full message."
        )
        box.setDetailedText(tech)
        # Qt's "Show Details…" button label follows the system UI language;
        # keep the technical payload localized separately.
        box.exec()
