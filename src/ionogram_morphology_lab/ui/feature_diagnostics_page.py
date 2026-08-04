"""Expert Feature Diagnostics — frame identity, performance, responsive layout (Phase 4B.2f)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Mapping

import numpy as np
from PySide6.QtCore import QByteArray, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFontMetrics, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStyle,
    QTabWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.cache.v2_feature_cache import (
    V2FeatureCache,
    cache_status_label,
    make_cache_key,
)
from ionogram_morphology_lab.features.v2.registry import explain_feature, feature_entry
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.morphology_candidate.cache import (
    MISS_INCOMPATIBLE_CACHE_SCHEMA,
    MISS_INCOMPATIBLE_LEDGER_SCHEMA,
    MorphologyCandidateCache,
    incompatible_candidate_cache_message,
    make_candidate_cache_key,
)
from ionogram_morphology_lab.morphology_candidate.compatibility import (
    INCOMPLETE_LEGACY_CACHE,
    classify_v2_for_candidate,
    legacy_incomplete_message,
)
from ionogram_morphology_lab.morphology_candidate.labels import disclaimer
from ionogram_morphology_lab.morphology_candidate.geometry_review_index import (
    load_geometry_review_corpus,
    save_geometry_review_update_in_place,
)
from ionogram_morphology_lab.morphology_candidate.presentation import (
    format_panel_text,
    fragmentation_gate_rows,
)
from ionogram_morphology_lab.morphology_candidate.status_messages import (
    StatusMessage,
    format_status,
)
from ionogram_morphology_lab.morphology_candidate.reviews import (
    ledger_hash,
    morphology_reviews_dir,
    save_morphology_review,
)
from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset, ruleset_hash
from ionogram_morphology_lab.morphology_candidate.service import (
    geometry_review_status_for_frame,
    resolve_or_evaluate_candidate,
)
from ionogram_morphology_lab.morphology_candidate.types import MorphologyCandidateReview
from ionogram_morphology_lab.projects.time_mapping import (
    format_hhmm,
    frame_to_minute,
    mapping_status,
    minute_to_frame,
    parse_hhmm,
)
from ionogram_morphology_lab.ui.active_source import (
    SourceStatus,
    empty_state_copy,
    paths_equal,
    prerequisite_message,
    resolve_active_source,
)
from ionogram_morphology_lab.ui.compact_source_strip import CompactSourceStrip
from ionogram_morphology_lab.ui.detachable_table_window import DetachableTableWindow
from ionogram_morphology_lab.ui.dialog_buttons import localize_dialog_buttons
from ionogram_morphology_lab.ui.evidence_dialog import EvidenceDialog, evidence_identity_from_result
from ionogram_morphology_lab.ui.features_table_model import (
    FeaturesFilterProxy,
    FeaturesTableModel,
    feature_group_filter_items,
)
from ionogram_morphology_lab.ui.sequence_table_presentation import (
    COMPACT_VISIBLE_COLUMNS,
    ESSENTIAL_COLUMNS,
    SEQ_COLUMN_COUNT,
    default_min_widths,
    marker_colors,
    preferred_widths,
    profile_label,
    sequence_header_labels,
    visible_columns_for_profile,
)
from ionogram_morphology_lab.ui.sequence_frame_state import (
    FD_LAYOUT_SCHEMA_VERSION,
    candidate_controls_for_state,
    control_tooltip,
    features_empty_message,
    format_sequence_progress_status,
    format_shortcuts_help,
    resolve_sequence_frame_state,
    sequence_state_message,
)
from ionogram_morphology_lab.ui.diagnostic_summary import (
    FEATURE_GROUPS,
    build_human_summary,
    explain_feature_human,
    group_for_feature,
    group_title,
    run_state_message,
)
from ionogram_morphology_lab.ui.fd_display import (
    compose_rgb,
    gray_to_qimage,
    orientation_identity_dict,
    overlay_rgba,
)
from ionogram_morphology_lab.ui.fd_display_cache import DisplayLayerCache
from ionogram_morphology_lab.ui.fd_frame_loader import (
    FrameLoadWorker,
    frame_sha256,
)

# Re-export for older tests: `from ...feature_diagnostics_page import frame_sha256`
__all__ = ["FeatureDiagnosticsPage", "frame_sha256"]
from ionogram_morphology_lab.ui.frame_diagnostic_context import (
    FrameDiagnosticContext,
    next_request_generation_id,
)
from ionogram_morphology_lab.ui.source_roles import format_missing_variable_user_message
from ionogram_morphology_lab.ui.theme import resolve_theme_name, source_card_tokens
from ionogram_morphology_lab.ui.v2_diagnostics_worker import V2DiagnosticsWorker
from ionogram_morphology_lab.ui.v2_process_worker import V2ProcessJobThread


class FeatureDiagnosticsPage(QWidget):
    navigate_requested = Signal(str)
    source_action = Signal(str)
    open_in_viewer_requested = Signal()
    frame_sync_to_viewer = Signal(int)

    # Construction counters for Phase 4B.2h tests
    ctor_io_ops = 0

    LAYER_KEYS = [
        ("raw", "Исходная ионограмма", "Source ionogram", (0, 0, 0, 0)),
        ("diagnostic_normalized", "Нормализованный диагностический вид", "Diagnostic normalized", (0, 0, 0, 0)),
        ("trace_candidate", "Кандидаты следа", "Trace candidates", (80, 180, 255, 140)),
        ("trace_accepted", "Принятый след", "Accepted trace", (40, 220, 80, 160)),
        ("interference", "Маска помех", "Interference mask", (220, 40, 40, 150)),
        ("uncertain", "Неопределённые области", "Uncertain regions", (240, 200, 40, 120)),
        ("centerline", "Осевая линия", "Centerline", (255, 255, 0, 220)),
        ("branch_labels", "Ветви", "Branches", (180, 80, 220, 130)),
        ("vertical_width_map", "Направления вертикальных измерений", "Vertical measurement directions", (0, 200, 200, 160)),
        ("horizontal_width_map", "Направления горизонтальных измерений", "Horizontal measurement directions", (200, 120, 0, 160)),
        ("excluded", "Исключённые области", "Excluded regions", (120, 120, 120, 100)),
        ("floor_clutter", "Нижняя засветка", "Floor clutter", (160, 100, 60, 120)),
    ]
    DEFAULT_LAYERS = ("raw", "trace_accepted", "interference", "centerline", "branch_labels")

    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self._result = None
        self._result_ser: dict | None = None
        self._masks: dict[str, np.ndarray] = {}
        self._raw = None
        self._raw_sha = ""
        self._source_sha = ""
        self._zoom = 0.0
        self._layer_checks: dict[str, QCheckBox] = {}
        self._running = False
        self._run_state = "no_active"
        self._theme_pref = "system"
        self._feature_index: dict[str, str] = {}
        self._worker: V2DiagnosticsWorker | None = None
        self._frame_worker: FrameLoadWorker | None = None
        self._cache_status = "not_computed"
        self._timings: dict = {}
        self._sequence_results: list[dict] = []
        self._sequence_frames: list[int] = []
        self._sequence_generation_id: str = ""
        self._sequence_progress_frame: int | None = None
        self._sequence_candidate_running = False
        self._sequence_cancelled = False
        self._sequence_frame_state: str = "sequence_not_started"
        self._sequence_follow = True
        self._sequence_follow_paused_manual = False
        self._sequence_last_completed_frame: int | None = None
        self._suppress_follow_pause = False
        self._features_hydrating = False
        self._chk_seq_follow: QCheckBox | None = None
        self._btn_resume_follow: QToolButton | None = None
        self._btn_show_latest_seq: QToolButton | None = None
        self._seq_follow_status: QLabel | None = None
        self._features_identity_label: QLabel | None = None
        self._features_empty_label: QLabel | None = None
        self._morph_result = None
        self._morph_result_dict: dict | None = None
        self._morph_cache_status = "not_computed"
        self._morph_compat_state: str | None = None
        self._morph_last_miss_reason: str | None = None
        self._morph_review_status = "unreviewed"
        self._morph_generation = 0
        self._morph_identity: dict | None = None
        self._evidence_dialog: EvidenceDialog | None = None
        self._review_dialog: QDialog | None = None
        self._status_msg: StatusMessage | None = None
        self._features_model: FeaturesTableModel | None = None
        self._features_proxy: FeaturesFilterProxy | None = None
        self._features_view: QTableView | None = None
        self._features_search: QLineEdit | None = None
        self._features_cat: QComboBox | None = None
        self._features_splitter: QSplitter | None = None
        self._features_detach_win: DetachableTableWindow | None = None
        self._seq_detach_win: DetachableTableWindow | None = None
        self._seq_detach_table: QTableWidget | None = None
        self._seq_table_profile: str = "compact"  # embedded default; detached uses full
        self._seq_user_hidden: set[int] = set()
        self._seq_column_widths_user: dict[int, int] = {}
        self._seq_column_profile_applied = False
        self._seq_applying_column_widths = False
        self._seq_columns_menu: QMenu | None = None
        self._seq_resize_debounce: QTimer | None = None
        self._mid_vsplit: QSplitter | None = None
        self._seq_pane: QWidget | None = None
        self._saved_seq_split_sizes: list[int] | None = None
        self._collapse_state: dict[str, bool] = {}
        self._btn_reset_layout: QToolButton | None = None
        self._btn_shortcuts_help: QToolButton | None = None
        self._btn_detach_features: QToolButton | None = None
        self._btn_features_more: QToolButton | None = None
        self._features_more_menu: QMenu | None = None
        self._btn_detach_seq: QToolButton | None = None
        self._btn_show_seq_table: QToolButton | None = None
        self._btn_features_expand: QToolButton | None = None
        self._btn_features_collapse_explain: QToolButton | None = None
        self._btn_features_reset_layout: QToolButton | None = None
        self._act_detach_features = None
        self._act_features_expand = None
        self._act_features_collapse = None
        self._act_features_reset = None
        self._act_features_tech = None
        self._act_features_copy = None
        self._act_features_export = None
        self._shortcuts_help_label: QLabel | None = None
        self._preferred_h_sizes = (150, 550, 300)  # Layers ~15% / canvas ~55% / inspector ~30%
        self._preferred_mid_sizes = (400, 220)
        self._preferred_features_sizes = (360, 160)
        self._layers_saved_width = 150
        self._sc_detach_features: QShortcut | None = None
        self._sc_detach_sequence: QShortcut | None = None
        self._sc_reset_layout: QShortcut | None = None
        self._sync_auto = True
        self._inline_note = ""
        self._n_frames = 1440
        self._loaded_frame = -1
        self._intended_frame = 1
        self._frame_navigation_generation = 0
        self._pending_frame_request: dict | None = None
        self._viewer_sync_accept = False
        self._loaded_mat_path: str | None = None
        self._last_known_source_sha: str = ""
        self._current_ctx: FrameDiagnosticContext | None = None
        self._active_generation_id: str = ""
        self._v2_generation_id: str = ""
        self._job_state = "idle"
        self._display_cache = DisplayLayerCache()
        self._progress_throttle = QTimer(self)
        self._progress_throttle.setInterval(100)
        self._progress_throttle.setSingleShot(True)
        self._pending_progress: dict | None = None
        self._progress_throttle.timeout.connect(self._flush_progress)
        self._spin_debounce = QTimer(self)
        self._spin_debounce.setInterval(300)
        self._spin_debounce.setSingleShot(True)
        self._spin_debounce.timeout.connect(self._apply_debounced_spin)
        self._pending_spin_frame: int | None = None
        self._v2_pipeline_runs = 0
        self._cache_writes = 0
        self._visible_timings: dict = {}
        self._viewer_frame_cache_status = "—"
        self._display_cache_status = "—"
        self._features_populated = False
        self._activated_once = False
        self._registry_reload_count = 0
        self._use_process_v2 = True
        self._features_tab_built = False
        self._review_tab_built = False
        self._tech_tab_built = False
        self._help_body_loaded = False
        self._last_cache_diag: dict = {}
        self._skeleton_constructed = True

        settings = getattr(session, "settings", None)
        cache_root = settings.cache_dir() if settings is not None else Path.home() / ".iml_cache"
        # Lightweight: construct cache handle only (no directory scan / MAT I/O).
        self._cache = V2FeatureCache(cache_root)
        self._morph_cache = MorphologyCandidateCache(cache_root)
        self._settings = settings

        # Outer scroll keeps low-height windows usable; tables keep their own scrollbars.
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        self._outer_scroll = QScrollArea()
        self._outer_scroll.setWidgetResizable(True)
        self._outer_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._outer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._outer_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._page_content = QWidget()
        root = QVBoxLayout(self._page_content)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)
        self._outer_scroll.setWidget(self._page_content)
        page_layout.addWidget(self._outer_scroll, 1)

        # Single compact title row: shadow badge + help (?) on the right.
        # MainWindow already shows the page title — do not repeat a large banner.
        title_row = QHBoxLayout()
        self.banner = QLabel()
        self.banner.setObjectName("fdShadowBadge")
        self.banner.setWordWrap(False)
        title_row.addWidget(self.banner)
        title_row.addStretch(1)
        self.btn_help = QToolButton()
        self.btn_help.clicked.connect(self._toggle_help_drawer)
        title_row.addWidget(self.btn_help)
        root.addLayout(title_row)

        self.subtitle = QLabel()
        self.subtitle.setWordWrap(True)
        self.subtitle.setObjectName("fdSubtitle")
        root.addWidget(self.subtitle)

        self.help_drawer = QFrame()
        self.help_drawer.setObjectName("fdHelpDrawer")
        self.help_drawer.setMinimumWidth(280)
        self.help_drawer.setMaximumWidth(420)
        hd = QVBoxLayout(self.help_drawer)
        hd.setContentsMargins(8, 8, 8, 8)
        help_head = QHBoxLayout()
        self.help_title = QLabel()
        self.help_title.setStyleSheet("font-weight:600;")
        self.btn_pin_help = QToolButton()
        self.btn_pin_help.setCheckable(True)
        self.btn_pin_help.toggled.connect(self._on_help_pin_toggled)
        self.btn_close_help = QToolButton()
        self.btn_close_help.clicked.connect(lambda: self._set_help_drawer_visible(False, persist=True))
        help_head.addWidget(self.help_title)
        help_head.addStretch(1)
        help_head.addWidget(self.btn_pin_help)
        help_head.addWidget(self.btn_close_help)
        hd.addLayout(help_head)
        self.explain_fd = QLabel()
        self.explain_fd.setWordWrap(True)
        self.explain_fd.setObjectName("fdExplain")
        # Full Help body text loaded lazily on first open (page skeleton).
        self.explain_fd.setText("")
        hd.addWidget(self.explain_fd, 1)
        self._shortcuts_help_label = QLabel()
        self._shortcuts_help_label.setWordWrap(True)
        self._shortcuts_help_label.setObjectName("fdShortcutsHelp")
        self._shortcuts_help_label.setText("")
        hd.addWidget(self._shortcuts_help_label)
        self.btn_open_full_help = QPushButton()
        self.btn_open_full_help.clicked.connect(lambda: self.navigate_requested.emit("help"))
        hd.addWidget(self.btn_open_full_help)

        self.source_card = CompactSourceStrip(i18n)
        self.source_card.action.connect(self.source_action.emit)
        root.addWidget(self.source_card)

        self.inline_note = QLabel()
        self.inline_note.setWordWrap(True)
        self.inline_note.hide()
        root.addWidget(self.inline_note)

        self.state_label = QLabel()
        self.state_label.setWordWrap(True)
        root.addWidget(self.state_label)

        # Identity / provenance live in Technical Details tab — keep one human status line.
        self.identity = QLabel()
        self.identity.setWordWrap(True)
        self.identity.hide()

        self.cache_status_row = QLabel()
        self.cache_status_row.setWordWrap(True)
        root.addWidget(self.cache_status_row)

        # --- Frame selection ---
        self.frame_box = QGroupBox()
        fl = QVBoxLayout(self.frame_box)
        fl.setContentsMargins(6, 6, 6, 6)
        row1 = QHBoxLayout()
        self.mode_label = QLabel()
        self.mode_combo = QComboBox()
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        row1.addWidget(self.mode_label)
        row1.addWidget(self.mode_combo)
        row1.addStretch(1)
        fl.addLayout(row1)

        nav = QHBoxLayout()
        self.frame_spin = QSpinBox()
        self.frame_spin.setRange(1, 1440)
        self.frame_spin.valueChanged.connect(self._on_frame_spin)
        self.frame_spin.editingFinished.connect(self._commit_spin_edit)
        self.time_edit = QLabel("—")
        self.btn_first = QPushButton("|<")
        self.btn_prev = QPushButton("<")
        self.btn_next = QPushButton(">")
        self.btn_last = QPushButton(">|")
        self.jump_spin = QSpinBox()
        self.jump_spin.setRange(1, 120)
        self.jump_spin.setValue(10)
        self.btn_minus = QPushButton("−N")
        self.btn_plus = QPushButton("+N")
        self.btn_first.clicked.connect(
            lambda: self._goto_frame(1, immediate=True, reason="previous_next")
        )
        self.btn_prev.clicked.connect(
            lambda: self._goto_frame(self.frame_spin.value() - 1, immediate=True, reason="previous_next")
        )
        self.btn_next.clicked.connect(
            lambda: self._goto_frame(self.frame_spin.value() + 1, immediate=True, reason="previous_next")
        )
        self.btn_last.clicked.connect(
            lambda: self._goto_frame(self._n_frames, immediate=True, reason="previous_next")
        )
        self.btn_minus.clicked.connect(
            lambda: self._goto_frame(
                self.frame_spin.value() - self.jump_spin.value(),
                immediate=True,
                reason="previous_next",
            )
        )
        self.btn_plus.clicked.connect(
            lambda: self._goto_frame(
                self.frame_spin.value() + self.jump_spin.value(),
                immediate=True,
                reason="previous_next",
            )
        )
        for w in (
            self.btn_first, self.btn_prev, self.frame_spin, self.btn_next, self.btn_last,
            self.jump_spin, self.btn_minus, self.btn_plus, self.time_edit,
        ):
            nav.addWidget(w)
        fl.addLayout(nav)

        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setRange(1, 1440)
        self.frame_slider.setValue(1)
        self.frame_slider.sliderMoved.connect(self._on_frame_slider_moved)
        self.frame_slider.sliderReleased.connect(self._on_frame_slider_released)
        fl.addWidget(self.frame_slider)

        sync = QHBoxLayout()
        self.btn_use_viewer = QPushButton()
        self.btn_send_viewer = QPushButton()
        self.chk_auto_sync = QCheckBox()
        self.chk_auto_sync.setChecked(True)
        self.chk_auto_sync.toggled.connect(lambda v: setattr(self, "_sync_auto", v))
        self.btn_use_viewer.clicked.connect(self._use_viewer_frame)
        self.btn_send_viewer.clicked.connect(self._send_frame_to_viewer)
        self.exact_time = QComboBox()
        self.exact_time.setEditable(True)
        self.btn_jump_time = QPushButton()
        self.btn_jump_time.clicked.connect(self._jump_exact_time)
        for w in (
            self.btn_use_viewer, self.btn_send_viewer, self.chk_auto_sync,
            self.exact_time, self.btn_jump_time,
        ):
            sync.addWidget(w)
        fl.addLayout(sync)

        # Sequence controls (conditional)
        self.seq_form = QGroupBox()
        sf = QVBoxLayout(self.seq_form)
        self.seq_type_label = QLabel()
        self.seq_type = QComboBox()
        self.seq_type.currentIndexChanged.connect(self._on_seq_type_changed)
        type_row = QHBoxLayout()
        type_row.addWidget(self.seq_type_label)
        type_row.addWidget(self.seq_type)
        sf.addLayout(type_row)
        self.seq_fields = QWidget()
        self.seq_fields_layout = QFormLayout(self.seq_fields)
        self.seq_start = QSpinBox()
        self.seq_start.setRange(1, 1440)
        self.seq_start.setValue(1)
        self.seq_end = QSpinBox()
        self.seq_end.setRange(1, 1440)
        self.seq_end.setValue(60)
        self.seq_step = QSpinBox()
        self.seq_step.setRange(1, 120)
        self.seq_step.setValue(10)
        self.seq_t0 = QComboBox()
        self.seq_t0.setEditable(True)
        self.seq_t0.setCurrentText("05:00")
        self.seq_t1 = QComboBox()
        self.seq_t1.setEditable(True)
        self.seq_t1.setCurrentText("07:00")
        self.seq_interval = QSpinBox()
        self.seq_interval.setRange(1, 120)
        self.seq_interval.setValue(10)
        self.seq_custom = QTextEdit()
        self.seq_custom.setMaximumHeight(48)
        self.seq_custom.setPlaceholderText("1,2,5-10")
        self.lbl_seq_start = QLabel()
        self.lbl_seq_end = QLabel()
        self.lbl_seq_step = QLabel()
        self.lbl_seq_t0 = QLabel()
        self.lbl_seq_t1 = QLabel()
        self.lbl_seq_interval = QLabel()
        self.lbl_seq_custom = QLabel()
        # Stable form rows — visibility toggled; never removeRow (would delete widgets)
        self.seq_fields_layout.addRow(self.lbl_seq_start, self.seq_start)
        self.seq_fields_layout.addRow(self.lbl_seq_end, self.seq_end)
        self.seq_fields_layout.addRow(self.lbl_seq_step, self.seq_step)
        self.seq_fields_layout.addRow(self.lbl_seq_t0, self.seq_t0)
        self.seq_fields_layout.addRow(self.lbl_seq_t1, self.seq_t1)
        self.seq_fields_layout.addRow(self.lbl_seq_interval, self.seq_interval)
        self.seq_fields_layout.addRow(self.lbl_seq_custom, self.seq_custom)
        self.seq_preview = QLabel()
        self.seq_preview.setWordWrap(True)
        sf.addWidget(self.seq_fields)
        sf.addWidget(self.seq_preview)
        self.btn_contact = QPushButton()
        self.btn_contact.clicked.connect(self._request_contact_sheet)
        sf.addWidget(self.btn_contact)
        fl.addWidget(self.seq_form)
        self.seq_form.hide()
        seq_row = QHBoxLayout()
        self.seq_summary = QLabel()
        self.seq_summary.setWordWrap(True)
        self.btn_sequence_settings = QPushButton()
        self.btn_sequence_settings.clicked.connect(self._open_sequence_settings)
        seq_row.addWidget(self.seq_summary, 1)
        seq_row.addWidget(self.btn_sequence_settings)
        fl.addLayout(seq_row)
        root.addWidget(self.frame_box)

        controls = QHBoxLayout()
        self.btn_run = QPushButton()
        self.btn_run.clicked.connect(self.run_shadow)
        self.btn_cancel = QPushButton()
        self.btn_cancel.clicked.connect(self._cancel_run)
        self.btn_cancel.setEnabled(False)
        self.btn_recalc = QPushButton()
        self.btn_recalc.clicked.connect(lambda: self.run_shadow(force=True))
        self.btn_clear_cache = QPushButton()
        self.btn_clear_cache.clicked.connect(self._clear_v2_cache)
        self.btn_layers = QToolButton()
        self.btn_layers.setCheckable(True)
        self.btn_layers.toggled.connect(self._set_layers_drawer_visible)
        self.btn_fit = QPushButton()
        self.btn_fit.clicked.connect(lambda: self._set_zoom("fit"))
        self.btn_100 = QPushButton()
        self.btn_100.clicked.connect(lambda: self._set_zoom("100"))
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.clicked.connect(lambda: self._nudge_zoom(1.25))
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.clicked.connect(lambda: self._nudge_zoom(0.8))
        self.btn_viewer = QPushButton()
        self.btn_viewer.clicked.connect(self.open_in_viewer_requested.emit)
        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self.export_package)
        self.btn_more = QToolButton()
        self.btn_more.setCheckable(True)
        self.btn_more.toggled.connect(lambda on: self.more_panel.setVisible(on))
        self.view_preset = QComboBox()
        self.view_preset.currentIndexChanged.connect(self._apply_view_preset)
        self.base_view = QComboBox()
        self.base_view.currentIndexChanged.connect(self._render_view)
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(10, 100)
        self.opacity.setValue(55)
        self.opacity.valueChanged.connect(self._render_view)
        self.opacity_label = QLabel()
        self.cache_label = QLabel()
        # Primary actions stay visible; secondary go under More…
        for w in (
            self.btn_run, self.btn_cancel,
            self.btn_layers, self.view_preset, self.btn_more,
        ):
            controls.addWidget(w)
        controls.addStretch(1)
        root.addLayout(controls)

        # Always-visible quick layer strip (owner-requested; not drawer-only).
        self.quick_layers = QWidget()
        self.quick_layers.setObjectName("fdQuickLayers")
        ql = QHBoxLayout(self.quick_layers)
        ql.setContentsMargins(2, 2, 2, 2)
        ql.setSpacing(6)
        self._quick_layer_btns: dict[str, QToolButton] = {}
        self.QUICK_LAYER_KEYS = (
            ("raw", "Исходная", "Source"),
            ("trace_accepted", "След", "Trace"),
            ("interference", "Помехи", "Interference"),
            ("centerline", "Осевая линия", "Centerline"),
            ("branch_labels", "Ветви", "Branches"),
        )
        for key, _ru, _en in self.QUICK_LAYER_KEYS:
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setChecked(key in self.DEFAULT_LAYERS)
            btn.toggled.connect(lambda on, k=key: self._on_quick_layer(k, on))
            self._quick_layer_btns[key] = btn
            ql.addWidget(btn)
        ql.addStretch(1)
        root.addWidget(self.quick_layers)

        self.more_panel = QFrame()
        more = QHBoxLayout(self.more_panel)
        more.setContentsMargins(4, 4, 4, 4)
        for w in (
            self.btn_recalc, self.btn_export, self.btn_clear_cache, self.btn_viewer,
            self.btn_fit, self.btn_100, self.btn_zoom_in, self.btn_zoom_out,
            self.base_view, self.opacity_label, self.opacity, self.cache_label,
        ):
            more.addWidget(w)
        more.addStretch(1)
        self.more_panel.hide()
        root.addWidget(self.more_panel)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)
        self.stage_label = QLabel()
        root.addWidget(self.stage_label)

        self.why_toggle = QToolButton()
        self.why_toggle.setCheckable(True)
        self.why_body = QTextEdit()
        self.why_body.setReadOnly(True)
        self.why_body.setVisible(False)
        self.why_body.setMaximumHeight(140)
        self.why_toggle.toggled.connect(self.why_body.setVisible)
        root.addWidget(self.why_toggle)
        root.addWidget(self.why_body)

        empty_row = QHBoxLayout()
        self.btn_open_projects = QPushButton()
        self.btn_open_import = QPushButton()
        self.btn_choose_mat = QPushButton()
        self.btn_pick_project = QPushButton()
        self.btn_refresh_state = QPushButton()
        self.btn_open_projects.clicked.connect(lambda: self.navigate_requested.emit("projects"))
        self.btn_open_import.clicked.connect(lambda: self.navigate_requested.emit("import"))
        self.btn_choose_mat.clicked.connect(lambda: self.source_action.emit("choose_mat"))
        self.btn_pick_project.clicked.connect(lambda: self.source_action.emit("pick_from_project"))
        self.btn_refresh_state.clicked.connect(self.refresh)
        for b in (
            self.btn_open_projects, self.btn_open_import, self.btn_choose_mat,
            self.btn_pick_project, self.btn_refresh_state,
        ):
            empty_row.addWidget(b)
        empty_row.addStretch(1)
        root.addLayout(empty_row)

        # Main work area: [layers | canvas | inspector] + optional right Help overlay
        work = QHBoxLayout()
        work.setContentsMargins(0, 0, 0, 0)
        work.setSpacing(4)

        self.split = QSplitter()
        self.split.setChildrenCollapsible(False)
        left = QWidget()
        left.setMinimumWidth(140)
        left.setMaximumWidth(280)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(2, 2, 2, 2)
        self.layers_toggle = QToolButton()
        self.layers_toggle.setCheckable(True)
        self.layers_toggle.setChecked(True)
        self.layers_toggle.toggled.connect(self._toggle_layers)
        ll.addWidget(self.layers_toggle)
        self.layers_panel = QWidget()
        self._layers_panel_layout = QVBoxLayout(self.layers_panel)
        self.layers_title = QLabel()
        self._layers_panel_layout.addWidget(self.layers_title)
        self._layers_built = False
        # Expert layer checkboxes built lazily when drawer opens (page skeleton first).
        self.legend = QLabel()
        self.legend.setWordWrap(True)
        self.btn_default_layers = QPushButton()
        self.btn_default_layers.clicked.connect(self._show_default_layers)
        self.btn_hide_overlays = QPushButton()
        self.btn_hide_overlays.clicked.connect(self._hide_overlays)
        ll.addWidget(self.layers_panel)
        # Preferred default: Layers visible on the left (not collapsed under the ionogram).
        self.layers_panel.show()
        self.split.addWidget(left)

        mid = QWidget()
        mid.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mid.setMinimumWidth(320)
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(2, 2, 2, 2)
        ml.setSpacing(2)
        canvas_bar = QHBoxLayout()
        self.zoom_mode = QComboBox()
        self.zoom_mode.currentIndexChanged.connect(self._on_zoom_mode)
        canvas_bar.addWidget(self.zoom_mode, 1)
        self._btn_reset_layout = QToolButton()
        self._btn_reset_layout.clicked.connect(self._reset_diagnostics_layout)
        canvas_bar.addWidget(self._btn_reset_layout)
        self._btn_shortcuts_help = QToolButton()
        self._btn_shortcuts_help.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._btn_shortcuts_help.clicked.connect(self._open_shortcuts_help)
        canvas_bar.addWidget(self._btn_shortcuts_help)
        self._btn_show_seq_table = QToolButton()
        self._btn_show_seq_table.clicked.connect(self._show_sequence_results_table)
        self._btn_show_seq_table.hide()
        canvas_bar.addWidget(self._btn_show_seq_table)
        self._btn_detach_seq = QToolButton()
        self._btn_detach_seq.clicked.connect(self._open_sequence_detach)
        self._btn_detach_seq.hide()
        canvas_bar.addWidget(self._btn_detach_seq)
        ml.addLayout(canvas_bar)

        # Vertical splitter: ionogram (upper) / sequence results (lower)
        self._mid_vsplit = QSplitter(Qt.Orientation.Vertical)
        self._mid_vsplit.setChildrenCollapsible(False)
        canvas_pane = QWidget()
        cpl = QVBoxLayout(canvas_pane)
        cpl.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumHeight(160)
        self.image.setMinimumWidth(280)
        self.scroll.setWidget(self.image)
        self.scroll.setMinimumHeight(160)
        cpl.addWidget(self.scroll, 1)
        self.pixel_info = QLabel()
        cpl.addWidget(self.pixel_info)
        self.contact_label = QLabel()
        self.contact_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.contact_label.hide()
        cpl.addWidget(self.contact_label)
        self._mid_vsplit.addWidget(canvas_pane)

        self._seq_pane = QWidget()
        spl = QVBoxLayout(self._seq_pane)
        spl.setContentsMargins(0, 0, 0, 0)
        seq_bar = QHBoxLayout()
        self._chk_seq_follow = QCheckBox()
        self._chk_seq_follow.setChecked(True)
        self._chk_seq_follow.toggled.connect(self._on_sequence_follow_toggled)
        seq_bar.addWidget(self._chk_seq_follow)
        self._btn_resume_follow = QToolButton()
        self._btn_resume_follow.clicked.connect(self._resume_sequence_follow)
        self._btn_resume_follow.hide()
        seq_bar.addWidget(self._btn_resume_follow)
        self._btn_show_latest_seq = QToolButton()
        self._btn_show_latest_seq.clicked.connect(self._show_latest_processed_sequence_frame)
        self._btn_show_latest_seq.hide()
        seq_bar.addWidget(self._btn_show_latest_seq)
        self.seq_filter = QComboBox()
        self.seq_filter.currentIndexChanged.connect(self._apply_sequence_filter)
        seq_bar.addWidget(self.seq_filter, 1)
        self._btn_seq_fit_cols = QToolButton()
        self._btn_seq_fit_cols.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._seq_columns_menu = QMenu(self._btn_seq_fit_cols)
        self._btn_seq_fit_cols.setMenu(self._seq_columns_menu)
        self._seq_columns_menu.aboutToShow.connect(self._rebuild_sequence_columns_menu)
        seq_bar.addWidget(self._btn_seq_fit_cols)
        spl.addLayout(seq_bar)
        self._seq_follow_status = QLabel()
        self._seq_follow_status.setWordWrap(True)
        self._seq_follow_status.hide()
        spl.addWidget(self._seq_follow_status)
        self.seq_table = QTableWidget(0, SEQ_COLUMN_COUNT)
        self.seq_table.setMinimumHeight(120)
        self.seq_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.seq_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.seq_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.seq_table.setAlternatingRowColors(False)
        self.seq_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.seq_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.seq_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.seq_table.setWordWrap(False)
        self.seq_table.verticalHeader().setVisible(False)
        self.seq_table.verticalHeader().setDefaultSectionSize(
            max(24, QFontMetrics(self.seq_table.font()).height() + 10)
        )
        hdr = self.seq_table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setMinimumSectionSize(36)
        hdr.sectionResized.connect(self._on_sequence_column_resized)
        self.seq_table.cellClicked.connect(self._on_sequence_cell_clicked)
        self.seq_table.setEnabled(True)
        spl.addWidget(self.seq_table, 1)
        self._seq_resize_debounce = QTimer(self)
        self._seq_resize_debounce.setSingleShot(True)
        self._seq_resize_debounce.setInterval(180)
        self._seq_resize_debounce.timeout.connect(self._on_sequence_pane_resize_settled)
        self._seq_pane.hide()
        self._mid_vsplit.addWidget(self._seq_pane)
        self._mid_vsplit.setStretchFactor(0, 65)
        self._mid_vsplit.setStretchFactor(1, 35)
        self._mid_vsplit.setSizes([400, 220])
        self._mid_vsplit.splitterMoved.connect(self._persist_mid_vsplit)
        self._mid_vsplit.splitterMoved.connect(self._schedule_sequence_pane_resize)
        ml.addWidget(self._mid_vsplit, 1)
        self.split.addWidget(mid)

        right = QWidget()
        right.setMinimumWidth(280)
        # No hard max width — user allocates space via the main horizontal splitter.
        rl = QVBoxLayout(right)
        rl.setContentsMargins(2, 2, 2, 2)
        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.currentChanged.connect(self._on_inspector_tab)

        # Tab 1 — Summary
        tab_summary = QWidget()
        ts = QVBoxLayout(tab_summary)
        self.summary_box = QGroupBox()
        sb = QVBoxLayout(self.summary_box)
        self.summary_view = QTextEdit()
        self.summary_view.setReadOnly(True)
        sb.addWidget(self.summary_view)
        ts.addWidget(self.summary_box, 1)
        self.summary_empty = QLabel()
        self.summary_empty.setWordWrap(True)
        ts.addWidget(self.summary_empty)
        self.inspector_tabs.addTab(tab_summary, "Summary")

        # Tab 2 — Features (shell only; model/view built on first open)
        self._tab_features = QWidget()
        self._features_host = QVBoxLayout(self._tab_features)
        self._features_shell_label = QLabel()
        self._features_host.addWidget(self._features_shell_label)
        # Legacy attribute kept for tests that clear/populate; replaced by QTableView on build.
        self.feature_list = QListWidget()
        self.feature_list.hide()
        self.explain = QTextEdit()
        self.explain.setReadOnly(True)
        self.explain.hide()
        self.tech_toggle = QToolButton()
        self.tech_toggle.setCheckable(True)
        self.tech_toggle.hide()
        self.inspector_tabs.addTab(self._tab_features, "Features")

        # Tab 3 — Provisional morphology candidate (shadow Phase 4C.1 / 4C.1a)
        tab_future = QWidget()
        tfu = QVBoxLayout(tab_future)
        self.future_box = QGroupBox()
        self.future_box.setObjectName("futureMorphology")
        fb = QVBoxLayout(self.future_box)
        self.morph_disclaimer = QLabel()
        self.morph_disclaimer.setWordWrap(True)
        self.morph_disclaimer.setObjectName("morphShadowDisclaimer")
        fb.addWidget(self.morph_disclaimer)
        self.morph_status = QLabel()
        self.morph_status.setWordWrap(True)
        fb.addWidget(self.morph_status)
        self.morph_summary = QTextEdit()
        self.morph_summary.setReadOnly(True)
        self.morph_summary.setMaximumHeight(220)
        fb.addWidget(self.morph_summary)
        # Primary actions — two rows so labels stay readable at narrow widths
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        self.btn_calc_morph = QPushButton()
        self.btn_calc_morph.setMinimumHeight(28)
        self.btn_calc_morph.clicked.connect(self._calculate_morphology_candidate)
        self.btn_recalc_morph = QPushButton()
        self.btn_recalc_morph.setMinimumHeight(28)
        self.btn_recalc_morph.clicked.connect(lambda: self._calculate_morphology_candidate(force=True))
        self.btn_morph_evidence = QPushButton()
        self.btn_morph_evidence.setMinimumHeight(28)
        self.btn_morph_evidence.clicked.connect(self._open_morph_evidence)
        self.btn_morph_review = QPushButton()
        self.btn_morph_review.setMinimumHeight(28)
        self.btn_morph_review.clicked.connect(self._open_morph_review_dialog)
        self.btn_recalc_v2_for_morph = QPushButton()
        self.btn_recalc_v2_for_morph.setMinimumHeight(28)
        self.btn_recalc_v2_for_morph.clicked.connect(lambda: self.run_shadow(force=True))
        self.btn_recalc_v2_for_morph.hide()
        row1.addWidget(self.btn_calc_morph)
        row1.addWidget(self.btn_recalc_morph)
        row2.addWidget(self.btn_morph_evidence)
        row2.addWidget(self.btn_morph_review)
        row2.addWidget(self.btn_recalc_v2_for_morph)
        self.btn_morph_more = QToolButton()
        self.btn_morph_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_morph_more.setMinimumHeight(28)
        self._morph_more_menu = QMenu(self)
        self.act_morph_provenance = self._morph_more_menu.addAction("Provenance")
        self.act_morph_provenance.triggered.connect(self._open_morph_provenance)
        self.act_copy_evidence_json = self._morph_more_menu.addAction("Copy evidence JSON")
        self.act_copy_evidence_json.triggered.connect(self._copy_evidence_json)
        self.act_export_evidence_json = self._morph_more_menu.addAction("Export evidence JSON")
        self.act_export_evidence_json.triggered.connect(self._export_evidence_json)
        self.act_copy_frag_gates = self._morph_more_menu.addAction("Copy fragmentation gate rows")
        self.act_copy_frag_gates.triggered.connect(self._copy_fragmentation_gate_rows)
        self.act_clear_morph_cache = self._morph_more_menu.addAction("Clear cache")
        self.act_clear_morph_cache.triggered.connect(self._clear_morph_cache_frame)
        self.act_export_morph_json = self._morph_more_menu.addAction("Export candidate JSON")
        self.act_export_morph_json.triggered.connect(self._export_morph_json)
        self.act_open_morph_reviews = self._morph_more_menu.addAction("Open review folder")
        self.act_open_morph_reviews.triggered.connect(self._open_morph_review_folder)
        self.act_geometry_review_overview = self._morph_more_menu.addAction("Geometry review overview")
        self.act_geometry_review_overview.triggered.connect(self._show_geometry_review_overview)
        self.btn_morph_more.setMenu(self._morph_more_menu)
        row2.addWidget(self.btn_morph_more)
        # Keep legacy attrs for tests / overflow mapping
        self.btn_morph_provenance = QPushButton()
        self.btn_morph_provenance.hide()
        self.btn_clear_morph_cache = QPushButton()
        self.btn_clear_morph_cache.hide()
        fb.addLayout(row1)
        fb.addLayout(row2)
        self.future_label = QLabel()
        self.future_label.setWordWrap(True)
        self.future_label.hide()  # empty-state text goes into morph_summary
        fb.addWidget(self.future_label)
        tfu.addWidget(self.future_box)
        tfu.addStretch(1)
        self.inspector_tabs.addTab(tab_future, "Morphology")

        # Tab 4 — Geometry review (shell; form built on first open)
        self._tab_review = QWidget()
        self._review_host = QVBoxLayout(self._tab_review)
        self._review_shell_label = QLabel()
        self._review_host.addWidget(self._review_shell_label)
        self.review_box = QGroupBox()
        self.review_box.hide()
        self.review_combo = QComboBox()
        self.review_comment = QTextEdit()
        self.review_comment.setMaximumHeight(60)
        self.btn_save_review = QPushButton()
        self.inspector_tabs.addTab(self._tab_review, "Geometry")

        # Tab 5 — Technical details (shell; body built on first open)
        self._tab_tech = QWidget()
        self._tech_host = QVBoxLayout(self._tab_tech)
        self._tech_shell_label = QLabel()
        self._tech_host.addWidget(self._tech_shell_label)
        self.tech_details = QTextEdit()
        self.tech_details.setReadOnly(True)
        self.tech_details.setObjectName("fdTechDetails")
        self.tech_details.hide()
        self.inspector_tabs.addTab(self._tab_tech, "Technical")

        rl.addWidget(self.inspector_tabs, 1)
        self.split.addWidget(right)
        self.split.setChildrenCollapsible(False)
        self.split.setStretchFactor(0, 15)
        self.split.setStretchFactor(1, 55)
        self.split.setStretchFactor(2, 30)
        # Preferred default: Layers | Canvas | Inspector (~15% / ~55% / ~30%)
        self.split.setSizes(list(self._preferred_h_sizes))
        self.split.splitterMoved.connect(self._persist_splitter)
        work.addWidget(self.split, 1)
        root.addLayout(work, 1)
        self._page_content.setMinimumHeight(640)
        # Help overlays from the right — not a permanent layout sibling that compresses canvas.
        self.help_drawer.setParent(self)
        self.help_drawer.hide()
        self.help_drawer.raise_()
        self._install_layout_shortcuts()
        # Restore/migrate layout then ensure authoritative Layers open state (no science I/O).
        QTimer.singleShot(0, self._restore_layout_and_layers)

        ev = getattr(session, "events", None)
        if ev is not None:
            ev.active_mat_changed.connect(self.refresh)
            ev.project_changed.connect(self.refresh)
            ev.frame_changed.connect(self._on_session_frame_changed)
            ev.profile_changed.connect(self.refresh)
            ev.source_detached.connect(self._on_source_detached)
            ev.inventory_changed.connect(self.refresh)
            if hasattr(ev, "cache_rebuilt"):
                ev.cache_rebuilt.connect(self.refresh)

        self.apply_theme("system")
        self.retranslate_ui()
        self.state_label.setText("Подготавливается источник…" if self.i18n.language == "ru" else "Preparing source…")
        # Stagger deferred work across event-loop turns (Phase 4B.2j skeleton).
        QTimer.singleShot(0, self._restore_help_drawer_state)
        # Layout restore/migration runs via _restore_layout_and_layers (single authority).
        # Sequence fields rebuild only when sequence settings are opened.
        QTimer.singleShot(0, self._deferred_first_activate)

    # ----- theme / i18n -----
    def apply_theme(self, preference: str | None = None) -> None:
        self._theme_pref = preference or self._theme_pref or "system"
        theme = resolve_theme_name(self._theme_pref)
        tokens = source_card_tokens(theme)
        self.banner.setStyleSheet(
            f"QLabel#fdShadowBadge {{ padding:3px 8px; border-radius:3px; "
            f"border:1px solid {tokens['warn_border']}; "
            f"background:{tokens['warn_bg']}; color:{tokens['warn_fg']}; font-size:11px; }}"
        )
        self.subtitle.setStyleSheet(f"color:{tokens['text_muted']}; font-size:12px;")
        self.help_drawer.setStyleSheet(
            f"QFrame#fdHelpDrawer {{ padding:8px; border:1px solid {tokens['border']}; "
            f"background:{tokens['bg_alt']}; color:{tokens['text']}; }}"
        )
        self.explain_fd.setStyleSheet(
            f"padding:8px; border:1px solid {tokens['border']}; "
            f"background:{tokens['bg_alt']}; color:{tokens['text']};"
        )
        self.state_label.setStyleSheet(
            f"padding:6px; border:1px solid {tokens['border']}; "
            f"background:{tokens['bg_alt']}; color:{tokens['text']};"
        )
        self.inline_note.setStyleSheet(
            f"padding:6px; border:1px solid {tokens['accent']}; "
            f"background:{tokens['bg']}; color:{tokens['text']};"
        )
        self.source_card.apply_theme(self._theme_pref)
        # Re-apply sequence row markers with theme-safe contrast (embedded defect fix).
        if getattr(self, "seq_table", None) is not None and self._sequence_results:
            for i, r in enumerate(self._sequence_results):
                if i < self.seq_table.rowCount():
                    self._style_sequence_table_row(i, r)
        if self._seq_detach_table is not None and self._sequence_results:
            self._sync_sequence_detach_table()

    def retranslate(self) -> None:
        """Compatibility alias — labels only; never reloads scientific data."""
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        ru = self.i18n.language == "ru"
        self.banner.setText("V2 · теневой режим" if ru else "V2 · shadow mode")
        self.subtitle.setText(
            (
                "Экспериментальное выделение следа, помех, ветвей и ширин. "
                "Тип рассеяния здесь пока не определяется."
            )
            if ru
            else (
                "Experimental trace, interference, branch and width extraction. "
                "Scatter type is not determined here."
            )
        )
        self.btn_help.setText("?" if ru else "?")
        self.btn_help.setToolTip("Справка" if ru else "Help")
        self.help_title.setText("Справка" if ru else "Help")
        self.btn_pin_help.setText("Закрепить" if ru else "Pin")
        self.btn_close_help.setText("×")
        self.btn_open_full_help.setText("Открыть полную справку" if ru else "Open full Help")
        if self._help_body_loaded:
            self.explain_fd.setText(self._fd_explanation())
            if self._shortcuts_help_label is not None:
                self._shortcuts_help_label.setText(format_shortcuts_help("ru" if ru else "en"))
        else:
            self.explain_fd.setText("…" if ru else "…")
        if hasattr(self, "inspector_tabs"):
            self.inspector_tabs.setTabText(0, "Сводка" if ru else "Summary")
            self.inspector_tabs.setTabText(1, "Признаки" if ru else "Features")
            self.inspector_tabs.setTabText(
                2, "Предв. морфология" if ru else "Provisional morphology"
            )
            self.inspector_tabs.setTabText(3, "Проверка геометрии" if ru else "Geometry review")
            self.inspector_tabs.setTabText(4, "Технические сведения" if ru else "Technical details")
        if hasattr(self, "_features_shell_label") and not self._features_tab_built:
            self._features_shell_label.setText(
                "Откройте вкладку, чтобы загрузить список признаков."
                if ru
                else "Open this tab to load the feature list."
            )
        if hasattr(self, "_review_shell_label") and not self._review_tab_built:
            self._review_shell_label.setText(
                "Откройте вкладку, чтобы загрузить форму проверки."
                if ru
                else "Open this tab to load the review form."
            )
        if hasattr(self, "_tech_shell_label") and not self._tech_tab_built:
            self._tech_shell_label.setText(
                "Откройте вкладку, чтобы загрузить технические сведения."
                if ru
                else "Open this tab to load technical details."
            )
        if hasattr(self, "zoom_mode"):
            prev_z = self.zoom_mode.currentData()
            self.zoom_mode.blockSignals(True)
            self.zoom_mode.clear()
            for data, ru_l, en_l in (
                ("fit", "Вписать — баланс", "Fit — balanced"),
                ("natural", "Натуральный", "Natural"),
                ("100", "100%", "100%"),
                ("compact", "Компактный", "Compact"),
                ("large", "Крупный", "Large"),
            ):
                self.zoom_mode.addItem(ru_l if ru else en_l, data)
            zi = max(0, self.zoom_mode.findData(prev_z or "fit"))
            self.zoom_mode.setCurrentIndex(zi)
            self.zoom_mode.blockSignals(False)
        if hasattr(self, "summary_empty"):
            self.summary_empty.setText(
                "V2 для этого кадра не рассчитан. Нажмите «Запустить V2»."
                if ru
                else "V2 is not calculated for this frame. Press “Run V2”."
            )
        self.frame_box.setTitle("Выбор кадра" if ru else "Frame Selection")
        self.mode_label.setText("Режим" if ru else "Mode")
        prev_mode = self.mode_combo.currentData()
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItem("Один кадр" if ru else "Single Frame", "single")
        self.mode_combo.addItem("Последовательность" if ru else "Sequence", "sequence")
        idx = max(0, self.mode_combo.findData(prev_mode or "single"))
        self.mode_combo.setCurrentIndex(idx)
        self.mode_combo.blockSignals(False)
        self.seq_form.setTitle("Выбор последовательности" if ru else "Sequence selection")
        self.btn_sequence_settings.setText("Настроить последовательность" if ru else "Configure sequence")
        self.seq_type_label.setText("Тип выбора" if ru else "Selection type")
        prev_t = self.seq_type.currentData()
        self.seq_type.blockSignals(True)
        self.seq_type.clear()
        for data, ru_l, en_l in (
            ("frame_range", "Диапазон кадров", "Frame range"),
            ("time_range", "Диапазон времени", "Time range"),
            ("every_n_frames", "Каждые N кадров", "Every N frames"),
            ("every_n_minutes", "Каждые N минут", "Every N minutes"),
            ("custom", "Произвольный список", "Custom list"),
        ):
            self.seq_type.addItem(ru_l if ru else en_l, data)
        ti = max(0, self.seq_type.findData(prev_t or "frame_range"))
        self.seq_type.setCurrentIndex(ti)
        self.seq_type.blockSignals(False)
        self.lbl_seq_start.setText("Начальный кадр" if ru else "Start frame")
        self.lbl_seq_end.setText("Конечный кадр" if ru else "End frame")
        self.lbl_seq_step.setText("Шаг" if ru else "Step")
        self.lbl_seq_t0.setText("Начальное время" if ru else "Start time")
        self.lbl_seq_t1.setText("Конечное время" if ru else "End time")
        self.lbl_seq_interval.setText("Интервал, мин" if ru else "Interval in minutes")
        self.lbl_seq_custom.setText("Список кадров" if ru else "Frame list")
        self.btn_contact.setText("Контактный лист…" if ru else "Contact sheet…")
        self.btn_run.setText("Запустить V2 (теневой режим)" if ru else "Run V2 (shadow)")
        self.btn_cancel.setText("Отмена" if ru else "Cancel")
        self.btn_recalc.setText("Пересчитать кадр" if ru else "Recalculate this frame")
        self.btn_clear_cache.setText("Очистить кэш V2 источника" if ru else "Clear V2 cache for source")
        self.btn_layers.setText("Слои" if ru else "Layers")
        self.btn_fit.setText("Вписать" if ru else "Fit")
        self.btn_100.setText("100%")
        self.btn_viewer.setText("Открыть в Viewer" if ru else "Open in Viewer")
        self.btn_export.setText("Экспорт диагностики" if ru else "Export diagnostics")
        self.btn_more.setText("Дополнительно…" if ru else "More…")
        self.btn_use_viewer.setText("Кадр Viewer" if ru else "Use Viewer frame")
        self.btn_send_viewer.setText("В Viewer" if ru else "Send to Viewer")
        self.chk_auto_sync.setText("Синхронизация с Viewer" if ru else "Synchronize with Viewer")
        self.btn_jump_time.setText("Перейти ко времени" if ru else "Jump to time")
        self.opacity_label.setText("Непрозрачность" if ru else "Opacity")
        self.layers_toggle.setText(
            ("▼ " if self.layers_toggle.isChecked() else "▶ ") + ("Слои" if ru else "Layers")
        )
        self.layers_title.setText("Слои" if ru else "Layers")
        self.summary_box.setTitle("Что сделала диагностика" if ru else "What the diagnostics did")
        self.btn_default_layers.setText("Слои по умолчанию" if ru else "Show default layers")
        self.btn_hide_overlays.setText("Скрыть наложения" if ru else "Hide all overlays")
        if self.tech_toggle.isVisible() or self._features_tab_built:
            self.tech_toggle.setText("Технические ID признаков" if ru else "Technical feature IDs")
        self.why_toggle.setText("Почему выполняется расчёт" if ru else "Why the calculation runs")
        # Avoid rewriting large why/help text trees on every language switch unless visible.
        if self.why_body.isVisible():
            self.why_body.setPlainText(self._why_text())
        self.future_box.setTitle(
            "Предварительный кандидат морфологии" if ru else "Provisional morphology candidate"
        )
        self.morph_disclaimer.setText(disclaimer("ru" if ru else "en"))
        self.btn_calc_morph.setText("Рассчитать" if ru else "Calculate")
        self.btn_calc_morph.setToolTip("Рассчитать кандидата" if ru else "Calculate candidate")
        self.btn_recalc_morph.setText("Пересчитать" if ru else "Recalculate")
        self.btn_recalc_morph.setToolTip("Пересчитать кандидата" if ru else "Recalculate candidate")
        self.btn_morph_evidence.setText("Доказательства" if ru else "Evidence")
        self.btn_morph_evidence.setToolTip("Открыть доказательства" if ru else "Open evidence")
        self.btn_morph_review.setText("Проверка" if ru else "Review")
        self.btn_morph_review.setToolTip("Проверить кандидата" if ru else "Review candidate")
        self.btn_recalc_v2_for_morph.setText("Пересчитать V2" if ru else "Recalculate V2")
        self.btn_morph_more.setText("Ещё…" if ru else "More…")
        self.act_morph_provenance.setText(
            "Техническое происхождение" if ru else "Technical provenance"
        )
        self.act_copy_evidence_json.setText(
            "Копировать JSON доказательств" if ru else "Copy evidence JSON"
        )
        self.act_export_evidence_json.setText(
            "Экспорт JSON доказательств" if ru else "Export evidence JSON"
        )
        self.act_copy_frag_gates.setText(
            "Копировать строки фрагментации" if ru else "Copy fragmentation gate rows"
        )
        self.act_clear_morph_cache.setText(
            "Очистить кэш кандидата" if ru else "Clear candidate cache"
        )
        self.act_export_morph_json.setText(
            "Экспорт кандидата JSON" if ru else "Export candidate JSON"
        )
        self.act_open_morph_reviews.setText(
            "Открыть папку проверок" if ru else "Open review folder"
        )
        self.act_geometry_review_overview.setText(
            "Обзор проверок" if ru else "Review corpus overview"
        )
        # Ensure parent page title label is localized (MainWindow title_* widget).
        parent = self.parent()
        while parent is not None:
            title = parent.findChild(QLabel, "title_feature_diagnostics") if hasattr(parent, "findChild") else None
            if title is not None:
                title.setText(
                    "Диагностика следа и геометрии" if ru else "Trace and Geometry Diagnostics"
                )
                break
            parent = parent.parent()
        self.future_label.setText(self._future_morphology_text())
        if self._status_msg is not None:
            text = format_status(self._status_msg, "ru" if ru else "en")
            self._inline_note = text
            self.inline_note.setText(text)
        if self._features_model is not None:
            self._features_model.set_language("ru" if ru else "en")
            self._refill_features_category_combo()
        self._retranslate_features_toolbar()
        if self._features_detach_win is not None:
            try:
                self._features_detach_win.retranslate("ru" if ru else "en")
                self._features_detach_win.setWindowTitle("Признаки" if ru else "Features")
            except RuntimeError:
                self._features_detach_win = None
        if self._seq_detach_win is not None:
            try:
                self._seq_detach_win.retranslate("ru" if ru else "en")
            except RuntimeError:
                self._seq_detach_win = None
                self._seq_detach_table = None
        if self._evidence_dialog is not None and self._morph_result_dict is not None:
            try:
                self._evidence_dialog.bind_result(
                    self._morph_result_dict, "ru" if ru else "en", follow_active=True
                )
            except RuntimeError:
                self._evidence_dialog = None
        # Labels / sequence status only — no V2 or candidate recalculation.
        self._refresh_sequence_frame_state()
        prev_f = self.seq_filter.currentData() if self.seq_filter.count() else None
        self.seq_filter.blockSignals(True)
        self.seq_filter.clear()
        for data, ru_l, en_l in (
            ("all", "Все", "All"),
            ("frequency_spread_candidate", "Частотный кандидат", "Frequency candidate"),
            ("range_spread_candidate", "Высотный кандидат", "Range candidate"),
            ("mixed_spread_candidate", "Смешанный кандидат", "Mixed candidate"),
            ("no_supported_visible_spread", "Без поддерживаемого рассеяния", "No supported spread"),
            ("indeterminate", "Неопределённо", "Indeterminate"),
            ("not_assessable", "Оценка невозможна", "Not assessable"),
            ("high_interference", "Высокие помехи", "High interference"),
            ("unreviewed", "Без проверки", "Unreviewed"),
            ("disagreement", "Расхождение с экспертом", "Candidate/reviewer disagreement"),
        ):
            self.seq_filter.addItem(ru_l if ru else en_l, data)
        fi = max(0, self.seq_filter.findData(prev_f or "all"))
        self.seq_filter.setCurrentIndex(fi)
        self.seq_filter.blockSignals(False)
        if self._review_tab_built:
            self.review_box.setTitle("Проверка геометрии (не морфология)" if ru else "Geometry review (not morphology)")
            prev_rev = self.review_combo.currentData()
            self.review_combo.blockSignals(True)
            self.review_combo.clear()
            for token, ru_l, en_l in (
                ("acceptable", "приемлемо", "acceptable"),
                ("unacceptable", "неприемлемо", "unacceptable"),
                ("uncertain", "неуверенно", "uncertain"),
            ):
                self.review_combo.addItem(ru_l if ru else en_l, token)
            ri = max(0, self.review_combo.findData(prev_rev or "acceptable"))
            self.review_combo.setCurrentIndex(ri)
            self.review_combo.blockSignals(False)
            self.btn_save_review.setText("Сохранить отзыв" if ru else "Save review")
        self.view_preset.blockSignals(True)
        self.view_preset.clear()
        for data, ru_l, en_l in (
            ("source", "Исходная ионограмма", "Source ionogram"),
            ("trace", "След и осевая линия", "Trace and centerline"),
            ("interference", "Помехи", "Interference"),
            ("widths", "Ширины", "Widths"),
            ("all", "Все диагностические слои", "All diagnostic layers"),
        ):
            self.view_preset.addItem(ru_l if ru else en_l, data)
        self.view_preset.blockSignals(False)
        self.base_view.blockSignals(True)
        self.base_view.clear()
        self.base_view.addItem("Viewer (цвет)" if ru else "Viewer-equivalent color", "jet")
        self.base_view.addItem("Сырой оттенки серого" if ru else "Raw grayscale", "gray")
        self.base_view.addItem("Нормализованный диагн." if ru else "Diagnostic normalized", "norm")
        self.base_view.blockSignals(False)
        labels = sequence_header_labels("ru" if ru else "en")
        self.seq_table.setHorizontalHeaderLabels(labels)
        if self._seq_detach_table is not None:
            self._seq_detach_table.setHorizontalHeaderLabels(labels)
        copy = empty_state_copy(self.i18n.language)
        self.btn_open_projects.setText(copy["open_projects"])
        self.btn_open_import.setText(copy["open_import"])
        self.btn_choose_mat.setText(copy["choose_mat"])
        self.btn_pick_project.setText(copy["pick_from_project"])
        self.btn_refresh_state.setText(copy["refresh"])
        if self._layers_built:
            for key, ru_lab, en_lab, _ in self.LAYER_KEYS:
                self._layer_checks[key].setText(ru_lab if ru else en_lab)
                self._layer_checks[key].setToolTip(ru_lab if ru else en_lab)
        self.source_card.retranslate()
        # Do not rebuild sequence fields / mode widgets on language switch.
        if self._result_ser or self._result:
            self._populate_summary_from_ser()
            if self._features_populated:
                self._populate_features()
        if hasattr(self, "_quick_layer_btns"):
            for key, ru_l, en_l in self.QUICK_LAYER_KEYS:
                btn = self._quick_layer_btns.get(key)
                if btn is not None:
                    btn.setText(ru_l if ru else en_l)
                    btn.setToolTip(ru_l if ru else en_l)
        # Intentionally NO refresh() / frame load / cache I/O / EXE hash here.

    def _fd_explanation(self) -> str:
        if self.i18n.language == "ru":
            return (
                "Диагностика признаков пока не определяет окончательный тип рассеяния.\n"
                "Она измеряет исходный кадр:\n"
                "— отделяет возможный след от помех;\n"
                "— определяет ветви и осевые линии;\n"
                "— измеряет ширину по осям частоты и высоты;\n"
                "— отмечает неопределённые и исключённые области;\n"
                "— оценивает пригодность измерений.\n"
                "Эти экспериментальные измерения не участвуют в текущем автоанализе.\n"
                "После проверки геометрии они будут использованы на следующем научном этапе "
                "для формирования кандидатов частотного, высотного и смешанного рассеяния."
            )
        return (
            "Feature Diagnostics does not yet determine a final scatter type.\n"
            "It measures the source frame:\n"
            "— separates a possible trace from interference;\n"
            "— finds branches and centerlines;\n"
            "— measures width along frequency and height axes;\n"
            "— marks uncertain and excluded regions;\n"
            "— assesses measurement suitability.\n"
            "These experimental measurements do not participate in current auto-analysis.\n"
            "After geometry review they will be used in a later scientific stage to form "
            "candidates for frequency, range, and mixed scatter."
        )

    def _future_morphology_text(self) -> str:
        if self.i18n.language == "ru":
            return (
                "Кандидат не запускается автоматически при открытии диагностики.\n"
                "Сначала нужен кэш/результат геометрии V2, затем «Рассчитать кандидата».\n"
                "Геометрия V2 и морфологический кандидат имеют раздельные состояния."
            )
        return (
            "Candidate does not auto-run when opening Diagnostics.\n"
            "Requires cached/available V2 geometry, then Calculate candidate.\n"
            "V2 geometry and morphology candidate have visibly separate states."
        )

    def _why_text(self) -> str:
        ru = self.i18n.language == "ru"
        if ru:
            return (
                "Кэш Viewer обеспечивает кадр/отрисовку.\n"
                "V2 отдельно вычисляет маски, осевые линии, геометрию ветвей, помехи и ширины.\n"
                "Первый запуск может занять больше времени.\n"
                "Повтор идентичного запуска может загрузиться из кэша V2.\n"
                "Смена профиля, версии признаков или параметров делает кэш недействительным.\n"
                "Цвет отображения не изменяет числовой анализ."
            )
        return (
            "The Viewer cache provides the frame/rendering.\n"
            "V2 separately computes masks, centerlines, branch geometry, interference and widths.\n"
            "The first run may take longer.\n"
            "Repeated identical runs may load from the V2 cache.\n"
            "Changing profile, feature version or parameters invalidates the cached result.\n"
            "Display color does not change the numeric analysis."
        )

    # ----- layout helpers -----
    def _settings_get(self, key: str, default=None):
        if self._settings is None:
            return default
        try:
            return self._settings.get("ux", key, default)
        except Exception:
            return default

    def _settings_set(self, key: str, value) -> None:
        if self._settings is None:
            return
        try:
            self._settings.set("ux", key, value)
            self._settings.save()
        except Exception:
            pass

    def _restore_help_drawer_state(self) -> None:
        pinned = bool(self._settings_get("fd_help_drawer_pinned", False))
        self.btn_pin_help.setChecked(pinned)
        first_seen = bool(self._settings_get("fd_help_expanded_once", False))
        open_saved = bool(self._settings_get("fd_help_drawer_open", False))
        if not first_seen:
            self._settings_set("fd_help_expanded_once", True)
            self._set_help_drawer_visible(True, persist=True)
        else:
            self._set_help_drawer_visible(open_saved or pinned, persist=False)
        width = int(self._settings_get("fd_help_drawer_width", 360) or 360)
        self.help_drawer.setMaximumWidth(max(260, min(720, width)))

    def _toggle_help_drawer(self) -> None:
        self._set_help_drawer_visible(not self.help_drawer.isVisible(), persist=True)

    def _ensure_help_body(self) -> None:
        if self._help_body_loaded:
            return
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.build_help_body"):
            self.explain_fd.setText(self._fd_explanation())
            lang = "ru" if self.i18n.language == "ru" else "en"
            if self._shortcuts_help_label is not None:
                self._shortcuts_help_label.setText(format_shortcuts_help(lang))
            self._help_body_loaded = True

    def _ensure_features_tab(self) -> None:
        if self._features_tab_built:
            return
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.features_tab.activate"):
            with span_timer("fd.build_features_tab"):
                self._features_shell_label.hide()
                self._features_identity_label = QLabel()
                self._features_identity_label.setWordWrap(True)
                self._features_identity_label.setObjectName("fdFeaturesIdentity")
                self._features_host.addWidget(self._features_identity_label)
                self._features_empty_label = QLabel()
                self._features_empty_label.setWordWrap(True)
                self._features_empty_label.setObjectName("fdFeaturesEmpty")
                self._features_empty_label.hide()
                self._features_host.addWidget(self._features_empty_label)
                toolbar = QHBoxLayout()
                self._features_cat = QComboBox()
                self._features_search = QLineEdit()
                self._features_search.setClearButtonEnabled(True)
                toolbar.addWidget(self._features_cat, 1)
                toolbar.addWidget(self._features_search, 2)
                # Primary compact action — short label + tooltip (no mid-word ellipsis)
                self._btn_detach_features = QToolButton()
                self._btn_detach_features.clicked.connect(self._open_features_detach)
                toolbar.addWidget(self._btn_detach_features)
                self._btn_features_more = QToolButton()
                self._btn_features_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                self._features_more_menu = QMenu(self)
                self._act_detach_features = self._features_more_menu.addAction("")
                self._act_detach_features.triggered.connect(self._open_features_detach)
                self._btn_features_expand = QToolButton()
                self._btn_features_expand.hide()  # secondary — live in overflow
                self._act_features_expand = self._features_more_menu.addAction("")
                self._act_features_expand.triggered.connect(self._expand_features_table)
                self._btn_features_collapse_explain = QToolButton()
                self._btn_features_collapse_explain.hide()
                self._act_features_collapse = self._features_more_menu.addAction("")
                self._act_features_collapse.triggered.connect(self._collapse_features_explain)
                self._btn_features_reset_layout = QToolButton()
                self._btn_features_reset_layout.hide()
                self._act_features_reset = self._features_more_menu.addAction("")
                self._act_features_reset.triggered.connect(self._reset_features_layout)
                self._act_features_tech = self._features_more_menu.addAction("")
                self._act_features_tech.setCheckable(True)
                self._act_features_tech.toggled.connect(self._on_features_tech_menu)
                self._act_features_copy = self._features_more_menu.addAction("")
                self._act_features_copy.triggered.connect(self._copy_selected_feature)
                self._act_features_export = self._features_more_menu.addAction("")
                self._act_features_export.triggered.connect(self._export_features_table)
                self._btn_features_more.setMenu(self._features_more_menu)
                toolbar.addWidget(self._btn_features_more)
                self._features_host.addLayout(toolbar)

                self._features_model = FeaturesTableModel(self)
                self._features_proxy = FeaturesFilterProxy(self)
                self._features_proxy.setSourceModel(self._features_model)
                self._features_view = QTableView()
                self._features_view.setModel(self._features_proxy)
                self._features_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
                self._features_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
                self._features_view.setSortingEnabled(True)
                self._features_view.verticalHeader().setVisible(False)
                self._features_view.setAlternatingRowColors(True)
                self._features_view.setWordWrap(False)
                self._features_view.setTextElideMode(Qt.TextElideMode.ElideRight)

                top = QWidget()
                tl = QVBoxLayout(top)
                tl.setContentsMargins(0, 0, 0, 0)
                tl.addWidget(self._features_view, 1)

                bottom = QWidget()
                bl = QVBoxLayout(bottom)
                bl.setContentsMargins(0, 0, 0, 0)
                bl.addWidget(self.explain, 1)
                bl.addWidget(self.tech_toggle)

                self._features_splitter = QSplitter(Qt.Orientation.Vertical)
                self._features_splitter.setChildrenCollapsible(True)
                self._features_splitter.addWidget(top)
                self._features_splitter.addWidget(bottom)
                self._features_splitter.setStretchFactor(0, 7)
                self._features_splitter.setStretchFactor(1, 3)
                self._features_splitter.setSizes([360, 160])
                self._features_splitter.splitterMoved.connect(self._persist_features_splitter)
                self._features_host.addWidget(self._features_splitter, 1)

                self.explain.setHidden(False)
                self.tech_toggle.setHidden(False)
                self._features_view.selectionModel().currentChanged.connect(self._on_feature_row)
                self.tech_toggle.toggled.connect(self._on_tech_toggle)
                self._features_cat.currentIndexChanged.connect(self._on_features_filter)
                self._features_search.textChanged.connect(self._on_features_filter)
                self._retranslate_features_toolbar()
                self._refill_features_category_combo()
                self._restore_features_splitter()
                self._features_tab_built = True
                self._update_features_identity_line()
                self._update_features_empty_state()

    def _ensure_review_tab(self) -> None:
        if self._review_tab_built:
            return
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.build_review_tab"):
            self._review_shell_label.hide()
            rb = QFormLayout(self.review_box)
            rb.addRow(self.review_combo)
            rb.addRow(self.review_comment)
            rb.addRow(self.btn_save_review)
            self._review_host.addWidget(self.review_box)
            self._review_host.addStretch(1)
            self.review_box.show()
            self.btn_save_review.clicked.connect(self._save_geometry_review)
            ru = self.i18n.language == "ru"
            self.review_box.setTitle("Проверка геометрии (не морфология)" if ru else "Geometry review (not morphology)")
            self.review_combo.clear()
            for token, ru_l, en_l in (
                ("acceptable", "приемлемо", "acceptable"),
                ("unacceptable", "неприемлемо", "unacceptable"),
                ("uncertain", "неуверенно", "uncertain"),
            ):
                self.review_combo.addItem(ru_l if ru else en_l, token)
            self.btn_save_review.setText("Сохранить отзыв" if ru else "Save review")
            self._review_tab_built = True

    def _ensure_tech_tab(self) -> None:
        if self._tech_tab_built:
            return
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.build_tech_tab"):
            self._tech_shell_label.hide()
            self._tech_host.addWidget(self.tech_details, 1)
            self.tech_details.show()
            self._tech_tab_built = True

    def _set_help_drawer_visible(self, visible: bool, *, persist: bool) -> None:
        # Overlay from the right — does not permanently resize the main splitter.
        if visible:
            self._ensure_help_body()
            self._position_help_overlay()
            self.help_drawer.show()
            self.help_drawer.raise_()
        else:
            self.help_drawer.hide()
        if persist:
            self._settings_set("fd_help_drawer_open", bool(visible))

    def _position_help_overlay(self) -> None:
        w = int(self._settings_get("fd_help_drawer_width", 360) or 360)
        w = max(260, min(420, w))
        h = max(200, self.height() - 8)
        self.help_drawer.setFixedWidth(w)
        self.help_drawer.setGeometry(max(0, self.width() - w - 4), 4, w, h)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.help_drawer.isVisible():
            self._position_help_overlay()
        self._apply_responsive_layout()
        self._update_features_action_visibility()
        if self._zoom == 0.0 and self._raw is not None:
            self._render_view()

    def _apply_responsive_layout(self) -> None:
        """Narrow windows: keep primary controls; stack inspector below when needed."""
        narrow = self.width() < 1100
        if hasattr(self, "split") and self.split.count() >= 3:
            if narrow:
                # Prefer readable inspector — vertical-ish sizes via stretch
                self.split.setOrientation(Qt.Orientation.Vertical)
            else:
                self.split.setOrientation(Qt.Orientation.Horizontal)
        if hasattr(self, "quick_layers"):
            self.quick_layers.setVisible(True)
        self._update_shortcuts_help_button()

    def _on_help_pin_toggled(self, pinned: bool) -> None:
        self._settings_set("fd_help_drawer_pinned", bool(pinned))
        if pinned:
            self._set_help_drawer_visible(True, persist=True)

    def _toggle_source_card(self, checked: bool) -> None:
        self.source_card.setVisible(checked)

    def _ensure_layer_checks(self) -> None:
        """Build expert layer checkboxes once (deferred from page construction)."""
        if self._layers_built:
            return
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.build_layer_drawer"):
            lp = self._layers_panel_layout
            for key, _ru, _en, _rgba in self.LAYER_KEYS:
                cb = QCheckBox(key)
                cb.setChecked(key in self.DEFAULT_LAYERS)
                cb.stateChanged.connect(self._on_layer_toggled)
                self._layer_checks[key] = cb
                lp.addWidget(cb)
            lp.addWidget(self.legend)
            lp.addWidget(self.btn_default_layers)
            lp.addWidget(self.btn_hide_overlays)
            lp.addStretch(1)
            self._layers_built = True
            self._sync_quick_layers_from_checks()
            # Apply current language labels
            ru = self.i18n.language == "ru"
            for key, ru_lab, en_lab, _ in self.LAYER_KEYS:
                self._layer_checks[key].setText(ru_lab if ru else en_lab)

    def _toggle_layers(self, checked: bool) -> None:
        """Authoritative Layers open/closed: left splitter pane content visibility."""
        if checked:
            self._ensure_layer_checks()
            self.layers_panel.setVisible(True)
            # Restore a practical Layers width if the left pane was collapsed.
            sizes = list(self.split.sizes()) if self.split.count() >= 3 else []
            if sizes and sizes[0] < 120:
                total = sum(sizes) or sum(self._preferred_h_sizes)
                left = max(140, int(self._layers_saved_width or self._preferred_h_sizes[0]))
                rest = max(1, total - left)
                mid = int(rest * 0.65)
                self.split.setSizes([left, mid, max(280, rest - mid)])
        else:
            sizes = list(self.split.sizes()) if self.split.count() >= 3 else []
            if sizes and sizes[0] >= 120:
                self._layers_saved_width = int(sizes[0])
            self.layers_panel.setVisible(False)
        self.btn_layers.blockSignals(True)
        self.btn_layers.setChecked(checked)
        self.btn_layers.blockSignals(False)
        ru = self.i18n.language == "ru"
        self.layers_toggle.setText(("▼ " if checked else "▶ ") + ("Слои" if ru else "Layers"))

    def _set_layers_drawer_visible(self, checked: bool) -> None:
        self.layers_toggle.blockSignals(True)
        self.layers_toggle.setChecked(checked)
        self.layers_toggle.blockSignals(False)
        self._toggle_layers(checked)
        self._settings_set("fd_layers_drawer_open", bool(checked))

    def _open_sequence_settings(self) -> None:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.build_sequence_drawer"):
            self._rebuild_seq_fields()
            self.seq_form.setVisible(not self.seq_form.isVisible())
            self._settings_set("fd_sequence_drawer_open", self.seq_form.isVisible())
            self._on_mode_changed()

    def _persist_splitter(self, *_args) -> None:
        if self._settings is None:
            return
        states = dict(self._settings.get("general", "splitter_states", {}) or {})
        states["feature_diagnostics"] = bytes(self.split.saveState().toBase64()).decode("ascii")
        if self._mid_vsplit is not None:
            states["feature_diagnostics_mid_v"] = bytes(
                self._mid_vsplit.saveState().toBase64()
            ).decode("ascii")
        self._settings.set("general", "splitter_states", states)
        try:
            self._settings.save()
        except Exception:
            pass

    def _persist_mid_vsplit(self, *_args) -> None:
        if self._mid_vsplit is not None:
            self._saved_seq_split_sizes = list(self._mid_vsplit.sizes())
        self._persist_splitter()

    def _persist_features_splitter(self, *_args) -> None:
        if self._features_splitter is None:
            return
        self._settings_set(
            "fd_features_splitter",
            bytes(self._features_splitter.saveState().toBase64()).decode("ascii"),
        )

    def _restore_features_splitter(self) -> None:
        if self._features_splitter is None:
            return
        raw = self._settings_get("fd_features_splitter", "")
        if not raw:
            return
        try:
            self._features_splitter.restoreState(QByteArray.fromBase64(str(raw).encode("ascii")))
        except Exception:
            pass

    def _apply_preferred_layout_defaults(self) -> None:
        """Apply Layers|Canvas|Inspector ~15/55/30 and balanced internal splitters."""
        if self.split.orientation() != Qt.Orientation.Horizontal:
            self.split.setOrientation(Qt.Orientation.Horizontal)
        self.split.setSizes(list(self._preferred_h_sizes))
        self._layers_saved_width = int(self._preferred_h_sizes[0])
        if self._mid_vsplit is not None:
            self._mid_vsplit.setSizes(list(self._preferred_mid_sizes))
            self._saved_seq_split_sizes = list(self._preferred_mid_sizes)
        if self._features_splitter is not None:
            self._features_splitter.setSizes(list(self._preferred_features_sizes))
            self._collapse_state["features_explain"] = False

    def _migrate_layout_schema_if_needed(self) -> bool:
        """One-shot migrate from pre-4C.1e (schema < 2) collapsed-Layers defaults.

        Returns True when migration applied (caller should skip restoring old state).
        """
        ver = int(self._settings_get("fd_layout_schema_version", 0) or 0)
        if ver >= FD_LAYOUT_SCHEMA_VERSION:
            return False
        self._apply_preferred_layout_defaults()
        self._settings_set("fd_layout_schema_version", FD_LAYOUT_SCHEMA_VERSION)
        self._settings_set("fd_layers_drawer_open", True)
        # Drop obsolete collapsed-layers splitter blobs from 4C.1d.
        if self._settings is not None:
            try:
                states = dict(self._settings.get("general", "splitter_states", {}) or {})
                states.pop("feature_diagnostics", None)
                states.pop("feature_diagnostics_mid_v", None)
                self._settings.set("general", "splitter_states", states)
                self._settings.save()
            except Exception:
                pass
        self._persist_splitter()
        return True

    def _restore_splitter(self) -> None:
        """Restore persisted splitter sizes when layout schema is current."""
        if self._migrate_layout_schema_if_needed():
            return
        if self._settings is None:
            return
        states = self._settings.get("general", "splitter_states", {}) or {}
        raw = states.get("feature_diagnostics")
        if raw:
            try:
                self.split.restoreState(QByteArray.fromBase64(raw.encode("ascii")))
            except Exception:
                self._apply_preferred_layout_defaults()
        else:
            # No saved state — keep constructor preferred sizes.
            pass
        raw_v = states.get("feature_diagnostics_mid_v")
        if raw_v and self._mid_vsplit is not None:
            try:
                self._mid_vsplit.restoreState(QByteArray.fromBase64(str(raw_v).encode("ascii")))
                self._saved_seq_split_sizes = list(self._mid_vsplit.sizes())
            except Exception:
                pass

    def _restore_layout_and_layers(self) -> None:
        """Single deferred authority for splitter restore + Layers open state."""
        self._restore_splitter()
        open_layers = bool(self._settings_get("fd_layers_drawer_open", True))
        self._set_layers_drawer_visible(open_layers)

    def _reset_diagnostics_layout(self) -> None:
        """Restore preferred Layers|Canvas|Inspector ratios — no science I/O."""
        self._apply_preferred_layout_defaults()
        self._settings_set("fd_layout_schema_version", FD_LAYOUT_SCHEMA_VERSION)
        self._set_layers_drawer_visible(True)
        self._reset_features_layout()
        self._persist_splitter()
        self._persist_features_splitter()

    def _update_shortcuts_help_button(self) -> None:
        """Readable Commands/Shortcuts control — never an ambiguous empty glyph."""
        if self._btn_shortcuts_help is None:
            return
        ru = self.i18n.language == "ru"
        tip = (
            "Быстрые команды и горячие клавиши"
            if ru
            else "Keyboard shortcuts and quick commands"
        )
        name = "Быстрые команды" if ru else "Keyboard shortcuts"
        self._btn_shortcuts_help.setToolTip(tip)
        self._btn_shortcuts_help.setAccessibleName(name)
        help_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton)
        very_narrow = self.width() < 900
        if very_narrow:
            self._btn_shortcuts_help.setIcon(help_icon)
            self._btn_shortcuts_help.setText("")
            self._btn_shortcuts_help.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        else:
            self._btn_shortcuts_help.setIcon(help_icon)
            self._btn_shortcuts_help.setText("Команды" if ru else "Shortcuts")
            self._btn_shortcuts_help.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )

    def _open_shortcuts_help(self) -> None:
        """Compact entry point — opens Help drawer on Keyboard shortcuts (no science)."""
        self._ensure_help_body()
        lang = "ru" if self.i18n.language == "ru" else "en"
        if self._shortcuts_help_label is not None:
            self._shortcuts_help_label.setText(format_shortcuts_help(lang))
            self._shortcuts_help_label.show()
        self._set_help_drawer_visible(True, persist=True)
        if self._shortcuts_help_label is not None:
            self._shortcuts_help_label.setFocus(Qt.FocusReason.OtherFocusReason)

    def _install_layout_shortcuts(self) -> None:
        # Persist on self so shortcuts are not garbage-collected; child-focus aware.
        ctx = Qt.ShortcutContext.WidgetWithChildrenShortcut
        self._sc_detach_features = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        self._sc_detach_features.setContext(ctx)
        self._sc_detach_features.activated.connect(self._open_features_detach)
        self._sc_detach_sequence = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        self._sc_detach_sequence.setContext(ctx)
        self._sc_detach_sequence.activated.connect(self._open_sequence_detach)
        self._sc_reset_layout = QShortcut(QKeySequence("Ctrl+0"), self)
        self._sc_reset_layout.setContext(ctx)
        self._sc_reset_layout.activated.connect(self._reset_diagnostics_layout)

    def _retranslate_features_toolbar(self) -> None:
        ru = self.i18n.language == "ru"
        detach_full = "Открыть таблицу отдельно" if ru else "Open table in separate window"
        if self._btn_detach_features is not None:
            # Short primary label — full text in tooltip (never mid-word ellipsis)
            self._btn_detach_features.setText("Отдельно" if ru else "Open")
            self._btn_detach_features.setToolTip(detach_full)
        if self._btn_features_more is not None:
            self._btn_features_more.setText("⋯")
            self._btn_features_more.setToolTip("Ещё…" if ru else "More…")
        if self._act_detach_features is not None:
            self._act_detach_features.setText(detach_full)
        expand_t = "Развернуть таблицу" if ru else "Expand table"
        collapse_t = "Свернуть объяснение" if ru else "Collapse explanation"
        reset_t = "Сбросить расположение признаков" if ru else "Reset feature layout"
        tech_t = "Показать технические ID" if ru else "Show technical IDs"
        copy_t = "Скопировать выбранный признак" if ru else "Copy selected feature"
        export_t = "Экспортировать признаки" if ru else "Export features"
        if self._act_features_expand is not None:
            self._act_features_expand.setText(expand_t)
        if self._act_features_collapse is not None:
            self._act_features_collapse.setText(collapse_t)
        if self._act_features_reset is not None:
            self._act_features_reset.setText(reset_t)
        if self._act_features_tech is not None:
            self._act_features_tech.setText(tech_t)
            if self.tech_toggle is not None:
                self._act_features_tech.blockSignals(True)
                self._act_features_tech.setChecked(self.tech_toggle.isChecked())
                self._act_features_tech.blockSignals(False)
        if self._act_features_copy is not None:
            self._act_features_copy.setText(copy_t)
        if self._act_features_export is not None:
            self._act_features_export.setText(export_t)
        if self._btn_features_expand is not None:
            self._btn_features_expand.setText(expand_t)
        if self._btn_features_collapse_explain is not None:
            self._btn_features_collapse_explain.setText(collapse_t)
        if self._btn_features_reset_layout is not None:
            self._btn_features_reset_layout.setText(reset_t)
        if self.tech_toggle is not None and self._features_tab_built:
            self.tech_toggle.setText("Технические ID признаков" if ru else "Technical feature IDs")
        if self._features_search is not None:
            self._features_search.setPlaceholderText("Поиск…" if ru else "Search…")
        if self._btn_reset_layout is not None:
            self._btn_reset_layout.setText("Сброс" if ru else "Reset")
            self._btn_reset_layout.setToolTip(
                "Сбросить расположение Diagnostics" if ru else "Reset Diagnostics layout"
            )
        self._update_shortcuts_help_button()
        if self._btn_show_seq_table is not None:
            self._btn_show_seq_table.setText("Таблица" if ru else "Results")
            self._btn_show_seq_table.setToolTip(
                "Показать таблицу результатов" if ru else "Show results table"
            )
        if self._chk_seq_follow is not None:
            self._chk_seq_follow.setText(
                "Следовать за обработкой" if ru else "Follow processing"
            )
        if self._btn_resume_follow is not None:
            self._btn_resume_follow.setText(
                "Возобновить следование" if ru else "Resume follow"
            )
        if self._btn_show_latest_seq is not None:
            self._btn_show_latest_seq.setText(
                "Последний кадр" if ru else "Latest frame"
            )
            self._btn_show_latest_seq.setToolTip(
                "Показать последний обработанный кадр"
                if ru
                else "Show the latest processed frame"
            )
        self._update_sequence_follow_ui()
        self._update_features_identity_line()
        self._update_features_empty_state()
        self._update_sequence_progress_status()
        if self._btn_detach_seq is not None:
            self._btn_detach_seq.setText("Отдельно" if ru else "Open")
            self._btn_detach_seq.setToolTip(
                "Открыть результаты отдельно" if ru else "Open results in separate window"
            )
        if getattr(self, "_btn_seq_fit_cols", None) is not None:
            self._btn_seq_fit_cols.setText("Столбцы" if ru else "Columns")
            prof = profile_label(self._seq_table_profile, "ru" if ru else "en")
            self._btn_seq_fit_cols.setToolTip(
                (
                    f"Видимость и ширина столбцов · сейчас: {prof}"
                    if ru
                    else f"Column visibility and widths · current: {prof}"
                )
            )
        self._update_features_action_visibility()

    def _features_identity(self) -> dict:
        ser = self._result_ser or (self._result.to_serializable() if self._result else {}) or {}
        snap = resolve_active_source(self.session, force_rebuild=False)
        return {
            "source_sha256": self._source_sha or ser.get("source_mat_sha256") or "",
            "mat_filename": str(snap.mat_filename or ""),
            "frame_index": int(self._authoritative_frame()),
            "interpreted_time": self.time_edit.text() if hasattr(self, "time_edit") else "",
            "diagnostics_cache_id": str(ser.get("diagnostics_cache_id") or ""),
            "feature_version": str(ser.get("feature_version") or FEATURE_VERSION),
        }

    def _update_features_action_visibility(self) -> None:
        """At narrow inspector widths, keep only filter/search/More primary (no clipped labels)."""
        if self._btn_detach_features is None:
            return
        # Prefer showing Open when inspector ≥ ~360 px; otherwise overflow only.
        wide = True
        try:
            if self.split.count() >= 3:
                wide = self.split.sizes()[2] >= 360
        except Exception:
            wide = True
        self._btn_detach_features.setVisible(wide)
        if self._act_detach_features is not None:
            self._act_detach_features.setVisible(True)

    def _on_features_tech_menu(self, checked: bool) -> None:
        if self.tech_toggle is not None:
            self.tech_toggle.setChecked(checked)

    def _copy_selected_feature(self) -> None:
        if self._features_model is None or self._features_proxy is None or self._features_view is None:
            return
        idx = self._features_view.currentIndex()
        if not idx.isValid():
            return
        src = self._features_proxy.mapToSource(idx)
        fid = self._features_model.feature_id_at(src.row())
        if not fid:
            return
        ser = self._result_ser or (self._result.to_serializable() if self._result else {}) or {}
        feat = (ser.get("features") or {}).get(fid) or {}
        QApplication.clipboard().setText(
            json.dumps({"feature_id": fid, **feat}, ensure_ascii=False, indent=2, default=str)
        )

    def _export_features_table(self) -> None:
        if self._features_model is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export features" if self.i18n.language != "ru" else "Экспорт признаков",
            "features.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = []
        for r in range(self._features_model.rowCount()):
            cols = []
            for c in range(self._features_model.columnCount()):
                val = self._features_model.data(
                    self._features_model.index(r, c), Qt.ItemDataRole.DisplayRole
                )
                cols.append(str(val or "").replace(",", ";"))
            rows.append(",".join(cols))
        Path(path).write_text("\n".join(rows), encoding="utf-8")

    def _show_sequence_results_table(self) -> None:
        """Scroll/expand to the sequence results pane (does not open a detached window)."""
        if self.mode_combo.currentData() != "sequence":
            return
        self._set_sequence_pane_visible(True)
        self._ensure_sequence_table_visible()
        if self._outer_scroll is not None and self._seq_pane is not None:
            self._outer_scroll.ensureWidgetVisible(self._seq_pane, 20, 20)

    def _ensure_sequence_table_visible(self) -> None:
        if self._mid_vsplit is None or self._seq_pane is None or not self._seq_pane.isVisible():
            return
        sizes = list(self._mid_vsplit.sizes())
        total = sum(sizes) or 620
        if len(sizes) < 2 or sizes[1] < 140:
            self._mid_vsplit.setSizes([max(200, total - 180), 180])
            self._saved_seq_split_sizes = list(self._mid_vsplit.sizes())

    def _expand_features_table(self) -> None:
        if self._features_splitter is None:
            return
        total = sum(self._features_splitter.sizes()) or 520
        self._features_splitter.setSizes([max(200, total - 40), 40])

    def _collapse_features_explain(self) -> None:
        if self._features_splitter is None:
            return
        total = sum(self._features_splitter.sizes()) or 520
        self._features_splitter.setSizes([total, 0])
        self._collapse_state["features_explain"] = True

    def _reset_features_layout(self) -> None:
        if self._features_splitter is None:
            return
        self._features_splitter.setSizes(list(self._preferred_features_sizes))
        self._collapse_state["features_explain"] = False
        self._persist_features_splitter()

    def _open_features_detach(self) -> None:
        self._ensure_features_tab()
        if self._features_model is None or self._features_proxy is None:
            return
        lang = "ru" if self.i18n.language == "ru" else "en"
        if self._features_detach_win is not None:
            try:
                self._features_detach_win.raise_()
                self._features_detach_win.activateWindow()
                return
            except RuntimeError:
                self._features_detach_win = None
        win = DetachableTableWindow(
            kind="features",
            title="Признаки" if lang == "ru" else "Features",
            parent=self.window(),
            settings_get=self._settings_get,
            settings_set=self._settings_set,
        )
        body = QWidget()
        lay = QVBoxLayout(body)
        filt = QHBoxLayout()
        cat = QComboBox()
        search = QLineEdit()
        search.setClearButtonEnabled(True)
        for data, label in feature_group_filter_items(lang):
            cat.addItem(label, data)
        filt.addWidget(cat, 1)
        filt.addWidget(search, 2)
        lay.addLayout(filt)
        view = QTableView()
        view.setModel(self._features_proxy)
        view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        view.setSortingEnabled(True)
        view.verticalHeader().setVisible(False)
        lay.addWidget(view, 2)
        explain = QTextEdit()
        explain.setReadOnly(True)
        lay.addWidget(explain, 1)

        def _on_sel(cur, _prev) -> None:
            if not cur.isValid() or self._features_model is None:
                return
            src = self._features_proxy.mapToSource(cur)
            fid = self._features_model.feature_id_at(src.row())
            if not fid:
                return
            # Reuse page selection handler text into detach explain
            self._features_view.setCurrentIndex(
                self._features_proxy.mapFromSource(self._features_model.index(src.row(), 0))
            ) if self._features_view is not None else None
            explain.setPlainText(self.explain.toPlainText())

        view.selectionModel().currentChanged.connect(_on_sel)
        cat.currentIndexChanged.connect(
            lambda *_: (
                self._features_proxy.set_category(str(cat.currentData() or "all")),
                self._features_cat.setCurrentIndex(self._features_cat.findData(cat.currentData()))
                if self._features_cat is not None
                else None,
            )
        )
        search.textChanged.connect(
            lambda t: (
                self._features_proxy.set_search(t),
                self._features_search.setText(t) if self._features_search is not None else None,
            )
        )
        win.set_body_widget(body)
        win.set_identity(self._features_identity(), lang)
        win.retranslate(lang)
        win.closed.connect(lambda: setattr(self, "_features_detach_win", None))
        self._features_detach_win = win
        win.show()

    def _sync_features_detach_on_frame(self) -> None:
        win = self._features_detach_win
        if win is None:
            return
        lang = "ru" if self.i18n.language == "ru" else "en"
        ident = self._features_identity()
        if win.pinned or not win.follow_active:
            win.mark_stale(
                lang,
                (
                    f"Это окно закреплено на кадре {win._identity.get('frame_index')} и не следует за текущим."
                    if lang == "ru"
                    else f"This window is pinned to frame {win._identity.get('frame_index')} and does not follow the current frame."
                ),
            )
            return
        win.clear_stale()
        win.set_identity(ident, lang)
        # Model already refreshed by _populate_features when tab/data updates

    def _open_sequence_detach(self) -> None:
        if self.mode_combo.currentData() != "sequence":
            return
        lang = "ru" if self.i18n.language == "ru" else "en"
        if self._seq_detach_win is not None:
            try:
                self._seq_detach_win.raise_()
                self._seq_detach_win.activateWindow()
                return
            except RuntimeError:
                self._seq_detach_win = None
        win = DetachableTableWindow(
            kind="sequence",
            title="Результаты последовательности" if lang == "ru" else "Sequence results",
            parent=self.window(),
            settings_get=self._settings_get,
            settings_set=self._settings_set,
        )
        body = QWidget()
        lay = QVBoxLayout(body)
        table = QTableWidget(0, self.seq_table.columnCount())
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(False)
        table.setTextElideMode(Qt.TextElideMode.ElideRight)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(
            max(24, QFontMetrics(table.font()).height() + 10)
        )
        th = table.horizontalHeader()
        th.setStretchLastSection(False)
        th.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        th.setMinimumSectionSize(36)
        table.setHorizontalHeaderLabels(
            sequence_header_labels("ru" if self.i18n.language == "ru" else "en")
        )
        table.setSortingEnabled(True)
        table.cellDoubleClicked.connect(lambda r, c: self._open_sequence_row(r, c))
        lay.addWidget(table, 1)
        btn_open = QPushButton("Открыть выбранный кадр" if lang == "ru" else "Open selected frame")
        btn_open.clicked.connect(
            lambda: self._open_sequence_row(table.currentRow(), 0) if table.currentRow() >= 0 else None
        )
        lay.addWidget(btn_open)
        win.set_body_widget(body)
        win.set_identity(
            {
                "source_sha256": self._source_sha or "",
                "frame_index": int(self.frame_spin.value()),
                "interpreted_time": self.time_edit.text() if hasattr(self, "time_edit") else "",
                "sequence_count": len(self._sequence_results),
            },
            lang,
        )
        win.retranslate(lang)
        def _on_seq_closed() -> None:
            self._seq_detach_win = None
            self._seq_detach_table = None

        win.closed.connect(_on_seq_closed)
        self._seq_detach_win = win
        self._seq_detach_table = table
        self._sync_sequence_detach_table()
        win.show()

    def _sync_sequence_detach_table(self) -> None:
        table = self._seq_detach_table
        if table is None:
            return
        rows = self._sequence_results
        lang = "ru" if self.i18n.language == "ru" else "en"
        table.setSortingEnabled(False)
        table.setHorizontalHeaderLabels(sequence_header_labels(lang))
        table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = self._sequence_row_values(r)
            for j, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setToolTip(val)
                table.setItem(i, j, item)
            self._style_sequence_table_row(i, r, table=table)
        table.setSortingEnabled(True)
        # Detached view uses the full column profile (same model, independent visibility).
        self._apply_sequence_column_profile(table, profile="full", force_widths=False)
        if self._seq_detach_win is not None:
            self._seq_detach_win.set_identity(
                {
                    "source_sha256": self._source_sha or "",
                    "frame_index": int(self.frame_spin.value()),
                    "interpreted_time": self.time_edit.text() if hasattr(self, "time_edit") else "",
                    "sequence_count": len(rows),
                    "table_profile": profile_label("full", lang),
                },
                lang,
            )
            self._seq_detach_win.setWindowTitle(
                (
                    f"Результаты последовательности ({len(rows)}) · {profile_label('full', lang)}"
                    if lang == "ru"
                    else f"Sequence results ({len(rows)}) · {profile_label('full', lang)}"
                )
            )

    def _rebuild_seq_fields(self) -> None:
        kind = self.seq_type.currentData() or "frame_range"
        frame_mode = kind in ("frame_range", "every_n_frames")
        time_mode = kind in ("time_range", "every_n_minutes")
        custom_mode = kind == "custom"
        for w, vis in (
            (self.lbl_seq_start, frame_mode),
            (self.seq_start, frame_mode),
            (self.lbl_seq_end, frame_mode),
            (self.seq_end, frame_mode),
            (self.lbl_seq_step, frame_mode),
            (self.seq_step, frame_mode),
            (self.lbl_seq_t0, time_mode),
            (self.seq_t0, time_mode),
            (self.lbl_seq_t1, time_mode),
            (self.seq_t1, time_mode),
            (self.lbl_seq_interval, time_mode),
            (self.seq_interval, time_mode),
            (self.lbl_seq_custom, custom_mode),
            (self.seq_custom, custom_mode),
        ):
            w.setVisible(vis)
        self._update_seq_preview()

    def _on_seq_type_changed(self) -> None:
        self._rebuild_seq_fields()

    # ----- lifecycle -----
    def _on_source_detached(self) -> None:
        self._invalidate_pending_loads()
        for win_attr in ("_features_detach_win", "_seq_detach_win", "_evidence_dialog"):
            win = getattr(self, win_attr, None)
            if win is not None:
                try:
                    win.close()
                except Exception:
                    pass
                setattr(self, win_attr, None)
        self._seq_detach_table = None
        self.clear_results()
        self.refresh()

    def clear_results(self) -> None:
        self._result = None
        self._result_ser = None
        self._masks = {}
        self._raw = None
        self._raw_sha = ""
        self._timings = {}
        self._sequence_results = []
        self._clear_candidate_presentation()
        self._current_ctx = None
        self._display_cache.clear()
        self._features_populated = False
        if self._features_model is not None:
            self._features_model.clear()
        self.feature_list.clear()
        self.explain.clear()
        self.summary_view.clear()
        if hasattr(self, "summary_empty"):
            self.summary_empty.show()
        self.image.clear()
        self._feature_index.clear()
        self.seq_table.setRowCount(0)
        self.contact_label.clear()
        if hasattr(self, "morph_summary"):
            self._refresh_morph_panel()

    def _set_status(self, key: str, *, args: dict | None = None, severity: str = "info") -> None:
        self._status_msg = StatusMessage(
            key=key,
            args=args or {},
            severity=severity,
            generation=self._active_generation_id,
            identity={"frame": int(self.frame_spin.value()) if hasattr(self, "frame_spin") else 0},
        )
        text = format_status(self._status_msg, self.i18n.language)
        self._inline_note = text
        self.inline_note.setText(text)
        self.inline_note.setVisible(bool(text))

    def _show_inline(self, text: str) -> None:
        """Legacy free-text path — prefer ``_set_status`` for localizable runtime messages."""
        self._status_msg = None
        self._inline_note = text
        self.inline_note.setText(text)
        self.inline_note.setVisible(bool(text))

    def _clear_candidate_presentation(self) -> None:
        self._morph_generation += 1
        self._morph_result = None
        self._morph_result_dict = None
        self._morph_identity = None
        self._morph_cache_status = "not_computed"
        self._morph_compat_state = None
        self._morph_last_miss_reason = None
        self._morph_review_status = "unreviewed"
        self._sync_evidence_dialog_on_identity_change(close_if_stale=True)
        if self._review_dialog is not None:
            try:
                self._review_dialog.reject()
            except Exception:
                pass
            self._review_dialog = None

    def _sync_evidence_dialog_on_identity_change(self, *, close_if_stale: bool = True) -> None:
        dlg = self._evidence_dialog
        if dlg is None:
            return
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.evidence.identity_change"):
            lang = "ru" if self.i18n.language == "ru" else "en"
            d = self._morph_result_dict
            if d is None:
                if close_if_stale:
                    dlg.mark_stale(lang)
                    dlg.close()
                    self._evidence_dialog = None
                else:
                    dlg.mark_stale(lang)
                return
            if dlg.matches_identity(d):
                return
            # Default: follow active candidate
            dlg.bind_result(d, lang, follow_active=True)

    def _on_session_frame_changed(self) -> None:
        if not self._sync_auto:
            return
        frame = int(getattr(self.session, "current_frame", 1) or 1)
        if frame == int(self._intended_frame) and self._loaded_frame == frame:
            return
        # Stale Viewer/session events must not rewind Diagnostics after a newer local intent.
        if (
            not self._viewer_sync_accept
            and self._frame_navigation_generation > 0
            and int(frame) != int(self._intended_frame)
        ):
            return
        self._viewer_sync_accept = False
        self._goto_frame(frame, from_viewer=True, immediate=True, reason="viewer_sync")

    def _on_mode_changed(self) -> None:
        seq = self.mode_combo.currentData() == "sequence"
        drawer_open = bool(self._settings_get("fd_sequence_drawer_open", False))
        self.seq_form.setVisible(seq and drawer_open and self.seq_form.isVisible())
        self.seq_summary.setVisible(seq)
        self.btn_sequence_settings.setVisible(seq)
        self.btn_contact.setVisible(seq)
        if self._btn_detach_seq is not None:
            self._btn_detach_seq.setVisible(seq)
        if self._btn_show_seq_table is not None:
            self._btn_show_seq_table.setVisible(seq)
        if self._chk_seq_follow is not None:
            self._chk_seq_follow.setVisible(seq)
        if self._btn_show_latest_seq is not None:
            self._btn_show_latest_seq.setVisible(seq)
        # Keep sequence results pane reachable in sequence mode (empty until results arrive).
        self._set_sequence_pane_visible(seq)
        if seq:
            QTimer.singleShot(0, self._ensure_sequence_table_visible)
        if not seq:
            self.contact_label.hide()
            self.seq_form.hide()
            if self._seq_follow_status is not None:
                self._seq_follow_status.hide()
            if self._btn_resume_follow is not None:
                self._btn_resume_follow.hide()
        self._update_seq_preview()
        self._update_sequence_follow_ui()
        self._refresh_sequence_frame_state()
        self._update_features_empty_state()

    def _set_sequence_pane_visible(self, visible: bool) -> None:
        if self._seq_pane is None or self._mid_vsplit is None:
            self.seq_table.setVisible(visible)
            self.seq_filter.setVisible(visible)
            return
        if visible:
            if self._saved_seq_split_sizes:
                self._mid_vsplit.setSizes(self._saved_seq_split_sizes)
            else:
                total = max(300, sum(self._mid_vsplit.sizes()) or 620)
                self._mid_vsplit.setSizes([int(total * 0.65), int(total * 0.35)])
            self._seq_pane.show()
            self.seq_filter.show()
            self.seq_table.show()
        else:
            if self._seq_pane.isVisible():
                self._saved_seq_split_sizes = list(self._mid_vsplit.sizes())
            self._seq_pane.hide()
            # Give all space to canvas when sequence pane hidden
            sizes = self._mid_vsplit.sizes()
            self._mid_vsplit.setSizes([sum(sizes) or 600, 0])

    def _update_seq_preview(self) -> None:
        frames = self._selected_sequence_frames()
        ru = self.i18n.language == "ru"
        snap = resolve_active_source(self.session, force_rebuild=False)
        text = (
            (
                f"MAT: {snap.mat_filename or '—'} | кадров: {len(frames)} | "
                f"профиль: {snap.profile_id} | feature_version: {FEATURE_VERSION}"
            )
            if ru
            else (
                f"MAT: {snap.mat_filename or '—'} | frames: {len(frames)} | "
                f"profile: {snap.profile_id} | feature_version: {FEATURE_VERSION}"
            )
        )
        self.seq_preview.setText(text)
        self.seq_summary.setText(
            (f"Последовательность: {len(frames)} кадров" if ru else f"Sequence: {len(frames)} frames")
        )

    def _selected_sequence_frames(self) -> list[int]:
        kind = self.seq_type.currentData() or "frame_range"
        custom = (self.seq_custom.toPlainText() or "").strip()
        # Custom list: explicit custom mode, or non-empty custom text (legacy/test compat)
        if kind == "custom" or (custom and kind in ("frame_range", "every_n_frames", "custom")):
            if custom:
                out: list[int] = []
                for part in custom.replace(" ", "").split(","):
                    if not part:
                        continue
                    if "-" in part:
                        a, b = part.split("-", 1)
                        out.extend(range(int(a), int(b) + 1))
                    else:
                        out.append(int(part))
                return sorted({max(1, min(self._n_frames, f)) for f in out})
            if kind == "custom":
                return []
        if kind in ("time_range", "every_n_minutes"):
            m0 = parse_hhmm(self.seq_t0.currentText().strip())
            m1 = parse_hhmm(self.seq_t1.currentText().strip())
            if m0 is None or m1 is None:
                return []
            step = max(1, int(self.seq_interval.value()))
            if m1 < m0:
                m0, m1 = m1, m0
            frames = [minute_to_frame(m) for m in range(m0, m1 + 1, step)]
            return sorted({max(1, min(self._n_frames, f)) for f in frames})
        start = int(self.seq_start.value())
        end = int(self.seq_end.value())
        step = max(1, int(self.seq_step.value()))
        if end < start:
            start, end = end, start
        return list(range(start, end + 1, step))

    def _on_frame_spin(self, v: int) -> None:
        # Debounce typing in the spin box; buttons use _goto_frame(..., immediate=True).
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(max(1, min(int(v), self._n_frames)))
        self.frame_slider.blockSignals(False)
        self._update_frame_preview_labels(int(v))
        self._pending_spin_frame = int(v)
        self._spin_debounce.start()

    def _commit_spin_edit(self) -> None:
        self._spin_debounce.stop()
        self._pending_spin_frame = None
        self._goto_frame(
            int(self.frame_spin.value()),
            immediate=True,
            reason="user_frame_entry",
        )

    def _apply_debounced_spin(self) -> None:
        if self._pending_spin_frame is None:
            return
        frame = self._pending_spin_frame
        self._pending_spin_frame = None
        self._goto_frame(frame, immediate=True, reason="user_frame_entry")

    def _on_frame_slider_moved(self, frame: int) -> None:
        frame = max(1, min(int(frame), self._n_frames))
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(frame)
        self.frame_slider.blockSignals(False)
        self.frame_spin.blockSignals(True)
        self.frame_spin.setValue(frame)
        self.frame_spin.blockSignals(False)
        self._update_frame_preview_labels(frame)

    def _on_frame_slider_released(self) -> None:
        self._goto_frame(int(self.frame_slider.value()), immediate=True)

    def _update_frame_preview_labels(self, frame: int) -> None:
        tm = mapping_status((getattr(self.session, "profile", {}) or {}).get("time_mapping"))
        self.time_edit.setText(format_hhmm(frame_to_minute(frame)) + (" *" if tm.available else "") if tm.available else "—")

    def _invalidate_pending_loads(self) -> None:
        self._active_generation_id = next_request_generation_id()
        self._pending_frame_request = None
        if self._frame_worker is not None and self._frame_worker.isRunning():
            self._frame_worker.request_cancel()
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()

    def _authoritative_frame(self) -> int:
        """Selected/intended frame for sequence membership and pending UI (not load completion)."""
        try:
            return int(self._intended_frame)
        except (TypeError, ValueError):
            return int(self.frame_spin.value()) if hasattr(self, "frame_spin") else 1

    def _bump_frame_navigation(self, frame: int, *, reason: str) -> int:
        """Advance frame-navigation generation and record intended frame."""
        frame = max(1, min(int(frame), int(self._n_frames) or 1))
        self._frame_navigation_generation = int(self._frame_navigation_generation) + 1
        self._intended_frame = frame
        self._pending_frame_request = None
        # Profiler / debug only — never shown in normal UI.
        try:
            from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler

            prof = get_profiler()
            if prof is not None:
                prof.event(
                    "fd_frame_navigation",
                    navigation_generation=self._frame_navigation_generation,
                    intended_frame=frame,
                    reason=reason,
                )
        except Exception:
            pass
        return self._frame_navigation_generation

    def _apply_selector_frame(self, frame: int) -> None:
        """Atomically update spin + slider without scheduling loads or emitting spin handlers."""
        frame = max(1, min(int(frame), int(self._n_frames) or 1))
        self.frame_spin.blockSignals(True)
        self.frame_slider.blockSignals(True)
        try:
            self.frame_spin.setValue(frame)
            self.frame_slider.setValue(frame)
        finally:
            self.frame_spin.blockSignals(False)
            self.frame_slider.blockSignals(False)
        self._update_frame_preview_labels(frame)

    def _goto_frame(
        self,
        frame: int,
        *,
        from_viewer: bool = False,
        immediate: bool = True,
        pause_follow: bool | None = None,
        reason: str = "user_frame_entry",
    ) -> None:
        frame = max(1, min(int(frame), self._n_frames))
        if pause_follow is None:
            pause_follow = (not self._suppress_follow_pause) and (not from_viewer)
        if pause_follow and self.mode_combo.currentData() == "sequence":
            if self._running or self._sequence_results or self._sequence_frames:
                self._pause_sequence_follow_manual()
        if reason == "user_frame_entry" and from_viewer:
            reason = "viewer_sync"
        prev_loaded = self._loaded_frame
        prev_intent = int(self._intended_frame)
        self._bump_frame_navigation(frame, reason=reason)
        self._apply_selector_frame(frame)
        self.session.set_current_frame(frame, emit=False)
        if (prev_loaded > 0 and prev_loaded != frame) or (prev_intent > 0 and prev_intent != frame):
            self._result = None
            self._result_ser = None
            self._masks = {}
            self._clear_candidate_presentation()
            self._display_cache.clear()
            if self._features_model is not None:
                self._features_model.clear()
            self._features_populated = False
            self.feature_list.clear()
            self.summary_view.clear()
            self._sync_features_detach_on_frame()
            if hasattr(self, "morph_summary"):
                self._refresh_morph_panel()
            self._set_status("frame_changed_cleared")
            self._cache_status = "not_computed"
            self._refresh_sequence_frame_state()
            self._update_features_empty_state()
            self._update_features_identity_line()
        self._schedule_frame_load(frame, reason=reason)
        if from_viewer is False and self._sync_auto:
            self.frame_sync_to_viewer.emit(frame)
        # Identity / empty-state follow intended frame immediately — do not wait for load.
        self._update_features_identity_line()
        self._update_features_empty_state()

    def _schedule_frame_load(self, frame: int, *, reason: str = "user_frame_entry") -> None:
        snap = resolve_active_source(self.session, force_rebuild=False)
        if snap.mat_path is None:
            return
        gen = next_request_generation_id()
        self._active_generation_id = gen
        nav_gen = int(self._frame_navigation_generation)
        known = ""
        try:
            if hasattr(self.session, "get_source_sha"):
                known = self.session.get_source_sha(allow_compute=False) or ""
        except Exception:
            known = self._source_sha
        self._pending_frame_request = {
            "request_generation_id": gen,
            "navigation_generation": nav_gen,
            "frame_index": int(frame),
            "source_sha": str(known or self._source_sha or ""),
            "reason": reason,
            "applied": False,
            "discard_reason": "",
        }
        if self._frame_worker is not None and self._frame_worker.isRunning():
            self._frame_worker.request_cancel()
            # Detach so the new worker is the only tracked load
            try:
                self._frame_worker.finished_ok.disconnect(self._on_frame_loaded)
                self._frame_worker.failed.disconnect(self._on_frame_load_failed)
                self._frame_worker.cancelled.disconnect(self._on_frame_load_cancelled)
            except Exception:
                pass
        self._job_state = "loading_frame"
        self._set_status("loading_frame", args={"frame": frame})
        self._set_run_state("loading")
        frame_store = None
        try:
            # Use existing ready FrameStore only — never build/hash the MAT on the UI thread
            store = getattr(self.session, "frame_store", None)
            if store is not None and store.status().valid:
                frame_store = store
        except Exception:
            frame_store = None
        worker = FrameLoadWorker(
            mat_path=snap.mat_path,
            frame_index=frame,
            profile=getattr(self.session, "profile", {}) or {},
            profile_id=snap.profile_id,
            signal_contract_id=snap.signal_contract_id,
            n_frames=self._n_frames,
            request_generation_id=gen,
            known_source_sha=known,
            frame_store=frame_store,
            parent=self,
        )
        self._frame_worker = worker
        worker.finished_ok.connect(self._on_frame_loaded)
        worker.failed.connect(self._on_frame_load_failed)
        worker.cancelled.connect(self._on_frame_load_cancelled)
        worker.start()

    def _discard_frame_load(self, reason: str) -> None:
        req = self._pending_frame_request
        if req is not None:
            req["applied"] = False
            req["discard_reason"] = reason
        try:
            from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler

            prof = get_profiler()
            if prof is not None:
                prof.event(
                    "fd_frame_load_discarded",
                    reason=reason,
                    navigation_generation=self._frame_navigation_generation,
                    intended_frame=self._intended_frame,
                    pending=req,
                )
        except Exception:
            pass

    def _on_frame_loaded(self, payload: dict) -> None:
        gen = str(payload.get("request_generation_id") or "")
        req = self._pending_frame_request
        if gen != self._active_generation_id:
            self._discard_frame_load("stale_request_generation")
            return
        if req is not None and str(req.get("request_generation_id") or "") == gen:
            if int(req.get("navigation_generation", -1)) != int(self._frame_navigation_generation):
                self._discard_frame_load("stale_navigation_generation")
                return
            if int(req.get("frame_index", -1)) != int(self._intended_frame):
                self._discard_frame_load("frame_no_longer_intended")
                return
            src_req = str(req.get("source_sha") or "")
            if src_req and self._source_sha and src_req != self._source_sha:
                # Allow first bind when page source_sha was empty at schedule time.
                pass
        ctx: FrameDiagnosticContext = payload["context"]
        # Late load completion must never rewrite selector intent.
        if int(ctx.frame_index) != int(self._intended_frame):
            self._discard_frame_load("loaded_frame_mismatch_intent")
            return
        if int(ctx.frame_index) != int(self.frame_spin.value()):
            self._discard_frame_load("loaded_frame_mismatch_selector")
            return
        if req is not None:
            req["applied"] = True
            req["discard_reason"] = ""
        self._current_ctx = ctx
        self._raw = payload["raw"]
        self._raw_sha = ctx.raw_frame_sha256
        self._source_sha = ctx.source_sha256
        self._loaded_frame = int(ctx.frame_index)
        self._loaded_mat_path = ctx.source_mat_path
        self._last_known_source_sha = ctx.source_sha256
        self.time_edit.setText(ctx.interpreted_time)
        self._display_cache.bind_context(ctx)
        self._display_cache_status = "miss"
        self._visible_timings = dict(payload.get("timings") or {})
        self._update_viewer_cache_hint()
        # Try V2 cache for this exact context
        self._job_state = "checking_cache"
        loaded = self._try_load_cache()
        if loaded:
            self._job_state = "loaded_from_cache"
            self._update_completed_state()
            if self._morph_cache_status == "cached":
                self._set_status("cached_return_both")
            elif self._morph_last_miss_reason in {
                MISS_INCOMPATIBLE_CACHE_SCHEMA,
                MISS_INCOMPATIBLE_LEDGER_SCHEMA,
            }:
                self._set_status("incompatible_candidate_cache")
            else:
                self._set_status("cached_return_v2_only")
        else:
            # Still hydrate morph from exact identity — never triggers V2.
            self._try_load_cached_morph(on_frame_activation=True)
            self._job_state = "completed" if self._running else "idle"
            if self._raw is not None and not self._running:
                self._set_run_state("frame_ready")
                if self._morph_cache_status == "cached":
                    self._set_status("frame_loaded_candidate_cached")
                elif self._morph_last_miss_reason in {
                    MISS_INCOMPATIBLE_CACHE_SCHEMA,
                    MISS_INCOMPATIBLE_LEDGER_SCHEMA,
                }:
                    self._set_status("incompatible_candidate_cache")
                else:
                    self._set_status("frame_loaded_no_v2")
        # Sequence: if this frame already has a result in the active sequence, hydrate it.
        if self.mode_combo.currentData() == "sequence":
            cur = int(self.frame_spin.value())
            seq_row = next(
                (r for r in self._sequence_results if int(r.get("frame_index", -1)) == cur),
                None,
            )
            if (
                seq_row
                and seq_row.get("status") != "failed"
                and str(seq_row.get("request_generation_id") or self._sequence_generation_id)
                in {"", self._v2_generation_id, self._sequence_generation_id}
            ):
                if not (self._result_ser or self._result):
                    self._apply_frame_result(seq_row)
                morph = seq_row.get("morph_candidate") or {}
                if morph and not self._morph_result_dict:
                    self._morph_result_dict = morph
                    self._morph_result = morph
                    self._morph_identity = evidence_identity_from_result(morph)
                    st = str(seq_row.get("morph_status") or "")
                    self._morph_cache_status = (
                        "cached" if st in {"cached", "candidate_cached"} else "new"
                    )
        self._job_state = "rendering"
        self._render_view()
        self._job_state = "completed" if (self._result or self._result_ser) else "idle"
        self._update_identity(resolve_active_source(self.session, force_rebuild=False))
        self._update_cache_status_row()
        self._refresh_sequence_frame_state()

    def _on_frame_load_failed(self, payload: dict) -> None:
        if str(payload.get("request_generation_id") or "") != self._active_generation_id:
            return
        self._job_state = "failed"
        user, tech = format_missing_variable_user_message(payload.get("error", ""), self.i18n.language)
        self._set_run_state("v2_failed", detail=user)
        self.image.setText(f"{user}\n\n{tech}")

    def _on_frame_load_cancelled(self, payload: dict) -> None:
        # Obsolete request — ignore silently
        _ = payload

    def _use_viewer_frame(self) -> None:
        self._viewer_sync_accept = True
        self._goto_frame(
            int(getattr(self.session, "current_frame", 1) or 1),
            from_viewer=True,
            immediate=True,
            reason="viewer_sync",
        )

    def _send_frame_to_viewer(self) -> None:
        self.session.set_current_frame(int(self._authoritative_frame()), emit=True)
        self.frame_sync_to_viewer.emit(int(self._authoritative_frame()))
        self.open_in_viewer_requested.emit()

    def _jump_exact_time(self) -> None:
        text = self.exact_time.currentText().strip()
        minute = parse_hhmm(text)
        if minute is None:
            self._show_inline("Некорректное время." if self.i18n.language == "ru" else "Invalid time.")
            return
        self._goto_frame(minute_to_frame(minute), immediate=True, reason="user_frame_entry")

    def _deferred_first_activate(self) -> None:
        self.activate(force_load=True)

    def activate(self, *, force_load: bool = False) -> None:
        """Lightweight page activation — never wait for workers; reuse canvas."""
        from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler, span_timer

        with span_timer("fd_activate", force_load=force_load):
            # Never start V2, never kill workers, never hash EXE / open MAT on activation.
            snap = resolve_active_source(self.session, force_rebuild=False)
            self.source_card.apply_snapshot(snap)
            self._update_cache_status_row()
            same_mat = False
            if self._loaded_mat_path and snap.mat_path is not None:
                same_mat = paths_equal(self._loaded_mat_path, snap.mat_path)
            if self._raw is not None and same_mat:
                # Retained canvas/result — show immediately, no reload / no mask scan.
                if int(self._loaded_frame) != int(self._authoritative_frame()):
                    # Spin may differ from session; keep showing retained frame labels only
                    pass
                self._activated_once = True
                if self._running:
                    self._set_run_state("v2_running")
                elif self._result_ser or self._result:
                    self._update_completed_state()
                prof = get_profiler()
                if prof is not None:
                    prof.event("fd_activate_reuse")
                return
            if force_load or not self._activated_once:
                # Capture navigation generation so a later user/sequence intent can discard this.
                scheduled_nav = int(self._frame_navigation_generation)
                QTimer.singleShot(
                    0,
                    lambda g=scheduled_nav: self._run_deferred_refresh(
                        g, reason="initial_page_activation"
                    ),
                )
            self._activated_once = True

    def _run_deferred_refresh(self, scheduled_nav_gen: int, *, reason: str) -> None:
        """Apply deferred source refresh only if frame intent has not advanced."""
        if int(scheduled_nav_gen) != int(self._frame_navigation_generation):
            # Stale initial/source-ready callback — update card only; never rewrite selector.
            snap = resolve_active_source(self.session, force_rebuild=False)
            self.source_card.apply_snapshot(snap)
            self._update_cache_status_row()
            self._update_identity(snap)
            try:
                from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler

                prof = get_profiler()
                if prof is not None:
                    prof.event(
                        "fd_refresh_discarded",
                        reason="stale_navigation_generation",
                        scheduled_nav_gen=scheduled_nav_gen,
                        current_nav_gen=self._frame_navigation_generation,
                        intended_frame=self._intended_frame,
                        refresh_reason=reason,
                    )
            except Exception:
                pass
            return
        self.refresh(reason=reason)

    def refresh(self, *, reason: str = "source_ready") -> None:
        # Warm refresh uses cached snapshot — no MAT open/stat/classify.
        snap = resolve_active_source(self.session, force_rebuild=False)
        self.source_card.apply_snapshot(snap)
        try:
            store = None
            svc = getattr(self.session, "source_service", None)
            if svc is not None:
                store = svc.get_existing_store()
            if store is None and self.session.frame_store is not None:
                store = self.session.frame_store
            if store is not None and store.status().valid:
                store_n = int(store.n_frames())
            else:
                store_n = int(snap.frame_count or 1440)
            # Never shrink the selectable range below an established intended frame
            # (prevents silent QSpinBox clamping of sequence-selected frames).
            self._n_frames = max(store_n, int(self._intended_frame or 1), 1)
            self.frame_spin.setMaximum(self._n_frames)
            self.frame_slider.setMaximum(self._n_frames)
            self.seq_start.setMaximum(self._n_frames)
            self.seq_end.setMaximum(self._n_frames)
        except Exception:
            pass

        if not snap.project_open:
            self._set_run_state("no_project")
            self._show_empty_actions(True)
            return
        if snap.status == SourceStatus.INVENTORY_INACTIVE or not snap.is_active:
            self._set_run_state("no_active")
            self.clear_results()
            self._show_empty_actions(True)
            return
        if snap.mat_path is None or snap.status == SourceStatus.MISSING:
            self._set_run_state("no_active")
            self.clear_results()
            self._show_empty_actions(True)
            return
        # Trust snapshot role — never re-classify MAT here.
        if snap.status == SourceStatus.INCOMPATIBLE or (
            snap.role and not snap.can_activate and snap.is_active
        ):
            self._set_run_state("incompatible")
            self.clear_results()
            self._show_empty_actions(True)
            return

        self._show_empty_actions(False)
        # Intended frame wins over snapshot/session default once navigation advanced.
        if self._frame_navigation_generation > 0:
            want = int(self._intended_frame)
        else:
            want = int(snap.frame)
            self._intended_frame = want
        want = max(1, min(int(want), int(self._n_frames) or 1))
        if int(self.frame_spin.value()) != want or int(self.frame_slider.value()) != want:
            self._apply_selector_frame(want)
        # Skip reload when already showing this frame from this MAT.
        same_mat = bool(
            self._loaded_mat_path
            and snap.mat_path is not None
            and paths_equal(self._loaded_mat_path, snap.mat_path)
        )
        if (
            self._raw is not None
            and same_mat
            and int(self._loaded_frame) == int(want)
        ):
            if self._running:
                self._set_run_state("v2_running")
            self._update_identity(snap)
            self._update_seq_preview()
            self._update_cache_status_row()
            return
        self.state_label.setText(
            "Подготавливается источник…" if self.i18n.language == "ru" else "Preparing source…"
        )
        # Initial activation establishes intent without a second bump when gen==0.
        if self._frame_navigation_generation == 0:
            self._bump_frame_navigation(want, reason=reason)
            self._apply_selector_frame(want)
            self.session.set_current_frame(want, emit=False)
        self._schedule_frame_load(want, reason=reason)
        if self._running:
            self._set_run_state("v2_running")
        self._update_identity(snap)
        self._update_seq_preview()
        self._update_cache_status_row()

    def _update_viewer_cache_hint(self) -> None:
        try:
            store = getattr(self.session, "frame_store", None)
            if store is not None and store.status().valid:
                self._viewer_frame_cache_status = "hit"
            else:
                self._viewer_frame_cache_status = "miss"
        except Exception:
            self._viewer_frame_cache_status = "—"

    def _update_cache_status_row(self) -> None:
        ru = self.i18n.language == "ru"
        v2 = self._cache_status
        if v2 == "cached":
            v2_txt = "V2 загружен из кэша" if ru else "V2 loaded from cache"
        elif v2 == "recomputed":
            v2_txt = "V2 рассчитан заново" if ru else "V2 recomputed"
        elif v2 == "running":
            v2_txt = "V2 рассчитывается" if ru else "V2 computing"
        elif v2 == "error":
            v2_txt = "Ошибка V2" if ru else "V2 error"
        else:
            v2_txt = "V2 не рассчитан" if ru else "V2 not computed"
        frame_txt = "Кадр загружен" if ru and self._raw is not None else (
            "Frame loaded" if self._raw is not None else ("Кадр…" if ru else "Frame…")
        )
        disp = "Отображение готово" if ru else "Display ready"
        self.cache_status_row.setText(f"{frame_txt} | {v2_txt} | {disp}")
        if self.tech_toggle.isChecked():
            t = self._visible_timings
            self.stage_label.setText(
                f"Viewer-cache={self._viewer_frame_cache_status} | "
                f"display-cache={self._display_cache_status} | "
                f"load={t.get('total_s', t.get('frame_extract_s', 0)):.2f}s "
                f"compose={t.get('compose_s', 0):.2f}s"
            )
        self.cache_label.setText(cache_status_label(self._cache_status, self.i18n.language))

    def _update_identity(self, snap) -> None:
        ru = self.i18n.language == "ru"
        ori = orientation_identity_dict()
        ctx = self._current_ctx
        frame = ctx.frame_index if ctx else int(self.frame_spin.value())
        time_s = ctx.interpreted_time if ctx else self.time_edit.text()
        sha_short = ((ctx.source_sha256 if ctx else self._source_sha)[:16] + "…") if (ctx or self._source_sha) else "—"
        raw_short = ((ctx.raw_frame_sha256 if ctx else self._raw_sha)[:16] + "…") if (ctx or self._raw_sha) else "—"
        # Enforce selector/identity agreement
        if ctx and int(self.frame_spin.value()) != int(ctx.frame_index):
            # Should not display mismatched identity — show selector as loading
            time_s = "…"
            raw_short = "…"
        self.identity.setText(
            f"{'Проект' if ru else 'Project'}: {snap.project_name} | "
            f"MAT: {snap.mat_filename} | SHA: {sha_short} | "
            f"{'Кадр' if ru else 'Frame'}: {frame} / {self._n_frames} "
            f"({time_s}) | "
            f"{'Профиль' if ru else 'Profile'}: {snap.profile_id} | "
            f"contract: {snap.signal_contract_id} | raw_frame_sha: {raw_short} | "
            f"feature_version: {FEATURE_VERSION} | "
            f"display: row0→{ori['row_zero_display_location']} | "
            f"vflip={ori['vertical_flip_applied']} | gen={self._active_generation_id[-8:]}"
        )
        self.cache_label.setText(cache_status_label(self._cache_status, self.i18n.language))

    def _show_empty_actions(self, show: bool) -> None:
        for b in (
            self.btn_open_projects, self.btn_open_import, self.btn_choose_mat,
            self.btn_pick_project, self.btn_refresh_state,
        ):
            b.setVisible(show)
        self.btn_run.setEnabled(not show and not self._running)

    def _set_run_state(self, state: str, detail: str = "") -> None:
        self._run_state = state
        self.state_label.setText(run_state_message(state, self.i18n.language, detail))
        if state in ("no_project", "no_active", "incompatible") and (
            self.image.pixmap() is None or self.image.pixmap().isNull()
        ):
            self.image.setText(self.state_label.text())

    def _update_completed_state(self) -> None:
        ser = self._result_ser or (self._result.to_serializable() if self._result else None)
        if not ser:
            return
        cls = ser.get("centerlines") or []
        if not cls:
            self._set_run_state("v2_no_trace")
        elif ser.get("oversegmentation_suspected") or str(ser.get("quality_status", "")).lower() in (
            "uncertain", "low", "poor"
        ):
            self._set_run_state("v2_uncertain")
        else:
            self._set_run_state("v2_done")

    def _load_raw_frame(self) -> None:
        """Compatibility: schedule async load for current spin value."""
        self._schedule_frame_load(int(self.frame_spin.value()))

    def wait_until_frame_ready(self, timeout_ms: int = 30000) -> bool:
        """Test helper: pump events until selector frame is loaded into context."""
        from PySide6.QtWidgets import QApplication

        deadline = time.perf_counter() + timeout_ms / 1000.0
        target = int(self.frame_spin.value())
        while time.perf_counter() < deadline:
            QApplication.processEvents()
            if (
                self._current_ctx is not None
                and int(self._current_ctx.frame_index) == target
                and self._raw is not None
                and int(self._loaded_frame) == target
            ):
                return True
            time.sleep(0.02)
        return False

    def _cache_key(self):
        snap = resolve_active_source(self.session, force_rebuild=False)
        return make_cache_key(
            source_mat_sha256=self._source_sha or snap.source_sha256 or "",
            frame_index=int(self.frame_spin.value()),
            profile_id=snap.profile_id or str(getattr(self.session, "profile_id", "") or ""),
            signal_contract_id=snap.signal_contract_id,
            profile=getattr(self.session, "profile", {}) or {},
        )

    def _try_load_cache(self) -> bool:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler, span_timer

        if not self._source_sha:
            self._cache_status = "not_computed"
            self._last_cache_diag = {"miss_reason": "no_source_sha", "status": "not_computed"}
            return False
        key = self._cache_key()
        with span_timer("v2.cache_lookup"):
            diag = self._cache.diagnose_lookup(key)
            # Prefer status_for so tests / wrappers can override without rebuilding diagnose.
            st = str(self._cache.status_for(key) or diag.get("status") or "not_computed")
            diag = {**diag, "status": st}
            # Annotate quick-layer presence when summary exists
            if st == "cached":
                try:
                    layers = self._cache.available_layers(key)
                    wanted = [k for k, *_ in self.QUICK_LAYER_KEYS if k != "raw"]
                    diag["requested_quick_layers_found"] = [k for k in wanted if k in layers]
                except Exception:
                    pass
            self._last_cache_diag = diag
            self._cache_status = st
            prof = get_profiler()
            if prof is not None:
                prof.event("v2_cache_diagnose", **diag)
            if st != "cached":
                return False
            hit = self._cache.load_summary(key)
            if not hit:
                self._cache_status = "error"
                self._last_cache_diag = {**diag, "status": "error", "miss_reason": "summary_load_failed"}
                if prof is not None:
                    prof.event("v2_cache_diagnose", **self._last_cache_diag)
                return False
        # Reject if context frame/source disagree
        if self._current_ctx and (
            int(self._current_ctx.frame_index) != int(self.frame_spin.value())
            or self._current_ctx.source_sha256 != self._source_sha
        ):
            self._last_cache_diag = {
                **diag,
                "status": "rejected",
                "miss_reason": "context_frame_or_source_mismatch",
            }
            return False
        self._result_ser = hit["result"]
        self._masks = {}
        self._result = None
        self._cache_status = "cached"
        self._last_known_source_sha = str(
            (hit.get("result") or {}).get("source_mat_sha256") or self._source_sha or ""
        )
        self._display_cache.clear()
        if self._current_ctx:
            self._display_cache.bind_context(self._current_ctx)
        self._features_populated = False
        with span_timer("v2.post.summary_only"):
            self._populate_summary_from_ser()
        # Features / tech populate lazily when those tabs are open.
        if hasattr(self, "inspector_tabs") and self.inspector_tabs.currentIndex() == 1:
            self._ensure_features_tab()
            self._populate_features()
        if hasattr(self, "inspector_tabs") and self.inspector_tabs.currentIndex() == 4:
            self._ensure_tech_tab()
            self._refresh_tech_details()
        # Morph candidate: hydrate cache only; never auto-run engine / never request V2.
        self._try_load_cached_morph(on_frame_activation=True)
        return True

    def run_shadow(self, force: bool = False) -> None:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler, span_timer

        with span_timer("v2.pre_submit"):
            with span_timer("v2.pre.context_validation"):
                ok, code = self._check_prerequisites()
            if not ok:
                QMessageBox.information(self, "IML", prerequisite_message(code, self.i18n.language))
                self.refresh()
                return
            if self._raw is None:
                with span_timer("v2.pre.raw_frame_retrieval"):
                    self._schedule_frame_load(int(self.frame_spin.value()))
                    self.wait_until_frame_ready(15000)
                if self._raw is None:
                    return
            snap = resolve_active_source(self.session, force_rebuild=False)
            assert snap.mat_path is not None
            mode = self.mode_combo.currentData() or "single"
            frames = [int(self.frame_spin.value())] if mode == "single" else self._selected_sequence_frames()
            if not frames:
                return
            if mode == "sequence" and len(frames) > 200:
                ru = self.i18n.language == "ru"
                ans = QMessageBox.question(
                    self,
                    "IML",
                    (
                        f"Будет обработано {len(frames)} кадров. Продолжить?"
                        if ru
                        else f"{len(frames)} frames will be processed. Continue?"
                    ),
                )
                if ans != QMessageBox.StandardButton.Yes:
                    return
            if mode == "single" and not force:
                with span_timer("v2.pre.cache_validity_check"):
                    cached = self._try_load_cache()
                if cached:
                    with span_timer("v2.post_result_cached"):
                        self._update_completed_state()
                        self._render_view()
                        self._set_status("v2_cache_loaded")
                        self._update_cache_status_row()
                    prof = get_profiler()
                    if prof is not None:
                        prof.event("v2_cache_hit_no_worker", **(self._last_cache_diag or {}))
                    return

            if self._worker is not None:
                try:
                    if hasattr(self._worker, "disarm"):
                        self._worker.disarm()
                    if self._worker.isRunning():
                        self._worker.request_cancel()
                except Exception:
                    pass
                self._worker = None

            gen = next_request_generation_id()
            self._v2_generation_id = gen
            self._running = True
            self._job_state = "computing"
            self.session.v2_job_status = "running"
            self._cache_status = "running"
            self._sequence_cancelled = False
            self._sequence_progress_frame = None
            self._sequence_candidate_running = False
            if mode == "sequence":
                self._sequence_frames = list(frames)
                self._sequence_generation_id = gen
                self._sequence_results = []
                self._sequence_last_completed_frame = None
                self._sequence_follow = True
                self._sequence_follow_paused_manual = False
                if self._chk_seq_follow is not None:
                    self._chk_seq_follow.blockSignals(True)
                    self._chk_seq_follow.setChecked(True)
                    self._chk_seq_follow.blockSignals(False)
                self._set_sequence_pane_visible(True)
                self._ensure_sequence_table_visible()
                cur = int(self._authoritative_frame())
                if cur not in frames:
                    self._suppress_follow_pause = True
                    try:
                        self._goto_frame(
                            int(frames[0]),
                            immediate=True,
                            pause_follow=False,
                            reason="sequence_start",
                        )
                    finally:
                        self._suppress_follow_pause = False
                self._update_sequence_follow_ui()
                self._update_features_empty_state()
            with span_timer("v2.pre.progress_widget_setup"):
                self.btn_run.setEnabled(False)
                self.btn_cancel.setEnabled(True)
                self.progress.setVisible(True)
                self.progress.setValue(0)
                if mode == "sequence":
                    self._update_sequence_progress_status()
                else:
                    self._set_run_state("v2_running")
            self._refresh_sequence_frame_state()

            # Prefer process-isolated V2 when raw frame(s) are already in memory.
            use_process = bool(self._use_process_v2) and mode == "single" and self._raw is not None
            with span_timer("v2.pre.frame_copy"):
                raw_copy = np.asarray(self._raw).copy() if use_process and self._raw is not None else None
            with span_timer("v2.pre.worker_thread_create"):
                if use_process:
                    self._worker = V2ProcessJobThread(
                        frames=frames,
                        profile=getattr(self.session, "profile", {}) or {},
                        profile_id=snap.profile_id,
                        signal_contract_id=snap.signal_contract_id,
                        cache=self._cache,
                        raw_by_frame={int(self.frame_spin.value()): raw_copy},
                        source_sha=self._source_sha,
                        force_recompute=force,
                        request_generation_id=gen,
                        parent=None,
                    )
                else:
                    # Never parent worker to this page — navigation must not destroy it.
                    self._worker = V2DiagnosticsWorker(
                        mat_path=snap.mat_path,
                        frames=frames,
                        profile=getattr(self.session, "profile", {}) or {},
                        profile_id=snap.profile_id,
                        signal_contract_id=snap.signal_contract_id,
                        cache=self._cache,
                        force_recompute=force,
                        request_generation_id=gen,
                        known_source_sha=self._source_sha,
                        parent=None,
                    )
            self._worker.progress.connect(self._on_worker_progress)
            self._worker.finished_ok.connect(self._on_worker_finished)
            self._worker.failed.connect(self._on_worker_failed)
            self._worker.cancelled.connect(self._on_worker_cancelled)
            if hasattr(self._worker, "frame_done"):
                self._worker.frame_done.connect(self._on_sequence_frame_done)
            with span_timer("v2.pre.worker_start"):
                self._morph_cache.counters.v2_request_count += 1
                self._worker.start()

    def _cancel_run(self) -> None:
        # Immediate UI acknowledgement — never waitForFinished / join / kill on UI thread.
        from ionogram_morphology_lab.ui.cancel_crash_audit import ensure_audit
        from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler

        t0 = time.perf_counter()
        audit = ensure_audit(enabled=True)
        text = "Отмена запрошена…" if self.i18n.language == "ru" else "Cancel requested…"
        self.stage_label.setText(text)
        self._show_inline(text)
        self._running = False
        old_gen = self._v2_generation_id
        self._v2_generation_id = next_request_generation_id()
        self._job_state = "cancel_requested"
        self.session.v2_job_status = ""
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(False)
        worker = self._worker
        self._worker = None
        if worker is not None:
            try:
                if hasattr(worker, "disarm"):
                    worker.disarm()
                # Disconnect UI slots before any process teardown callbacks
                try:
                    worker.progress.disconnect(self._on_worker_progress)
                    worker.finished_ok.disconnect(self._on_worker_finished)
                    worker.failed.disconnect(self._on_worker_failed)
                    worker.cancelled.disconnect(self._on_worker_cancelled)
                    if hasattr(worker, "frame_done"):
                        worker.frame_done.disconnect(self._on_sequence_frame_done)
                except Exception:
                    pass
                worker.request_cancel()
            except Exception as exc:  # noqa: BLE001
                audit.exception("fd_cancel_run", exc)
        self._sequence_cancelled = True
        self._refresh_sequence_frame_state()
        ack_s = time.perf_counter() - t0
        audit.parent("cancel_ack", gen_old=old_gen, gen_new=self._v2_generation_id, ack_s=ack_s)
        prof = get_profiler()
        if prof is not None:
            prof.span("cancel_ack", ack_s)

    def _on_worker_progress(self, info: dict) -> None:
        if str(info.get("request_generation_id") or "") != self._v2_generation_id:
            return
        self._pending_progress = info
        if not self._progress_throttle.isActive():
            self._flush_progress()
            self._progress_throttle.start()

    def _flush_progress(self) -> None:
        info = self._pending_progress
        if not info:
            return
        self._pending_progress = None
        if str(info.get("request_generation_id") or "") != self._v2_generation_id:
            return
        if "percent" in info:
            self.progress.setValue(int(info["percent"]))
        stage = info.get("job_state") or info.get("stage", "")
        self._job_state = str(stage)
        try:
            self._sequence_progress_frame = int(info["frame_index"])
        except (KeyError, TypeError, ValueError):
            pass
        ru = self.i18n.language == "ru"
        if self.tech_toggle.isChecked():
            self.stage_label.setText(
                f"{stage} | frame {info.get('frame_index', '—')} | "
                f"{info.get('frame_i', '')}/{info.get('frame_n', '')} | "
                f"cache_hits={info.get('cache_hits', 0)} recomputed={info.get('recomputed', 0)} | "
                f"elapsed={info.get('elapsed_s', 0):.1f}s"
            )
        elif self.mode_combo.currentData() == "sequence":
            self._update_sequence_progress_status()
        else:
            self.stage_label.setText(
                (
                    f"Расчёт V2: кадр {info.get('frame_i', '')}/{info.get('frame_n', '')}, "
                    f"{int(info.get('percent', 0))}%"
                )
                if ru
                else (
                    f"Computing V2: frame {info.get('frame_i', '')}/{info.get('frame_n', '')}, "
                    f"{int(info.get('percent', 0))}%"
                )
            )
        self._refresh_sequence_frame_state()
        self._update_features_empty_state()

    def _on_sequence_frame_done(self, row: dict) -> None:
        """Update sequence row; optionally follow-hydrate the completed frame (identity-guarded)."""
        if str(row.get("request_generation_id") or "") != self._v2_generation_id:
            return
        if self._source_sha and row.get("source_sha256") and row["source_sha256"] != self._source_sha:
            return
        frame = int(row.get("frame_index", -1))
        replaced = False
        for i, existing in enumerate(self._sequence_results):
            if int(existing.get("frame_index", -1)) == frame:
                self._sequence_results[i] = row
                replaced = True
                break
        if not replaced:
            self._sequence_results.append(row)
        if row.get("status") != "failed":
            self._sequence_last_completed_frame = frame
        if self.mode_combo.currentData() == "sequence":
            self._fill_sequence_table()
            self._ensure_sequence_table_visible()
            self._update_sequence_progress_status()
            follow = bool(self._sequence_follow) and not self._sequence_follow_paused_manual
            if follow:
                self._hydrate_sequence_row_to_inspector(row, reason="follow")
                return
            # Follow-off: update row/progress only — never rewrite selector intent.
        cur = int(self._authoritative_frame())
        if frame == cur and row.get("status") != "failed":
            self._apply_frame_result(row)
            if not (row.get("morph_candidate") or {}):
                self._hydrate_sequence_row_candidate(row, update_panel=True)
            else:
                self._bind_sequence_row_candidate(row)
            self._ensure_features_tab()
            self._populate_features()
            self._render_view()
        self._refresh_sequence_frame_state()
        self._update_features_empty_state()
        self._update_features_identity_line()

    def _hydrate_sequence_row_candidate(self, r: dict, *, update_panel: bool = False) -> None:
        """Resolve/evaluate candidate for one sequence row — existing sequence contract only."""
        ser = r.get("result")
        frame = int(r.get("frame_index") or 0)
        if not ser:
            r["morph_status"] = "v2_missing"
            r["morph_candidate"] = {}
            return
        if int(frame) != int(self.frame_spin.value()) and update_panel:
            # Never let another frame's hydrate overwrite the current panel.
            update_panel = False
        snap = resolve_active_source(self.session, force_rebuild=False)
        src = str((ser or {}).get("source_mat_sha256") or self._source_sha or "")
        project_root = str(self.session.project.root) if self.session.project else None
        r["geometry_review_status"] = geometry_review_status_for_frame(
            project_root, source_sha256=src, frame_index=frame
        )
        r["morph_review_status"] = r.get("morph_review_status") or "unreviewed"
        diag_id = make_cache_key(
            source_mat_sha256=src,
            frame_index=frame,
            profile_id=snap.profile_id or "",
            signal_contract_id=snap.signal_contract_id or str(ser.get("signal_contract_id") or ""),
            profile=getattr(self.session, "profile", {}) or {},
        ).digest()
        if update_panel and int(frame) == int(self.frame_spin.value()):
            self._sequence_candidate_running = True
            self._refresh_sequence_frame_state()
        try:
            out = resolve_or_evaluate_candidate(
                ser,
                diagnostics_cache_id=diag_id,
                cache=self._morph_cache,
                profile_id=str(snap.profile_id or ""),
                signal_contract_id=str(ser.get("signal_contract_id") or snap.signal_contract_id or ""),
                force=False,
                interpreted_time=format_hhmm(frame_to_minute(frame)),
            )
        except Exception:
            r["morph_status"] = "candidate_error"
            r["morph_candidate"] = {}
            out = None
        finally:
            if update_panel:
                self._sequence_candidate_running = False
        if not out:
            if update_panel:
                self._refresh_sequence_frame_state()
            return
        r["morph_status"] = out.get("status")
        r["morph_candidate"] = out.get("result") or {}
        if out.get("result"):
            r["morph_candidate"]["cache_status"] = out.get("status")
        if update_panel and int(frame) == int(self.frame_spin.value()):
            if out.get("status") in {"v2_incomplete_legacy", INCOMPLETE_LEGACY_CACHE}:
                self._morph_result = None
                self._morph_result_dict = None
                self._morph_cache_status = "v2_incomplete_legacy"
            elif out.get("result") is not None:
                self._morph_result_dict = out["result"]
                self._morph_result = out["result"]
                self._morph_identity = evidence_identity_from_result(out["result"])
                self._morph_cache_status = "cached" if out.get("cache_hit") else "new"
                self._restore_morph_review_status()
            self._refresh_morph_panel()
            self._sync_evidence_dialog_on_identity_change()

    def _on_worker_finished(self, payload: dict) -> None:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        if str(payload.get("request_generation_id") or "") != self._v2_generation_id:
            return  # stale V2 job
        with span_timer("v2.post_result"):
            with span_timer("v2.post.ui_ack"):
                self._running = False
                self._job_state = "completed"
                self.session.v2_job_status = ""
                self.btn_run.setEnabled(True)
                self.btn_cancel.setEnabled(False)
                self.progress.setVisible(False)
                self._ensure_sequence_table_interactive()
            # Reject previous-source results
            if self._source_sha and payload.get("source_sha") and payload["source_sha"] != self._source_sha:
                self._show_inline(
                    "Устаревший результат источника отклонён."
                    if self.i18n.language == "ru"
                    else "Stale previous-source result discarded."
                )
                self._refresh_sequence_frame_state()
                return
            with span_timer("v2.post.payload_apply"):
                results = payload.get("results") or []
                self._sequence_results = results
                ok_frames = [
                    int(r.get("frame_index", -1))
                    for r in results
                    if r.get("status") != "failed" and r.get("frame_index") is not None
                ]
                if ok_frames:
                    self._sequence_last_completed_frame = ok_frames[-1]
                cur = int(self._authoritative_frame())
                match = next((r for r in results if int(r.get("frame_index", -1)) == cur), None)
                if match is None and len(results) == 1:
                    match = results[0]
                seq_mode = self.mode_combo.currentData() == "sequence"
                follow = (
                    seq_mode
                    and bool(self._sequence_follow)
                    and not self._sequence_follow_paused_manual
                )
                if follow and self._sequence_last_completed_frame is not None:
                    last = next(
                        (
                            r
                            for r in results
                            if int(r.get("frame_index", -1)) == int(self._sequence_last_completed_frame)
                        ),
                        None,
                    )
                    if last and last.get("status") != "failed":
                        match = last
                if match and match.get("status") != "failed":
                    if follow or int(match.get("frame_index", -1)) == cur:
                        if int(match.get("frame_index", -1)) != cur:
                            self._suppress_follow_pause = True
                            try:
                                self._goto_frame(
                                    int(match["frame_index"]),
                                    immediate=True,
                                    pause_follow=False,
                                    reason="sequence_follow",
                                )
                            finally:
                                self._suppress_follow_pause = False
                        self._apply_frame_result(match)
            # Sequence table / candidate enrichment for sequence mode (any length).
            if seq_mode and self._sequence_results:
                with span_timer("v2.post.sequence_candidates"):
                    self._enrich_sequence_morph_candidates()
                with span_timer("v2.post.sequence_table"):
                    self._fill_sequence_table()
                cur = int(self._authoritative_frame())
                cur_row = next(
                    (r for r in self._sequence_results if int(r.get("frame_index", -1)) == cur),
                    None,
                )
                if cur_row and cur_row.get("morph_candidate") and int(cur_row.get("frame_index", -1)) == cur:
                    self._bind_sequence_row_candidate(cur_row)
                elif cur_row and not cur_row.get("morph_candidate"):
                    self._hydrate_sequence_row_candidate(cur_row, update_panel=True)
                self._ensure_features_tab()
                self._populate_features()
            elif len(self._sequence_results) > 1:
                with span_timer("v2.post.sequence_candidates"):
                    self._enrich_sequence_morph_candidates()
                with span_timer("v2.post.sequence_table"):
                    self._fill_sequence_table()
            self._update_completed_state()
            self._job_state = "rendering"
            with span_timer("v2.post.canvas_update"):
                self._render_view()
            self._job_state = "completed"
            self._refresh_sequence_frame_state()
            tech_payload = {
                "cache_hits": payload.get("cache_hits"),
                "recomputed": payload.get("recomputed"),
                "failures": payload.get("failures"),
                "elapsed_s": payload.get("elapsed_s", 0),
            }
            if match and match.get("timings"):
                self._timings = match["timings"]
                tech_payload["timings"] = self._timings
            with span_timer("v2.post.status_text"):
                if seq_mode:
                    self._update_sequence_progress_status()
                    self._show_inline(self.stage_label.text())
                else:
                    ru = self.i18n.language == "ru"
                    self._show_inline(
                        "Диагностика V2 завершена." if ru else "V2 diagnostics completed."
                    )
                    if self._features_tab_built and self.tech_toggle.isChecked():
                        self.stage_label.setText(json.dumps(tech_payload, ensure_ascii=False))
            # Defer large why/tech text unless those widgets are open
            if self.why_body.isVisible():
                with span_timer("v2.post.why_body"):
                    self.why_body.setPlainText(self._why_text() + "\n\n" + json.dumps(tech_payload, indent=2))
            self._update_cache_status_row()
            self._update_features_empty_state()
            self._update_features_identity_line()
            # Post-result must not re-resolve / reopen MAT — use cached snapshot.
            self._update_identity(resolve_active_source(self.session, force_rebuild=False))

    @staticmethod
    def _extract_sequence_row_payload(row: Mapping | dict | None) -> dict:
        """Canonical sequence-row identity extraction (wrapper + nested result).

        Trusted wrapper fields supply frame/source when the nested V2 result omits them.
        Never invents scientific values — only normalizes identity for UI binding.
        """
        r = dict(row or {})
        try:
            frame = int(r.get("frame_index", -1))
        except (TypeError, ValueError):
            frame = -1
        ser = r.get("result")
        if ser is not None and not isinstance(ser, dict):
            ser = None
        ser_out = dict(ser) if ser else None
        if ser_out is not None and frame >= 1:
            # Stamp trusted row-wrapper frame when nested result lacks frame_index.
            try:
                nested_frame = int(ser_out.get("frame_index", -1))
            except (TypeError, ValueError):
                nested_frame = -1
            if nested_frame < 1:
                ser_out["frame_index"] = frame
        src = str(
            r.get("source_sha256")
            or (ser_out or {}).get("source_mat_sha256")
            or ""
        )
        status = str(r.get("status") or "")
        feat_ver = str((ser_out or {}).get("feature_version") or FEATURE_VERSION)
        return {
            "frame_index": frame,
            "result": ser_out,
            "source_sha256": src,
            "status": status,
            "feature_version": feat_ver,
            "request_generation_id": str(r.get("request_generation_id") or ""),
            "morph_candidate": r.get("morph_candidate") or {},
            "morph_status": str(r.get("morph_status") or ""),
        }

    def _result_matches_intended_frame(self, ser: Mapping | dict | None) -> bool:
        """True when a bound V2 result is identity-compatible with the intended frame."""
        if not ser:
            return False
        intended = int(self._authoritative_frame())
        try:
            result_frame = int(ser.get("frame_index", -1))
        except (TypeError, ValueError):
            result_frame = -1
        if result_frame != intended:
            return False
        ser_src = str(ser.get("source_mat_sha256") or "")
        if ser_src and self._source_sha and ser_src != self._source_sha:
            return False
        return True

    def _apply_frame_result(self, match: dict) -> None:
        """Bind one sequence/single-frame V2 row into the inspector result slots.

        Lower-level binder: sets cache status, result/ser, summary, Features model.
        Full sequence-row UX hydration (selector, candidate, identity refresh) is
        ``_hydrate_sequence_row_to_inspector``.
        """
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("v2.post.apply_frame_result"):
            payload = self._extract_sequence_row_payload(match)
            status = payload["status"]
            self._cache_status = "cached" if status == "cached" else "recomputed"
            if status == "recomputed":
                self._v2_pipeline_runs += 1
            if match.get("pipeline_result") is not None:
                self._result = match["pipeline_result"]
                self._result_ser = self._result.to_serializable()
                self._masks = dict(self._result.masks)
                # Ensure serializable carries the trusted frame identity.
                if isinstance(self._result_ser, dict) and payload["frame_index"] >= 1:
                    if int(self._result_ser.get("frame_index", -1) or -1) < 1:
                        self._result_ser["frame_index"] = int(payload["frame_index"])
                if match.get("raw") is not None and int(payload["frame_index"]) == int(
                    self._authoritative_frame()
                ):
                    self._raw = match["raw"]
                    self._raw_sha = match.get("raw_frame_sha256") or frame_sha256(self._raw)
            else:
                self._result = None
                self._result_ser = payload["result"]
                self._masks = match.get("masks") or {}
            ser = self._result_ser or {}
            if isinstance(ser, dict) and payload["frame_index"] >= 1:
                if int(ser.get("frame_index", -1) or -1) < 1:
                    ser = dict(ser)
                    ser["frame_index"] = int(payload["frame_index"])
                    self._result_ser = ser
            self._last_known_source_sha = str(
                ser.get("source_mat_sha256") or payload["source_sha256"] or self._source_sha or ""
            )
            if payload["source_sha256"] and not self._source_sha:
                self._source_sha = payload["source_sha256"]
            self._display_cache.clear()
            if self._current_ctx:
                self._display_cache.bind_context(self._current_ctx)
            self._features_populated = False
            # Layer defaults without immediate double-render (render happens in post_result)
            if self._layers_built:
                for key, cb in self._layer_checks.items():
                    cb.blockSignals(True)
                    cb.setChecked(key in self.DEFAULT_LAYERS)
                    cb.blockSignals(False)
            for key, btn in getattr(self, "_quick_layer_btns", {}).items():
                btn.blockSignals(True)
                btn.setChecked(key in self.DEFAULT_LAYERS)
                btn.blockSignals(False)
            with span_timer("v2.post.summary_text"):
                self._populate_summary_from_ser()
            self._try_load_cached_morph(on_frame_activation=True)
            # Always bind Features model to the active frame result (single-frame inspector).
            with span_timer("v2.post.feature_model"):
                self._ensure_features_tab()
                self._populate_features()
            if hasattr(self, "inspector_tabs") and self.inspector_tabs.currentIndex() == 4:
                self._ensure_tech_tab()
                with span_timer("v2.post.tech_tab"):
                    self._refresh_tech_details()
            if match.get("cache_write_ok") is False:
                self._show_inline(
                    "Результат рассчитан; запись кэша не удалась (результат сохранён в сессии)."
                    if self.i18n.language == "ru"
                    else "Result computed; cache write failed (result kept in session)."
                )
            self._update_features_identity_line()
            self._update_features_empty_state()

    def _on_worker_failed(self, payload) -> None:
        if isinstance(payload, str):
            payload = {"error": payload, "request_generation_id": self._v2_generation_id}
        if str(payload.get("request_generation_id") or "") != self._v2_generation_id:
            return
        self._running = False
        self._job_state = "failed"
        self.session.v2_job_status = ""
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(False)
        self._cache_status = "error"
        user, tech = format_missing_variable_user_message(payload.get("error", ""), self.i18n.language)
        if self.mode_combo.currentData() == "sequence":
            self._update_sequence_progress_status()
            self.stage_label.setText(f"{self.stage_label.text()} · {user}")
        else:
            self._set_run_state("v2_failed", detail=user)
            self.stage_label.setText(f"failed | {user}")
        self._update_features_empty_state()

    def _on_worker_cancelled(self, payload=None) -> None:
        if isinstance(payload, dict) and str(payload.get("request_generation_id") or "") not in (
            "",
            self._v2_generation_id,
        ):
            return
        self._running = False
        self._job_state = "cancelled"
        self._sequence_cancelled = True
        self.session.v2_job_status = ""
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(False)
        self._set_status("cancelled")
        self._update_sequence_progress_status()
        self._refresh_sequence_frame_state()
        self._update_features_empty_state()

    def _sequence_row_values(self, r: dict) -> list[str]:
        ser = r.get("result") or {}
        feats = ser.get("features") or {}
        n_br = len(ser.get("centerlines") or [])
        inter = feats.get("v2_interference_fraction") or feats.get("v2_interference_level") or {}
        h = feats.get("v2_width_h_median") or feats.get("v2_horizontal_width_median") or {}
        v = feats.get("v2_width_v_median") or feats.get("v2_vertical_width_median") or {}
        morph = r.get("morph_candidate") or {}
        morph_status = str(r.get("morph_status") or morph.get("cache_status") or "candidate_not_calculated")
        return [
            str(r.get("frame_index")),
            format_hhmm(frame_to_minute(int(r.get("frame_index", 1)))),
            str(ser.get("quality_status", r.get("status", ""))),
            "yes" if n_br else "no",
            str(n_br),
            str(inter.get("value", "—") if isinstance(inter, dict) else "—"),
            str(h.get("value", "—") if isinstance(h, dict) else "—"),
            str(v.get("value", "—") if isinstance(v, dict) else "—"),
            str(morph.get("assessability", "—") if morph else "—"),
            str(morph.get("candidate", "—") if morph else "—"),
            str(morph.get("evidence_strength", "—") if morph else "—"),
            str((morph.get("h_evidence") or {}).get("supported", "—") if morph else "—"),
            str((morph.get("v_evidence") or {}).get("supported", "—") if morph else "—"),
            str((morph.get("interference") or {}).get("level", "—") if morph else "—"),
            str((morph.get("temporal_summary") or {}).get("present", "—") if morph else "—"),
            ";".join(morph.get("abstention_reasons") or []) if morph else "—",
            morph_status,
            str(r.get("morph_review_status", "unreviewed")),
            str(r.get("geometry_review_status", "geometry_unreviewed")),
        ]

    def _fill_sequence_table(self) -> None:
        rows = self._sequence_results
        seq_mode = self.mode_combo.currentData() == "sequence"
        self._set_sequence_pane_visible(seq_mode)
        # Never leave the embedded table disabled after run/completion.
        self._ensure_sequence_table_interactive()
        self.seq_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = self._sequence_row_values(r)
            for j, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setToolTip(val)
                self.seq_table.setItem(i, j, item)
            self._style_sequence_table_row(i, r)
        if not self._seq_column_profile_applied:
            self._restore_sequence_column_prefs()
            self._apply_sequence_column_profile(
                self.seq_table,
                profile=self._seq_table_profile,
                force_widths=True,
            )
            self._seq_column_profile_applied = True
        else:
            # Visibility only — do not ResizeToContents on every frame_done.
            self._apply_sequence_column_visibility(self.seq_table, self._seq_table_profile)
        self._sync_sequence_detach_table()
        self._apply_sequence_filter()
        if seq_mode:
            self._ensure_sequence_table_visible()
            self._select_sequence_table_row_for_frame(int(self.frame_spin.value()))

    def _ensure_sequence_table_interactive(self) -> None:
        """Embedded Sequence Results must stay enabled for scroll/select during and after run."""
        if getattr(self, "seq_table", None) is None:
            return
        if not self.seq_table.isEnabled():
            self.seq_table.setEnabled(True)
        pane = self._seq_pane
        if pane is not None and not pane.isEnabled():
            pane.setEnabled(True)
        if self._mid_vsplit is not None and not self._mid_vsplit.isEnabled():
            self._mid_vsplit.setEnabled(True)
        if self.seq_table.graphicsEffect() is not None:
            self.seq_table.setGraphicsEffect(None)

    def _restore_sequence_column_prefs(self) -> None:
        raw_prof = str(self._settings_get("fd_seq_table_profile", "compact") or "compact")
        self._seq_table_profile = "full" if raw_prof == "full" else "compact"
        raw_hidden = self._settings_get("fd_seq_hidden_columns", [])
        hidden: set[int] = set()
        if isinstance(raw_hidden, (list, tuple)):
            for x in raw_hidden:
                try:
                    idx = int(x)
                except (TypeError, ValueError):
                    continue
                if 0 <= idx < SEQ_COLUMN_COUNT and idx not in ESSENTIAL_COLUMNS:
                    hidden.add(idx)
        self._seq_user_hidden = hidden
        raw_widths = self._settings_get("fd_seq_column_widths", {})
        widths: dict[int, int] = {}
        if isinstance(raw_widths, dict):
            for k, v in raw_widths.items():
                try:
                    idx = int(k)
                    w = int(v)
                except (TypeError, ValueError):
                    continue
                if 0 <= idx < SEQ_COLUMN_COUNT and w >= 24:
                    widths[idx] = w
        self._seq_column_widths_user = widths

    def _persist_sequence_column_prefs(self) -> None:
        self._settings_set("fd_seq_table_profile", self._seq_table_profile)
        self._settings_set("fd_seq_hidden_columns", sorted(self._seq_user_hidden))
        self._settings_set(
            "fd_seq_column_widths",
            {str(k): int(v) for k, v in self._seq_column_widths_user.items()},
        )

    def _effective_visible_columns(self, profile: str) -> set[int]:
        base = set(visible_columns_for_profile(profile))
        # User may hide nonessential columns within the active profile.
        return (base - self._seq_user_hidden) | set(ESSENTIAL_COLUMNS)

    def _apply_sequence_column_visibility(self, table: QTableWidget, profile: str) -> None:
        visible = self._effective_visible_columns(profile)
        for j in range(table.columnCount()):
            table.setColumnHidden(j, j not in visible)

    def _apply_sequence_column_profile(
        self,
        table: QTableWidget,
        *,
        profile: str,
        force_widths: bool,
    ) -> None:
        """Apply view-specific visibility/widths. Never rebuilds the model."""
        self._apply_sequence_column_visibility(table, profile)
        self._seq_applying_column_widths = True
        try:
            if not force_widths and table is self.seq_table and self._seq_column_widths_user:
                mins = default_min_widths(table.font())
                for j, w in self._seq_column_widths_user.items():
                    if 0 <= j < table.columnCount() and not table.isColumnHidden(j):
                        table.setColumnWidth(j, max(int(w), mins.get(j, 36)))
                return
            prefs = preferred_widths(table.font())
            mins = default_min_widths(table.font())
            for j in range(table.columnCount()):
                if table.isColumnHidden(j):
                    continue
                if table is self.seq_table and j in self._seq_column_widths_user and not force_widths:
                    w = self._seq_column_widths_user[j]
                else:
                    w = prefs.get(j, mins.get(j, 48))
                table.setColumnWidth(j, max(int(w), mins.get(j, 36)))
        finally:
            self._seq_applying_column_widths = False

    def _on_sequence_column_resized(self, index: int, _old: int, new: int) -> None:
        if self._seq_applying_column_widths:
            return
        if new < 24 or index < 0:
            return
        # Only track embedded interactive resizes (not programmatic detach apply).
        if self.sender() is self.seq_table.horizontalHeader():
            self._seq_column_widths_user[int(index)] = int(new)
            self._persist_sequence_column_prefs()

    def _schedule_sequence_pane_resize(self, *_args) -> None:
        if self._seq_resize_debounce is not None:
            self._seq_resize_debounce.start()

    def _on_sequence_pane_resize_settled(self) -> None:
        # Debounced: keep visibility; do not ResizeToContents across all rows.
        if getattr(self, "seq_table", None) is None:
            return
        self._ensure_sequence_table_interactive()
        self._apply_sequence_column_visibility(self.seq_table, self._seq_table_profile)

    def _rebuild_sequence_columns_menu(self) -> None:
        menu = self._seq_columns_menu
        if menu is None:
            return
        menu.clear()
        ru = self.i18n.language == "ru"
        lang = "ru" if ru else "en"
        labels = sequence_header_labels(lang)
        hdr = QAction(
            (
                f"Профиль: {profile_label(self._seq_table_profile, lang)}"
                if ru
                else f"Profile: {profile_label(self._seq_table_profile, lang)}"
            ),
            menu,
        )
        hdr.setEnabled(False)
        menu.addAction(hdr)
        act_compact = QAction("Компактный набор" if ru else "Compact set", menu)
        act_compact.triggered.connect(lambda: self._set_sequence_table_profile("compact"))
        menu.addAction(act_compact)
        act_full = QAction("Показать все столбцы" if ru else "Show all columns", menu)
        act_full.triggered.connect(lambda: self._set_sequence_table_profile("full"))
        menu.addAction(act_full)
        act_reset = QAction(
            "Сбросить ширину столбцов" if ru else "Reset column widths",
            menu,
        )
        act_reset.triggered.connect(self._reset_sequence_column_widths)
        menu.addAction(act_reset)
        menu.addSeparator()
        visible = self._effective_visible_columns(self._seq_table_profile)
        profile_cols = set(visible_columns_for_profile(self._seq_table_profile))
        for j, lab in enumerate(labels):
            act = QAction(lab, menu)
            act.setCheckable(True)
            act.setChecked(j in visible)
            # Outside compact profile: show as unchecked and explain via tooltip.
            if j not in profile_cols and self._seq_table_profile == "compact":
                act.setToolTip(
                    "Скрыт в компактной таблице — «Показать все столбцы»"
                    if ru
                    else "Hidden in compact table — use “Show all columns”"
                )
            if j in ESSENTIAL_COLUMNS:
                act.setEnabled(False)
                act.setToolTip(
                    "Обязательный столбец" if ru else "Essential column"
                )
            else:
                act.triggered.connect(
                    lambda checked, col=j: self._toggle_sequence_column(col, checked)
                )
            menu.addAction(act)

    def _set_sequence_table_profile(self, profile: str) -> None:
        self._seq_table_profile = "full" if profile == "full" else "compact"
        if self._seq_table_profile == "compact":
            # Drop user-hides that are outside compact — they are already profile-hidden.
            compact = set(COMPACT_VISIBLE_COLUMNS)
            self._seq_user_hidden = {c for c in self._seq_user_hidden if c in compact}
        else:
            self._seq_user_hidden.clear()
        self._seq_column_widths_user.clear()
        self._apply_sequence_column_profile(
            self.seq_table,
            profile=self._seq_table_profile,
            force_widths=True,
        )
        self._persist_sequence_column_prefs()
        self.retranslate_ui()

    def _reset_sequence_column_widths(self) -> None:
        self._seq_column_widths_user.clear()
        self._apply_sequence_column_profile(
            self.seq_table,
            profile=self._seq_table_profile,
            force_widths=True,
        )
        self._persist_sequence_column_prefs()

    def _toggle_sequence_column(self, col: int, checked: bool) -> None:
        if col in ESSENTIAL_COLUMNS:
            return
        if checked:
            self._seq_user_hidden.discard(col)
            # Showing a column outside compact profile promotes to full.
            if col not in visible_columns_for_profile(self._seq_table_profile):
                self._seq_table_profile = "full"
        else:
            self._seq_user_hidden.add(col)
        self._apply_sequence_column_visibility(self.seq_table, self._seq_table_profile)
        self._persist_sequence_column_prefs()

    def _fit_sequence_columns(self) -> None:
        """Legacy entry: reset widths for the active embedded profile (manual only)."""
        self._reset_sequence_column_widths()

    def _on_sequence_cell_clicked(self, row: int, _col: int) -> None:
        self._open_sequence_row(row, _col)

    def _open_sequence_row(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self._sequence_results):
            return
        r = self._sequence_results[row]
        self._pause_sequence_follow_manual()
        self._hydrate_sequence_row_to_inspector(r, reason="manual")

    def _bind_sequence_row_candidate(self, r: dict) -> None:
        morph = r.get("morph_candidate") or {}
        if not morph:
            return
        if int(r.get("frame_index", -1)) != int(self.frame_spin.value()):
            return
        self._morph_result_dict = morph
        self._morph_result = morph
        self._morph_identity = evidence_identity_from_result(morph)
        st = str(r.get("morph_status") or "")
        self._morph_cache_status = "cached" if st in {"cached", "candidate_cached"} else "new"
        self._refresh_morph_panel()
        self._sync_evidence_dialog_on_identity_change()

    def _on_sequence_follow_toggled(self, checked: bool) -> None:
        self._sequence_follow = bool(checked)
        if checked:
            self._sequence_follow_paused_manual = False
            self._resume_sequence_follow()
        else:
            self._sequence_follow_paused_manual = True
            self._update_sequence_follow_ui()

    def _pause_sequence_follow_manual(self) -> None:
        if self.mode_combo.currentData() != "sequence":
            return
        if self._suppress_follow_pause:
            return
        if not (self._running or self._sequence_results or self._sequence_frames):
            return
        self._sequence_follow = False
        self._sequence_follow_paused_manual = True
        if self._chk_seq_follow is not None:
            self._chk_seq_follow.blockSignals(True)
            self._chk_seq_follow.setChecked(False)
            self._chk_seq_follow.blockSignals(False)
        self._update_sequence_follow_ui()

    def _resume_sequence_follow(self) -> None:
        self._sequence_follow = True
        self._sequence_follow_paused_manual = False
        if self._chk_seq_follow is not None:
            self._chk_seq_follow.blockSignals(True)
            self._chk_seq_follow.setChecked(True)
            self._chk_seq_follow.blockSignals(False)
        self._update_sequence_follow_ui()
        latest = self._sequence_last_completed_frame
        if latest is None:
            return
        row = next(
            (r for r in self._sequence_results if int(r.get("frame_index", -1)) == int(latest)),
            None,
        )
        if row is not None:
            self._hydrate_sequence_row_to_inspector(row, reason="resume")

    def _show_latest_processed_sequence_frame(self) -> None:
        latest = self._sequence_last_completed_frame
        if latest is None:
            return
        row = next(
            (r for r in self._sequence_results if int(r.get("frame_index", -1)) == int(latest)),
            None,
        )
        if row is None:
            return
        self._pause_sequence_follow_manual()
        self._hydrate_sequence_row_to_inspector(row, reason="latest")

    def _update_sequence_follow_ui(self) -> None:
        ru = self.i18n.language == "ru"
        seq = hasattr(self, "mode_combo") and self.mode_combo.currentData() == "sequence"
        outside = bool(seq and not self._current_frame_in_sequence())
        paused = bool(seq and self._sequence_follow_paused_manual)
        if self._btn_resume_follow is not None:
            self._btn_resume_follow.setVisible(bool(paused or (outside and not self._sequence_follow)))
        if self._btn_show_latest_seq is not None:
            self._btn_show_latest_seq.setVisible(
                bool(
                    seq
                    and self._sequence_last_completed_frame is not None
                    and (paused or outside)
                )
            )
        if self._seq_follow_status is not None:
            if outside:
                fr = int(self.frame_spin.value()) if hasattr(self, "frame_spin") else 0
                self._seq_follow_status.setText(
                    f"Кадр {fr} не входит в выбранную последовательность. "
                    "Выберите строку результатов или включите «Следовать за обработкой»."
                    if ru
                    else f"Frame {fr} is not part of the selected sequence. "
                    "Select a results row or enable “Follow processing”."
                )
                self._seq_follow_status.show()
            elif paused:
                self._seq_follow_status.setText(
                    "Автоматическое следование приостановлено: выбран кадр вручную."
                    if ru
                    else "Automatic follow paused: a frame was selected manually."
                )
                self._seq_follow_status.show()
            elif seq and not self._sequence_follow:
                self._seq_follow_status.setText(
                    "Следование за обработкой выключено."
                    if ru
                    else "Follow processing is off."
                )
                self._seq_follow_status.show()
            else:
                self._seq_follow_status.hide()

    def _update_sequence_progress_status(self) -> None:
        if not hasattr(self, "mode_combo") or self.mode_combo.currentData() != "sequence":
            return
        total = len(self._sequence_frames) or len(self._sequence_results)
        completed = sum(
            1
            for r in self._sequence_results
            if str(r.get("status") or "") not in {"", "failed"} or r.get("result")
        )
        # Count failed as processed for progress denominator messaging
        processed = len(self._sequence_results)
        lang = "ru" if self.i18n.language == "ru" else "en"
        text = format_sequence_progress_status(
            lang=lang,
            completed=processed,
            total=max(total, processed),
            progress_frame=self._sequence_progress_frame,
            last_completed_frame=self._sequence_last_completed_frame,
            running=bool(self._running),
            cancelled=bool(self._sequence_cancelled) or self._job_state == "cancelled",
            finished=(not self._running) and processed > 0 and (
                processed >= total if total else True
            ) and self._job_state in {"completed", "idle", "rendering"},
        )
        self.stage_label.setText(text)
        # Avoid leaving a perpetual generic pipeline-running banner.
        if not self._running and self._job_state == "completed":
            self.state_label.setText(text)

    def _select_sequence_table_row_for_frame(self, frame: int) -> None:
        if not hasattr(self, "seq_table"):
            return
        for i in range(self.seq_table.rowCount()):
            item = self.seq_table.item(i, 0)
            if item is None:
                continue
            try:
                if int(item.text()) == int(frame):
                    self.seq_table.blockSignals(True)
                    self.seq_table.selectRow(i)
                    self.seq_table.blockSignals(False)
                    self.seq_table.scrollToItem(item)
                    return
            except ValueError:
                continue

    def _style_sequence_table_row(
        self,
        row_index: int,
        r: dict,
        *,
        table: QTableWidget | None = None,
    ) -> None:
        target = table if table is not None else self.seq_table
        ru = self.i18n.language == "ru"
        frame = int(r.get("frame_index", -1))
        status = str(r.get("status") or "")
        displayed = frame == int(self.frame_spin.value())
        processing = (
            self._running
            and self._sequence_progress_frame is not None
            and int(self._sequence_progress_frame) == frame
            and status not in {"cached", "recomputed", "failed"}
        )
        last = (
            self._sequence_last_completed_frame is not None
            and int(self._sequence_last_completed_frame) == frame
        )
        failed = status == "failed"
        cached = status == "cached"
        tip_parts = []
        if displayed:
            tip_parts.append("Отображаемый кадр" if ru else "Displayed frame")
        elif failed:
            tip_parts.append("Ошибка обработки" if ru else "Processing failed")
        elif processing:
            tip_parts.append("Сейчас обрабатывается" if ru else "Currently processing")
        elif last:
            tip_parts.append("Последний завершённый" if ru else "Last completed")
        elif cached:
            tip_parts.append("Результат из кэша" if ru else "Cached result")
        marker_tip = " · ".join(tip_parts) if tip_parts else (
            "Строка последовательности" if ru else "Sequence row"
        )
        colors = marker_colors(
            displayed=displayed,
            failed=failed,
            processing=processing,
            last_completed=last and not displayed and not failed and not processing,
            cached=cached and not displayed and not failed and not processing and not last,
            theme=resolve_theme_name(self._theme_pref),
        )
        for j in range(target.columnCount()):
            item = target.item(row_index, j)
            if item is None:
                continue
            item.setBackground(colors.background)
            item.setForeground(colors.foreground)
            # Full cell value always available via tooltip (elision-safe).
            cell = item.text()
            item.setToolTip(f"{cell}\n{marker_tip}" if cell else marker_tip)
            # Keep items enabled so Disabled palette never washes out row text.
            item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
            )

    def _hydrate_sequence_row_to_inspector(self, row: dict, *, reason: str = "") -> None:
        """Complete sequence-row hydration into the single-frame inspector (no V2 rerun).

        Establishes selector intent, binds V2 result via ``_apply_frame_result``,
        hydrates/binds candidate, refreshes Features identity/empty state.
        """
        payload = self._extract_sequence_row_payload(row)
        frame = int(payload["frame_index"])
        if frame < 1:
            return
        gen = str(payload.get("request_generation_id") or "")
        if gen and gen not in {self._v2_generation_id, self._sequence_generation_id}:
            return
        if self._source_sha and payload["source_sha256"] and payload["source_sha256"] != self._source_sha:
            return
        nav_reason = {
            "follow": "sequence_follow",
            "resume": "resume_follow",
            "manual": "sequence_row_selection",
            "latest": "sequence_row_selection",
        }.get(reason, "sequence_row_selection")
        self._suppress_follow_pause = True
        self._features_hydrating = True
        self._update_features_empty_state()
        self._goto_frame(frame, immediate=True, pause_follow=False, reason=nav_reason)
        apply_nav_gen = int(self._frame_navigation_generation)

        def _apply_when_ready() -> None:
            try:
                if int(self._frame_navigation_generation) != apply_nav_gen:
                    return
                if int(self._authoritative_frame()) != frame:
                    return
                if payload["status"] == "failed":
                    self._features_populated = False
                    if self._features_model is not None:
                        self._features_model.clear()
                    self._refresh_sequence_frame_state()
                    return
                if payload["status"] not in {"cached", "recomputed"} and not payload["result"]:
                    # Pending row — do not rerun V2.
                    self._features_populated = False
                    if self._features_model is not None:
                        self._features_model.clear()
                    self._refresh_sequence_frame_state()
                    return
                ready = self.wait_until_frame_ready(10000)
                if not ready:
                    return
                if int(self._frame_navigation_generation) != apply_nav_gen:
                    return
                if int(self._authoritative_frame()) != frame:
                    return
                # Re-bind with stamped identity (wrapper frame → nested result).
                bind_row = dict(row)
                if payload["result"] is not None:
                    bind_row["result"] = payload["result"]
                self._apply_frame_result(bind_row)
                if payload["morph_candidate"]:
                    self._bind_sequence_row_candidate(bind_row)
                else:
                    self._hydrate_sequence_row_candidate(bind_row, update_panel=True)
                self._ensure_features_tab()
                self._populate_features()
                self._render_view()
                self._select_sequence_table_row_for_frame(frame)
                if reason == "follow" and payload["status"] != "failed":
                    ru = self.i18n.language == "ru"
                    self._show_inline(
                        f"Кадр {frame} завершён. Признаки и кандидат загружены."
                        if ru
                        else f"Frame {frame} completed. Features and candidate loaded."
                    )
                self._refresh_sequence_frame_state()
            finally:
                self._features_hydrating = False
                self._suppress_follow_pause = False
                self._update_features_empty_state()
                self._update_features_identity_line()
                self._update_sequence_progress_status()
                self._fill_sequence_table()

        QTimer.singleShot(0, _apply_when_ready)

    def _current_frame_in_sequence(self) -> bool:
        frames = self._sequence_frames or self._selected_sequence_frames()
        if not frames:
            return True
        return int(self._authoritative_frame()) in {int(f) for f in frames}

    def _update_features_identity_line(self) -> None:
        if self._features_identity_label is None:
            return
        ru = self.i18n.language == "ru"
        snap = resolve_active_source(self.session, force_rebuild=False)
        mat = snap.mat_filename or "—"
        # Authoritative: intended/selected frame. Never prefer a stale _loaded_frame.
        frame = int(self._authoritative_frame()) if hasattr(self, "frame_spin") else 0
        ser = self._result_ser or (self._result.to_serializable() if self._result else None)
        matching_result = self._result_matches_intended_frame(ser)
        if matching_result and ser is not None:
            try:
                frame = int(ser.get("frame_index", frame))
            except (TypeError, ValueError):
                pass
        time_s = format_hhmm(frame_to_minute(frame))
        v2 = self._cache_status or "not_computed"
        if not matching_result and v2 in {"cached", "recomputed"}:
            # Stale result status must not advertise ready for another intended frame.
            v2 = "not_computed"
        if v2 == "cached":
            v2_l = "V2 из кэша" if ru else "V2 cached"
        elif v2 == "recomputed":
            v2_l = "V2 новый" if ru else "V2 new"
        elif v2 == "running":
            v2_l = "V2 выполняется" if ru else "V2 running"
        else:
            v2_l = "V2 не готов" if ru else "V2 not ready"
        state = self._sequence_frame_state if self.mode_combo.currentData() == "sequence" else ""
        state_l = ""
        if matching_result and v2 in {"cached", "recomputed"}:
            state_l = " · " + ("готово" if ru else "ready")
        elif state in {
            "sequence_v2_pending",
            "sequence_frame_not_yet_processed",
            "sequence_v2_running_current_frame",
        }:
            state_l = " · " + ("ожидание" if ru else "pending")
        elif matching_result and state in {
            "sequence_candidate_ready",
            "sequence_candidate_cached",
            "sequence_v2_ready_candidate_pending",
        }:
            state_l = " · " + ("готово" if ru else "ready")
        elif state == "sequence_frame_failed":
            state_l = " · " + ("ошибка" if ru else "failed")
        elif not matching_result and self.mode_combo.currentData() == "sequence":
            state_l = " · " + ("ожидание" if ru else "pending")
        ver = str((ser or {}).get("feature_version") or FEATURE_VERSION) if matching_result else FEATURE_VERSION
        text = (
            f"Источник: {mat} · Кадр: {frame} · Время: {time_s} · {v2_l} · {ver}{state_l}"
            if ru
            else f"Source: {mat} · Frame: {frame} · Time: {time_s} · {v2_l} · {ver}{state_l}"
        )
        self._features_identity_label.setText(text)

    def _update_features_empty_state(self) -> None:
        if self._features_empty_label is None:
            return
        lang = "ru" if self.i18n.language == "ru" else "en"
        has_rows = bool(self._features_populated and self._features_model and self._features_model.rowCount() > 0)
        if has_rows and not self._features_hydrating:
            self._features_empty_label.hide()
            if self._features_view is not None:
                self._features_view.show()
            return
        kind = "no_result"
        # Pending/outside UI must use intended frame, never a stale loaded frame.
        frame = int(self._authoritative_frame()) if hasattr(self, "frame_spin") else 0
        ser = self._result_ser or (self._result.to_serializable() if self._result else None)
        if self._features_hydrating:
            kind = "hydrating"
        elif self.mode_combo.currentData() == "sequence":
            if not self._current_frame_in_sequence():
                kind = "outside_sequence"
            else:
                row = next(
                    (r for r in self._sequence_results if int(r.get("frame_index", -1)) == frame),
                    None,
                )
                if row is not None and str(row.get("status") or "") == "failed":
                    kind = "failed"
                elif not ser:
                    kind = "pending"
                elif self._morph_cache_status == "v2_incomplete_legacy":
                    self._features_empty_label.setText(legacy_incomplete_message(lang))
                    self._features_empty_label.show()
                    if self._features_view is not None and not has_rows:
                        self._features_view.hide()
                    return
                elif not (ser.get("features") or {}):
                    kind = "not_applicable"
        elif not ser:
            kind = "pending" if self._running else "no_result"
        elif not (ser.get("features") or {}):
            kind = "not_applicable"
        self._features_empty_label.setText(features_empty_message(kind, lang, frame=frame))
        self._features_empty_label.show()
        if self._features_view is not None and not has_rows:
            self._features_view.hide()
        if kind == "outside_sequence":
            self._update_sequence_follow_ui()

    def _request_contact_sheet(self) -> None:
        """Lazy contact sheet — only after explicit request."""
        if not self._sequence_results:
            return
        ru = self.i18n.language == "ru"
        self.contact_label.setVisible(True)
        self.contact_label.setText(
            f"{'Контактный лист' if ru else 'Contact sheet'}: "
            f"{len(self._sequence_results)} "
            f"{'кадров (миниатюры по запросу — откройте строку таблицы)' if ru else 'frames (thumbnails on demand — open a table row)'}"
        )

    def _clear_v2_cache(self) -> None:
        if not self._source_sha:
            return
        ru = self.i18n.language == "ru"
        ans = QMessageBox.question(
            self,
            "IML",
            (
                "Очистить кэш V2 для текущего источника? Исходный MAT не будет изменён."
                if ru
                else "Clear V2 cache for the current source? The source MAT will not be modified."
            ),
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        n = self._cache.clear_for_source(self._source_sha)
        self.clear_results()
        self._cache_status = "not_computed"
        self._show_inline(
            f"Удалено записей кэша: {n}" if ru else f"Cache entries removed: {n}"
        )
        self.refresh()

    def _check_prerequisites(self) -> tuple[bool, str]:
        """Validate V2 request from ActiveSourceSnapshot + in-memory context — no MAT I/O."""
        snap = resolve_active_source(self.session, force_rebuild=False)
        if not snap.project_open:
            return False, "project_not_open"
        if snap.status == SourceStatus.INVENTORY_INACTIVE:
            return False, "mat_not_active"
        if snap.mat_path is None or not snap.is_active:
            return False, "no_active_mat"
        if snap.status == SourceStatus.MISSING:
            return False, "mat_path_missing"
        if snap.status == SourceStatus.INCOMPATIBLE or (
            snap.role and not snap.can_activate
        ):
            return False, "incompatible_source"
        if not snap.profile_id:
            return False, "profile_missing"
        return True, ""

    def is_job_running(self) -> bool:
        return bool(self._running)

    def current_raw_frame_sha(self) -> str:
        return self._raw_sha

    def display_orientation(self) -> dict:
        return orientation_identity_dict()

    def current_context(self) -> FrameDiagnosticContext | None:
        return self._current_ctx

    def job_state(self) -> str:
        return self._job_state

    # ----- summary / features -----
    def _populate_summary(self) -> None:
        self._populate_summary_from_ser()

    def _populate_summary_from_ser(self) -> None:
        ser = self._result_ser
        if ser is None and self._result is not None:
            ser = self._result.to_serializable()
        if ser is None:
            self.summary_view.clear()
            if hasattr(self, "summary_empty"):
                self.summary_empty.show()
            return
        if hasattr(self, "summary_empty"):
            self.summary_empty.hide()
        # Pure formatting — mat name from context/snapshot, never reopen MAT.
        mat_name = ""
        if self._current_ctx is not None:
            mat_name = Path(str(self._current_ctx.source_mat_path or "")).name
        if not mat_name and self._loaded_mat_path:
            mat_name = Path(self._loaded_mat_path).name
        if not mat_name:
            mat_name = resolve_active_source(self.session, force_rebuild=False).mat_filename or "—"

        class _R:
            pass

        r = _R()
        r.features = {}
        from ionogram_morphology_lab.features.v2.types import MeasuredFeature

        for k, v in (ser.get("features") or {}).items():
            if isinstance(v, dict):
                r.features[k] = MeasuredFeature(
                    feature_id=k,
                    value=v.get("value"),
                    unit=v.get("unit", ""),
                    valid=bool(v.get("valid", True)),
                    reason_invalid=v.get("reason_invalid", ""),
                    affected_region=v.get("affected_region", ""),
                )
        r.centerlines = ser.get("centerlines") or []
        r.component_decisions = ser.get("component_decisions") or {}
        r.oversegmentation_suspected = bool(ser.get("oversegmentation_suspected"))
        r.quality_status = ser.get("quality_status", "")
        self.summary_view.setPlainText(
            build_human_summary(
                r,
                language=self.i18n.language,
                mat_name=mat_name or "—",
                frame=int(self.frame_spin.value()),
                feature_version=FEATURE_VERSION,
            )
        )

    def _on_inspector_tab(self, index: int) -> None:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        if index == 1:
            with span_timer("fd.features_tab.activate"):
                t0 = time.perf_counter()
                self._ensure_features_tab()
                if (self._result_ser or self._result):
                    # Always refresh model from current ser (cheap); skip MAT/V2
                    self._populate_features()
                with span_timer("fd.features.first_paint"):
                    if self._features_view is not None:
                        self._features_view.viewport().update()
                _ = time.perf_counter() - t0
        elif index == 3:
            self._ensure_review_tab()
        elif index == 4:
            self._ensure_tech_tab()
            self._refresh_tech_details()

    def _on_tech_toggle(self, *_args) -> None:
        if self._features_model is not None:
            self._features_model.set_show_technical_ids(self.tech_toggle.isChecked())
        elif self._features_tab_built and self._features_populated:
            self._populate_features()

    def _on_zoom_mode(self, *_args) -> None:
        mode = self.zoom_mode.currentData() if hasattr(self, "zoom_mode") else "fit"
        if mode == "100":
            self._zoom = 1.0
        elif mode == "compact":
            self._zoom = 0.55
        elif mode == "large":
            self._zoom = 1.6
        elif mode == "natural":
            self._zoom = 1.0
        else:
            self._zoom = 0.0  # fit balanced
        self._render_view()

    def _layer_checked(self, key: str) -> bool:
        cb = self._layer_checks.get(key)
        if cb is not None:
            return bool(cb.isChecked())
        # Before drawer built: prefer quick-button state, else defaults
        btn = getattr(self, "_quick_layer_btns", {}).get(key)
        if btn is not None:
            return bool(btn.isChecked())
        return key in self.DEFAULT_LAYERS

    def _on_quick_layer(self, key: str, on: bool) -> None:
        if self._layers_built:
            cb = self._layer_checks.get(key)
            if cb is not None:
                cb.blockSignals(True)
                cb.setChecked(bool(on))
                cb.blockSignals(False)
        self._render_view()

    def _sync_quick_layers_from_checks(self) -> None:
        if not hasattr(self, "_quick_layer_btns"):
            return
        for key, btn in self._quick_layer_btns.items():
            on = self._layer_checked(key)
            btn.blockSignals(True)
            btn.setChecked(on)
            btn.blockSignals(False)

    def _refresh_tech_details(self) -> None:
        if not hasattr(self, "tech_details"):
            return
        from ionogram_morphology_lab.ui.build_identity import collect_build_identity, format_build_identity
        from ionogram_morphology_lab.ui.fd_frame_loader import nav_stats
        from ionogram_morphology_lab.ui.v2_process_worker import worker_start_count
        from ionogram_morphology_lab.utils.paths import app_root

        settings = getattr(self.session, "settings", None)
        cache_root = settings.cache_dir() if settings is not None else ""
        # Never re-hash EXE on the UI thread during ordinary tab opens.
        ident = collect_build_identity(
            cache_root=cache_root,
            workspace_root=app_root() / "workspaces",
            active_project_path=getattr(self.session.project, "root", None) if self.session.project else None,
            compute_sha=False,
        )
        svc = getattr(self.session, "source_service", None)
        svc_c = svc.counters.as_dict() if svc is not None else {}
        lines = [
            format_build_identity(ident, self.i18n.language),
            "",
            "=== FD counters ===",
            f"job_state: {self._job_state}",
            f"cache_status: {self._cache_status}",
            f"loaded_frame: {self._loaded_frame}",
            f"source_sha: {(self._source_sha or '')[:24]}",
            f"v2_pipeline_runs: {self._v2_pipeline_runs}",
            f"registry_reload_count: {self._registry_reload_count}",
            f"features_populated: {self._features_populated}",
            f"worker_start_count: {worker_start_count()}",
            f"nav_stats: {nav_stats()}",
            f"source_service: {svc_c}",
            f"timings: {self._visible_timings}",
            f"identity_row: {self.identity.text()}",
        ]
        self.tech_details.setPlainText("\n".join(lines))

    def _refill_features_category_combo(self) -> None:
        if self._features_cat is None:
            return
        lang = "ru" if self.i18n.language == "ru" else "en"
        prev = self._features_cat.currentData()
        self._features_cat.blockSignals(True)
        self._features_cat.clear()
        for data, label in feature_group_filter_items(lang):
            self._features_cat.addItem(label, data)
        idx = max(0, self._features_cat.findData(prev or "all"))
        self._features_cat.setCurrentIndex(idx)
        self._features_cat.blockSignals(False)

    def _on_features_filter(self, *_args) -> None:
        if self._features_proxy is None:
            return
        cat = self._features_cat.currentData() if self._features_cat is not None else "all"
        needle = self._features_search.text() if self._features_search is not None else ""
        self._features_proxy.set_category(str(cat or "all"))
        self._features_proxy.set_search(needle)

    def _populate_features(self, *_args) -> None:
        if not self._features_tab_built or self._features_model is None:
            return
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        with span_timer("fd.features.model_build"):
            ser = self._result_ser
            if ser is None and self._result is not None:
                ser = self._result.to_serializable()
            with span_timer("fd.features.registry_access"):
                # Registry is lru-cached; count once per populate for profiler visibility
                self._registry_reload_count += 1
            lang = "ru" if self.i18n.language == "ru" else "en"
            self._features_model.set_language(lang)
            self._features_model.set_show_technical_ids(self.tech_toggle.isChecked())
            with span_timer("fd.features.presentation_build"):
                self._features_model.load_from_serializable(ser)
            self._features_populated = bool(ser) and bool((ser or {}).get("features"))
            if self.explain is not None:
                self.explain.clear()
            if self._features_view is not None and self._features_populated:
                self._features_view.show()
            self._sync_features_detach_on_frame()
            self._update_features_identity_line()
            self._update_features_empty_state()

    def _on_feature_row(self, current, _previous) -> None:
        if self._features_model is None or self._features_proxy is None or not current.isValid():
            return
        src = self._features_proxy.mapToSource(current)
        fid = self._features_model.feature_id_at(src.row())
        if not fid:
            return
        ser = self._result_ser or (self._result.to_serializable() if self._result else {})
        feat_d = (ser.get("features") or {}).get(fid) or {}
        lang = "ru" if self.i18n.language == "ru" else "en"
        # Explanations built only for the selected row
        registry_text = explain_feature(fid, feat_d, lang=lang)

        class _F:
            pass

        f = _F()
        f.value = feat_d.get("value")
        f.unit = feat_d.get("unit", "")
        f.valid = bool(feat_d.get("valid", True))
        f.reason_invalid = feat_d.get("reason_invalid", "")
        f.affected_region = feat_d.get("affected_region", "")
        self.explain.setPlainText(explain_feature_human(fid, f, lang, registry_text))

    def _on_feature_item(self, current, _previous) -> None:
        # Backward-compatible alias (legacy QListWidget path)
        self._on_feature_row(current, _previous)

    def _save_geometry_review(self) -> None:
        snap = resolve_active_source(self.session, force_rebuild=False)
        if self.session.project is None or snap.mat_path is None:
            return
        key = self._cache_key()
        review = {
            "review_kind": "geometry_only",
            "not_morphology_ground_truth": True,
            "status": self.review_combo.currentData(),
            "comment": self.review_comment.toPlainText().strip(),
            "source_sha256": self._source_sha,
            "frame_index": int(self.frame_spin.value()),
            "feature_version": FEATURE_VERSION,
            "diagnostics_cache_id": key.digest(),
            "shadow_mode": True,
        }
        path = save_geometry_review_update_in_place(self.session.project.root, review)
        corpus = load_geometry_review_corpus(self.session.project.root)
        ru = self.i18n.language == "ru"
        self._show_inline(
            (
                f"Отзыв сохранён: {path.name}. "
                f"Логических кадров: {corpus.logical_reviewed_frames}; "
                f"файлов: {corpus.files_found}; устаревших: {corpus.superseded_reviews}."
            )
            if ru
            else (
                f"Review saved: {path.name}. "
                f"Logical frames: {corpus.logical_reviewed_frames}; "
                f"files: {corpus.files_found}; superseded: {corpus.superseded_reviews}."
            )
        )

    # ----- layers / render -----
    def _on_layer_toggled(self, *_args) -> None:
        # Display-only: never rerun V2 or rewrite scientific cache
        self._sync_quick_layers_from_checks()
        self._render_view()

    def _show_default_layers(self) -> None:
        if self._layers_built:
            for key, cb in self._layer_checks.items():
                cb.blockSignals(True)
                cb.setChecked(key in self.DEFAULT_LAYERS)
                cb.blockSignals(False)
        for key, btn in getattr(self, "_quick_layer_btns", {}).items():
            btn.blockSignals(True)
            btn.setChecked(key in self.DEFAULT_LAYERS)
            btn.blockSignals(False)
        self._render_view()

    def _hide_overlays(self) -> None:
        if self._layers_built:
            for key, cb in self._layer_checks.items():
                cb.blockSignals(True)
                cb.setChecked(key == "raw")
                cb.blockSignals(False)
        for key, btn in getattr(self, "_quick_layer_btns", {}).items():
            btn.blockSignals(True)
            btn.setChecked(key == "raw")
            btn.blockSignals(False)
        self._render_view()

    def _apply_view_preset(self) -> None:
        preset = self.view_preset.currentData()
        mapping = {
            "source": ("raw",),
            "trace": ("raw", "trace_accepted", "centerline"),
            "interference": ("raw", "interference", "excluded"),
            "widths": ("raw", "vertical_width_map", "horizontal_width_map", "centerline"),
            "all": tuple(k for k, *_ in self.LAYER_KEYS),
        }
        keys = mapping.get(preset, self.DEFAULT_LAYERS)
        if self._layers_built:
            for key, cb in self._layer_checks.items():
                cb.blockSignals(True)
                cb.setChecked(key in keys)
                cb.blockSignals(False)
        for key, btn in getattr(self, "_quick_layer_btns", {}).items():
            btn.blockSignals(True)
            btn.setChecked(key in keys)
            btn.blockSignals(False)
        self._render_view()

    def _ensure_visible_masks(self) -> None:
        """Load only cached masks that are currently visible."""
        if not self._result_ser or not self._source_sha:
            return
        needed: list[str] = []
        for key, _ru, _en, rgba in self.LAYER_KEYS:
            if key in ("raw", "diagnostic_normalized", "centerline") or rgba[3] == 0:
                continue
            if self._layer_checked(key) and key not in self._masks:
                needed.append(key)
        if not needed:
            return
        try:
            self._masks.update(self._cache.load_layers(self._cache_key(), needed))
        except Exception:
            pass

    def _set_zoom(self, mode: str) -> None:
        self._zoom = 1.0 if mode == "100" else 0.0
        self._render_view()

    def _nudge_zoom(self, factor: float) -> None:
        if self._zoom <= 0:
            self._zoom = 1.0
        self._zoom = max(0.25, min(8.0, self._zoom * factor))
        self._render_view()

    def _render_view(self) -> None:
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        if self._raw is None or not isinstance(self._raw, np.ndarray):
            if self._run_state not in ("no_project", "no_active", "incompatible"):
                self.image.setText(run_state_message("blank_guard", self.i18n.language))
            return
        # Identity guard: do not paint raw from a different frame than the selector
        if self._current_ctx is not None and int(self._current_ctx.frame_index) != int(self.frame_spin.value()):
            return
        t0 = time.perf_counter()
        with span_timer("v2.post.render_view"):
            h, w = self._raw.shape[:2]
            self._display_cache.bind_context(self._current_ctx)
            with span_timer("v2.post.display_bases"):
                self._display_cache.ensure_bases(self._raw, self._masks, self._result)
            base_mode = self.base_view.currentData() or "jet"
            if base_mode == "norm":
                base_rgb = None
                base_u8 = self._display_cache.get("base_norm")
            elif base_mode == "gray":
                base_rgb = None
                base_u8 = self._display_cache.get("base_gray")
            else:
                base_rgb = self._display_cache.get("base_jet")
                base_u8 = self._display_cache.get("base_gray")
            if base_u8 is None and base_rgb is None:
                return
            overlays: list[np.ndarray] = []
            op = self.opacity.value() / 100.0
            with span_timer("v2.post.visible_layer_load"):
                self._ensure_visible_masks()
            masks = self._masks
            if self._result is not None and not masks:
                masks = self._result.masks
            centerlines = []
            if self._result is not None:
                centerlines = self._result.centerlines
            elif self._result_ser:
                centerlines = self._result_ser.get("centerlines") or []

            with span_timer("v2.post.overlay_composition"):
                for key, _ru, _en, rgba in self.LAYER_KEYS:
                    if key in ("raw", "diagnostic_normalized"):
                        continue
                    if not self._layer_checked(key) or rgba[3] == 0:
                        continue
                    if key == "centerline":
                        md = self._display_cache.ensure_mask_layer(
                            "centerline", masks, centerlines=centerlines, shape=(h, w)
                        )
                    else:
                        md = self._display_cache.ensure_mask_layer(key, masks, shape=(h, w))
                    if md is None:
                        continue
                    overlays.append(overlay_rgba(h, w, md, rgba))

                stats = self._display_cache.stats()
                self._display_cache_status = "hit" if stats["hits"] > 0 and stats["misses"] == 0 else (
                    "hit" if stats["hits"] >= stats["misses"] else "composed"
                )

                if base_rgb is not None:
                    rgb = base_rgb.astype(np.float64)
                    for ov in overlays:
                        a = (ov[..., 3:4].astype(np.float64) / 255.0) * op
                        rgb = rgb * (1 - a) + ov[..., :3].astype(np.float64) * a
                    rgb = np.ascontiguousarray(np.clip(rgb, 0, 255).astype(np.uint8))
                else:
                    assert base_u8 is not None
                    rgb = compose_rgb(base_u8, overlays, op if overlays else 0.0)

            with span_timer("v2.post.qimage_pixmap"):
                qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
                pix = QPixmap.fromImage(qimg)
                if self._zoom == 0.0:
                    vp = self.scroll.viewport().size()
                    if vp.width() > 10 and vp.height() > 10:
                        pix = pix.scaled(vp, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
                elif abs(self._zoom - 1.0) > 1e-9:
                    pix = pix.scaled(
                        int(w * self._zoom), int(h * self._zoom),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.FastTransformation,
                    )
                self.image.setPixmap(pix)
            compose_s = time.perf_counter() - t0
            self._visible_timings = {**(self._visible_timings or {}), "compose_s": compose_s}
            ori = orientation_identity_dict()
            self.pixel_info.setText(
                f"shape={h}x{w} | zoom={'fit' if self._zoom == 0 else f'{self._zoom:.2f}'} | "
                f"raw_sha={self._raw_sha[:12]}… | row0_display={ori['row_zero_display_location']} | "
                f"vflip={ori['vertical_flip_applied']} | compose={compose_s*1000:.0f}ms"
            )
            self._update_cache_status_row()

    def export_package(self) -> None:
        if self._raw is None:
            return
        ru = self.i18n.language == "ru"
        dest = QFileDialog.getExistingDirectory(
            self, "Экспорт пакета диагностики" if ru else "Export diagnostic package"
        )
        if not dest:
            return
        from ionogram_morphology_lab.ui.fd_display import prepare_overlay_mask, scientific_to_display_gray

        out = Path(dest) / f"iml_feature_diag_v2_f{self.frame_spin.value()}"
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "raw_frame_scientific.npy", self._raw)
        u8 = scientific_to_display_gray(self._raw)
        gray_to_qimage(u8).save(str(out / "raw_display.png"))
        (out / "display_orientation.json").write_text(
            json.dumps(orientation_identity_dict(), indent=2), encoding="utf-8"
        )
        (out / "raw_frame_sha256.txt").write_text(self._raw_sha, encoding="utf-8")
        if self._current_ctx:
            (out / "frame_context.json").write_text(
                json.dumps(self._current_ctx.to_dict(), indent=2), encoding="utf-8"
            )
        for name, arr in self._masks.items():
            np.save(out / f"mask_{name}_scientific.npy", arr)
            np.save(out / f"mask_{name}_display.npy", prepare_overlay_mask(arr))
        if self._result_ser:
            (out / "features.json").write_text(
                json.dumps(self._result_ser, indent=2, default=str), encoding="utf-8"
            )
        if self._morph_result_dict:
            (out / "morphology_candidate.json").write_text(
                json.dumps(self._morph_result_dict, indent=2, default=str), encoding="utf-8"
            )
        (out / "summary.txt").write_text(self.summary_view.toPlainText(), encoding="utf-8")
        QMessageBox.information(
            self, "IML", (f"Экспортировано в {out}" if ru else f"Exported to {out}")
        )

    # ----- Phase 4C.1 / 4C.1a provisional morphology candidate (shadow) -----
    def _morph_cache_key(self, frame_index: int | None = None):
        rs = load_ruleset()
        snap = resolve_active_source(self.session, force_rebuild=False)
        frame = int(self.frame_spin.value() if frame_index is None else frame_index)
        v2_key = make_cache_key(
            source_mat_sha256=self._source_sha or snap.source_sha256 or "",
            frame_index=frame,
            profile_id=snap.profile_id or str(getattr(self.session, "profile_id", "") or ""),
            signal_contract_id=snap.signal_contract_id
            or str((self._result_ser or {}).get("signal_contract_id") or "kfu_amp_all_v1"),
            profile=getattr(self.session, "profile", {}) or {},
        )
        return make_candidate_cache_key(
            source_sha256=self._source_sha or snap.source_sha256 or "",
            frame_index=frame,
            profile_id=str(snap.profile_id or ""),
            signal_contract_id=str(
                (self._result_ser or {}).get("signal_contract_id")
                or snap.signal_contract_id
                or "kfu_amp_all_v1"
            ),
            feature_version=FEATURE_VERSION,
            diagnostics_cache_id=v2_key.digest(),
            ruleset_version=str(rs.get("ruleset_version")),
            ruleset_hash=ruleset_hash(rs),
        )

    def _try_load_cached_morph(self, *, on_frame_activation: bool = False) -> bool:
        """Load cached candidate from exact key. Never runs V2 or engine."""
        gen = self._morph_generation
        self._morph_last_miss_reason = None
        try:
            key = self._morph_cache_key()
        except Exception:
            self._morph_cache_status = "not_computed"
            self._morph_last_miss_reason = "no_index"
            self._refresh_morph_panel()
            return False
        # Compatibility gate when V2 ser is already available (does not evaluate)
        ser = self._result_ser or (self._result.to_serializable() if self._result else None)
        if ser is not None:
            compat = classify_v2_for_candidate(
                ser,
                expected_source_sha=self._source_sha or None,
                expected_frame_index=int(self.frame_spin.value()),
            )
            self._morph_compat_state = compat.get("state")
            if compat.get("state") == INCOMPLETE_LEGACY_CACHE:
                self._morph_result = None
                self._morph_result_dict = None
                self._morph_identity = None
                self._morph_cache_status = "v2_incomplete_legacy"
                self._refresh_morph_panel()
                return False
        else:
            self._morph_compat_state = None

        lu = self._morph_cache.lookup(key)
        if gen != self._morph_generation:
            return False  # late callback discarded
        if not lu.hit or lu.result is None:
            self._morph_cache_status = "not_computed"
            self._morph_last_miss_reason = lu.miss_reason
            self._morph_result = None
            self._morph_result_dict = None
            self._morph_identity = None
            self._refresh_morph_panel()
            return False
        # Frame/source identity guard against swapped payloads
        if int(lu.result.get("frame_index") or -1) != int(self.frame_spin.value()):
            self._morph_last_miss_reason = "frame_identity_mismatch"
            self._morph_result = None
            self._morph_result_dict = None
            self._morph_identity = None
            self._morph_cache_status = "not_computed"
            self._refresh_morph_panel()
            return False
        self._morph_result_dict = lu.result
        self._morph_result = lu.result
        self._morph_identity = evidence_identity_from_result(lu.result)
        self._morph_cache_status = "cached"
        if on_frame_activation:
            self._morph_cache.counters.candidate_loaded_on_frame_activation_count += 1
        self._restore_morph_review_status()
        self._refresh_morph_panel()
        self._sync_evidence_dialog_on_identity_change()
        return True

    def _restore_morph_review_status(self) -> None:
        self._morph_review_status = "unreviewed"
        if self.session.project is None or not self._morph_result_dict:
            return
        rh = str(self._morph_result_dict.get("result_hash") or "")
        folder = morphology_reviews_dir(self.session.project.root)
        if not folder.is_dir():
            return
        for p in folder.glob("morph_review_*.json"):
            if p.name.endswith("_export.json"):
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if str(data.get("candidate_result_hash") or "") == rh:
                self._morph_review_status = str(data.get("reviewer_decision") or "reviewed")
                return

    def _calculate_morphology_candidate(self, force: bool = False) -> None:
        ru = self.i18n.language == "ru"
        if self._sequence_candidate_running:
            self._show_inline(
                "Расчёт кандидата уже выполняется."
                if ru
                else "Candidate calculation is already in progress."
            )
            return
        ser = self._result_ser or (self._result.to_serializable() if self._result else None)
        if not ser:
            self._show_inline(
                "Сначала нужен результат геометрии V2."
                if ru
                else "V2 geometry result is required first."
            )
            return
        t0 = time.perf_counter()
        out = resolve_or_evaluate_candidate(
            ser,
            diagnostics_cache_id=self._cache_key().digest(),
            cache=self._morph_cache,
            profile_id=str(resolve_active_source(self.session, force_rebuild=False).profile_id or ""),
            signal_contract_id=str(ser.get("signal_contract_id") or ""),
            force=force,
            interpreted_time=format_hhmm(frame_to_minute(int(self.frame_spin.value()))),
        )
        self._morph_compat_state = (out.get("compatibility") or {}).get("state")
        if out.get("status") in {"v2_incomplete_legacy", INCOMPLETE_LEGACY_CACHE}:
            self._morph_result = None
            self._morph_result_dict = None
            self._morph_cache_status = "v2_incomplete_legacy"
            self._refresh_morph_panel()
            self._show_inline(legacy_incomplete_message("ru" if ru else "en"))
            return
        if out.get("result") is None:
            self._morph_cache_status = str(out.get("status") or "candidate_error")
            self._refresh_morph_panel()
            return
        if self._morph_generation:  # generation guard after async-like work
            pass
        self._morph_result_dict = out["result"]
        self._morph_result = out["result"]
        self._morph_identity = evidence_identity_from_result(out["result"])
        self._morph_cache_status = "cached" if out.get("cache_hit") else "new"
        self._restore_morph_review_status()
        self._refresh_morph_panel()
        self._sync_evidence_dialog_on_identity_change()
        if out.get("evaluated"):
            self._set_status("candidate_newly_evaluated")
        else:
            self._set_status("candidate_cache_loaded")
        _ = t0

    def _refresh_sequence_frame_state(self) -> None:
        """Update sequence/candidate clarity for the currently displayed frame (UI only)."""
        seq = self.mode_combo.currentData() == "sequence" if hasattr(self, "mode_combo") else False
        state = resolve_sequence_frame_state(
            sequence_mode=bool(seq),
            running=bool(self._running),
            job_state=str(self._job_state or ""),
            generation_id=str(self._sequence_generation_id or ""),
            active_generation_id=str(self._v2_generation_id or ""),
            current_frame=int(self._authoritative_frame()) if hasattr(self, "frame_spin") else 0,
            sequence_frames=self._sequence_frames,
            sequence_results=self._sequence_results,
            progress_frame=self._sequence_progress_frame,
            v2_ready=bool(self._result_ser or self._result),
            candidate_present=bool(self._morph_result_dict),
            candidate_cached=self._morph_cache_status in {"cached", "candidate_cached"},
            candidate_running=bool(self._sequence_candidate_running),
            cancelled=bool(self._sequence_cancelled) or str(self._job_state) == "cancelled",
        )
        self._sequence_frame_state = state
        if hasattr(self, "morph_summary"):
            self._refresh_morph_panel()

    def _refresh_morph_panel(self) -> None:
        if not hasattr(self, "morph_summary"):
            return
        ru = self.i18n.language == "ru"
        lang = "ru" if ru else "en"
        # Full disclaimer once at the top only
        self.morph_disclaimer.setText(disclaimer(lang))
        legacy = self._morph_cache_status == "v2_incomplete_legacy" or (
            self._morph_compat_state == INCOMPLETE_LEGACY_CACHE
        )
        schema_stale = self._morph_last_miss_reason in {
            MISS_INCOMPATIBLE_CACHE_SCHEMA,
            MISS_INCOMPATIBLE_LEDGER_SCHEMA,
        }
        if hasattr(self, "btn_recalc_v2_for_morph"):
            self.btn_recalc_v2_for_morph.setVisible(legacy)
        seq = hasattr(self, "mode_combo") and self.mode_combo.currentData() == "sequence"
        seq_state = self._sequence_frame_state if seq else "sequence_not_started"
        seq_pending = seq and seq_state in {
            "sequence_v2_pending",
            "sequence_v2_running_current_frame",
            "sequence_frame_not_yet_processed",
            "sequence_cancelled",
            "sequence_result_stale",
            "sequence_candidate_running",
            "sequence_v2_ready_candidate_pending",
        } and not self._morph_result_dict
        empty_hint = (
            incompatible_candidate_cache_message(lang)
            if schema_stale
            else (
                sequence_state_message(seq_state, lang)
                if seq_pending or (seq and not self._morph_result_dict and seq_state != "sequence_not_started")
                else self._future_morphology_text()
            )
        )
        status, body = format_panel_text(
            None if legacy or schema_stale else self._morph_result_dict,
            lang=lang,
            v2_status=self._cache_status,
            candidate_status=self._morph_cache_status,
            compatibility_state=INCOMPLETE_LEGACY_CACHE if legacy else self._morph_compat_state,
            empty_hint=empty_hint,
        )
        if seq and not self._morph_result_dict and not legacy and not schema_stale:
            # Prefer explicit sequence state over generic “not calculated”.
            status = sequence_state_message(seq_state, lang).split("\n")[0]
            body = sequence_state_message(seq_state, lang)
        elif seq and self._morph_result_dict and seq_state in {
            "sequence_candidate_ready",
            "sequence_candidate_cached",
        }:
            status = sequence_state_message(seq_state, lang).split("\n")[0] + " | " + status
        if self._morph_review_status and self._morph_review_status != "unreviewed" and self._morph_result_dict:
            status += f"; review={self._morph_review_status}"
        self.morph_status.setText(status)
        self.morph_summary.setPlainText(body)
        disc = disclaimer(lang)
        if body.count(disc) > 0:
            self.morph_summary.setPlainText(body.replace(disc, "").strip())
        identity_ok = bool(self._morph_result_dict) and not legacy and not schema_stale
        if seq and not legacy and not schema_stale:
            ctrl = candidate_controls_for_state(seq_state)
            tip = control_tooltip(str(ctrl.get("calc_tooltip_key") or ""), lang)
            if getattr(self, "btn_calc_morph", None) is not None:
                # Sequence mode must not blanket-disable; depend on current-frame state.
                if self._morph_result_dict:
                    self.btn_calc_morph.setEnabled(False)
                else:
                    self.btn_calc_morph.setEnabled(bool(ctrl.get("calc_enabled")) and bool(
                        self._result_ser or self._result
                    ))
                if tip:
                    self.btn_calc_morph.setToolTip(tip)
            if getattr(self, "btn_recalc_morph", None) is not None:
                self.btn_recalc_morph.setEnabled(bool(ctrl.get("recalc_enabled")) and bool(
                    self._result_ser or self._result or self._morph_result_dict
                ))
            for btn, key in (
                (getattr(self, "btn_morph_evidence", None), "evidence_enabled"),
                (getattr(self, "btn_morph_review", None), "review_enabled"),
            ):
                if btn is not None:
                    btn.setEnabled(bool(ctrl.get(key)) and identity_ok)
            return
        for btn in (
            getattr(self, "btn_morph_evidence", None),
            getattr(self, "btn_morph_review", None),
        ):
            if btn is not None:
                btn.setEnabled(identity_ok)
        if getattr(self, "btn_calc_morph", None) is not None:
            self.btn_calc_morph.setEnabled(bool(self._result_ser or self._result) and not legacy)
            self.btn_calc_morph.setToolTip("")

    def _open_morph_evidence(self) -> None:
        """Primary Evidence action: identity-bound localized table (not raw JSON)."""
        from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer

        ru = self.i18n.language == "ru"
        lang = "ru" if ru else "en"
        d = self._morph_result_dict
        if not d:
            self._set_status("no_candidate")
            QMessageBox.information(self, "IML", format_status(self._status_msg, lang))
            return
        with span_timer("fd.evidence.open"):
            if self._evidence_dialog is not None:
                try:
                    self._evidence_dialog.bind_result(d, lang, follow_active=True)
                    self._evidence_dialog.raise_()
                    self._evidence_dialog.activateWindow()
                    return
                except RuntimeError:
                    self._evidence_dialog = None
            dlg = EvidenceDialog(self)
            dlg.set_closed_callback(lambda: setattr(self, "_evidence_dialog", None))
            dlg.bind_result(d, lang, follow_active=True)
            self._evidence_dialog = dlg
            dlg.show()

    def _open_morph_provenance(self) -> None:
        ru = self.i18n.language == "ru"
        d = self._morph_result_dict
        if not d:
            QMessageBox.information(self, "IML", "Нет кандидата." if ru else "No candidate.")
            return
        keys = [
            "candidate_engine_version",
            "ruleset_id",
            "ruleset_version",
            "ruleset_hash",
            "feature_version",
            "source_sha256",
            "frame_index",
            "diagnostics_cache_id",
            "input_identity_hash",
            "result_hash",
            "evidence_ledger_hash",
            "candidate_cache_schema_version",
            "evidence_ledger_schema_version",
            "candidate_result_contract_version",
            "provisional",
            "shadow_mode",
            "scientifically_validated",
            "production_applied",
            "created_at",
        ]
        payload = {k: d.get(k) for k in keys}
        if not payload.get("evidence_ledger_hash"):
            payload["evidence_ledger_hash"] = ledger_hash(d.get("evidence_ledger") or [])
        box = QMessageBox(self)
        box.setWindowTitle("Provenance" if not ru else "Происхождение")
        box.setText(json.dumps(payload, indent=2, ensure_ascii=False))
        box.exec()

    def _review_identity_matches_display(self, d: dict) -> bool:
        cur = self._morph_result_dict
        if not cur:
            return False
        checks = (
            ("result_hash", "result_hash"),
            ("source_sha256", "source_sha256"),
            ("frame_index", "frame_index"),
            ("diagnostics_cache_id", "diagnostics_cache_id"),
            ("ruleset_hash", "ruleset_hash"),
        )
        for a, b in checks:
            if str(d.get(a) or "") != str(cur.get(b) or ""):
                return False
        lh = ledger_hash(cur.get("evidence_ledger") or [])
        if str(d.get("reviewed_evidence_ledger_hash") or lh) != lh and d.get(
            "reviewed_evidence_ledger_hash"
        ):
            # When checking the live candidate before save, ledger hash is computed below
            pass
        if int(cur.get("frame_index") or -1) != int(self.frame_spin.value()):
            return False
        return True

    def _open_morph_review_dialog(self) -> None:
        ru = self.i18n.language == "ru"
        d = self._morph_result_dict
        if not d or self.session.project is None:
            QMessageBox.information(
                self,
                "IML",
                "Нужны кандидат и открытый проект." if ru else "Candidate and open project required.",
            )
            return
        if not self._review_identity_matches_display(d):
            self._set_status("identity_mismatch_review")
            QMessageBox.warning(
                self,
                "IML",
                format_status(self._status_msg, "ru" if ru else "en"),
            )
            self._try_load_cached_morph()
            return
        notice = (
            "Эта проверка отделена от более ранней проверки геометрии."
            if ru
            else "This review is separate from the earlier geometry review."
        )
        form = QDialog(self)
        self._review_dialog = form
        form.setWindowTitle("Morphology review" if not ru else "Проверка морфологии")
        lay = QVBoxLayout(form)
        id_lbl = QLabel(
            f"{'Кадр' if ru else 'Frame'} {d.get('frame_index')} · "
            f"hash={(str(d.get('result_hash') or ''))[:12]}"
        )
        lay.addWidget(id_lbl)
        lay.addWidget(QLabel(notice))
        fl = QFormLayout()
        q_assess = QComboBox()
        q_inter = QComboBox()
        q_h = QComboBox()
        q_v = QComboBox()
        q_final = QComboBox()
        for cb in (q_assess, q_inter, q_h, q_v, q_final):
            cb.addItem("yes" if not ru else "да", "yes")
            cb.addItem("no" if not ru else "нет", "no")
            cb.addItem("uncertain" if not ru else "неуверенно", "uncertain")
        decision = QComboBox()
        for token, ru_l, en_l in (
            ("agree_frequency", "согласен: частотное", "agree frequency"),
            ("agree_range", "согласен: высотное", "agree range"),
            ("agree_mixed", "согласен: смешанное", "agree mixed"),
            ("agree_no_supported_visible_spread", "согласен: нет рассеяния", "agree no supported spread"),
            ("override_frequency", "переопределить: частотное", "override frequency"),
            ("override_range", "переопределить: высотное", "override range"),
            ("override_mixed", "переопределить: смешанное", "override mixed"),
            ("override_no_supported_visible_spread", "переопределить: нет рассеяния", "override no spread"),
            ("mark_indeterminate", "отметить неопределённо", "mark indeterminate"),
            ("mark_not_assessable", "отметить оценка невозможна", "mark not assessable"),
            ("needs_second_review", "нужна вторая проверка", "needs second review"),
        ):
            decision.addItem(ru_l if ru else en_l, token)
        comment = QTextEdit()
        comment.setMaximumHeight(80)
        fl.addRow("1. Assessable?" if not ru else "1. Кадр оцениваем?", q_assess)
        fl.addRow("2. Interference OK?" if not ru else "2. Помехи обработаны верно?", q_inter)
        fl.addRow("3. H evidence OK?" if not ru else "3. H-доказательства разумны?", q_h)
        fl.addRow("4. V evidence OK?" if not ru else "4. V-доказательства разумны?", q_v)
        fl.addRow("5. Final candidate OK?" if not ru else "5. Итоговый кандидат разумен?", q_final)
        fl.addRow("6. Reviewer label" if not ru else "6. Метка эксперта", decision)
        fl.addRow("7. Comment" if not ru else "7. Комментарий", comment)
        lay.addLayout(fl)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        localize_dialog_buttons(buttons, "ru" if ru else "en")
        lay.addWidget(buttons)
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)

        def _on_save() -> None:
            # Re-verify identity at save time
            cur = self._morph_result_dict
            if cur is None or str(cur.get("result_hash") or "") != str(d.get("result_hash") or ""):
                self._set_status("identity_mismatch_review")
                QMessageBox.warning(
                    self, "IML", format_status(self._status_msg, "ru" if ru else "en")
                )
                if save_btn is not None:
                    save_btn.setEnabled(False)
                return
            form.accept()

        buttons.accepted.connect(_on_save)
        buttons.rejected.connect(form.reject)
        try:
            if form.exec() != QDialog.DialogCode.Accepted:
                return
        finally:
            self._review_dialog = None
        cur = self._morph_result_dict
        if cur is None or str(cur.get("result_hash") or "") != str(d.get("result_hash") or ""):
            self._set_status("identity_mismatch_review")
            return
        review = MorphologyCandidateReview(
            source_sha256=str(cur.get("source_sha256") or ""),
            frame_index=int(cur.get("frame_index") or self.frame_spin.value()),
            interpreted_time=str(cur.get("interpreted_time") or ""),
            feature_version=str(cur.get("feature_version") or FEATURE_VERSION),
            diagnostics_cache_id=str(cur.get("diagnostics_cache_id") or ""),
            ruleset_version=str(cur.get("ruleset_version") or ""),
            ruleset_hash=str(cur.get("ruleset_hash") or ""),
            candidate_result_hash=str(cur.get("result_hash") or ""),
            displayed_candidate=str(cur.get("candidate") or ""),
            reviewer_decision=str(decision.currentData()),
            reviewer_selected_morphology_label=str(decision.currentData()),
            assessable_for_morphology=str(q_assess.currentData()),
            interference_handled_correctly=str(q_inter.currentData()),
            horizontal_evidence_reasonable=str(q_h.currentData()),
            vertical_evidence_reasonable=str(q_v.currentData()),
            final_candidate_reasonable=str(q_final.currentData()),
            comment=comment.toPlainText().strip(),
            reviewed_evidence_ledger_hash=ledger_hash(cur.get("evidence_ledger") or []),
            provisional_expert_review=True,
            confirmed_ground_truth=False,
        )
        path = save_morphology_review(self.session.project.root, review)
        export_path = path.with_name(path.stem + "_export.json")
        export_path.write_text(json.dumps(review.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        folder = morphology_reviews_dir(self.session.project.root)
        self._morph_review_status = str(decision.currentData())
        self._show_inline(
            (f"Проверка морфологии сохранена: {path.name} ({folder})" if ru else f"Morphology review saved: {path.name} ({folder})")
        )

    def _export_morph_json(self) -> None:
        ru = self.i18n.language == "ru"
        d = self._morph_result_dict
        if not d:
            QMessageBox.information(self, "IML", "Нет кандидата." if ru else "No candidate.")
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Export candidate JSON" if not ru else "Экспорт кандидата JSON",
            f"morph_candidate_f{int(self.frame_spin.value()):04d}.json",
            "JSON (*.json)",
        )
        if not dest:
            return
        Path(dest).write_text(json.dumps(d, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def _copy_evidence_json(self) -> None:
        from PySide6.QtWidgets import QApplication

        ru = self.i18n.language == "ru"
        d = self._morph_result_dict
        if not d:
            QMessageBox.information(self, "IML", "Нет кандидата." if ru else "No candidate.")
            return
        QApplication.clipboard().setText(
            json.dumps(d.get("evidence_ledger") or [], indent=2, ensure_ascii=False, default=str)
        )
        self._set_status("evidence_json_copied")

    def _export_evidence_json(self) -> None:
        ru = self.i18n.language == "ru"
        d = self._morph_result_dict
        if not d:
            QMessageBox.information(self, "IML", "Нет кандидата." if ru else "No candidate.")
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Export evidence JSON" if not ru else "Экспорт JSON доказательств",
            f"evidence_ledger_f{int(self.frame_spin.value()):04d}.json",
            "JSON (*.json)",
        )
        if not dest:
            return
        Path(dest).write_text(
            json.dumps(d.get("evidence_ledger") or [], indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _copy_fragmentation_gate_rows(self) -> None:
        from PySide6.QtWidgets import QApplication

        ru = self.i18n.language == "ru"
        d = self._morph_result_dict
        if not d:
            QMessageBox.information(self, "IML", "Нет кандидата." if ru else "No candidate.")
            return
        rows = fragmentation_gate_rows(d.get("evidence_ledger") or [])
        QApplication.clipboard().setText(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
        self._show_inline(
            f"Скопировано строк фрагментации: {len(rows)}"
            if ru
            else f"Fragmentation gate rows copied: {len(rows)}"
        )

    def _show_geometry_review_overview(self) -> None:
        ru = self.i18n.language == "ru"
        if self.session.project is None:
            QMessageBox.information(self, "IML", "Нет проекта." if ru else "No project.")
            return
        corpus = load_geometry_review_corpus(self.session.project.root)
        summary = corpus.to_dict()
        files_n = summary["review_files_found"]
        logical_n = summary["logical_reviewed_frames"]
        current_n = summary["current_reviews"]
        superseded_n = summary["superseded_reviews"]
        counts = f"{files_n} / {logical_n} / {current_n} / {superseded_n}"
        text = (
            (
                "Сводка корпуса проверок геометрии\n"
                f"(файлы / логические кадры / текущие / устаревшие): {counts}\n\n"
                f"Файлов: {files_n}\n"
                f"Логических кадров: {logical_n}\n"
                f"Текущих проверок: {current_n}\n"
                f"Устаревших (история): {superseded_n}\n\n"
            )
            if ru
            else (
                "Geometry review corpus overview\n"
                f"(files / logical frames / current / superseded): {counts}\n\n"
                f"Files: {files_n}\n"
                f"Logical frames: {logical_n}\n"
                f"Current reviews: {current_n}\n"
                f"Superseded (history): {superseded_n}\n\n"
            )
        )
        text += json.dumps(summary, indent=2, ensure_ascii=False)
        box = QMessageBox(self)
        box.setWindowTitle(
            "Обзор проверок" if ru else "Review corpus overview"
        )
        box.setText(
            (
                f"Корпус: {counts}\n"
                f"(файлы / логические кадры / текущие / устаревшие)"
            )
            if ru
            else (
                f"Corpus: {counts}\n"
                f"(files / logical frames / current / superseded)"
            )
        )
        box.setDetailedText(text)
        box.exec()

    def _open_morph_review_folder(self) -> None:
        if self.session.project is None:
            return
        folder = morphology_reviews_dir(self.session.project.root)
        folder.mkdir(parents=True, exist_ok=True)
        import os
        import subprocess

        try:
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except Exception:
            subprocess.Popen(["explorer", str(folder)])

    def _enrich_sequence_morph_candidates(self) -> None:
        """Fill morph_candidate for every sequence row with compatible V2 — no geometry-review gate."""
        cur = int(self.frame_spin.value())
        for r in self._sequence_results:
            update_panel = int(r.get("frame_index") or -1) == cur
            self._hydrate_sequence_row_candidate(r, update_panel=update_panel)

    def _clear_morph_cache_frame(self) -> None:
        ru = self.i18n.language == "ru"
        try:
            key = self._morph_cache_key()
            self._morph_cache.clear_frame(key)
        except Exception:
            pass
        self._morph_result = None
        self._morph_result_dict = None
        self._morph_cache_status = "not_computed"
        self._refresh_morph_panel()
        self._show_inline(
            "Кэш кандидата кадра очищен (V2/geometry/reviews сохранены)."
            if ru
            else "Frame candidate cache cleared (V2/geometry/reviews preserved)."
        )

    def _apply_sequence_filter(self) -> None:
        if not hasattr(self, "seq_filter") or self.seq_table.rowCount() == 0:
            return
        token = self.seq_filter.currentData() or "all"
        for i in range(self.seq_table.rowCount()):
            show = True
            if token != "all":
                cand_item = self.seq_table.item(i, 9)
                inter_item = self.seq_table.item(i, 13)
                rev_item = self.seq_table.item(i, 17)
                cand = cand_item.text() if cand_item else ""
                inter = inter_item.text() if inter_item else ""
                rev = rev_item.text() if rev_item else ""
                if token == "high_interference":
                    show = inter in {"high", "blocking"}
                elif token == "unreviewed":
                    show = rev in {"unreviewed", "—", ""}
                elif token == "disagreement":
                    show = rev not in {"unreviewed", "—", "", "agree"}
                else:
                    show = cand == token
            self.seq_table.setRowHidden(i, not show)
