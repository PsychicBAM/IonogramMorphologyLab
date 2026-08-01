"""IML-2 bilingual research shell: real viewer, batch UX, help, settings."""

from __future__ import annotations

import csv
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QAction, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
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
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

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
from ionogram_morphology_lab.projects.model import create_project
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
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.utils.paths import app_root, ensure_dir


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
    ("expert", "nav.expert"),
    ("atlas", "nav.atlas"),
    ("science", "nav.science"),
    ("matlab", "nav.matlab"),
    ("rules", "nav.rules"),
    ("rule_test", "nav.rule_test"),
    ("compare", "nav.compare"),
    ("pipeline", "nav.pipeline"),
    ("models", "nav.models"),
    ("reports", "nav.reports"),
    ("settings", "nav.settings"),
    ("help", "nav.help"),
]


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
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._playback_tick)
        self._cache_worker: CacheBuildWorker | None = None
        self._syncing_time = False
        self._build_ui()
        self._bind_shortcuts()
        self.retranslate()
        self._update_status_bar()
        if self.settings.get("general", "show_onboarding", True):
            QTimer.singleShot(300, self._maybe_onboarding)

    def t(self, key: str) -> str:
        return self.i18n.t(key)

    def _build_ui(self) -> None:
        self.setMinimumSize(1200, 780)
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        self.nav = QListWidget()
        self.nav.setFixedWidth(230)
        for key, _ in NAV_KEYS:
            self.nav.addItem(key)
        self.nav.currentRowChanged.connect(self._on_nav)
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
            "expert": self._page_expert,
            "atlas": self._page_atlas,
            "science": self._page_science,
            "matlab": self._page_matlab,
            "rules": self._page_rules,
            "rule_test": self._page_rule_test,
            "compare": self._page_compare,
            "pipeline": self._page_pipeline,
            "models": self._page_models,
            "reports": self._page_reports,
            "settings": self._page_settings,
            "help": self._page_help,
        }
        from ionogram_morphology_lab.ui.page_intros import attach_intro

        self.intro_panels: dict[str, object] = {}
        for key, _ in NAV_KEYS:
            page = QWidget()
            layout = QVBoxLayout(page)
            title = QLabel(key)
            title.setObjectName(f"title_{key}")
            title.setStyleSheet("font-size: 18px; font-weight: 600;")
            layout.addWidget(title)
            layout.addWidget(builders[key](), 1)
            panel = attach_intro(key, layout, self.i18n, self.settings)
            if panel is not None:
                self.intro_panels[key] = panel
            self.pages[key] = page
            self.stack.addWidget(page)

        tb = QToolBar()
        self.addToolBar(tb)
        # Language is controlled only via first-launch dialog and Settings → General.
        self.btn_collapse_nav = QPushButton("☰")
        self.btn_collapse_nav.setFixedWidth(36)
        self.btn_collapse_nav.clicked.connect(self._toggle_nav)
        tb.addWidget(self.btn_collapse_nav)
        self.btn_about = QPushButton()
        self.btn_about.setObjectName("btn_about")
        self.btn_about.clicked.connect(self._show_about)
        tb.addWidget(self.btn_about)
        self.lang_indicator = QLabel()
        tb.addWidget(self.lang_indicator)
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
        self.nav.setCurrentRow(0)
        if self.settings.get("general", "nav_collapsed", False):
            self.nav.setVisible(False)

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

    def _page_expert(self) -> QWidget:
        # Expert review redirects to results expert actions
        w = QWidget()
        lay = QVBoxLayout(w)
        lab = QLabel()
        lab.setObjectName("expert_help")
        lab.setWordWrap(True)
        btn = QPushButton()
        btn.setObjectName("btn_goto_results")
        btn.clicked.connect(lambda: self.nav.setCurrentRow([k for k, _ in NAV_KEYS].index("results")))
        lay.addWidget(lab)
        lay.addWidget(btn)
        lay.addStretch(1)
        return w

    def _page_matlab(self) -> QWidget:
        from ionogram_morphology_lab.ui.matlab_studio_page import MatlabStudioPage

        return MatlabStudioPage(self.session, self.i18n)

    def _page_parameters(self) -> QWidget:
        from ionogram_morphology_lab.ui.parameters_page import ParametersPage

        return ParametersPage(self.session, self.i18n)

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
        # Keep legacy labels for retranslate compatibility (hidden)
        self.home_welcome = QLabel()
        self.home_welcome.hide()
        self.home_disclaimer = QLabel()
        self.home_disclaimer.hide()
        return self.home_dashboard

    def _page_project(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.proj_name = QLineEdit("IML_Project")
        btn = QPushButton()
        btn.setObjectName("btn_create_project")
        btn.clicked.connect(self._create_project)
        self.proj_status = QLabel("")
        lay.addWidget(self._labeled("project.name", self.proj_name))
        lay.addWidget(btn)
        lay.addWidget(self.proj_status)
        lay.addStretch(1)
        return w

    def _page_import(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
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
        self.import_cards = QTextEdit()
        self.import_cards.setReadOnly(True)
        self.import_tech = QPlainTextEdit()
        self.import_tech.setReadOnly(True)
        self.import_tech.setVisible(False)
        tech_btn = QPushButton()
        tech_btn.setObjectName("btn_import_tech")
        tech_btn.clicked.connect(lambda: self.import_tech.setVisible(not self.import_tech.isVisible()))
        lay.addWidget(self.import_cards, 2)
        lay.addWidget(tech_btn)
        lay.addWidget(self.import_tech, 1)
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
        why = QPushButton("Why? provisional profile / nominal height")
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
        lay = QVBoxLayout(w)
        self.viewer_meta = QLabel()
        self.viewer_meta.setWordWrap(True)
        lay.addWidget(self.viewer_meta)

        ctrl = QHBoxLayout()
        self.frame_spin = QSpinBox()
        self.frame_spin.setRange(1, 1440)
        self.frame_spin.valueChanged.connect(self._on_frame_spin)
        self.time_edit = QLineEdit("00:00")
        self.time_edit.editingFinished.connect(self._on_time_edit)
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setRange(1, 1440)
        self.frame_slider.valueChanged.connect(self._on_frame_slider)
        self.jump_combo = QComboBox()
        self.jump_combo.addItems(["1", "5", "10", "15", "30", "60"])
        self.jump_combo.setCurrentText(str(DEFAULT_KFU_INTERVAL_MINUTES))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5", "1", "2", "5", "10"])
        self.speed_combo.setCurrentText("2")
        self.loop_chk = QCheckBox()
        self.view_mode = QComboBox()
        self.view_mode.addItems(["raw", "trace", "interference", "components", "overlay"])
        self.preview_mode = QComboBox()
        self.preview_mode.addItems(["auto", "fast", "full"])
        for name, wdg, tip in [
            ("viewer.open_real", None, None),
        ]:
            pass
        ctrl.addWidget(tip_button("tip.frame_index", self.i18n))
        ctrl.addWidget(self.frame_spin)
        ctrl.addWidget(tip_button("tip.interpreted_time", self.i18n))
        ctrl.addWidget(self.time_edit)
        ctrl.addWidget(self.frame_slider, 1)
        lay.addLayout(ctrl)

        nav = QHBoxLayout()
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
        for b, slot in [
            (self.btn_first, lambda: self._goto_frame(1)),
            (self.btn_prev, lambda: self._goto_frame(self.session.current_frame - 1)),
            (self.btn_next, lambda: self._goto_frame(self.session.current_frame + 1)),
            (self.btn_last, lambda: self._goto_frame(self.frame_spin.maximum())),
            (self.btn_back, self._jump_back),
            (self.btn_fwd, self._jump_fwd),
            (self.btn_play, self._play),
            (self.btn_pause, self._pause_play),
            (self.btn_cache, self._build_cache_async),
            (self.btn_contact, self._make_contact_sheet),
            (self.btn_save_img, self._save_current_image),
        ]:
            b.clicked.connect(slot)
            nav.addWidget(b)
        nav.addWidget(self.loop_chk)
        nav.addWidget(self.jump_combo)
        nav.addWidget(self.speed_combo)
        nav.addWidget(self.view_mode)
        nav.addWidget(self.preview_mode)
        lay.addLayout(nav)

        self.viewer_image = QLabel()
        self.viewer_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer_image.setMinimumHeight(420)
        self.viewer_image.setStyleSheet("background:#111;color:#ddd;")
        self.viewer_view_label = QLabel()
        lay.addWidget(self.viewer_view_label)
        lay.addWidget(self.viewer_image, 1)
        self.cache_progress = QProgressBar()
        self.cache_progress.setVisible(False)
        lay.addWidget(self.cache_progress)
        open_btn = QPushButton()
        open_btn.setObjectName("btn_open_real")
        open_btn.clicked.connect(self._open_real_viewer)
        lay.addWidget(open_btn)
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
        self.batch_mode = QComboBox()
        self.batch_mode.addItems(
            ["single", "frame_range", "time_range", "full_day", "custom_list", "contact_sheet"]
        )
        self.batch_mode.currentTextChanged.connect(self._refresh_batch_preview)
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
        form.addRow("mode", self.batch_mode)
        form.addRow("start", self.b_start)
        form.addRow("end", self.b_end)
        form.addRow("step", self.b_step)
        form.addRow("t0", self.b_t0)
        form.addRow("t1", self.b_t1)
        form.addRow("day_interval", self.b_day_interval)
        form.addRow("custom", self.b_custom)
        lay.addLayout(form)

        ops_box = QGroupBox()
        ops_box.setObjectName("batch_ops_box")
        ops_lay = QHBoxLayout(ops_box)
        self.op_checks: dict[str, QCheckBox] = {}
        for op in [
            "audit",
            "build_cache",
            "render",
            "features",
            "rules",
            "references",
            "export_reports",
            "full_pipeline",
        ]:
            c = QCheckBox(op)
            c.setChecked(op == "full_pipeline")
            self.op_checks[op] = c
            ops_lay.addWidget(c)
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
        split = QSplitter()
        self.results_table = QTableWidget(0, 10)
        self.results_table.setHorizontalHeaderLabels(
            [
                "frame",
                "time",
                "quality",
                "layer",
                "morphology",
                "ambiguity",
                "status",
                "confidence",
                "OX",
                "expert",
            ]
        )
        self.results_table.itemSelectionChanged.connect(self._show_selected_result)
        self.results_tabs = QTabWidget()
        self.res_overview = QTextEdit()
        self.res_overview.setReadOnly(True)
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
        self.res_image = QLabel()
        self.res_image.setMinimumHeight(240)
        self.res_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for name, widget in [
            ("overview", self.res_overview),
            ("raw", self.res_image),
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
                form.addRow(f"{section}.{key}", wid)
            self.settings_tabs.addTab(tab, name_key)

        add_tab(
            "general",
            [
                ("general", "language", "lang"),
                ("general", "theme", "str"),
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
        self.settings_tabs.addTab(adv, "advanced")

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
        lay.addLayout(row)
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
        if hasattr(self, "btn_about"):
            self.btn_about.setText(t("about.title"))
        self.lang_indicator.setText(f"{t('settings.interface_language')}: {self.i18n.language}")
        # Retranslate v1.1 child pages when present
        for key in ("parameters", "rules", "rule_test", "compare", "pipeline", "matlab", "models"):
            page = self.pages.get(key)
            if page is None:
                continue
            # Content is the last layout item (title + optional intro + page body).
            lay = page.layout()
            if lay and lay.count() >= 2:
                w = lay.itemAt(lay.count() - 1).widget()
                if w is not None and hasattr(w, "retranslate"):
                    w.retranslate()
        for panel in getattr(self, "intro_panels", {}).values():
            if hasattr(panel, "retranslate"):
                panel.retranslate()
        for i, (key, nav_key) in enumerate(NAV_KEYS):
            self.nav.item(i).setText(t(nav_key))
            title = self.pages[key].findChild(QLabel, f"title_{key}")
            if title:
                title.setText(t(nav_key))
        if hasattr(self, "home_welcome"):
            self.home_welcome.setText(t("home.welcome"))
        if hasattr(self, "home_disclaimer"):
            self.home_disclaimer.setText(t("home.disclaimer"))
        if hasattr(self, "home_dashboard"):
            self.home_dashboard.retranslate()
            self.home_dashboard.refresh()
        if hasattr(self, "seq_info"):
            self.seq_info.setText(t("sequences.help"))
        expert = self.findChild(QLabel, "expert_help")
        if expert:
            expert.setText(t("expert.help"))
        mapping = {
            "btn_onboarding": "home.start",
            "btn_create_project": "project.create",
            "btn_import_file": "import.select_file",
            "btn_import_folder": "import.select_folder",
            "btn_import_tech": "import.technical",
            "btn_load_kfu": "profile.load_kfu",
            "btn_wizard": "profile.wizard",
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
        # viewer buttons
        self.btn_first.setText(t("viewer.first"))
        self.btn_prev.setText(t("viewer.prev"))
        self.btn_next.setText(t("viewer.next"))
        self.btn_last.setText(t("viewer.last"))
        self.btn_back.setText(t("viewer.jump_back"))
        self.btn_fwd.setText(t("viewer.jump_forward"))
        self.btn_play.setText(t("viewer.play"))
        self.btn_pause.setText(t("viewer.pause"))
        self.btn_cache.setText(t("viewer.build_cache"))
        self.btn_contact.setText(t("viewer.contact"))
        self.btn_save_img.setText(t("viewer.save_image"))
        self.loop_chk.setText(t("viewer.loop"))
        for i, key in enumerate(
            [
                "results.overview",
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
                self.results_tabs.setTabText(i, t(key))
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
                "settings.reference_packs",
                "settings.privacy",
                "settings.advanced",
            ]
        ):
            if i < self.settings_tabs.count():
                self.settings_tabs.setTabText(i, t(key))
        self.privacy_label.setText(
            f"{t('settings.telemetry')}\n{t('settings.network')}\n"
            f"{t('settings.protected_study')}\n"
            f"Source MAT: read-only by default\n"
            f"Analysis mode: {self.settings.analysis_mode()}"
        )
        self.advanced_label.setText(
            f"rule_pack={self.settings.get('advanced','rule_pack_version')}\n"
            f"reference_pack={self.settings.get('advanced','reference_pack_version')}\n"
            f"analysis_mode={self.settings.analysis_mode()}"
        )
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
        self._refresh_viewer_meta()
        self._refresh_batch_preview()

    def set_language(self, language: str) -> None:
        lang = "ru" if language == "ru" else "en"
        self.i18n.set_language(lang)
        self.settings.set("general", "language", lang)
        self.settings.save()
        self.retranslate()
        self._update_status_bar()

    def _show_about(self) -> None:
        body = self.t("about.body").replace("{version}", __version__)
        QMessageBox.about(self, self.t("about.title"), body)

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
        if row >= 0:
            self.stack.setCurrentIndex(row)
            keys = [k for k, _ in NAV_KEYS]
            if row < len(keys) and keys[row] == "home" and hasattr(self, "home_dashboard"):
                self.home_dashboard.refresh()

    def _navigate_key(self, key: str) -> None:
        keys = [k for k, _ in NAV_KEYS]
        if key in keys:
            self.nav.setCurrentRow(keys.index(key))

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
    def _create_project(self) -> None:
        name = self.proj_name.text().strip() or "IML_Project"
        ws = self.settings.get("general", "workspace_dir") or None
        self.session.project = create_project(
            name,
            language=self.i18n.language,
            workspace_parent=ws,
            profile_id=self.session.profile_id,
        )
        self.proj_status.setText(f"{self.t('project.created')}: {self.session.project.root}")
        self._update_status_bar()

    def _import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "MAT", "", "MAT (*.mat)")
        if path:
            self._add_mat(Path(path))

    def _import_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "MAT folder")
        if not path:
            return
        try:
            files = list_mat_files(path, recursive=bool(self.settings.get("data", "recursive_folder_scan", True)))
        except ForbiddenPathError:
            QMessageBox.critical(self, "IML", self.t("import.blocked"))
            return
        for f in files:
            self._add_mat(f)

    def _add_mat(self, path: Path) -> None:
        try:
            default_blocklist().assert_allowed(path)
        except ForbiddenPathError:
            QMessageBox.critical(self, "IML", self.t("import.blocked"))
            return
        if path not in self.session.selected_mats:
            self.session.selected_mats.append(path)
        self.session.set_active_mat(path)
        audit = audit_mat_path(path, self.session.profile)
        self.session.last_audits.append(audit.to_dict())
        lang = self.i18n.language
        cards = [audit_card(a, lang) for a in self.session.last_audits[-20:]]
        self.import_cards.setPlainText("\n\n———\n\n".join(cards))
        self.import_tech.setPlainText(json.dumps(audit.to_dict(), indent=2, ensure_ascii=False))
        self._refresh_viewer_meta()
        self._update_status_bar()
        # auto navigate hint
        self.nav.setCurrentRow([k for k, _ in NAV_KEYS].index("viewer"))

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
            return
        if self.settings.get("performance", "automatic_cache_creation", True):
            self._build_cache_async()
        else:
            self._goto_frame(self.session.current_frame)

    def _build_cache_async(self) -> None:
        if not self.session.has_real_import():
            QMessageBox.information(self, "IML", self.t("viewer.no_import"))
            return
        store = self.session.ensure_store()
        self.cache_progress.setVisible(True)
        self.cache_progress.setValue(0)
        self.session.background_task = "cache"
        self._update_status_bar()
        self._cache_worker = CacheBuildWorker(store)
        self._cache_worker.progress.connect(self._on_cache_progress)
        self._cache_worker.finished_ok.connect(self._on_cache_ready)
        self._cache_worker.failed.connect(lambda e: self._error_dialog(e, e))
        self._cache_worker.start()

    def _on_cache_progress(self, info: dict) -> None:
        if "percent" in info:
            self.cache_progress.setValue(int(info["percent"]))
        self.session.background_task = info.get("event", "cache")
        self._update_status_bar()

    def _on_cache_ready(self, info: dict) -> None:
        self.cache_progress.setVisible(False)
        self.session.background_task = ""
        self._goto_frame(self.session.current_frame)
        self._update_status_bar()

    def _refresh_viewer_meta(self) -> None:
        lang = self.i18n.language
        tm = mapping_status(self.session.profile.get("time_mapping"))
        mat = self.session.active_mat.name if self.session.active_mat else "—"
        cache = "—"
        if self.session.frame_store:
            st = self.session.frame_store.status()
            cache = "ready" if st.valid else (st.reason or "missing")
        warn = tm.warning_ru if lang == "ru" else tm.warning_en
        self.viewer_meta.setText(
            f"Project: {self.session.project.name if self.session.project else '—'}\n"
            f"MAT: {mat}\n"
            f"Variable: {self.session.profile.get('amplitude_variable_name')}\n"
            f"Profile: {self.session.profile_id} [{self.session.profile.get('profile_verification_status')}]\n"
            f"Cache: {cache}\n"
            f"Frequency axis: {self.session.profile.get('frequency_variable_name') or 'profile'}\n"
            f"Range axis: {self.session.profile.get('range_axis_label_en')}\n"
            f"Time mapping: {tm.status}\n{warn}"
        )
        self.time_edit.setEnabled(tm.available)

    def _goto_frame(self, frame_id: int) -> None:
        if not self.session.has_real_import():
            return
        try:
            store = self.session.ensure_store()
            st = store.status()
            if not st.valid:
                if self.settings.get("performance", "automatic_cache_creation", True):
                    self._build_cache_async()
                    return
                QMessageBox.information(self, "IML", "Cache required. Build cache first.")
                return
            n = store.n_frames()
            frame_id = max(1, min(int(frame_id), n))
            self.frame_spin.setMaximum(n)
            self.frame_slider.setMaximum(n)
            self.session.current_frame = frame_id
            self._syncing_time = True
            self.frame_spin.setValue(frame_id)
            self.frame_slider.setValue(frame_id)
            if mapping_status(self.session.profile.get("time_mapping")).available:
                self.time_edit.setText(format_hhmm(frame_to_minute(frame_id)))
            self._syncing_time = False
            self._render_current_frame()
            self._update_status_bar()
        except Exception as exc:  # noqa: BLE001
            self._error_dialog(str(exc), traceback.format_exc())

    def _on_frame_spin(self, v: int) -> None:
        if not self._syncing_time:
            self._goto_frame(v)

    def _on_frame_slider(self, v: int) -> None:
        if not self._syncing_time:
            self._goto_frame(v)

    def _on_time_edit(self) -> None:
        if self._syncing_time:
            return
        m = parse_hhmm(self.time_edit.text())
        if m is None:
            return
        self._goto_frame(minute_to_frame(m))

    def _jump_minutes(self) -> int:
        return int(self.jump_combo.currentText())

    def _jump_back(self) -> None:
        self._goto_frame(self.session.current_frame - self._jump_minutes())

    def _jump_fwd(self) -> None:
        self._goto_frame(self.session.current_frame + self._jump_minutes())

    def _play(self) -> None:
        fps = float(self.speed_combo.currentText())
        self._play_timer.start(int(1000 / max(fps, 0.1)))

    def _pause_play(self) -> None:
        self._play_timer.stop()

    def _toggle_play(self) -> None:
        if self._play_timer.isActive():
            self._pause_play()
        else:
            self._play()

    def _playback_tick(self) -> None:
        nxt = self.session.current_frame + 1
        if nxt > self.frame_spin.maximum():
            if self.loop_chk.isChecked():
                nxt = 1
            else:
                self._pause_play()
                return
        self._goto_frame(nxt)

    def _goto_dialog(self) -> None:
        text, ok = QInputDialog.getText(self, "Go to", "Frame or HH:MM")
        if not ok:
            return
        if ":" in text:
            m = parse_hhmm(text)
            if m is not None:
                self._goto_frame(minute_to_frame(m))
        else:
            try:
                self._goto_frame(int(text))
            except ValueError:
                pass

    def _render_current_frame(self) -> None:
        store = self.session.ensure_store()
        frame = store.get_frame(self.session.current_frame)
        original = frame.copy()
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
                display = frame * seg.trace_mask
        if preview == "fast" or (preview == "auto" and mode == "raw"):
            # display-only downsample
            display = display[::2, ::2]
            label = f"{label} | {self.t('viewer.fast_preview')}"
        assert np.array_equal(frame, original)
        prof = load_profile(app_root() / "config/instrument_profiles" / f"{self.session.profile_id}.yaml")
        # axes may be shorter after downsample — use index axes for fast preview
        if display.shape != frame.shape:
            freq = list(range(display.shape[1]))
            rng = list(range(display.shape[0]))
        else:
            freq = frequency_axis_from_profile(prof)
            rng = range_axis_from_profile(prof)
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
        self.viewer_image.setPixmap(
            pix.scaled(self.viewer_image.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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
        mode = self.batch_mode.currentText()
        if mode == "single":
            return select_single(self.b_start.value(), n)
        if mode == "frame_range":
            return select_frame_range(self.b_start.value(), self.b_end.value(), self.b_step.value(), n)
        if mode == "time_range":
            return select_time_range(self.b_t0.text(), self.b_t1.text(), self.b_step.value(), n)
        if mode == "full_day":
            return select_full_day(int(self.b_day_interval.currentText()), n)
        if mode == "custom_list":
            return select_custom_list([x.strip() for x in self.b_custom.text().replace(";", ",").split(",")], n)
        return select_contact_sequence(self.b_start.value(), 5, 5, self.b_step.value(), n)

    def _refresh_batch_preview(self) -> None:
        try:
            sel = self._current_selection()
            est = estimate_resources(sel)
            expl = sel.explanation_ru if self.i18n.language == "ru" else sel.explanation_en
            self.batch_preview.setPlainText(
                f"{expl}\n\n"
                f"{self.t('batch.expected')}: {est['expected_frames']}\n"
                f"Memory ~ {est['estimated_memory_mb']} MB (selected frames)\n"
                f"Cache day ~ {est['estimated_cache_mb']} MB\n"
                f"Render ~ {est['estimated_render_seconds']} s | Analysis ~ {est['estimated_analysis_seconds']} s\n"
                f"Frame interval: {sel.frame_interval} | Time interval: {sel.time_interval_minutes} min"
            )
        except Exception as exc:  # noqa: BLE001
            self.batch_preview.setPlainText(str(exc))

    def _batch_start(self) -> None:
        if self.session.project is None:
            QMessageBox.warning(self, "IML", self.t("nav.new_project"))
            return
        mats = self.session.selected_mats
        if not mats:
            QMessageBox.information(self, "IML", self.t("viewer.no_import"))
            return
        sel = self._current_selection()
        ops = [k for k, c in self.op_checks.items() if c.isChecked()] or ["full_pipeline"]
        expl = sel.explanation_ru if self.i18n.language == "ru" else sel.explanation_en
        if (
            QMessageBox.question(self, "IML", expl + "\n\n" + self.t("batch.confirm"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.batch_controller = BatchController()
        self.batch_progress.setValue(0)
        self.batch_status.setText("")

        def factory(path, profile):
            return FrameStore(
                path,
                profile,
                cache_root=self.settings.cache_dir(),
                prefetch_radius=int(self.settings.get("viewer", "prefetch_count", 2)),
                lru_capacity=int(self.settings.get("performance", "lru_capacity", 16)),
            )

        def progress(info: dict) -> None:
            self.batch_tech.appendPlainText(json.dumps(info, ensure_ascii=False))
            if info.get("event") == "progress":
                self.batch_progress.setValue(int(info.get("percent", 0)))
                self.batch_status.setText(
                    f"{info.get('file')} f{info.get('frame')} | "
                    f"{info.get('completed')}/{info.get('total')} | "
                    f"ETA {info.get('eta_s')}s | op={info.get('operation')} | "
                    f"cache hit/miss {info.get('cache_hits')}/{info.get('cache_misses')}"
                )
            self.session.background_task = info.get("operation", "")
            self._update_status_bar()

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

    def _load_results_table(self) -> None:
        self.session.last_results = []
        self.results_table.setRowCount(0)
        if not self.session.last_run_root:
            return
        for p in sorted((self.session.last_run_root / "predictions").glob("*.json")):
            rec = json.loads(p.read_text(encoding="utf-8"))
            self.session.last_results.append(rec)
        self.results_table.setRowCount(len(self.session.last_results))
        lang = self.i18n.language
        for r, rec in enumerate(self.session.last_results):
            fid = rec.get("frame_index", 0)
            sci = rec.get("scientific_axes") or {}
            morph = sci.get("morphology") or rec.get("morphology") or rec.get("candidate_morphology", "")
            vals = [
                str(rec.get("frame_id")),
                format_hhmm(frame_to_minute(int(fid))) if fid else "",
                str(sci.get("quality") or rec.get("data_quality_status")),
                str(sci.get("layer") or rec.get("layer") or "indeterminate"),
                morphology_label(morph, lang),
                str(sci.get("ambiguity") or rec.get("ambiguity") or "no_visible_ambiguity"),
                str(rec.get("final_auto_status")),
                "uncalibrated" if rec.get("confidence_score") is None else str(rec.get("confidence_score")),
                "yes" if rec.get("possible_ox_confusion") else "no",
                "pending",
            ]
            for c, v in enumerate(vals):
                self.results_table.setItem(r, c, QTableWidgetItem(v))

    def _show_selected_result(self) -> None:
        rows = self.results_table.selectionModel().selectedRows()
        if not rows:
            return
        rec = self.session.last_results[rows[0].row()]
        lang = self.i18n.language
        sci = rec.get("scientific_axes") or {}
        axes = (
            f"Layer / Слой: {sci.get('layer', rec.get('layer', 'indeterminate'))}\n"
            f"Morphology / Морфология: {sci.get('morphology', rec.get('candidate_morphology', 'indeterminate'))}\n"
            f"Ambiguity / Неоднозначность: {sci.get('ambiguity', rec.get('ambiguity', 'no_visible_ambiguity'))}\n"
            f"Quality / Качество: {sci.get('quality', rec.get('data_quality_status', ''))}\n"
            "These axes are stored separately — never as one overloaded ionogram type.\n\n"
        )
        self.res_overview.setPlainText(axes + explain_result(rec, lang))
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
        img = rec.get("raw_render_path")
        if img and Path(img).exists():
            self.res_image.setPixmap(QPixmap(img).scaledToWidth(700))

    def _human_decision(self, kind: str) -> None:
        if not self.session.project or not self.session.last_results:
            return
        rows = self.results_table.selectionModel().selectedRows()
        if not rows:
            return
        rec = self.session.last_results[rows[0].row()]
        reason = ""
        category = rec.get("candidate_morphology")
        if kind == "change":
            category, ok = QInputDialog.getText(self, "IML", "New category token")
            if not ok:
                return
            reason, ok = QInputDialog.getText(self, "IML", "Expert reason (required)")
            if not ok or not reason.strip():
                QMessageBox.warning(self, "IML", "Reason required when changing.")
                return
        elif kind in ("uncertain", "not_assessable"):
            category = kind
            reason = kind
        elif kind == "accept":
            reason = "accepted proposed category"
        human = {
            "decision": kind,
            "category": category,
            "reason": reason,
            "ts": datetime.now(timezone.utc).isoformat(),
            "reviewer": "local_user",
        }
        db = ProjectDatabase(Path(self.session.project.root) / "project.sqlite")
        db.update_human_decision(rec["frame_id"], human)
        db.append_audit(human["ts"], "human_decision", {"frame_id": rec["frame_id"], **human})
        self.res_expert.setPlainText(json.dumps(human, indent=2, ensure_ascii=False))
        # auto unchanged
        self.res_overview.setPlainText(
            explain_result(rec, self.i18n.language)
            + "\n\n"
            + self.t("results.auto")
            + f": {rec.get('candidate_morphology')}\n"
            + self.t("results.human")
            + f": {category}"
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
            else:
                val = wid.text()
            self.settings.set(section, key, val)
        # Apply optional protected study mode from privacy flag
        from ionogram_morphology_lab.security import ProtectedStudyConfig, set_active_protection

        enabled = bool(self.settings.get("privacy", "protected_study_enabled", False))
        set_active_protection(ProtectedStudyConfig(enabled=enabled))
        self.settings.save()
        self.set_language(self.settings.get("general", "language", "en"))
        QMessageBox.information(self, "IML", self.t("settings.save"))

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
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(self.t("error.generic"))
        box.setText(summary)
        box.setInformativeText(
            "Source MAT files were not modified.\n"
            "Use Technical details for the full message."
        )
        box.setDetailedText(technical)
        box.exec()
