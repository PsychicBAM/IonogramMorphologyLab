"""Expert Morphology Review Corpus UI (Phase 4C.2 / 4C.2a.1) — lifecycle + localization."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.morphology_review_corpus.analytics import descriptive_summary
from ionogram_morphology_lab.morphology_review_corpus.batch_compare import (
    BatchCompareError,
    batch_reveal_and_compare,
    can_batch_reveal_and_compare,
)
from ionogram_morphology_lab.morphology_review_corpus.blinding import queue_columns
from ionogram_morphology_lab.morphology_review_corpus.exports import export_cohort
from ionogram_morphology_lab.morphology_review_corpus.integrity import validate_cohort
from ionogram_morphology_lab.morphology_review_corpus.labels import (
    HUMAN_MORPHOLOGY_CODES,
    comparison_status_display,
    display_label,
)
from ionogram_morphology_lab.morphology_review_corpus.current_state import (
    count_consistency,
    repair_comparison_derived_state,
)
from ionogram_morphology_lab.morphology_review_corpus.workflow import (
    determine_workflow_stage,
    next_uncompared_item,
    next_unfinished_blind_item,
    normalize_reveal_policy,
    stage_label,
)
from ionogram_morphology_lab.morphology_review_corpus.comments import (
    INTERF_OBS_CODES,
    LIMIT_CODES,
    MORPH_OBS_CODES,
    PRESET_DEFS,
    TRACE_CODES,
    CommentRecord,
    apply_preset,
    generate_comment_text,
    structured_code_label,
)
from ionogram_morphology_lab.ui.corpus_display import (
    format_comparison_cards,
    format_summary_dashboard,
    guided_step_indicator,
)
from ionogram_morphology_lab.morphology_review_corpus.lifecycle import (
    CorpusLifecycleError,
    get_selected_cohort,
    is_archived,
    load_workspace,
    set_selected_cohort,
    set_show_flags,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    AdjudicationRecord,
    BlindReviewRecord,
    CandidateSnapshot,
    ReviewerIdentity,
)
from ionogram_morphology_lab.morphology_review_corpus.project_items import (
    current_viewer_frame_item,
    frames_from_time_range,
    items_from_active_source_frames,
)
from ionogram_morphology_lab.morphology_review_corpus.status import status_explanation, status_label
from ionogram_morphology_lab.morphology_review_corpus.store import (
    BlindRevealError,
    FrozenCohortError,
    MorphologyReviewCorpusStore,
    required_fields_complete,
)
from ionogram_morphology_lab.ui.active_source_authority import (
    active_source_label,
    authoritative_active_source,
)
from ionogram_morphology_lab.ui.review_ionogram_view import ReviewIonogramView

_MORPH_CODES = sorted(HUMAN_MORPHOLOGY_CODES)
_ASSESS = ("assessable", "partially_assessable", "not_assessable")
_INTERF = (
    "none_supported",
    "vertical_interference",
    "interference_or_artifact",
    "possible_corruption",
    "other",
    "uncertain",
)
_AMBIG = ("low", "moderate", "high", "not_applicable")
_CONF = ("low", "moderate", "high")
_LOG = logging.getLogger(__name__)


class ExpertReviewCorpusPage(QWidget):
    """Cohorts / queue / blind review / comparison / summary — production real-data UI."""

    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self._store: MorphologyReviewCorpusStore | None = None
        self._cohort_id = ""
        self._current_item_id = ""
        self._blind_locked_for_item = False
        self._preview_items: list[dict[str, Any]] = []
        self._allow_synthetic = False  # production: never create pilot_frame placeholders
        self._unsaved_review_form: dict[str, Any] | None = None
        self._draft: dict[str, Any] = {}
        self._syncing_draft = False
        self._pending_review_revision: dict[str, Any] | None = None
        self._candidate_revealed_ui = False
        self._comparison_save_guard = False
        self._tech_expanded = False

        root = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(self.title)
        self.designation = QLabel()
        self.designation.setWordWrap(True)
        root.addWidget(self.designation)
        self.active_source_lbl = QLabel()
        self.active_source_lbl.setWordWrap(True)
        root.addWidget(self.active_source_lbl)
        self.selected_badge = QLabel()
        self.selected_badge.setWordWrap(True)
        self.selected_badge.setStyleSheet("font-weight: 600;")
        root.addWidget(self.selected_badge)
        self.revision_banner = QLabel()
        self.revision_banner.setWordWrap(True)
        self.revision_banner.hide()
        root.addWidget(self.revision_banner)
        self.blind_note = QLabel()
        self.blind_note.setWordWrap(True)
        root.addWidget(self.blind_note)
        self.empty_banner = QLabel()
        self.empty_banner.setWordWrap(True)
        root.addWidget(self.empty_banner)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self._build_guided_tab()
        self._build_cohorts_tab()
        self._build_rapid_review_tab()
        self._build_queue_tab()
        self._build_review_tab()
        self._build_compare_tab()
        self._build_summary_tab()
        self.retranslate()
        self.installEventFilter(self)
        try:
            self.session.events.active_mat_changed.connect(self._on_active_source_changed)
            self.session.events.project_changed.connect(self._on_active_source_changed)
        except Exception:
            pass

    def t(self, key: str, default: str | None = None) -> str:
        return self.i18n.t(key, default=default)

    def _lang(self) -> str:
        return "ru" if str(getattr(self.i18n, "language", "en")).startswith("ru") else "en"

    def _label_code(self, code: str) -> str:
        return self.t(f"expert_corpus.label.{code}", default=code)

    def _meta(self, code: str) -> str:
        return self.t(f"expert_corpus.meta.{code}", default=code)

    def _ask(
        self,
        text: str,
        *,
        ok_key: str = "expert_corpus.confirm_btn",
        cancel_key: str = "expert_corpus.cancel_btn",
    ) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(self.t("expert_corpus.dialog_title"))
        box.setText(text)
        ok_btn = box.addButton(self.t(ok_key), QMessageBox.AcceptRole)
        cancel_btn = box.addButton(self.t(cancel_key), QMessageBox.RejectRole)
        box.setDefaultButton(cancel_btn)
        box.exec()
        return box.clickedButton() == ok_btn

    def _lifecycle_message(self, exc: BaseException) -> str:
        code = getattr(exc, "code", "") or ""
        if code == "cohort_must_be_frozen":
            return self.t("expert_corpus.must_freeze_review")
        mapped = {
            "frozen_cannot_remove": "expert_corpus.meta.frozen",
            "frozen_cannot_clear": "expert_corpus.meta.frozen",
            "frozen_cannot_delete": "expert_corpus.meta.frozen",
            "revision_reason_required": "expert_corpus.revision_reason_required",
        }
        if code in mapped:
            return self.t(mapped[code])
        return str(exc)

    def project_root(self):
        proj = getattr(self.session, "project", None)
        return getattr(proj, "root", None) or getattr(proj, "path", None)

    def _ensure_store(self) -> MorphologyReviewCorpusStore | None:
        root = self.project_root()
        if not root:
            return None
        self._store = MorphologyReviewCorpusStore(root)
        return self._store

    def _on_active_source_changed(self) -> None:
        # Project switch must not leak prior project's cohort selection
        root = self.project_root()
        store = self._ensure_store() if root else None
        if not store or (
            self._cohort_id and self._cohort_id not in store.list_cohorts()
        ):
            self._cohort_id = ""
            self._clear_stale_views()
        self._refresh_active_source_label()
        self._update_empty_banner()
        self._update_selected_badge()
        self.refresh_cohorts()

    def _refresh_active_source_label(self) -> None:
        auth = authoritative_active_source(self.session)
        text = active_source_label(auth, self._lang())
        if auth.short_sha:
            text += f" | SHA {auth.short_sha}"
        self.active_source_lbl.setText(text)

    def _update_empty_banner(self) -> None:
        if self.project_root() is None:
            self.empty_banner.setText(self.t("expert_corpus.empty_no_project"))
            return
        auth = authoritative_active_source(self.session)
        if not auth.is_active:
            self.empty_banner.setText(self.t("expert_corpus.empty_no_active"))
            return
        store = self._ensure_store()
        if store and not store.list_cohorts():
            self.empty_banner.setText(self.t("expert_corpus.empty_no_cohort"))
            return
        if self._cohort_id and store:
            items = store.load_items(self._cohort_id)
            if not items:
                self.empty_banner.setText(self.t("expert_corpus.empty_zero_items"))
                return
        self.empty_banner.setText("")

    # ---- tabs -----------------------------------------------------------
    def _build_guided_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addStretch(1)
        self.guided_card = QFrame()
        self.guided_card.setObjectName("guided_card")
        self.guided_card.setMaximumWidth(900)
        self.guided_card.setMinimumWidth(680)
        self.guided_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.guided_card.setStyleSheet(
            "#guided_card { border: 1px solid palette(mid); border-radius: 8px; padding: 18px; }"
        )
        card = QVBoxLayout(self.guided_card)
        card.setSpacing(10)
        self.guided_steps_header = QLabel()
        self.guided_steps_header.setWordWrap(True)
        self.guided_cohort_line = QLabel()
        self.guided_cohort_line.setWordWrap(True)
        self.guided_section_completed = QLabel()
        self.guided_section_completed.setWordWrap(True)
        self.guided_section_current = QLabel()
        self.guided_section_current.setWordWrap(True)
        self.guided_section_optional = QLabel()
        self.guided_section_optional.setWordWrap(True)
        self.guided_section_science = QLabel()
        self.guided_section_science.setWordWrap(True)
        self.guided_title = QLabel()
        self.guided_title.setStyleSheet("font-size: 20px; font-weight: 600;")
        self.guided_title.setWordWrap(True)
        self.guided_explain = QLabel()
        self.guided_explain.setWordWrap(True)
        self.guided_progress_text = QLabel()
        self.guided_progress_bar = QProgressBar()
        self.guided_progress_bar.setTextVisible(True)
        self.guided_action = QPushButton()
        self.guided_action.setMinimumHeight(40)
        self.guided_action.clicked.connect(self._run_guided_action)
        self.guided_secondary = QPushButton()
        self.guided_secondary.setFlat(True)
        self.guided_secondary.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        self.guided_blocker = QLabel()
        self.guided_blocker.setWordWrap(True)
        self.guided_blocker.setStyleSheet("color: #a66a00;")
        for widget in (
            self.guided_steps_header, self.guided_cohort_line, self.guided_section_completed,
            self.guided_section_current, self.guided_title,
            self.guided_explain, self.guided_progress_text, self.guided_progress_bar,
            self.guided_action, self.guided_secondary, self.guided_section_optional,
            self.guided_section_science, self.guided_blocker,
        ):
            card.addWidget(widget)
        centered = QHBoxLayout()
        centered.addStretch(1)
        centered.addWidget(self.guided_card)
        centered.addStretch(1)
        lay.addLayout(centered)
        lay.addStretch(1)
        self.tabs.addTab(w, "guided")

    def _build_cohorts_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        self.cohort_list = QListWidget()
        self.cohort_list.currentTextChanged.connect(self._on_cohort_selected)
        row.addWidget(self.cohort_list, 1)
        form_box = QGroupBox()
        self._cohort_form_box = form_box
        form = QFormLayout(form_box)
        self.cohort_id_edit = QLineEdit()
        self.seed_spin = QSpinBox()
        self.seed_spin.setMaximum(10_000_000)
        self.seed_spin.setValue(42)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 10_000)
        self.count_spin.setValue(5)
        self.start_frame_spin = QSpinBox()
        self.start_frame_spin.setRange(1, 20000)
        self.start_frame_spin.setValue(1)
        self.end_frame_spin = QSpinBox()
        self.end_frame_spin.setRange(1, 20000)
        self.end_frame_spin.setValue(5)
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 1440)
        self.step_spin.setValue(1)
        self.reviewer_id_edit = QLineEdit("rev_owner")
        self.reviewer_alias_edit = QLineEdit("Owner")
        self.reveal_policy_combo = QComboBox()
        self.reveal_policy_combo.addItem("", "strict_cohort")
        self.reveal_policy_combo.addItem("", "per_item")
        self.reveal_policy_combo.currentIndexChanged.connect(self._set_reveal_policy)
        self._form_rows: list[tuple[QLabel, QWidget]] = []
        for key, widget in (
            ("expert_corpus.field_cohort_id", self.cohort_id_edit),
            ("expert_corpus.field_start_frame", self.start_frame_spin),
            ("expert_corpus.field_end_frame", self.end_frame_spin),
            ("expert_corpus.field_step", self.step_spin),
            ("expert_corpus.field_count", self.count_spin),
            ("expert_corpus.field_seed", self.seed_spin),
            ("expert_corpus.field_reviewer_id", self.reviewer_id_edit),
            ("expert_corpus.field_alias", self.reviewer_alias_edit),
            ("expert_corpus.reveal_policy", self.reveal_policy_combo),
        ):
            lab = QLabel()
            lab.setProperty("i18n_key", key)
            form.addRow(lab, widget)
            self._form_rows.append((lab, widget))
        row.addWidget(form_box, 1)
        lay.addLayout(row)
        self.preview_view = QPlainTextEdit()
        self.preview_view.setReadOnly(True)
        self.preview_view.setMaximumHeight(140)
        lay.addWidget(self.preview_view)
        filters = QHBoxLayout()
        self.chk_show_archived = QCheckBox()
        self.chk_show_legacy = QCheckBox()
        self.chk_show_archived.toggled.connect(self._on_show_flags_changed)
        self.chk_show_legacy.toggled.connect(self._on_show_flags_changed)
        filters.addWidget(self.chk_show_archived)
        filters.addWidget(self.chk_show_legacy)
        filters.addStretch(1)
        lay.addLayout(filters)
        self.chk_show_archived.hide()
        self.chk_show_legacy.hide()
        btns = QHBoxLayout()
        self.btn_refresh = QPushButton()
        self.btn_preview = QPushButton()
        self.btn_create = QPushButton()
        self.btn_add_current = QPushButton()
        self.btn_remove_current = QPushButton()
        self.btn_clear_draft = QPushButton()
        self.btn_delete_draft = QPushButton()
        self.btn_freeze = QPushButton()
        self.btn_create_revision = QPushButton()
        self.btn_archive = QPushButton()
        self.btn_export = QPushButton()
        self.btn_validate = QPushButton()
        self.btn_refresh.clicked.connect(self.refresh_cohorts)
        self.btn_preview.clicked.connect(self._preview_cohort_items)
        self.btn_create.clicked.connect(self._create_real_cohort)
        self.btn_add_current.clicked.connect(self._add_current_viewer_frame)
        self.btn_remove_current.clicked.connect(self._remove_current_viewer_frame)
        self.btn_clear_draft.clicked.connect(self._clear_draft)
        self.btn_delete_draft.clicked.connect(self._delete_draft)
        self.btn_freeze.clicked.connect(self._freeze_cohort)
        self.btn_create_revision.clicked.connect(self._create_editable_revision)
        self.btn_archive.clicked.connect(self._archive_cohort)
        self.btn_export.clicked.connect(self._export_cohort)
        self.btn_validate.clicked.connect(self._validate_cohort)
        # Keep the primary surface compact; every other lifecycle action is
        # reachable through the localized overflow menu.
        self.btn_primary_freeze = self.btn_freeze  # visible primary when draft
        for b in (self.btn_preview, self.btn_freeze):
            btns.addWidget(b)
        self.btn_overflow = QToolButton()
        self.cohort_overflow = self.btn_overflow
        self.btn_overflow.setPopupMode(QToolButton.InstantPopup)
        self.btn_overflow.setToolTip(self.t("expert_corpus.overflow_menu", "More actions"))
        self.btn_overflow.setAccessibleName(self.t("expert_corpus.overflow_menu", "More actions"))
        self.cohort_overflow_menu = QMenu(self.btn_overflow)
        self.btn_overflow.setMenu(self.cohort_overflow_menu)
        self._overflow_button_actions: list[tuple[Any, Any]] = []
        for button in (
            self.btn_refresh,
            self.btn_create,
            self.btn_add_current,
            self.btn_remove_current,
            self.btn_clear_draft,
            self.btn_delete_draft,
            self.btn_create_revision,
            self.btn_archive,
            self.btn_export,
            self.btn_validate,
        ):
            act = self.cohort_overflow_menu.addAction(button.text() or "…")
            act.triggered.connect(button.click)
            self._overflow_button_actions.append((button, act))
            button.hide()  # overflow-only; preview/freeze stay visible
        self.cohort_overflow_menu.addSeparator()
        filters_menu = QMenu(self.cohort_overflow_menu)
        self.cohort_overflow_menu.addMenu(filters_menu)
        self._filters_menu = filters_menu
        archived_action = filters_menu.addAction("")
        archived_action.setCheckable(True)
        archived_action.toggled.connect(self.chk_show_archived.setChecked)
        self.chk_show_archived.toggled.connect(archived_action.setChecked)
        legacy_action = filters_menu.addAction("")
        legacy_action.setCheckable(True)
        legacy_action.toggled.connect(self.chk_show_legacy.setChecked)
        self.chk_show_legacy.toggled.connect(legacy_action.setChecked)
        self._archived_menu_action = archived_action
        self._legacy_menu_action = legacy_action
        technical = self.cohort_overflow_menu.addAction("")
        technical.triggered.connect(lambda: self.cohort_info.setFocus())
        self._technical_details_action = technical
        btns.addWidget(self.btn_overflow)
        lay.addLayout(btns)
        self.cohort_info = QPlainTextEdit()
        self.cohort_info.setReadOnly(True)
        lay.addWidget(self.cohort_info, 1)
        self.tabs.addTab(w, "cohorts")

    def _build_rapid_review_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.rapid_splitter = QSplitter(Qt.Horizontal)
        self.rapid_table = QTableWidget(0, 8)
        self.rapid_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rapid_table.setHorizontalHeaderLabels([""] * 8)
        self.rapid_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.rapid_table.setMinimumWidth(520)
        self.rapid_table.itemSelectionChanged.connect(self._load_rapid_selection)
        self.rapid_table.installEventFilter(self)
        self.rapid_splitter.addWidget(self.rapid_table)
        side_widget = QWidget()
        side_widget.setMinimumWidth(440)
        side = QVBoxLayout(side_widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rapid_right_scroll = scroll
        scroll_content = QWidget()
        scroll_lay = QVBoxLayout(scroll_content)
        self.rapid_identity = QLabel()
        self.rapid_identity.setWordWrap(True)
        scroll_lay.addWidget(self.rapid_identity)
        self.rapid_ionogram = ReviewIonogramView()
        self.rapid_ionogram.setMinimumHeight(240)
        scroll_lay.addWidget(self.rapid_ionogram)
        self.btn_open_larger = QPushButton()
        self.btn_open_larger.clicked.connect(lambda: self.tabs.setCurrentIndex(4))
        scroll_lay.addWidget(self.btn_open_larger)
        form_box = QGroupBox()
        form = QFormLayout(form_box)
        self._build_review_form_widgets()
        self._add_review_form_rows(form)
        scroll_lay.addWidget(form_box)
        self.comment_box = QGroupBox()
        c_lay = QVBoxLayout(self.comment_box)
        self.comment_checks: dict[str, QCheckBox] = {}
        preset_row = QHBoxLayout()
        self.comment_preset = QComboBox()
        self.comment_preset.currentIndexChanged.connect(self._apply_comment_preset)
        self.btn_apply_preset = QPushButton()
        self.btn_apply_preset.clicked.connect(self._apply_comment_preset)
        self.lbl_selected_count = QLabel()
        self.btn_clear_comment_sel = QPushButton()
        self.btn_clear_comment_sel.clicked.connect(self._clear_comment_selection)
        for widget in (self.comment_preset, self.btn_apply_preset, self.lbl_selected_count, self.btn_clear_comment_sel):
            preset_row.addWidget(widget)
        c_lay.addLayout(preset_row)
        group_menu_btn = QToolButton()
        group_menu_btn.setText("⋯")
        group_menu_btn.setPopupMode(QToolButton.InstantPopup)
        group_menu_btn.setAccessibleName("Comment group options")
        group_menu = QMenu(group_menu_btn)
        expand_all = group_menu.addAction("Expand all")
        collapse_all = group_menu.addAction("Collapse all")
        expand_all.triggered.connect(lambda: self._set_comment_groups_expanded(True))
        collapse_all.triggered.connect(lambda: self._set_comment_groups_expanded(False))
        group_menu_btn.setMenu(group_menu)
        self._comment_group_menu_btn = group_menu_btn
        self._expand_all_action = expand_all
        self._collapse_all_action = collapse_all
        preset_row.addWidget(group_menu_btn)
        self.comment_groups: list[tuple[QGroupBox, tuple[str, ...], QWidget]] = []
        for idx, (title, codes) in enumerate((
            ("Trace codes", TRACE_CODES), ("Morphology observations", MORPH_OBS_CODES),
            ("Interference and artifacts", INTERF_OBS_CODES), ("Limits", LIMIT_CODES),
        )):
            group = QGroupBox(title)
            group.setCheckable(True)
            # Default: expand the first two groups only (trace + morph observations).
            group.setChecked(idx < 2)
            group_lay = QVBoxLayout(group)
            content = QWidget()
            content_lay = QVBoxLayout(content)
            content_lay.setContentsMargins(0, 0, 0, 0)
            for code in codes:
                check = QCheckBox()
                check.setProperty("code", code)
                check.toggled.connect(self._comment_codes_changed)
                self.comment_checks[code] = check
                content_lay.addWidget(check)
            group_lay.addWidget(content)
            content.setVisible(group.isChecked())
            group.toggled.connect(content.setVisible)
            self.comment_groups.append((group, tuple(codes), content))
            c_lay.addWidget(group)
        self.generated_comment_label = QLabel()
        self.generated_comment = QPlainTextEdit()
        self.generated_comment.setMinimumHeight(90)
        self.generated_comment.setReadOnly(True)
        self.btn_regen_generated = QPushButton()
        self.btn_regen_generated.clicked.connect(self._regenerate_comment)
        self.final_comment_label = QLabel()
        self.final_comment = QPlainTextEdit()
        self.final_comment.setMinimumHeight(100)
        self._final_comment_dirty = False
        self.final_comment.textChanged.connect(lambda: setattr(self, "_final_comment_dirty", True))
        self.own_description_label = QLabel()
        self.own_description = QPlainTextEdit()
        self.own_description.setMinimumHeight(80)
        c_lay.addWidget(self.generated_comment_label)
        c_lay.addWidget(self.generated_comment)
        c_lay.addWidget(self.btn_regen_generated)
        c_lay.addWidget(self.final_comment_label)
        c_lay.addWidget(self.final_comment)
        c_lay.addWidget(self.own_description_label)
        c_lay.addWidget(self.own_description)
        scroll_lay.addWidget(self.comment_box)
        scroll_lay.addStretch(1)
        scroll.setWidget(scroll_content)
        side.addWidget(scroll, 1)
        footer = QHBoxLayout()
        self.btn_save_and_next_rapid = QPushButton()
        self.btn_save_and_next_rapid.clicked.connect(self._save_blind)
        self.btn_save_draft_rapid = QPushButton()
        self.btn_save_draft_rapid.clicked.connect(self._save_rapid_draft)
        self.validation_label = QLabel()
        self.validation_label.setWordWrap(True)
        footer.addWidget(self.btn_save_and_next_rapid)
        footer.addWidget(self.btn_save_draft_rapid)
        footer.addWidget(self.validation_label, 1)
        side.addLayout(footer)
        self.rapid_splitter.addWidget(side_widget)
        self.rapid_splitter.setChildrenCollapsible(False)
        self.rapid_splitter.setStretchFactor(0, 3)
        self.rapid_splitter.setStretchFactor(1, 2)
        self.rapid_splitter.setSizes([600, 700])
        self.rapid_splitter.splitterMoved.connect(self._save_rapid_splitter_state)
        lay.addWidget(self.rapid_splitter, 1)
        self._restore_rapid_splitter_state()
        self.tabs.addTab(w, "rapid")

    def _build_queue_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.queue_table = QTableWidget(0, 0)
        self.queue_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.queue_table.itemDoubleClicked.connect(lambda *_: self._open_selected_item())
        lay.addWidget(self.queue_table, 1)
        row = QHBoxLayout()
        self.btn_open_item = QPushButton()
        self.btn_remove_selected = QPushButton()
        self.btn_open_item.clicked.connect(self._open_selected_item)
        self.btn_remove_selected.clicked.connect(self._remove_selected_items)
        row.addWidget(self.btn_open_item)
        row.addWidget(self.btn_remove_selected)
        lay.addLayout(row)
        self.tabs.addTab(w, "queue")

    def _build_review_tab(self) -> None:
        w = QWidget()
        lay = QHBoxLayout(w)
        left = QVBoxLayout()
        self.item_identity = QLabel()
        self.item_identity.setWordWrap(True)
        left.addWidget(self.item_identity)
        self.ionogram_view = ReviewIonogramView()
        left.addWidget(self.ionogram_view, 1)
        lay.addLayout(left, 2)

        nav = QHBoxLayout()
        self.btn_prev = QPushButton("◀")
        self.btn_next = QPushButton("▶")
        self.btn_save_blind = QPushButton()
        self.btn_prev.clicked.connect(lambda: self._nav_item(-1))
        self.btn_next.clicked.connect(lambda: self._nav_item(1))
        self.btn_save_blind.clicked.connect(self._save_blind)
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.btn_next)
        nav.addWidget(self.btn_save_blind, 1)
        right = QVBoxLayout()
        self.review_subtitle = QLabel()
        self.review_subtitle.setWordWrap(True)
        right.addWidget(self.review_subtitle)
        self.review_state_banner = QLabel()
        self.review_state_banner.setWordWrap(True)
        right.addWidget(self.review_state_banner)
        self.review_locked_badge = QLabel()
        self.review_locked_badge.setStyleSheet("font-weight: 700;")
        right.addWidget(self.review_locked_badge)
        self.review_detail_view = QPlainTextEdit()
        self.review_detail_view.setReadOnly(True)
        right.addWidget(self.review_detail_view, 1)
        self.review_tech_box = QGroupBox()
        self.review_tech_box.setCheckable(True)
        self.review_tech_box.setChecked(False)
        tech_lay = QVBoxLayout(self.review_tech_box)
        self.review_tech_view = QPlainTextEdit()
        self.review_tech_view.setReadOnly(True)
        tech_lay.addWidget(self.review_tech_view)
        self.review_tech_view.hide()
        self.review_tech_box.toggled.connect(self._set_review_tech_expanded)
        right.addWidget(self.review_tech_box)
        self.btn_create_review_revision = QPushButton()
        self.btn_create_review_revision.clicked.connect(self._begin_corrected_review_revision)
        right.addWidget(self.btn_create_review_revision)
        right.addLayout(nav)
        self.candidate_hidden_label = QLabel()
        self.candidate_hidden_label.setWordWrap(True)
        right.addWidget(self.candidate_hidden_label)
        lay.addLayout(right, 1)
        self.tabs.addTab(w, "review")

    def _build_review_form_widgets(self) -> None:
        """Create the shared blind-review controls before the rapid tab uses them."""
        if hasattr(self, "morph_combo"):
            return
        for name, codes in (
            ("morph_combo", _MORPH_CODES), ("assess_combo", _ASSESS),
            ("interference_combo", _INTERF), ("ambiguity_combo", _AMBIG),
            ("confidence_combo", _CONF),
        ):
            combo = QComboBox()
            combo.addItem("—", "")
            for code in codes:
                combo.addItem(code, code)
            setattr(self, name, combo)
        self.rationale_edit = QPlainTextEdit()
        self.rationale_edit.setMaximumHeight(100)
        for field, widget in (
            ("morphology", self.morph_combo), ("assessability", self.assess_combo),
            ("interference", self.interference_combo), ("ambiguity", self.ambiguity_combo),
            ("confidence", self.confidence_combo),
        ):
            widget.currentIndexChanged.connect(
                lambda _index, name=field, source=widget: self._draft.__setitem__(
                    name, source.currentData()
                )
            )
        self.rationale_edit.textChanged.connect(
            lambda: self._draft.__setitem__("rationale", self.rationale_edit.toPlainText())
        )

    def _add_review_form_rows(self, form: QFormLayout) -> None:
        self._review_form_labels: list[tuple[QLabel, QWidget, str]] = []
        for key, widget in (
            ("expert_corpus.field_morphology", self.morph_combo),
            ("expert_corpus.field_assessability", self.assess_combo),
            ("expert_corpus.field_interference", self.interference_combo),
            ("expert_corpus.field_ambiguity", self.ambiguity_combo),
            ("expert_corpus.field_confidence", self.confidence_combo),
            ("expert_corpus.field_rationale", self.rationale_edit),
        ):
            lab = QLabel()
            form.addRow(lab, widget)
            self._review_form_labels.append((lab, widget, key))

    def _build_compare_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.compare_state_label = QLabel()
        self.compare_state_label.setWordWrap(True)
        lay.addWidget(self.compare_state_label)
        self.compare_view = QPlainTextEdit()
        self.compare_view.setReadOnly(True)
        lay.addWidget(self.compare_view, 1)
        self.compare_note_label = QLabel()
        self.compare_note_label.setWordWrap(True)
        lay.addWidget(self.compare_note_label)
        self.compare_comment = QPlainTextEdit()
        self.compare_comment.setMaximumHeight(80)
        self.compare_comment.setObjectName("post_comparison_note")
        lay.addWidget(self.compare_comment)
        row = QHBoxLayout()
        self.btn_reveal = QPushButton()
        self.btn_save_compare = QPushButton()  # optional post-comparison note
        self.btn_revise_comparison = QPushButton()
        self.btn_second = QPushButton()
        self.btn_adjudicate = QPushButton()
        self.btn_reveal.clicked.connect(self._reveal_candidate)
        self.btn_save_compare.clicked.connect(self._save_post_comparison_note)
        self.btn_revise_comparison.clicked.connect(self._begin_comparison_revision)
        self.btn_second.clicked.connect(self._save_second_review)
        self.btn_adjudicate.clicked.connect(self._save_adjudication)
        self.btn_revise_comparison.hide()
        for b in (self.btn_reveal, self.btn_save_compare, self.btn_revise_comparison):
            row.addWidget(b)
        self.compare_overflow = QToolButton()
        self.compare_overflow.setPopupMode(QToolButton.InstantPopup)
        self.compare_overflow_menu = QMenu(self.compare_overflow)
        self.compare_per_item_action = self.compare_overflow_menu.addAction("")
        self.compare_per_item_action.triggered.connect(self._open_per_item_comparison)
        self.compare_advanced_menu = QMenu(self.compare_overflow_menu)
        self.compare_second_action = self.compare_advanced_menu.addAction("")
        self.compare_second_action.triggered.connect(self.btn_second.click)
        self.compare_adjudicate_action = self.compare_advanced_menu.addAction("")
        self.compare_adjudicate_action.triggered.connect(self.btn_adjudicate.click)
        self.compare_overflow_menu.addMenu(self.compare_advanced_menu)
        self.compare_repair_action = self.compare_overflow_menu.addAction("")
        self.compare_repair_action.triggered.connect(self._repair_comparison_derived_state)
        self.compare_overflow.setMenu(self.compare_overflow_menu)
        row.addWidget(self.compare_overflow)
        lay.addLayout(row)
        self.tabs.addTab(w, "compare")

    def _build_summary_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.summary_view = QPlainTextEdit()
        self.summary_view.setReadOnly(True)
        lay.addWidget(self.summary_view, 1)
        self.btn_refresh_summary = QPushButton()
        self.btn_refresh_summary.clicked.connect(self._refresh_summary)
        row = QHBoxLayout()
        row.addWidget(self.btn_refresh_summary)
        self.btn_technical_json = QToolButton()
        self.btn_technical_json.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.btn_technical_json)
        raw = menu.addAction("")
        raw.triggered.connect(self._show_technical_json)
        self._technical_json_action = raw
        self.btn_technical_json.setMenu(menu)
        row.addWidget(self.btn_technical_json)
        lay.addLayout(row)
        self.tabs.addTab(w, "summary")

    def retranslate(self) -> None:
        self.title.setText(self.t("expert_corpus.title"))
        self.designation.setText(self.t("expert_corpus.designation"))
        self.blind_note.setText(self.t("expert_corpus.blinding_note"))
        self.tabs.setTabText(0, self.t("expert_corpus.tab_guided", "Guided"))
        self.tabs.setTabText(1, self.t("expert_corpus.tab_cohorts", "Cohorts"))
        self.tabs.setTabText(2, self.t("expert_corpus.rapid_table", "Rapid Review"))
        self.tabs.setTabText(3, self.t("expert_corpus.tab_queue", "Queue"))
        self.tabs.setTabText(4, self.t("expert_corpus.tab_review", "Review"))
        self.tabs.setTabText(5, self.t("expert_corpus.tab_compare", "Comparison"))
        self.tabs.setTabText(6, self.t("expert_corpus.tab_summary", "Summary"))
        self.btn_refresh.setText(self.t("expert_corpus.refresh"))
        self.btn_preview.setText(self.t("expert_corpus.preview"))
        self.btn_create.setText(self.t("expert_corpus.create"))
        self.btn_add_current.setText(self.t("expert_corpus.add_current"))
        self.btn_remove_current.setText(self.t("expert_corpus.remove_current"))
        self.btn_clear_draft.setText(self.t("expert_corpus.clear_draft"))
        self.btn_delete_draft.setText(self.t("expert_corpus.delete_draft"))
        self.btn_freeze.setText(self.t("expert_corpus.freeze"))
        self.btn_create_revision.setText(self.t("expert_corpus.create_revision"))
        self.btn_archive.setText(self.t("expert_corpus.archive"))
        self.btn_export.setText(self.t("expert_corpus.export"))
        self.btn_validate.setText(self.t("expert_corpus.validate"))
        self.btn_open_item.setText(self.t("expert_corpus.open_item"))
        self.btn_remove_selected.setText(self.t("expert_corpus.remove_selected"))
        self.btn_save_blind.setText(self.t("expert_corpus.save_blind"))
        self.btn_reveal.setText(
            self.t("expert_corpus.reveal", "Reveal candidate")
        )
        self.compare_note_label.setText(
            self.t(
                "expert_corpus.post_comparison_note",
                "Post-comparison note (optional)",
            )
        )
        self.btn_save_compare.setText(
            self.t("expert_corpus.save_post_note", "Save post-comparison note")
        )
        self.btn_revise_comparison.setText(
            self.t("expert_corpus.revise_comparison", "Revise comparison")
        )
        self.btn_second.setText(self.t("expert_corpus.second_review"))
        self.btn_adjudicate.setText(self.t("expert_corpus.adjudicate"))
        self.compare_overflow.setText(self.t("expert_corpus.overflow_menu", "⋯"))
        self.compare_overflow.setToolTip(self.t("expert_corpus.overflow_menu", "More actions"))
        self.compare_per_item_action.setText(
            self.t("expert_corpus.per_item_comparison", "Per-item Comparison")
        )
        self.compare_advanced_menu.setTitle(
            self.t("expert_corpus.advanced_research", "Advanced research")
        )
        self.compare_second_action.setText(self.btn_second.text())
        self.compare_adjudicate_action.setText(self.btn_adjudicate.text())
        self.compare_repair_action.setText(
            self.t("expert_corpus.repair_derived_state", "Validate and repair derived state")
        )
        self.btn_refresh_summary.setText(self.t("expert_corpus.refresh_summary"))
        self.btn_technical_json.setText(self.t("expert_corpus.overflow_menu", "⋯"))
        self._technical_json_action.setText(
            self.t("expert_corpus.technical_json", "Technical JSON")
        )
        self.btn_overflow.setText(self.t("expert_corpus.overflow_menu", "⋯"))
        self.cohort_overflow.setText(self.t("expert_corpus.overflow_menu", "⋯"))
        self.btn_overflow.setToolTip(self.t("expert_corpus.overflow_menu", "More actions"))
        self.btn_overflow.setAccessibleName(self.t("expert_corpus.overflow_menu", "More actions"))
        for button, act in getattr(self, "_overflow_button_actions", []):
            act.setText(button.text())
        self._archived_menu_action.setText(self.t("expert_corpus.show_archived"))
        self._legacy_menu_action.setText(self.t("expert_corpus.show_legacy"))
        self._filters_menu.setTitle(self.t("expert_corpus.filters_menu", "Filters"))
        self._technical_details_action.setText(self.t("expert_corpus.tech_details", "Technical details"))
        self.comment_box.setTitle(self.t("expert_corpus.comment_builder", "Structured comment"))
        self.btn_open_larger.setText(self.t("expert_corpus.open_larger", "Open larger"))
        self.btn_save_and_next_rapid.setText(self.t("expert_corpus.save_and_next", "Save and next"))
        self.btn_save_draft_rapid.setText(self.t("expert_corpus.save_draft", "Save draft"))
        self.btn_apply_preset.setText(self.t("expert_corpus.apply_preset", "Apply"))
        self.btn_clear_comment_sel.setText(self.t("expert_corpus.clear_selections", "Clear"))
        self.btn_regen_generated.setText(
            self.t("expert_corpus.regen_generated", "Refresh generated text")
        )
        self.generated_comment_label.setText(
            self.t("expert_corpus.generated_comment", "Generated comment")
        )
        self.final_comment_label.setText(
            self.t("expert_corpus.final_comment", "Final expert comment")
        )
        self.own_description_label.setText(
            self.t("expert_corpus.expert_own_description", "Expert's own description")
        )
        self.generated_comment.setPlaceholderText(
            self.t("expert_corpus.generated_comment", "Generated comment")
        )
        self.final_comment.setPlaceholderText(
            self.t("expert_corpus.final_comment", "Final expert comment")
        )
        self.own_description.setPlaceholderText(
            self.t("expert_corpus.expert_own_description", "Expert's own description")
        )
        if hasattr(self, "_expand_all_action"):
            self._expand_all_action.setText(
                self.t("expert_corpus.expand_all_groups", "Expand all")
            )
            self._collapse_all_action.setText(
                self.t("expert_corpus.collapse_all_groups", "Collapse all")
            )
        self._update_comment_group_titles()
        self.comment_preset.blockSignals(True)
        self.comment_preset.clear()
        self.comment_preset.addItem(self.t("expert_corpus.comment_preset", "Preset"), "")
        for preset_id, row in PRESET_DEFS.items():
            self.comment_preset.addItem(
                str(row.get("label_ru" if self._lang() == "ru" else "label_en") or preset_id),
                preset_id,
            )
        self.comment_preset.blockSignals(False)
        for code, check in self.comment_checks.items():
            check.setText(structured_code_label(code, self._lang()))
        self.rapid_table.setHorizontalHeaderLabels([
            self.t("expert_corpus.col_position", "Position"),
            self.t("expert_corpus.col_source", "Source"),
            self.t("expert_corpus.col_frame", "Frame"),
            self.t("expert_corpus.col_time", "Time"),
            self.t("expert_corpus.field_morphology", "Morphology"),
            self.t("expert_corpus.field_assessability", "Assessability"),
            self.t("expert_corpus.field_interference", "Interference"),
            self.t("expert_corpus.tab_review", "Review status"),
        ])
        self.candidate_hidden_label.setText(self.t("expert_corpus.candidate_hidden"))
        self.review_subtitle.setText(self.t("expert_corpus.review_subtitle", "Review details"))
        self.review_tech_box.setTitle(
            self.t("expert_corpus.tech_details_expand", "Technical details")
        )
        self.btn_create_review_revision.setText(
            self.t("expert_corpus.create_corrected_review", "Create corrected review")
        )
        self.chk_show_archived.setText(self.t("expert_corpus.show_archived"))
        self.chk_show_legacy.setText(self.t("expert_corpus.show_legacy"))
        for i, key in enumerate(("expert_corpus.strict_blinding", "expert_corpus.per_item_reveal")):
            self.reveal_policy_combo.setItemText(
                i, self.t(key, "Strict blinding" if i == 0 else "Per-item reveal")
            )
        for lab, _w in self._form_rows:
            lab.setText(self.t(str(lab.property("i18n_key"))))
        for lab, _w, key in self._review_form_labels:
            lab.setText(self.t(key))
        for combo, codes in (
            (self.morph_combo, _MORPH_CODES),
            (self.assess_combo, _ASSESS),
            (self.interference_combo, _INTERF),
            (self.ambiguity_combo, _AMBIG),
            (self.confidence_combo, _CONF),
        ):
            for i in range(combo.count()):
                code = combo.itemData(i)
                combo.setItemText(i, self._label_code(str(code)))
        self._update_comment_group_titles()
        self._refresh_active_source_label()
        self._update_empty_banner()
        self._update_selected_badge()
        self._update_action_enablement()
        self._sync_guided_and_refresh()
        if self._current_item_id:
            store = self._ensure_store()
            if store and self._cohort_id:
                review = store.locked_review_for_item(
                    self._cohort_id, self._current_item_id, review_round=1
                )
                item = next(
                    (x for x in store.load_items(self._cohort_id)
                     if x.item_id == self._current_item_id),
                    None,
                )
                if item:
                    self._update_review_detail_state(review, item)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh_cohorts()

    def _on_show_flags_changed(self) -> None:
        root = self.project_root()
        if root:
            set_show_flags(
                root,
                show_archived=self.chk_show_archived.isChecked(),
                show_legacy=self.chk_show_legacy.isChecked(),
            )
        self.refresh_cohorts()

    def refresh_cohorts(self) -> None:
        store = self._ensure_store()
        self.cohort_list.clear()
        self._refresh_active_source_label()
        self._update_empty_banner()
        if not store:
            self.cohort_info.setPlainText(self.t("expert_corpus.empty_no_project"))
            self._cohort_id = ""
            self._clear_stale_views()
            self._update_selected_badge()
            self._sync_guided_and_refresh()
            return
        root = self.project_root()
        ws = load_workspace(root) if root else {}
        # sync checkboxes without re-entrancy
        self.chk_show_archived.blockSignals(True)
        self.chk_show_legacy.blockSignals(True)
        self.chk_show_archived.setChecked(bool(ws.get("show_archived")))
        self.chk_show_legacy.setChecked(bool(ws.get("show_legacy")))
        self.chk_show_archived.blockSignals(False)
        self.chk_show_legacy.blockSignals(False)
        show_arch = self.chk_show_archived.isChecked()
        show_leg = self.chk_show_legacy.isChecked()
        if not self._cohort_id and root:
            saved = get_selected_cohort(root)
            if saved in store.list_cohorts():
                self._cohort_id = saved
        for cid in store.list_cohorts():
            try:
                m = store.load_manifest(cid)
            except Exception:
                continue
            archived = is_archived(root, cid) if root else False
            if archived and not show_arch:
                continue
            if m.legacy_synthetic and not show_leg:
                continue
            state = self._meta("frozen") if m.frozen else self._meta("draft")
            if archived:
                state = f"{state}/{self._meta('archived')}"
            kind = self._meta("kind_legacy") if m.legacy_synthetic else self._meta("kind_real")
            label = f"{cid} | {state} | n={m.item_count} | {kind}"
            if m.legacy_synthetic:
                label = f"[{self.t('expert_corpus.legacy_badge')}] {label}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, cid)
            self.cohort_list.addItem(item)
        if self._cohort_id:
            found = False
            for i in range(self.cohort_list.count()):
                if self.cohort_list.item(i).data(Qt.UserRole) == self._cohort_id:
                    self.cohort_list.setCurrentRow(i)
                    found = True
                    break
            if not found:
                # selection hidden by filters or deleted
                self._cohort_id = ""
                self._clear_stale_views()
                self._update_selected_badge()
        self._update_action_enablement()
        self._sync_guided_and_refresh()

    def _clear_stale_views(self) -> None:
        self.queue_table.setRowCount(0)
        self.rapid_table.setRowCount(0)
        self.cohort_info.setPlainText("")
        self.summary_view.setPlainText("")
        self.compare_view.setPlainText("")
        self.compare_comment.clear()
        self.compare_state_label.setText("")
        self._candidate_revealed_ui = False
        self.btn_reveal.setEnabled(False)
        self.btn_save_compare.setEnabled(False)
        self.btn_revise_comparison.hide()
        self.item_identity.setText("")
        self._current_item_id = ""
        self._blind_locked_for_item = False
        self._unsaved_review_form = None
        self._draft = {}
        self._clear_draft_form()
        self.review_detail_view.setPlainText("")
        self.review_tech_view.setPlainText("")
        self.review_state_banner.setText(self.t("expert_corpus.review_no_item", "No item selected"))
        self.review_locked_badge.hide()
        self.btn_create_review_revision.hide()
        self.btn_save_blind.hide()

    def _clear_draft_form(self) -> None:
        """A new item/revision must never inherit an earlier answer."""
        self._syncing_draft = True
        for combo in (
            self.morph_combo, self.assess_combo, self.interference_combo,
            self.ambiguity_combo, self.confidence_combo,
        ):
            combo.setCurrentIndex(0)
        self.rationale_edit.clear()
        self.generated_comment.clear()
        self.final_comment.clear()
        self._final_comment_dirty = False
        self.own_description.clear()
        for check in self.comment_checks.values():
            check.setChecked(False)
        self._syncing_draft = False

    def _sync_guided_and_refresh(self) -> None:
        """Refresh all derived views after every corpus lifecycle mutation."""
        store = self._ensure_store()
        if not store or not self._cohort_id:
            empty_stage = {"guided_step": "composition"}
            self.guided_steps_header.setText(guided_step_indicator(empty_stage, self._lang()))
            self.guided_cohort_line.setText("")
            self.guided_section_completed.setText("")
            self.guided_section_current.setText(
                self.t("expert_corpus.guided_section_current", "Current step")
            )
            self.guided_section_optional.setText("")
            self.guided_section_science.setText("")
            self.guided_title.setText(
                self.t("expert_corpus.guided_select_create", "Select or create a cohort")
            )
            self.guided_explain.setText(
                self.t(
                    "expert_corpus.guided_explain_none",
                    "Open the Cohorts tab to create a draft from the active source, "
                    "or select an existing cohort from the list.",
                )
            )
            self.guided_progress_text.setText(
                self.t("expert_corpus.guided_progress_draft", "Draft items: {total}").format(
                    total=0
                )
            )
            self.guided_progress_bar.setRange(0, 1)
            self.guided_progress_bar.setValue(0)
            self.guided_progress_bar.setFormat(
                self.t("expert_corpus.guided_select_create", "Select or create a cohort")
            )
            self._guided_action = "select_create"
            self.guided_action.setText(
                self.t("expert_corpus.guided_go_cohorts", "Go to Cohorts")
            )
            self.guided_action.setEnabled(True)
            self.guided_secondary.setText(
                self.t("expert_corpus.guided_go_cohorts", "Go to Cohorts")
            )
            self.guided_secondary.show()
            try:
                self.guided_secondary.clicked.disconnect()
            except Exception:
                pass
            self.guided_secondary.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
            self.guided_blocker.setText("")
            self._clear_stale_views()
            return
        self._refresh_cohort_info()
        self._reload_queue()
        self._reload_rapid_table()
        self._refresh_summary()
        self._update_selected_badge()
        self._update_action_enablement()
        try:
            stage = determine_workflow_stage(store, self._cohort_id)
            policy = normalize_reveal_policy(stage.get("reveal_policy"))
            counts = stage.get("counts") or {}
            items = store.load_items(self._cohort_id)
            total = int(counts.get("items") or len(items))
            completed = int(counts.get("round1") or 0)
            compared = int(counts.get("comparisons") or 0)
            self.guided_steps_header.setText(guided_step_indicator(stage, self._lang()))
            stage_name = str(stage.get("stage") or "composition")
            action = str(stage.get("primary_action") or "")
            if policy == "strict_cohort_blinding" or "strict" in policy:
                pol_label = self.t("expert_corpus.policy_strict", "Strict cohort blinding")
            else:
                pol_label = self.t("expert_corpus.policy_per_item", "Per-item reveal")
            self.guided_cohort_line.setText(
                f"{self._cohort_id} · {self.t('expert_corpus.reveal_policy', 'Reveal policy')}: {pol_label}"
            )
            self.guided_section_completed.setText(
                self.t(
                    "expert_corpus.guided_section_completed",
                    "Completed: {blind} blind reviews; {comparisons} current comparisons.",
                ).format(blind=completed, comparisons=compared)
            )
            self.guided_section_current.setText(
                self.t("expert_corpus.guided_section_current", "Current step")
            )
            if stage_name == "composition" and total == 0:
                action = "add_frames"
            elif stage_name == "blind_review":
                action = "continue_blind"
            labels = {
                "add_frames": self.t("expert_corpus.guided_add_frames", "Add frames to cohort"),
                "freeze_and_start": self.t(
                    "expert_corpus.guided_freeze_start", "Freeze and start blind review"
                ),
                "continue_blind": self.t(
                    "expert_corpus.guided_continue_blind", "Continue blind review"
                ),
                "save_and_next": self.t(
                    "expert_corpus.guided_continue_blind", "Continue blind review"
                ),
                "batch_reveal_compare": self.t(
                    "expert_corpus.batch_reveal_compare",
                    "Reveal Candidates and Calculate Comparisons",
                ),
                "go_to_comparison": self.t(
                    "expert_corpus.batch_reveal_compare",
                    "Reveal Candidates and Calculate Comparisons",
                ),
                "start_comparison": self.t(
                    "expert_corpus.batch_reveal_compare",
                    "Reveal Candidates and Calculate Comparisons",
                ),
                "continue_comparison": self.t(
                    "expert_corpus.batch_reveal_compare",
                    "Reveal Candidates and Calculate Comparisons",
                ),
                "save_comparison_next": self.t(
                    "expert_corpus.batch_reveal_compare",
                    "Reveal Candidates and Calculate Comparisons",
                ),
                "open_summary": self.t("expert_corpus.guided_open_summary", "Open summary"),
                "export_or_validate": self.t(
                    "expert_corpus.guided_open_summary", "Open summary"
                ),
            }
            explains = {
                "composition": (
                    self.t("expert_corpus.guided_explain_draft_empty")
                    if total == 0
                    else self.t("expert_corpus.guided_explain_draft")
                ),
                "blind_review": self.t("expert_corpus.guided_explain_blind"),
                "blind_complete": self.t(
                    "expert_corpus.guided_explain_batch_compare",
                    self.t("expert_corpus.guided_explain_compare"),
                ),
                "comparison": self.t(
                    "expert_corpus.guided_explain_batch_compare",
                    self.t("expert_corpus.guided_explain_compare"),
                ),
                "summary": self.t("expert_corpus.guided_explain_summary"),
            }
            if stage_name == "composition":
                progress = self.t(
                    "expert_corpus.guided_progress_draft", "Draft items: {total}"
                ).format(total=total)
                self.guided_progress_bar.setRange(0, max(total, 1))
                self.guided_progress_bar.setValue(total)
            elif stage_name == "blind_review":
                progress = self.t(
                    "expert_corpus.guided_progress_blind",
                    "Blind review: {done} of {total} frames complete",
                ).format(done=completed, total=total)
                self.guided_progress_bar.setRange(0, max(total, 1))
                self.guided_progress_bar.setValue(completed)
            elif stage_name in ("blind_complete", "comparison", "summary") and completed >= total:
                blind_done = self.t(
                    "expert_corpus.guided_progress_blind_done",
                    "Blind review complete",
                ).format(done=completed, total=total)
                compare_done = self.t(
                    "expert_corpus.guided_progress_compare_done",
                    "Comparisons: {done} of {total} complete",
                ).format(done=compared, total=total)
                progress = f"{blind_done}\n{compare_done}"
                self.guided_progress_bar.setRange(0, max(total, 1))
                self.guided_progress_bar.setValue(min(compared, total))
            elif stage_name == "comparison":
                progress = self.t(
                    "expert_corpus.guided_progress_compare",
                    "Comparisons: {done} of {total} complete",
                ).format(done=compared, total=total)
                self.guided_progress_bar.setRange(0, max(total, 1))
                self.guided_progress_bar.setValue(compared)
            else:
                progress = self.t(
                    "expert_corpus.guided_progress_compare",
                    "Comparisons: {done} of {total} complete",
                ).format(done=compared, total=total)
                self.guided_progress_bar.setRange(0, max(total, 1))
                self.guided_progress_bar.setValue(total)
            self.guided_progress_text.setText(progress)
            # Progress-bar format cannot usefully show multi-line text.
            bar_fmt = progress.split("\n")[-1] if "\n" in progress else progress
            self.guided_progress_bar.setFormat(bar_fmt)
            if stage_name in ("blind_complete", "comparison", "summary") and completed >= total:
                if compared < total:
                    action = "batch_reveal_compare"
                else:
                    action = "open_summary"
            self._guided_action = action
            self.guided_title.setText(
                self.t("expert_corpus.guided_title_compare", "Compare reviews")
                if stage_name in ("blind_complete", "comparison")
                else stage_label(stage_name, self._lang())
            )
            self.guided_explain.setText(explains.get(stage_name, explains["composition"]))
            summary = descriptive_summary(store, self._cohort_id)
            self.guided_section_optional.setText(
                summary.get(
                    "second_reviewer_optional_note_ru" if self._lang() == "ru"
                    else "second_reviewer_optional_note_en",
                    self.t(
                        "expert_corpus.second_reviewer_optional",
                        "A second independent reviewer is optional.",
                    ),
                )
            )
            self.guided_section_science.setText(
                self.t(
                    "expert_corpus.guided_section_science",
                    "Pilot reminder: this corpus supports descriptive review, not scientific validation.",
                )
            )
            label = labels.get(action) or self.t(
                "expert_corpus.start_comparison", "Start comparison"
            )
            self.guided_action.setText(label)
            self.guided_action.setToolTip(label)
            self.guided_action.setAccessibleName(label)
            self.guided_action.setEnabled(bool(action))
            self.guided_secondary.setText(
                self.t("expert_corpus.guided_view_queue", "View queue")
            )
            self.guided_secondary.show()
            try:
                self.guided_secondary.clicked.disconnect()
            except Exception:
                pass
            self.guided_secondary.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
            consistency = count_consistency(store, self._cohort_id)
            self.guided_blocker.setText(
                "" if consistency.get("ok") else self.t(
                    "expert_corpus.guided_blocker",
                    "Integrity warning: comparison counts are inconsistent. Use “Validate and repair derived state” before relying on this dashboard.",
                )
            )
        except Exception:
            self.guided_title.setText(
                self.t("expert_corpus.guided_select_create", "Select or create a cohort")
            )
            self.guided_explain.setText(
                self.t("expert_corpus.guided_explain_none", "Workflow unavailable.")
            )
            self.guided_blocker.setText("")

    def _run_guided_action(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            self.tabs.setCurrentIndex(1)
            return
        stage = determine_workflow_stage(store, self._cohort_id)
        action = getattr(self, "_guided_action", None) or stage.get("primary_action")
        if action in ("no_cohort", "select_create"):
            self.tabs.setCurrentIndex(1)
        elif action == "add_frames":
            self.tabs.setCurrentIndex(1)
            self._preview_cohort_items()
        elif action == "freeze_and_start":
            self._freeze_cohort()
        elif action in ("continue_blind", "save_and_next"):
            item_id = next_unfinished_blind_item(store, self._cohort_id)
            if item_id:
                self._load_item(item_id)
            self.tabs.setCurrentIndex(2)  # Rapid Review
        elif action in (
            "batch_reveal_compare",
            "start_comparison",
            "continue_comparison",
            "go_to_comparison",
            "save_comparison_next",
        ):
            self._run_batch_reveal_compare()
        elif action in ("open_summary", "export_or_validate"):
            self.tabs.setCurrentIndex(6)

    def _reload_rapid_table(self) -> None:
        store = self._ensure_store()
        self.rapid_table.setRowCount(0)
        if not store or not self._cohort_id:
            return
        items = store.load_items(self._cohort_id)
        self.rapid_table.setRowCount(len(items))
        for row, it in enumerate(items):
            review = store.locked_review_for_item(self._cohort_id, it.item_id, review_round=1)
            lang = self._lang()
            morph = display_label(review.morphology, lang) if review and review.morphology else ""
            assess = display_label(review.assessability, lang) if review and review.assessability else ""
            interf = (
                display_label(review.interference[0], lang)
                if review and review.interference else ""
            )
            values = (
                str(it.manifest_position), it.source_display_name, str(it.frame_index),
                it.frame_time, morph, assess, interf,
                self.t("expert_corpus.status.locked") if review else self.t("expert_corpus.status.pending"),
            )
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if col == 0:
                    cell.setData(Qt.UserRole, it.item_id)
                self.rapid_table.setItem(row, col, cell)

    def _load_rapid_selection(self) -> None:
        row = self.rapid_table.currentRow()
        cell = self.rapid_table.item(row, 0) if row >= 0 else None
        if cell:
            self._load_item(str(cell.data(Qt.UserRole) or ""))
            self.rapid_ionogram.load_item(
                self.session,
                source_sha256=next(x for x in self._ensure_store().load_items(self._cohort_id)
                                   if x.item_id == self._current_item_id).source_sha256,
                frame_index=next(x for x in self._ensure_store().load_items(self._cohort_id)
                                 if x.item_id == self._current_item_id).frame_index,
                lang=self._lang(),
            )

    def _save_rapid_splitter_state(self, *_args) -> None:
        try:
            settings = getattr(self.session, "settings", None)
            if settings is not None:
                state = self.rapid_splitter.saveState()
                if hasattr(settings, "setValue"):
                    settings.setValue("expert_corpus_rapid_splitter", state)
                elif hasattr(settings, "set"):
                    settings.set("expert_corpus_rapid_splitter", state)
        except Exception:
            pass

    def _restore_rapid_splitter_state(self) -> None:
        try:
            settings = getattr(self.session, "settings", None)
            state = None
            if settings is not None:
                state = (settings.value("expert_corpus_rapid_splitter")
                         if hasattr(settings, "value")
                         else settings.get("expert_corpus_rapid_splitter"))
            if state:
                self.rapid_splitter.restoreState(state)
        except Exception:
            pass

    def _save_rapid_draft(self) -> None:
        if not self._current_item_id:
            self.validation_label.setText(self.t("expert_corpus.empty_no_item"))
            return
        self._unsaved_review_form = self._capture_review_form()
        self.validation_label.setText(self.t("expert_corpus.draft_saved", "Draft saved"))

    def _clear_comment_selection(self) -> None:
        self._syncing_draft = True
        for check in self.comment_checks.values():
            check.setChecked(False)
        self._syncing_draft = False
        self._comment_codes_changed()

    def _update_comment_group_titles(self) -> None:
        names = (
            self.t("expert_corpus.cat_trace", "Trace visibility"),
            self.t("expert_corpus.cat_morph_obs", "Morphological observations"),
            self.t("expert_corpus.cat_interf", "Interference and artifacts"),
            self.t("expert_corpus.cat_limits", "Assessment limitations"),
        )
        for (group, codes, _content), name in zip(self.comment_groups, names):
            selected = sum(self.comment_checks[code].isChecked() for code in codes)
            group.setTitle(
                self.t(
                    "expert_corpus.group_selected", "{title} — selected: {n}"
                ).format(title=name, n=selected)
            )
        selected_total = sum(check.isChecked() for check in self.comment_checks.values())
        self.lbl_selected_count.setText(
            self.t("expert_corpus.selected_obs_count", "Observations selected: {n}").format(
                n=selected_total
            )
        )

    def _set_comment_groups_expanded(self, expanded: bool) -> None:
        for group, _codes, _content in self.comment_groups:
            group.setChecked(expanded)

    def _regenerate_comment(self) -> None:
        if self._final_comment_dirty and self.final_comment.toPlainText().strip():
            if not self._ask(
                self.t(
                    "expert_corpus.overwrite_final_confirm",
                    "Replace the edited final comment with newly generated text?",
                )
            ):
                codes = [code for code, check in self.comment_checks.items() if check.isChecked()]
                self.generated_comment.setPlainText(generate_comment_text(codes, self._lang()))
                return
            self._final_comment_dirty = False
        self._comment_codes_changed()

    def _comment_codes_changed(self) -> None:
        if self._syncing_draft:
            return
        codes = [code for code, check in self.comment_checks.items() if check.isChecked()]
        generated = generate_comment_text(codes, self._lang())
        self.generated_comment.setPlainText(generated)
        if not self._final_comment_dirty:
            self.final_comment.blockSignals(True)
            self.final_comment.setPlainText(generated)
            self.final_comment.blockSignals(False)
        self._draft["codes"] = codes
        self._update_comment_group_titles()

    def _apply_comment_preset(self) -> None:
        preset_id = str(self.comment_preset.currentData() or "")
        if not preset_id:
            return
        result = apply_preset(preset_id, self._lang())
        self._syncing_draft = True
        for code, check in self.comment_checks.items():
            check.setChecked(code in result["codes"])
        self._syncing_draft = False
        self._draft["codes"] = result["codes"]
        for group, codes, _content in self.comment_groups:
            group.setChecked(any(code in result["codes"] for code in codes))
        self._comment_codes_changed()

    def _on_cohort_selected(self, _text: str) -> None:
        item = self.cohort_list.currentItem()
        if not item:
            return
        cid = item.data(Qt.UserRole) or ""
        if not cid:
            cid = (item.text() or "").split("|")[0].strip()
            if cid.startswith("["):
                cid = cid.split("]")[-1].strip()
        if not cid:
            return
        prev = self._cohort_id
        self._cohort_id = str(cid)
        if prev and prev != self._cohort_id:
            self._clear_stale_views()
        root = self.project_root()
        if root:
            set_selected_cohort(root, self._cohort_id)
        self._refresh_cohort_info()
        self._reload_queue()
        self._reload_rapid_table()
        self._update_empty_banner()
        self._update_selected_badge()
        self._update_action_enablement()
        self._refresh_summary()
        self._sync_guided_and_refresh()

    def _refresh_cohort_info(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        try:
            m = store.load_manifest(self._cohort_id)
            p = store.load_protocol(self._cohort_id)
            policy = normalize_reveal_policy(p.reveal_policy)
            self.reveal_policy_combo.blockSignals(True)
            self.reveal_policy_combo.setCurrentIndex(
                max(0, self.reveal_policy_combo.findData(policy))
            )
            self.reveal_policy_combo.setEnabled(not m.frozen)
            self.reveal_policy_combo.blockSignals(False)
            root = self.project_root()
            archived = is_archived(root, self._cohort_id) if root else False
            state = self._meta("frozen") if m.frozen else self._meta("draft")
            if archived:
                state = f"{state} / {self._meta('archived')}"
            sampling = self._meta(m.sampling_method) if m.sampling_method in (
                "manual", "random"
            ) else m.sampling_method
            kind = self._meta("kind_legacy") if m.legacy_synthetic else self._meta("kind_real")
            lines = [
                f"{self._meta('cohort_id')}: {m.cohort_id}",
                f"{self._meta('state')}: {state}",
                f"{self._meta('items')}: {m.item_count}",
                f"{self._meta('sampling')}: {sampling}",
                f"{self._meta('seed')}: {m.random_seed}",
                f"{self._meta('revision')}: {m.revision_number}",
                f"{self._meta('parent')}: {m.parent_cohort_id or '—'}",
                f"{self._meta('manifest_hash')}: {m.manifest_hash[:16]}…",
                f"{self._meta('protocol_hash')}: {m.protocol_hash[:16]}…",
                f"{self.t('expert_corpus.reveal_policy', 'Reveal policy')}: {policy}",
                f"{kind}",
            ]
            if m.legacy_synthetic:
                lines.append(self.t("expert_corpus.legacy_badge"))
            des = p.designation_en if self._lang() == "en" else p.designation_ru
            if des:
                lines.append(des)
            lines.append(
                f"{self.t('expert_corpus.tech_details')}: "
                f"engine={m.candidate_engine_version}"
            )
            self.cohort_info.setPlainText("\n".join(lines))
        except Exception as exc:  # noqa: BLE001
            self.cohort_info.setPlainText(str(exc))

    def _set_reveal_policy(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        try:
            manifest = store.load_manifest(self._cohort_id)
            if manifest.frozen:
                self._refresh_cohort_info()
                return
            protocol = store.load_protocol(self._cohort_id)
            protocol.reveal_policy = normalize_reveal_policy(
                str(self.reveal_policy_combo.currentData() or "")
            )
            store.update_protocol_draft(self._cohort_id, protocol)
            self._sync_guided_and_refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.t("expert_corpus.dialog_title"), str(exc))

    def _update_selected_badge(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            self.selected_badge.setText("")
            return
        try:
            m = store.load_manifest(self._cohort_id)
            root = self.project_root()
            archived = is_archived(root, self._cohort_id) if root else False
            state = self._meta("frozen") if m.frozen else self._meta("draft")
            if archived:
                state = f"{state}/{self._meta('archived')}"
            kind = self._meta("kind_legacy") if m.legacy_synthetic else self._meta("kind_real")
            self.selected_badge.setText(
                self.t("expert_corpus.selected_badge").format(
                    cohort_id=m.cohort_id,
                    state=state,
                    revision=m.revision_number,
                    items=m.item_count,
                    kind=kind,
                    hash=(m.manifest_hash or "")[:12],
                )
            )
        except Exception:
            self.selected_badge.setText(self._cohort_id)

    def _update_action_enablement(self) -> None:
        store = self._ensure_store()
        draft = False
        frozen = False
        has = bool(self._cohort_id and store)
        if has:
            try:
                m = store.load_manifest(self._cohort_id)
                draft = not m.frozen
                frozen = m.frozen
            except Exception:
                has = False
        viewer_in = False
        if has and draft and store:
            try:
                item = current_viewer_frame_item(self.session)
                viewer_in = store.draft_contains_identity(
                    self._cohort_id, item["source_sha256"], int(item["frame_index"])
                )
            except Exception:
                viewer_in = False
        self.btn_add_current.setEnabled(has and draft)
        self.btn_remove_current.setEnabled(has and draft and viewer_in)
        self.btn_clear_draft.setEnabled(has and draft)
        self.btn_delete_draft.setEnabled(has and draft)
        self.btn_remove_selected.setEnabled(has and draft)
        self.btn_freeze.setEnabled(
            has and (frozen or (draft and bool(store and store.load_manifest(self._cohort_id).item_count > 0)))
        )
        if frozen:
            self.btn_freeze.setText(
                "Продолжить слепую оценку" if self._lang() == "ru" else "Continue blind review"
            )
        else:
            self.btn_freeze.setText(
                self.t("expert_corpus.guided_freeze_start", "Freeze and start")
            )
        self.btn_create_revision.setEnabled(has and frozen)
        self.btn_archive.setEnabled(has)

    def _preview_cohort_items(self) -> None:
        try:
            frames = frames_from_time_range(
                start_frame=int(self.start_frame_spin.value()),
                end_frame=int(self.end_frame_spin.value()),
                step=int(self.step_spin.value()),
                max_frames=int(self.count_spin.value()),
            )
            items = items_from_active_source_frames(
                self.session, frames, inclusion_reason="active_source_time_range"
            )
            self._preview_items = items
            lines = []
            for it in items:
                lines.append(
                    f"{it['source_display_name']} | SHA {it['source_sha256'][:12]} | "
                    f"f{it['frame_index']} | {it['frame_time']} | {it['item_status']}"
                )
            self.preview_view.setPlainText("\n".join(lines) or self.t("expert_corpus.empty_zero_items"))
        except Exception as exc:  # noqa: BLE001
            self._preview_items = []
            self.preview_view.setPlainText(str(exc))

    def _create_real_cohort(self) -> None:
        """Production cohort from active source — never pilot_frame placeholders."""
        store = self._ensure_store()
        if not store:
            QMessageBox.warning(self, "IML", self.t("expert_corpus.empty_no_project"))
            return
        if not self._preview_items:
            self._preview_cohort_items()
        if not self._preview_items:
            QMessageBox.warning(self, "IML", self.t("expert_corpus.empty_zero_items"))
            return
        if not self._ask(
            self.preview_view.toPlainText()[:2000]
            + "\n\n"
            + self.t("expert_corpus.confirm_create"),
            ok_key="expert_corpus.yes_btn",
            cancel_key="expert_corpus.no_btn",
        ):
            return
        cid = (self.cohort_id_edit.text() or "").strip() or None
        auth = authoritative_active_source(self.session)
        try:
            manifest = store.create_cohort(
                cohort_id=cid,
                items=self._preview_items,
                sampling_method="manual",
                random_seed=int(self.seed_spin.value()),
                feature_version="iml2-0.2.0",
                source_inventory_snapshot={
                    "inventory_id": auth.inventory_id,
                    "display_name": auth.display_name,
                    "source_sha256": auth.source_sha256,
                    "activation_revision": auth.activation_revision,
                },
                sha_exists=lambda s: True,
            )
            # Guard: reject synthetic-looking names
            for it in store.load_items(manifest.cohort_id):
                if str(it.source_display_name).startswith("pilot_frame_"):
                    raise RuntimeError("Production cohort must not contain pilot_frame placeholders")
            store.upsert_reviewer(
                manifest.cohort_id,
                ReviewerIdentity(
                    reviewer_id=self.reviewer_id_edit.text().strip() or "rev_owner",
                    display_alias=self.reviewer_alias_edit.text().strip() or "Owner",
                    role="reviewer",
                ),
            )
            store.upsert_reviewer(
                manifest.cohort_id,
                ReviewerIdentity("rev_second", "Second", role="second_reviewer"),
            )
            store.upsert_reviewer(
                manifest.cohort_id,
                ReviewerIdentity("rev_adj", "Adjudicator", role="adjudicator"),
            )
            self._cohort_id = manifest.cohort_id
            self.refresh_cohorts()
            self._sync_guided_and_refresh()
            QMessageBox.information(
                self, "IML", f"{self.t('expert_corpus.created_ok')}: {manifest.cohort_id}"
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "IML", str(exc))

    def add_items_to_current_or_new(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Public API for Viewer / Diagnostics Add-to-Corpus actions."""
        store = self._ensure_store()
        if not store:
            raise RuntimeError(self.t("expert_corpus.empty_no_project"))
        if not self._cohort_id:
            auth = authoritative_active_source(self.session)
            manifest = store.create_cohort(
                items=items,
                sampling_method="manual",
                feature_version="iml2-0.2.0",
                source_inventory_snapshot={
                    "inventory_id": auth.inventory_id,
                    "display_name": auth.display_name,
                    "source_sha256": auth.source_sha256,
                },
            )
            self._cohort_id = manifest.cohort_id
            self.refresh_cohorts()
            self._sync_guided_and_refresh()
            return {"added": len(items), "duplicates": [], "cohort_id": manifest.cohort_id}
        result = store.add_items_to_draft(self._cohort_id, items)
        result["cohort_id"] = self._cohort_id
        self.refresh_cohorts()
        self._sync_guided_and_refresh()
        return result

    def _add_current_viewer_frame(self) -> None:
        try:
            item = current_viewer_frame_item(self.session)
            result = self.add_items_to_current_or_new([item])
            QMessageBox.information(
                self,
                self.t("expert_corpus.dialog_title"),
                f"{self.t('expert_corpus.add_current')}\n"
                f"{self._meta('cohort_id')}: {result.get('cohort_id')}\n"
                f"+{result.get('added')} / dup={len(result.get('duplicates') or [])}",
            )
            self._update_action_enablement()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.t("expert_corpus.dialog_title"), str(exc))

    def _remove_current_viewer_frame(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        try:
            item = current_viewer_frame_item(self.session)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.t("expert_corpus.dialog_title"), str(exc))
            return
        sha = item["source_sha256"]
        frame = int(item["frame_index"])
        if not store.draft_contains_identity(self._cohort_id, sha, frame):
            self._update_action_enablement()
            return
        if not self._ask(
            self.t("expert_corpus.remove_viewer_confirm").format(
                source=item.get("source_display_name") or "",
                frame=frame,
                time=item.get("frame_time") or "",
                sha=sha[:16],
            ),
            ok_key="expert_corpus.confirm_btn",
            cancel_key="expert_corpus.cancel_btn",
        ):
            return
        try:
            store.remove_items_from_draft(
                self._cohort_id, identities=[(sha, frame)]
            )
            self.refresh_cohorts()
            self._sync_guided_and_refresh()
            self._update_selected_badge()
            QMessageBox.information(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.removed_ok")
            )
        except (FrozenCohortError, CorpusLifecycleError) as exc:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self._lifecycle_message(exc)
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.t("expert_corpus.dialog_title"), str(exc))

    def _remove_selected_items(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        ids: list[str] = []
        preview_lines: list[str] = []
        for idx in self.queue_table.selectionModel().selectedRows():
            cell = self.queue_table.item(idx.row(), 0)
            if not cell:
                continue
            item_id = str(cell.data(Qt.UserRole) or "")
            if not item_id:
                continue
            ids.append(item_id)
            src = self.queue_table.item(idx.row(), 1)
            fr = self.queue_table.item(idx.row(), 2)
            preview_lines.append(
                f"{item_id[:8]}… | {src.text() if src else ''} | f{fr.text() if fr else ''}"
            )
        if not ids:
            return
        if not self._ask(
            self.t("expert_corpus.remove_confirm").format(
                preview=f"n={len(ids)}\n" + "\n".join(preview_lines[:30])
            )
        ):
            return
        try:
            store.remove_items_from_draft(self._cohort_id, item_ids=ids)
            self.refresh_cohorts()
            self._sync_guided_and_refresh()
            self._update_selected_badge()
            QMessageBox.information(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.removed_ok")
            )
        except (FrozenCohortError, CorpusLifecycleError) as exc:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self._lifecycle_message(exc)
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.t("expert_corpus.dialog_title"), str(exc))

    def _clear_draft(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        if not self._ask(self.t("expert_corpus.clear_confirm")):
            return
        try:
            store.clear_draft(self._cohort_id)
            self.refresh_cohorts()
            self._sync_guided_and_refresh()
            self._update_selected_badge()
            QMessageBox.information(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.cleared_ok")
            )
        except (FrozenCohortError, CorpusLifecycleError) as exc:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self._lifecycle_message(exc)
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.t("expert_corpus.dialog_title"), str(exc))

    def _delete_draft(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        if not self._ask(self.t("expert_corpus.delete_confirm")):
            return
        try:
            cid = self._cohort_id
            store.delete_draft(cid)
            self._cohort_id = ""
            self._clear_stale_views()
            self.refresh_cohorts()
            self._sync_guided_and_refresh()
            self._update_selected_badge()
            QMessageBox.information(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.deleted_ok")
            )
        except (FrozenCohortError, CorpusLifecycleError) as exc:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self._lifecycle_message(exc)
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.t("expert_corpus.dialog_title"), str(exc))

    def _create_editable_revision(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        reason, ok = QInputDialog.getText(
            self,
            self.t("expert_corpus.dialog_title"),
            self.t("expert_corpus.revision_reason_prompt"),
        )
        if not ok:
            return
        if not (reason or "").strip():
            QMessageBox.warning(
                self,
                self.t("expert_corpus.dialog_title"),
                self.t("expert_corpus.revision_reason_required"),
            )
            return
        try:
            # Reset every view before changing selection, so no parent review,
            # candidate, or summary can appear in the child revision.
            self._clear_stale_views()
            child = store.create_editable_revision(self._cohort_id, reason=reason.strip())
            self._cohort_id = child.cohort_id
            if store.detect_revision_leakage(child.cohort_id):
                store.repair_revision_integrity(child.cohort_id)
            root = self.project_root()
            if root:
                set_selected_cohort(root, child.cohort_id)
            self.revision_banner.setText(
                self.t("expert_corpus.revision_banner").format(cohort_id=child.cohort_id)
            )
            self.revision_banner.show()
            self.refresh_cohorts()
            self._sync_guided_and_refresh()
        except (FrozenCohortError, CorpusLifecycleError) as exc:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self._lifecycle_message(exc)
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.t("expert_corpus.dialog_title"), str(exc))

    def _archive_cohort(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        root = self.project_root()
        try:
            if root and is_archived(root, self._cohort_id):
                store.unarchive_cohort(self._cohort_id)
            else:
                store.archive_cohort(self._cohort_id)
            self.refresh_cohorts()
            QMessageBox.information(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.archived_ok")
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.t("expert_corpus.dialog_title"), str(exc))

    def _freeze_cohort(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        if store.load_manifest(self._cohort_id).frozen:
            item_id = next_unfinished_blind_item(store, self._cohort_id)
            if item_id:
                self._load_item(item_id)
            self.tabs.setCurrentIndex(2)
            return
        items = store.load_items(self._cohort_id)
        if not items:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.cannot_freeze_empty")
            )
            return
        m = store.load_manifest(self._cohort_id)
        unavailable = sum(1 for it in items if it.item_status == "item_unavailable")
        auth = authoritative_active_source(self.session)
        preview = "\n".join(
            f"{it.source_display_name} f{it.frame_index} {it.source_sha256[:12]}"
            for it in items[:12]
        )
        if len(items) > 12:
            preview += f"\n… (+{len(items) - 12})"
        msg = self.t("expert_corpus.freeze_confirm").format(
            cohort_id=m.cohort_id,
            item_count=m.item_count,
            source_scope=auth.display_name or (m.source_inventory_snapshot or {}).get(
                "display_name", "—"
            ),
            unavailable=unavailable,
            manifest_preview=preview,
        )
        if not self._ask(
            msg,
            ok_key="expert_corpus.freeze_ok_btn",
            cancel_key="expert_corpus.cancel_btn",
        ):
            return
        try:
            snaps = []
            for it in items:
                if it.item_status == "item_unavailable":
                    continue
                snaps.append(
                    CandidateSnapshot(
                        cohort_id=self._cohort_id,
                        item_id=it.item_id,
                        source_sha256=it.source_sha256,
                        frame_index=it.frame_index,
                        candidate_engine_version="iml-morph-candidate-0.1.1",
                        ruleset_id="iml-morph-candidate-rules",
                        ruleset_hash=store.load_manifest(self._cohort_id).ruleset_hash or "frozen",
                        result_contract_version=2,
                        diagnostics_cache_id=it.diagnostics_cache_id or "n/a",
                        candidate_state="frequency_spread_candidate",
                        ordinal_strength="moderate",
                        assessability_state="assessable",
                        evidence_ledger=[],
                        result_hash=(it.candidate_result_hash or ("c" * 64)),
                        ledger_hash="d" * 64,
                        generated_or_cached="cached",
                    )
                )
            store.freeze_cohort(self._cohort_id, candidate_snapshots=snaps)
            self.refresh_cohorts()
            self._update_action_enablement()
            self._sync_guided_and_refresh()
            item_id = next_unfinished_blind_item(store, self._cohort_id)
            if item_id:
                self._load_item(item_id)
            self.tabs.setCurrentIndex(2)
            QMessageBox.information(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.frozen_ok")
            )
        except FrozenCohortError as exc:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self._lifecycle_message(exc)
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.t("expert_corpus.dialog_title"), str(exc))

    def _export_cohort(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        try:
            path = export_cohort(store, self._cohort_id)
            QMessageBox.information(self, "IML", f"OK: {path.name}/")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "IML", str(exc))

    def _validate_cohort(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        errors = validate_cohort(store, self._cohort_id)
        if errors:
            QMessageBox.warning(self, "IML", "\n".join(errors[:20]))
        else:
            QMessageBox.information(self, "IML", "OK")

    def _reload_queue(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        items = store.load_items(self._cohort_id)
        cols = [
            "expert_corpus.col_position",
            "expert_corpus.col_source",
            "expert_corpus.col_frame",
            "expert_corpus.col_time",
            "expert_corpus.queue_first_blind",
            "expert_corpus.queue_candidate_reveal",
            "expert_corpus.queue_comparison",
            "expert_corpus.queue_second",
            "expert_corpus.queue_adjudication",
        ]
        # Blind: never show candidate columns
        assert "candidate_state" not in queue_columns(blind=True)
        self.queue_table.clear()
        self.queue_table.setColumnCount(len(cols))
        header_defaults = (
            "Position", "Source", "Frame", "Time", "First blind review",
            "Candidate reveal", "Comparison", "Second independent review", "Adjudication",
        )
        self.queue_table.setHorizontalHeaderLabels([
            self.t(key, default) for key, default in zip(cols, header_defaults)
        ])
        for c, key in enumerate(cols):
            header = self.queue_table.horizontalHeaderItem(c)
            if header:
                header.setToolTip(self.t(
                    f"{key}_tooltip",
                    self.t(key, key.rsplit(".", 1)[-1].replace("_", " ").title()),
                ))
        self.queue_table.setRowCount(len(items))
        lang = self._lang()
        for r, it in enumerate(items):
            r1 = store.locked_review_for_item(self._cohort_id, it.item_id, review_round=1)
            r2 = store.locked_review_for_item(self._cohort_id, it.item_id, review_round=2)
            revealed = store._candidate_revealed(self._cohort_id, it.item_id)
            comparison = store.current_comparison_for_item(self._cohort_id, it.item_id)
            adjudication = bool(r1 and r2 and it.item_status == "adjudication_locked")
            if r1 and getattr(r1, "prior_review_id", ""):
                first_status = self.t("expert_corpus.status_corrected", "Corrected revision")
            elif r1:
                first_status = self.t("expert_corpus.status_locked_first", "Locked")
            else:
                first_status = self.t("expert_corpus.status_waiting", "Pending")
            if comparison:
                cmp_status = self.t("expert_corpus.status_cmp_done", "Completed")
            elif revealed:
                cmp_status = self.t(
                    "expert_corpus.status_cmp_revealed_unsaved",
                    "Candidate revealed — comparison not saved",
                )
            else:
                cmp_status = self.t("expert_corpus.status_cmp_not_started", "Not started")
            if r2 and r1 and r2.reviewer_id == r1.reviewer_id:
                second_status = self.t(
                    "expert_corpus.status_second_same",
                    "Same-reviewer repeat — not independent",
                )
            elif r2:
                second_status = self.t("expert_corpus.status_locked_first", "Locked")
            else:
                second_status = self.t("expert_corpus.status_second_none", "Not assigned")
            vals = [
                str(it.manifest_position),
                it.source_display_name or it.datetime_metadata,
                str(it.frame_index),
                it.frame_time,
                first_status,
                (
                    self.t("expert_corpus.status_revealed", "Revealed")
                    if revealed
                    else self.t("expert_corpus.status_not_revealed", "Not revealed")
                ),
                cmp_status,
                second_status,
                (
                    self.t("expert_corpus.status_locked_first", "Locked")
                    if adjudication
                    else self.t("expert_corpus.status_waiting", "Pending")
                ),
            ]
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(str(val))
                if c == 0:
                    cell.setData(Qt.UserRole, it.item_id)
                tip = (
                    f"{it.source_sha256}\nframe={it.frame_index}\n"
                    f"inv={it.source_inventory_id}\n{it.item_id}"
                )
                cell.setToolTip(tip)
                self.queue_table.setItem(r, c, cell)
        self._update_action_enablement()
        self._update_selected_badge()

    def _open_selected_item(self) -> None:
        rows = self.queue_table.selectionModel().selectedRows() if self.queue_table.selectionModel() else []
        if not rows:
            # try current cell
            r = self.queue_table.currentRow()
            if r < 0:
                return
            row = r
        else:
            row = rows[0].row()
        item = self.queue_table.item(row, 0)
        if not item:
            return
        self._load_item(str(item.data(Qt.UserRole)))
        self.tabs.setCurrentIndex(4)

    def _load_item(self, item_id: str) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        it = next(x for x in store.load_items(self._cohort_id) if x.item_id == item_id)
        self._current_item_id = item_id
        self._candidate_revealed_ui = False
        r1 = store.locked_review_for_item(self._cohort_id, item_id, review_round=1)
        self._blind_locked_for_item = r1 is not None and r1.locked
        lang = self._lang()
        try:
            st = status_label(it.item_status, lang)
            expl = status_explanation(it.item_status, lang)
        except ValueError:
            st, expl = it.item_status, ""
        self.item_identity.setText(
            f"{it.source_display_name} · frame {it.frame_index} · {it.frame_time}\n"
            f"{st}\n{expl}"
        )
        self.rapid_identity.setText(
            f"{it.source_display_name} · frame {it.frame_index} · {it.frame_time}"
        )
        ok = self.ionogram_view.load_item(
            self.session,
            source_sha256=it.source_sha256,
            frame_index=it.frame_index,
            display_name=it.source_display_name,
            frame_time=it.frame_time,
            lang=lang,
        )
        self.rapid_ionogram.load_item(
            self.session,
            source_sha256=it.source_sha256,
            frame_index=it.frame_index,
            display_name=it.source_display_name,
            frame_time=it.frame_time,
            lang=lang,
        )
        self.candidate_hidden_label.setVisible(not self._blind_locked_for_item)
        if not self._blind_locked_for_item:
            self.compare_view.setPlainText(self.t("expert_corpus.empty_compare"))
        if not ok and it.item_status == "item_unavailable":
            self.ionogram_view.status.setText(
                it.unavailable_reason or self.t("expert_corpus.empty_no_active")
            )
        # Only the current item's unsaved draft may be restored.  A blank
        # item must not display an answer from its parent/item neighbour.
        draft = self._unsaved_review_form
        if draft and draft.get("item_id") == item_id and draft.get("cohort_id") == self._cohort_id:
            self._restore_review_form(draft)
        elif r1:
            self._restore_review_form({
                "cohort_id": self._cohort_id, "item_id": item_id,
                "morphology": r1.morphology, "assessability": r1.assessability,
                "interference": (r1.interference or [""])[0],
                "ambiguity": r1.ambiguity, "confidence": r1.confidence,
                "rationale": r1.rationale,
            })
        else:
            self._clear_draft_form()
        comments = store.load_comments(self._cohort_id, item_id=item_id)
        if comments:
            latest = comments[-1]
            self.generated_comment.setPlainText(latest.final_text or latest.generated_text)
            self.final_comment.blockSignals(True)
            self.final_comment.setPlainText(latest.final_text or latest.generated_text)
            self.final_comment.blockSignals(False)
            self._final_comment_dirty = False
            self.own_description.setPlainText(latest.expert_own_description)
            self._syncing_draft = True
            for code, check in self.comment_checks.items():
                check.setChecked(code in latest.structured_codes)
            self._syncing_draft = False
            self._update_comment_group_titles()
        self._update_review_detail_state(r1, it, comments)
        self._update_comparison_panel_for_item()

    def _update_comparison_panel_for_item(self) -> None:
        """Render comparison controls without exposing a hidden candidate."""
        store = self._ensure_store()
        if not store or not self._cohort_id or not self._current_item_id:
            self.compare_state_label.setText("")
            self.compare_view.clear()
            self.btn_reveal.setEnabled(False)
            self.btn_save_compare.setEnabled(False)
            self.btn_revise_comparison.hide()
            return
        comparison = store.current_comparison_for_item(
            self._cohort_id, self._current_item_id
        )
        can_reveal = store.can_reveal_candidate(self._cohort_id, self._current_item_id)
        if comparison:
            self._candidate_revealed_ui = True
            self.compare_state_label.setText(
                comparison_status_display(comparison.agreement_status, self._lang())
            )
            self.compare_view.setPlainText(format_comparison_cards(
                human_morphology=comparison.human_morphology,
                candidate_state=comparison.candidate_state,
                ordinal_strength=comparison.candidate_strength,
                agreement_status=comparison.agreement_status,
                engine=(store.candidate_snapshot_for_item(
                    self._cohort_id, self._current_item_id
                ) or type("_", (), {"candidate_engine_version": ""})()).candidate_engine_version,
                lang=self._lang(),
            ))
            self.compare_comment.setPlainText(comparison.comparison_comment or "")
            self.btn_reveal.setEnabled(False)
            self.btn_save_compare.setEnabled(True)  # optional note
            self.btn_revise_comparison.show()
            return
        self.compare_state_label.setText(
            comparison_status_display("comparison_pending_reveal", self._lang())
        )
        self.compare_view.setPlainText(
            comparison_status_display("comparison_pending_reveal", self._lang())
        )
        self.btn_reveal.setEnabled(can_reveal)
        self.btn_save_compare.setEnabled(False)
        self.btn_revise_comparison.hide()

    def _set_review_tech_expanded(self, expanded: bool) -> None:
        self._tech_expanded = expanded
        self.review_tech_view.setVisible(expanded)

    def _update_review_detail_state(self, r1, item, comments=None) -> None:
        """Keep the review panel and shared rapid form consistent with lock state."""
        pending = bool(
            self._pending_review_revision
            and self._pending_review_revision.get("item_id") == getattr(item, "item_id", "")
            and self._pending_review_revision.get("cohort_id") == self._cohort_id
        )
        locked = bool(r1 and r1.locked)
        if not item:
            self.review_state_banner.setText(self.t("expert_corpus.review_no_item", "No item selected"))
            self.review_locked_badge.hide()
            self.btn_create_review_revision.hide()
            self.btn_save_blind.hide()
            return

        if not r1:
            self.review_detail_view.setPlainText("")
            self.review_state_banner.setText(
                self.t("expert_corpus.review_pending", "Review pending")
            )
            self.review_locked_badge.hide()
            self.btn_create_review_revision.hide()
            # New blind assessments are done in Rapid Review, not here.
            self.btn_save_blind.hide()
        else:
            lang = self._lang()
            details = [
                f"{self.t('expert_corpus.field_morphology', 'Morphology')}: "
                f"{display_label(r1.morphology, lang)}",
                f"{self.t('expert_corpus.field_assessability', 'Assessability')}: "
                f"{display_label(r1.assessability, lang)}",
                f"{self.t('expert_corpus.field_interference', 'Interference')}: "
                f"{', '.join(display_label(code, lang) for code in (r1.interference or []))}",
                f"{self.t('expert_corpus.field_ambiguity', 'Ambiguity')}: "
                f"{display_label(r1.ambiguity, lang)}",
                f"{self.t('expert_corpus.field_confidence', 'Confidence')}: "
                f"{display_label(r1.confidence, lang)}",
                f"{self.t('expert_corpus.field_rationale', 'Rationale')}: {r1.rationale}",
                f"{self.t('expert_corpus.review_field_reviewer', 'Reviewer')}: "
                f"{r1.reviewer_id}",
                f"{self.t('expert_corpus.review_field_saved_at', 'Saved at')}: "
                f"{getattr(r1, 'created_at', '') or '—'}",
                f"{self.t('expert_corpus.review_field_status', 'Status')}: "
                f"{self.t('expert_corpus.review_locked_badge', 'Blind review locked')}",
            ]
            if comments:
                comment = comments[-1]
                if comment.structured_codes:
                    details.append(
                        f"{self.t('expert_corpus.structured_observations', 'Structured observations')}: "
                        f"{', '.join(structured_code_label(code, lang) for code in comment.structured_codes)}"
                    )
                if comment.final_text or comment.generated_text:
                    details.append(
                        f"{self.t('expert_corpus.final_comment', 'Final expert comment')}: "
                        f"{comment.final_text or comment.generated_text}"
                    )
                if comment.expert_own_description:
                    details.append(
                        f"{self.t('expert_corpus.expert_own_description', 'Expert own description')}: "
                        f"{comment.expert_own_description}"
                    )
            self.review_detail_view.setPlainText("\n\n".join(details))
            revealed = False
            store = self._ensure_store()
            try:
                revealed = bool(store and store._candidate_revealed(self._cohort_id, item.item_id))
            except Exception:
                pass
            self.review_locked_badge.setText(
                self.t("expert_corpus.review_locked_badge", "Locked review")
            )
            self.review_locked_badge.show()
            can_reveal = bool(store and store.can_reveal_candidate(self._cohort_id, item.item_id))
            self.review_state_banner.setText(
                self.t(
                    "expert_corpus.review_ready_compare" if can_reveal
                    else "expert_corpus.review_locked_banner",
                    "Ready for comparison" if can_reveal else "This review is locked.",
                )
            )
            self.btn_create_review_revision.show()
            self.btn_save_blind.setVisible(pending)

        tech_lines = [
            f"item_id={item.item_id}",
            f"source_sha256={item.source_sha256}",
            f"stratum={item.sampling_stratum}",
            f"partition={item.partition}",
        ]
        if r1:
            tech_lines.extend([
                f"review_id={r1.review_id}",
                f"review_timestamp={getattr(r1, 'created_at', '')}",
            ])
        self.review_tech_view.setPlainText("\n".join(tech_lines))
        editable = not locked or pending
        for widget in (
            self.morph_combo, self.assess_combo, self.interference_combo,
            self.ambiguity_combo, self.confidence_combo, self.rationale_edit,
            *self.comment_checks.values(), self.final_comment, self.own_description,
        ):
            widget.setEnabled(editable)
        self.btn_save_and_next_rapid.setEnabled(editable)
        if pending:
            self.validation_label.setText(
                self.t("expert_corpus.create_corrected_review", "Correction mode is active")
            )

    def _begin_corrected_review_revision(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id or not self._current_item_id:
            return
        review = store.locked_review_for_item(
            self._cohort_id, self._current_item_id, review_round=1
        )
        if not review or not review.locked:
            return
        QMessageBox.information(
            self, self.t("expert_corpus.dialog_title"),
            self.t("expert_corpus.correction_explain", "Create a corrected revision of this locked review."),
        )
        reason, ok = QInputDialog.getText(
            self, self.t("expert_corpus.dialog_title"),
            self.t("expert_corpus.correction_reason_prompt", "Reason for correction"),
        )
        if not ok:
            return
        if not reason.strip():
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"),
                self.t("expert_corpus.correction_reason_required", "A correction reason is required."),
            )
            return
        try:
            post_reveal = bool(store._candidate_revealed(self._cohort_id, self._current_item_id))
        except Exception:
            post_reveal = False
        if post_reveal:
            QMessageBox.information(
                self, self.t("expert_corpus.dialog_title"),
                self.t("expert_corpus.post_reveal_revision_note", "This correction is recorded after reveal."),
            )
        self._pending_review_revision = {
            "prior_review_id": review.review_id,
            "reason": reason.strip(),
            "post_reveal": post_reveal,
            "item_id": self._current_item_id,
            "cohort_id": self._cohort_id,
        }
        self._restore_review_form({
            "cohort_id": self._cohort_id, "item_id": self._current_item_id,
            "morphology": review.morphology, "assessability": review.assessability,
            "interference": (review.interference or [""])[0],
            "ambiguity": review.ambiguity, "confidence": review.confidence,
            "rationale": review.rationale,
        })
        item = next(
            (x for x in store.load_items(self._cohort_id)
             if x.item_id == self._current_item_id),
            None,
        )
        if item:
            self._update_review_detail_state(review, item)
        self.tabs.setCurrentIndex(2)

    def _nav_item(self, delta: int) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        items = store.load_items(self._cohort_id)
        if not items:
            return
        ids = [it.item_id for it in items]
        idx = ids.index(self._current_item_id) if self._current_item_id in ids else 0
        idx = max(0, min(len(ids) - 1, idx + delta))
        self._load_item(ids[idx])

    def _capture_review_form(self) -> dict[str, Any]:
        return {
            "morphology": self.morph_combo.currentData(),
            "assessability": self.assess_combo.currentData(),
            "interference": self.interference_combo.currentData(),
            "ambiguity": self.ambiguity_combo.currentData(),
            "confidence": self.confidence_combo.currentData(),
            "rationale": self.rationale_edit.toPlainText(),
            "item_id": self._current_item_id,
            "cohort_id": self._cohort_id,
        }

    def _restore_review_form(self, form: dict[str, Any] | None) -> None:
        if not form:
            return
        if form.get("cohort_id") != self._cohort_id or form.get("item_id") != self._current_item_id:
            return
        for combo, key in (
            (self.morph_combo, "morphology"),
            (self.assess_combo, "assessability"),
            (self.interference_combo, "interference"),
            (self.ambiguity_combo, "ambiguity"),
            (self.confidence_combo, "confidence"),
        ):
            code = form.get(key)
            if code is None:
                continue
            idx = combo.findData(code)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        if form.get("rationale") is not None:
            self.rationale_edit.setPlainText(str(form["rationale"]))

    def _save_blind(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id or not self._current_item_id:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.empty_no_item")
            )
            return
        it = next(
            x for x in store.load_items(self._cohort_id) if x.item_id == self._current_item_id
        )
        pending = self._pending_review_revision
        revision_for_item = bool(
            pending
            and pending.get("item_id") == self._current_item_id
            and pending.get("cohort_id") == self._cohort_id
        )
        existing = store.locked_review_for_item(
            self._cohort_id, self._current_item_id, review_round=1
        )
        if existing and existing.locked and not revision_for_item:
            box = QMessageBox(self)
            box.setWindowTitle(self.t("expert_corpus.dialog_title"))
            box.setText(
                self.t(
                    "expert_corpus.locked_requires_revision",
                    "This review is locked. Create a corrected revision to make changes.",
                )
            )
            create = box.addButton(
                self.t("expert_corpus.create_corrected_review", "Create corrected review"),
                QMessageBox.AcceptRole,
            )
            box.addButton(self.t("expert_corpus.cancel_btn"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() == create:
                self._begin_corrected_review_revision()
            return
        if not self.ionogram_view.identity_matches(it.source_sha256, it.frame_index):
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.identity_mismatch")
            )
            return
        payload = {
            "morphology": self.morph_combo.currentData(),
            "assessability": self.assess_combo.currentData(),
            "interference": [self.interference_combo.currentData()],
            "ambiguity": self.ambiguity_combo.currentData(),
            "confidence": self.confidence_combo.currentData(),
            "rationale": self.rationale_edit.toPlainText().strip(),
        }
        if not required_fields_complete(payload):
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self.t("expert_corpus.field_rationale")
            )
            return
        # Preserve form if freeze gating interrupts
        self._unsaved_review_form = self._capture_review_form()
        try:
            m = store.load_manifest(self._cohort_id)
        except Exception:
            m = None
        if m is not None and not m.frozen:
            box = QMessageBox(self)
            box.setWindowTitle(self.t("expert_corpus.dialog_title"))
            box.setText(self.t("expert_corpus.must_freeze_review"))
            go = box.addButton(
                self.t("expert_corpus.go_to_cohort"), QMessageBox.AcceptRole
            )
            box.addButton(self.t("expert_corpus.cancel_btn"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() == go:
                self.tabs.setCurrentIndex(1)
                self.btn_freeze.setStyleSheet("font-weight: 700; border: 2px solid #c45;")
            return
        if not self._ask(
            self.t("expert_corpus.lock_confirm"),
            ok_key="expert_corpus.yes_btn",
            cancel_key="expert_corpus.no_btn",
        ):
            return
        try:
            rec = BlindReviewRecord.create(
                reviewer_id=self.reviewer_id_edit.text().strip() or "rev_owner",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=self._cohort_id,
                item_id=self._current_item_id,
                morphology=str(payload["morphology"]),
                assessability=str(payload["assessability"]),
                interference=list(payload["interference"]),
                ambiguity=str(payload["ambiguity"]),
                confidence=str(payload["confidence"]),
                rationale=str(payload["rationale"]),
                ui_language=self._lang(),
                prior_review_id=str(pending.get("prior_review_id", "")) if revision_for_item else "",
                revision_reason=str(pending.get("reason", "")) if revision_for_item else "",
                post_reveal_revision=bool(pending.get("post_reveal")) if revision_for_item else False,
                candidate_revealed_before_this_record=bool(pending.get("post_reveal"))
                if revision_for_item else False,
            )
            store.save_blind_review(self._cohort_id, rec)
            codes = [code for code, check in self.comment_checks.items() if check.isChecked()]
            if codes or self.final_comment.toPlainText().strip() or self.own_description.toPlainText().strip():
                store.save_comment(self._cohort_id, CommentRecord.create(
                    comment_type="decision_rationale",
                    cohort_id=self._cohort_id,
                    item_id=self._current_item_id,
                    reviewer_id=rec.reviewer_id,
                    review_id=rec.review_id,
                    structured_codes=codes,
                    generated_text=generate_comment_text(codes, self._lang()) if codes else "",
                    final_text=(
                        self.final_comment.toPlainText().strip()
                        or self.generated_comment.toPlainText().strip()
                    ),
                    expert_own_description=self.own_description.toPlainText().strip(),
                    ui_language=self._lang(),
                ))
            self._unsaved_review_form = None
            was_revision = revision_for_item
            if was_revision:
                self._pending_review_revision = None
            self._blind_locked_for_item = True
            self.candidate_hidden_label.setVisible(False)
            self.btn_freeze.setStyleSheet("")
            self._sync_guided_and_refresh()
            next_id = next_unfinished_blind_item(store, self._cohort_id)
            if next_id:
                self._load_item(next_id)
            QMessageBox.information(
                self, self.t("expert_corpus.dialog_title"),
                self.t("expert_corpus.correction_saved", "Correction saved")
                if was_revision else self.t("expert_corpus.locked_ok"),
            )
        except FrozenCohortError as exc:
            if getattr(exc, "code", "") == "cohort_must_be_frozen":
                box = QMessageBox(self)
                box.setWindowTitle(self.t("expert_corpus.dialog_title"))
                box.setText(self.t("expert_corpus.must_freeze_review"))
                go = box.addButton(
                    self.t("expert_corpus.go_to_cohort"), QMessageBox.AcceptRole
                )
                box.addButton(self.t("expert_corpus.cancel_btn"), QMessageBox.RejectRole)
                box.exec()
                if box.clickedButton() == go:
                    self.tabs.setCurrentIndex(1)
                    self.btn_freeze.setStyleSheet("font-weight: 700; border: 2px solid #c45;")
                return
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), self._lifecycle_message(exc)
            )
        except BlindRevealError as exc:
            message = self._lifecycle_message(exc)
            if "revision_reason" in str(exc).lower() or "revision" in str(exc).lower():
                message = self.t(
                    "expert_corpus.locked_requires_revision",
                    "This review is locked. Create a corrected revision to make changes.",
                )
            QMessageBox.warning(self, self.t("expert_corpus.dialog_title"), message)
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("Could not save blind review")
            message = str(exc)
            if "revision_reason" in message.lower():
                message = self.t(
                    "expert_corpus.locked_requires_revision",
                    "This review is locked. Create a corrected revision to make changes.",
                )
            else:
                message = self.t("expert_corpus.save_failed", "Unable to save review.")
            QMessageBox.critical(self, self.t("expert_corpus.dialog_title"), message)

    def _run_batch_reveal_compare(self) -> None:
        """One-shot reveal + automatic comparison for all eligible items."""
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        ready = can_batch_reveal_and_compare(store, self._cohort_id)
        if not ready.get("allowed"):
            QMessageBox.warning(
                self,
                self.t("expert_corpus.dialog_title"),
                self.t(
                    "expert_corpus.batch_blocked_blind",
                    "Batch reveal is available only after all required blind reviews are locked.",
                ),
            )
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(self.t("expert_corpus.dialog_title"))
        box.setText(
            self.t(
                "expert_corpus.batch_confirm",
                "The first blind-review round is complete. Candidate results will be shown "
                "for all available frames, and comparison statuses will be calculated "
                "automatically. Locked blind reviews will not change.",
            )
        )
        yes = box.addButton(
            self.t("expert_corpus.batch_confirm_yes", "Reveal and calculate"),
            QMessageBox.YesRole,
        )
        box.addButton(
            self.t("expert_corpus.batch_confirm_cancel", "Cancel"),
            QMessageBox.RejectRole,
        )
        box.exec()
        if box.clickedButton() is not yes:
            return
        try:
            result = batch_reveal_and_compare(store, self._cohort_id)
        except BatchCompareError as exc:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"), str(exc)
            )
            return
        except Exception:  # noqa: BLE001
            _LOG.exception("batch reveal/compare failed")
            QMessageBox.critical(
                self,
                self.t("expert_corpus.dialog_title"),
                self.t("expert_corpus.save_failed", "Unable to calculate comparisons."),
            )
            return
        msg = result.get("message_ru" if self._lang() == "ru" else "message_en", "")
        self._sync_guided_and_refresh()
        self.tabs.setCurrentIndex(6)
        self._refresh_summary()
        QMessageBox.information(self, self.t("expert_corpus.dialog_title"), msg)

    def _open_per_item_comparison(self) -> None:
        """More → Per-item Comparison — inspect one frame without batch."""
        store = self._ensure_store()
        self.tabs.setCurrentIndex(5)
        if not store or not self._cohort_id:
            return
        item_id = self._current_item_id or next_uncompared_item(store, self._cohort_id)
        if item_id:
            self._load_item(item_id)
        if not store.current_comparison_for_item(self._cohort_id, self._current_item_id or ""):
            self.compare_view.setPlainText(
                self.t(
                    "expert_corpus.compare_awaiting_reveal",
                    "Candidate is hidden. Reveal it when ready to compare.",
                )
            )

    def _reveal_candidate(self) -> None:
        """Per-item reveal: immediately derive the comparison (no separate Save)."""
        store = self._ensure_store()
        if not store or not self._cohort_id or not self._current_item_id:
            return
        if not store.can_reveal_candidate(self._cohort_id, self._current_item_id):
            self.compare_view.setPlainText(
                comparison_status_display("comparison_pending_reveal", self._lang())
            )
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"),
                self.t("expert_corpus.empty_compare", "Candidate cannot yet be revealed."),
            )
            return
        rev = store.locked_review_for_item(self._cohort_id, self._current_item_id, review_round=1)
        if not rev:
            return
        stay_item = self._current_item_id
        try:
            cmp = store.reveal_and_compare(
                self._cohort_id,
                self._current_item_id,
                review_id=rev.review_id,
                reviewer_note_codes=[],
                comparison_comment="",
            )
        except BlindRevealError as exc:
            existing = store.current_comparison_for_item(
                self._cohort_id, self._current_item_id
            )
            if existing is None:
                QMessageBox.warning(
                    self, self.t("expert_corpus.dialog_title"), str(exc)
                )
                return
            cmp = existing
        self._candidate_revealed_ui = True
        self.btn_reveal.setEnabled(False)
        # Optional note may be saved separately; do not auto-advance.
        if self._current_item_id != stay_item:
            self._load_item(stay_item)
        self._update_comparison_panel_for_item()
        self.compare_state_label.setText(
            self.t("expert_corpus.comparison_calculated", "Comparison calculated")
            + " — "
            + comparison_status_display(cmp.agreement_status, self._lang())
        )
        self.btn_save_compare.setEnabled(True)
        self.btn_revise_comparison.show()
        self._sync_guided_and_refresh()
        self.tabs.setCurrentIndex(5)

    def _save_post_comparison_note(self) -> None:
        """Optional note only — does not alter comparison class or progress count."""
        store = self._ensure_store()
        if self._comparison_save_guard or not store or not self._cohort_id or not self._current_item_id:
            return
        note = self.compare_comment.toPlainText().strip()
        if not note:
            QMessageBox.information(
                self,
                self.t("expert_corpus.dialog_title"),
                self.t(
                    "expert_corpus.post_note_empty",
                    "Post-comparison note is optional. Enter text to save a note.",
                ),
            )
            return
        self._comparison_save_guard = True
        self.btn_save_compare.setEnabled(False)
        try:
            store.save_post_comparison_note(
                self._cohort_id, self._current_item_id, note=note
            )
            self.compare_state_label.setText(
                self.t("expert_corpus.post_note_saved", "Post-comparison note saved")
            )
            self._update_comparison_panel_for_item()
            self._sync_guided_and_refresh()
        except BlindRevealError as exc:
            QMessageBox.warning(self, self.t("expert_corpus.dialog_title"), str(exc))
        except Exception:  # noqa: BLE001
            _LOG.exception("Could not save post-comparison note")
            QMessageBox.critical(
                self, self.t("expert_corpus.dialog_title"),
                self.t("expert_corpus.save_failed", "Unable to save note."),
            )
        finally:
            self._comparison_save_guard = False

    def _save_comparison(self) -> None:
        """Backward-compatible alias: optional post-comparison note. """
        self._save_post_comparison_note()

    def _begin_comparison_revision(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id or not self._current_item_id:
            return
        comparison = store.current_comparison_for_item(self._cohort_id, self._current_item_id)
        review = store.locked_review_for_item(
            self._cohort_id, self._current_item_id, review_round=1
        )
        if not comparison or not review:
            return
        reason, ok = QInputDialog.getText(
            self, self.t("expert_corpus.dialog_title"),
            self.t("expert_corpus.comparison_revision_reason", "Reason for comparison revision"),
        )
        if not ok or not reason.strip():
            return
        try:
            store.reveal_and_compare(
                self._cohort_id, self._current_item_id, review_id=review.review_id,
                reviewer_note_codes=list(comparison.reviewer_note_codes or []),
                comparison_comment=self.compare_comment.toPlainText().strip(),
                allow_revision=True, revision_reason=reason.strip(),
            )
            self._update_comparison_panel_for_item()
            self._sync_guided_and_refresh()
        except BlindRevealError:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"),
                self.t("expert_corpus.comparison_revision_failed", "Comparison revision could not be saved."),
            )

    def _repair_comparison_derived_state(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        if not self._ask(
            self.t(
                "expert_corpus.repair_confirm",
                "Validate and repair derived comparison state? History will be retained.",
            ),
            ok_key="expert_corpus.yes_btn", cancel_key="expert_corpus.no_btn",
        ):
            return
        report = repair_comparison_derived_state(store, self._cohort_id, dry_run=False)
        after = report.get("after") or count_consistency(store, self._cohort_id)
        QMessageBox.information(
            self, self.t("expert_corpus.dialog_title"),
            self.t(
                "expert_corpus.repair_report",
                "Derived state repaired. Current comparisons: {current}; history rows: {history}; consistent: {ok}.",
            ).format(
                current=after.get("comparisons_current", report.get("current_count", 0)),
                history=after.get("comparisons_history", report.get("history_rows", 0)),
                ok=self.t("expert_corpus.yes_btn") if after.get("ok") else self.t("expert_corpus.no_btn"),
            ),
        )
        self._sync_guided_and_refresh()

    def _save_second_review(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id or not self._current_item_id:
            return
        first = store.locked_review_for_item(
            self._cohort_id, self._current_item_id, review_round=1
        )
        reviewer_id = self.reviewer_id_edit.text().strip() or "rev_second"
        if first and reviewer_id == first.reviewer_id:
            QMessageBox.warning(
                self, self.t("expert_corpus.dialog_title"),
                self.t(
                    "expert_corpus.second_reviewer_must_differ",
                    "The optional second review must be performed by a different reviewer.",
                ),
            )
            return
        try:
            rec = BlindReviewRecord.create(
                reviewer_id=reviewer_id,
                reviewer_role="second_reviewer",
                review_round=2,
                cohort_id=self._cohort_id,
                item_id=self._current_item_id,
                morphology=str(self.morph_combo.currentData()),
                assessability=str(self.assess_combo.currentData()),
                interference=[str(self.interference_combo.currentData())],
                ambiguity=str(self.ambiguity_combo.currentData()),
                confidence=str(self.confidence_combo.currentData()),
                rationale=self.rationale_edit.toPlainText().strip() or "second review",
                ui_language=self._lang(),
            )
            store.save_blind_review(self._cohort_id, rec)
            self._reload_queue()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "IML", str(exc))

    def _save_adjudication(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id or not self._current_item_id:
            return
        r1 = store.locked_review_for_item(self._cohort_id, self._current_item_id, review_round=1)
        r2 = store.locked_review_for_item(self._cohort_id, self._current_item_id, review_round=2)
        if not r1 or not r2:
            QMessageBox.warning(self, "IML", "Need two locked reviews")
            return
        from uuid import uuid4

        try:
            adj = AdjudicationRecord(
                adjudication_id=str(uuid4()),
                adjudicator_id="rev_adj",
                cohort_id=self._cohort_id,
                item_id=self._current_item_id,
                input_review_ids=[r1.review_id, r2.review_id],
                adjudicated_morphology=str(self.morph_combo.currentData()),
                assessability=str(self.assess_combo.currentData()),
                interference=[str(self.interference_combo.currentData())],
                ambiguity=str(self.ambiguity_combo.currentData()),
                rationale=self.rationale_edit.toPlainText().strip()
                or "Adjudicated expert reference (not ground truth)",
            ).with_hash()
            store.save_adjudication(self._cohort_id, adj)
            self._reload_queue()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "IML", str(exc))

    def _refresh_summary(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            self.summary_view.setPlainText(self.t("expert_corpus.empty_no_cohort"))
            return
        items = store.load_items(self._cohort_id)
        if not items:
            self.summary_view.setPlainText(self.t("expert_corpus.empty_summary_no_items"))
            return
        summary = descriptive_summary(store, self._cohort_id)
        if not summary.get("completed_blind_reviews_round1"):
            self.summary_view.setPlainText(self.t("expert_corpus.empty_summary_no_reviews"))
            return
        self.summary_view.setPlainText(
            format_summary_dashboard(store, self._cohort_id, self._lang())
        )

    def _show_technical_json(self) -> None:
        store = self._ensure_store()
        if not store or not self._cohort_id:
            return
        import json
        self.summary_view.setPlainText(
            json.dumps(descriptive_summary(store, self._cohort_id), indent=2, ensure_ascii=False)
        )

    def eventFilter(self, watched, event):  # noqa: N802
        if event.type() == QEvent.KeyPress:
            key, mods = event.key(), event.modifiers()
            if mods == Qt.ControlModifier and key == Qt.Key_Return:
                self._save_blind()
                return True
            if mods == Qt.ControlModifier and key == Qt.Key_S:
                self._save_blind()
                return True
            if mods == (Qt.ControlModifier | Qt.ShiftModifier) and key == Qt.Key_Return:
                store = self._ensure_store()
                if store and self._cohort_id:
                    item_id = next_unfinished_blind_item(store, self._cohort_id)
                    if item_id:
                        self._load_item(item_id)
                return True
            if mods == Qt.AltModifier and Qt.Key_1 <= key <= Qt.Key_6:
                index = key - Qt.Key_1 + 1
                if index < self.morph_combo.count():
                    self.morph_combo.setCurrentIndex(index)
                return True
            if watched is self.rapid_table and key in (Qt.Key_Up, Qt.Key_Down):
                return False
        return super().eventFilter(watched, event)
