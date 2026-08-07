"""ML Data Readiness workspace (Phase ML-A.1a) — audit/governance only."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.ml_dataset_readiness.acquisition_date import (
    MISSING_DATE_LABEL,
    diagnose_invalid_date_projection,
    is_valid_acquisition_date,
)
from ionogram_morphology_lab.ml_dataset_readiness.constants import (
    GATE_OUTCOMES,
    NO_CLAIM_STATEMENT_EN,
    NO_CLAIM_STATEMENT_RU,
    TASK_CONTRACTS,
)
from ionogram_morphology_lab.ml_dataset_readiness.contracts import (
    CONTRACT_LABELS,
    contract_descriptor,
)
from ionogram_morphology_lab.ml_dataset_readiness.coverage import build_coverage_summary
from ionogram_morphology_lab.ml_dataset_readiness.display_labels import (
    REVIEW_NOTE,
    SEQUENCE_CORRELATION_NOTE,
    SYNTHETIC_GROUP_NOTE,
    class_label,
    contract_label,
    denom_label,
    gate_outcome_label,
    lifecycle_label,
    missingness_label,
    review_field_label,
)
from ionogram_morphology_lab.ml_dataset_readiness.missingness import build_missingness_report
from ionogram_morphology_lab.ml_dataset_readiness.readiness_gate import (
    GATE_LABELS,
    outcome_labels,
    suggest_gate_blockers,
)
from ionogram_morphology_lab.ml_dataset_readiness.store import (
    MLDatasetReadinessStore,
    ReadinessStoreError,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore

_LOG = logging.getLogger(__name__)

# Overview denominator keys grouped for human-readable display
_OVERVIEW_SECTIONS: list[tuple[str, tuple[str, ...]]] = [
    (
        "inventory",
        (
            "selected_records",
            "unique_current_items",
            "raw_frame_count",
            "unique_sources",
            "unique_source_dates",
            "unique_frame_times",
            "unique_campaigns",
        ),
    ),
    (
        "independence",
        (
            "unique_related_frame_groups",
            "unique_sequences",
            "synthetic_related_frame_groups",
        ),
    ),
    (
        "review",
        (
            "locked_first_reviews",
            "independent_second_reviews",
            "items_with_paired_independent_reviews",
            "arbitration_records",
            "corrected_first_reviews",
            "corrected_second_reviews",
        ),
    ),
    (
        "assessability",
        ("assessable", "partially_assessable", "not_assessable"),
    ),
    (
        "missingness",
        (
            "indeterminate_labels",
            "abstentions",
            "missing_required_fields",
            "unavailable_sources",
        ),
    ),
    (
        "contamination",
        ("development_exposed_items", "untouched_eligible_items"),
    ),
]

_SECTION_TITLES = {
    "inventory": {"en": "Inventory", "ru": "Инвентарь"},
    "independence": {
        "en": "Independence / grouping",
        "ru": "Независимость / группировка",
    },
    "review": {"en": "Review availability", "ru": "Доступность разметки"},
    "assessability": {"en": "Assessability", "ru": "Оценимость"},
    "missingness": {"en": "Missingness", "ru": "Пропуски"},
    "contamination": {"en": "Contamination", "ru": "Контаминация"},
    "holdout": {"en": "Holdout eligibility", "ru": "Допустимость holdout"},
}


class FreezeReadinessWorker(QThread):
    """Background freeze / corrected-revision worker with explicit progress lifecycle."""

    progress = Signal(int, str)
    finished_ok = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    MODE_FREEZE = "freeze"
    MODE_REVISION = "revision"

    def __init__(
        self,
        readiness_store: MLDatasetReadinessStore,
        corpus_store: MorphologyReviewCorpusStore,
        *,
        mode: str = MODE_FREEZE,
        audit_id: str = "",
        parent_audit_id: str = "",
        revision_reason: str = "",
        analyst_id: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._readiness_store = readiness_store
        self._corpus_store = corpus_store
        self._mode = mode
        self._audit_id = audit_id
        self._parent_audit_id = parent_audit_id
        self._revision_reason = revision_reason
        self._analyst_id = analyst_id
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            if self._mode == self.MODE_REVISION:
                manifest = self._readiness_store.create_revision(
                    self._parent_audit_id,
                    self._corpus_store,
                    revision_reason=self._revision_reason,
                    analyst_id=self._analyst_id,
                    progress_cb=lambda pct, msg: self.progress.emit(int(pct), str(msg)),
                    cancel_cb=lambda: self._cancel,
                )
            else:
                manifest = self._readiness_store.freeze_audit(
                    self._audit_id,
                    self._corpus_store,
                    progress_cb=lambda pct, msg: self.progress.emit(int(pct), str(msg)),
                    cancel_cb=lambda: self._cancel,
                )
            if self._cancel:
                self.cancelled.emit("cancelled")
                return
            # Belt-and-suspenders: success must report 100% before finished_ok.
            self.progress.emit(100, "complete")
            self.finished_ok.emit(manifest)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if self._cancel or "cancelled" in msg.lower():
                self.cancelled.emit(msg or "cancelled")
            else:
                self.failed.emit(msg)


class MLDataReadinessPage(QWidget):
    def __init__(self, session, i18n, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self._store: MLDatasetReadinessStore | None = None
        self._corpus: MorphologyReviewCorpusStore | None = None
        self._audit_id = ""
        self._frozen_task_contract = ""
        self._rows: list[Any] = []
        self._last_coverage: dict[str, Any] = {}
        self._last_missingness: dict[str, Any] = {}
        self._last_holdout: dict[str, Any] | None = None
        self._last_gate: dict[str, Any] | None = None
        self._worker: FreezeReadinessWorker | None = None
        self._preview: dict[str, Any] = {}
        self._form_labels: dict[str, QLabel] = {}
        self._op_terminal: str = ""  # "", "success", "cancelled", "failed"
        self._last_progress_pct: int = 0

        root = QVBoxLayout(self)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setObjectName("readiness_banner")
        root.addWidget(self.banner)

        self.lbl_current_contract = QLabel()
        self.lbl_current_contract.setWordWrap(True)
        self.lbl_current_contract.setObjectName("readiness_current_contract")
        root.addWidget(self.lbl_current_contract)

        self.lbl_legacy_date_warn = QLabel()
        self.lbl_legacy_date_warn.setWordWrap(True)
        self.lbl_legacy_date_warn.setObjectName("readiness_legacy_date_warn")
        self.lbl_legacy_date_warn.setVisible(False)
        root.addWidget(self.lbl_legacy_date_warn)
        self.btn_corrected_revision = QPushButton()
        self.btn_corrected_revision.setObjectName("readiness_corrected_revision")
        self.btn_corrected_revision.setVisible(False)
        self.btn_corrected_revision.clicked.connect(self._on_corrected_revision)
        root.addWidget(self.btn_corrected_revision)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self._build_select_tab()
        self._build_overview_tab()
        self._build_class_tab()
        self._build_sources_tab()
        self._build_review_tab()
        self._build_missing_tab()
        self._build_contam_tab()
        self._build_holdout_tab()
        self._build_gate_tab()

        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.btn_cancel = QPushButton()
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.status = QLabel()
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.btn_cancel)
        bottom.addWidget(self.status, 2)
        root.addLayout(bottom)

        self.retranslate()
        self._connect_project_signals()
        self.on_project_changed()

    def _connect_project_signals(self) -> None:
        for target in (
            getattr(self.session, "project_changed", None),
            getattr(getattr(self.session, "events", None), "project_changed", None),
        ):
            if target is None:
                continue
            try:
                target.connect(self.on_project_changed)
            except Exception:  # noqa: BLE001
                pass

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # Load saved audits independently of corpus selection
        self.on_project_changed()

    def _lang(self) -> str:
        lang = str(
            getattr(self.i18n, "language", None)
            or getattr(self.i18n, "lang", None)
            or "en"
        )
        return "ru" if lang.lower().startswith("ru") else "en"

    def t(self, key: str, **kwargs) -> str:
        try:
            return self.i18n.t(key, **kwargs)
        except Exception:
            return key

    def retranslate(self) -> None:
        ru = self._lang() == "ru"
        lang = self._lang()
        self.banner.setText(NO_CLAIM_STATEMENT_RU if ru else NO_CLAIM_STATEMENT_EN)
        tab_keys = [
            "readiness.tab_select",
            "readiness.tab_overview",
            "readiness.tab_class",
            "readiness.tab_sources",
            "readiness.tab_review",
            "readiness.tab_missing",
            "readiness.tab_contam",
            "readiness.tab_holdout",
            "readiness.tab_gate",
        ]
        for i, key in enumerate(tab_keys):
            self.tabs.setTabText(i, self.t(key))

        self._form_labels["title"].setText(self.t("readiness.title"))
        self._form_labels["description"].setText(self.t("readiness.description"))
        self._form_labels["analyst"].setText(self.t("readiness.analyst"))
        self._form_labels["contract"].setText(self.t("readiness.task_contract"))
        self.lbl_contract_explain.setText(self.t("readiness.task_contract_explain"))
        self.box_cohorts.setTitle(self.t("readiness.select_cohorts"))
        self.box_saved.setTitle(self.t("readiness.saved_audits"))
        self._update_current_contract_label()
        self.btn_corrected_revision.setText(self.t("readiness.create_corrected_revision"))

        self.btn_preview.setText(self.t("readiness.preview"))
        self.btn_freeze.setText(self.t("readiness.freeze"))
        self.btn_refresh.setText(self.t("readiness.refresh"))
        self.btn_export.setText(self.t("readiness.export"))
        self.btn_holdout.setText(self.t("readiness.run_holdout"))
        self.btn_gate.setText(self.t("readiness.record_gate"))
        self.btn_cancel.setText(self.t("readiness.cancel"))

        self.tbl_class.setHorizontalHeaderLabels(
            [self.t("readiness.col_class"), self.t("readiness.col_count")]
        )
        self.tbl_sources.setHorizontalHeaderLabels(
            [
                self.t("readiness.col_source"),
                self.t("readiness.col_acquisition_date"),
                self.t("readiness.col_frame_time"),
                self.t("readiness.col_count"),
            ]
        )
        self.tbl_missing.setHorizontalHeaderLabels(
            [self.t("readiness.col_category"), self.t("readiness.col_count")]
        )
        self.tech_details.setTitle(self.t("readiness.technical_details"))
        self.lbl_gate_outcome.setText(self.t("readiness.gate_outcome"))
        self.lbl_gate_blockers.setText(self.t("readiness.gate_blockers"))
        self.lbl_gate_rationale.setText(self.t("readiness.gate_rationale"))

        self._reload_contract_combo()
        self._reload_gate_combo()
        self._retranslate_blocker_checks()
        self._refresh_saved()
        # Refresh populated views with current language
        if self._last_coverage:
            self._populate_from_coverage(
                self._last_coverage,
                self._last_missingness,
                task_contract=self._active_task_contract(),
            )
        if self._last_holdout is not None:
            self._render_holdout(self._last_holdout)
        if self._last_gate is not None:
            self._render_gate(self._last_gate)

    def on_project_changed(self, *_args) -> None:
        self._bind_stores()
        self._refresh_cohort_list()
        self._refresh_saved()

    def _project_root(self) -> Path | None:
        proj = getattr(self.session, "current_project", None) or getattr(
            self.session, "project", None
        )
        if proj is None:
            return None
        root = getattr(proj, "root", None) or getattr(proj, "path", None)
        return Path(root) if root else None

    def _bind_stores(self) -> None:
        root = self._project_root()
        if root is None:
            self._store = None
            self._corpus = None
            return
        self._store = MLDatasetReadinessStore(root)
        self._corpus = MorphologyReviewCorpusStore(root)

    def _build_select_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QFormLayout()
        self.ed_title = QLineEdit()
        self.ed_desc = QLineEdit()
        self.ed_analyst = QLineEdit()
        self.cmb_contract = QComboBox()
        self._form_labels["title"] = QLabel()
        self._form_labels["description"] = QLabel()
        self._form_labels["analyst"] = QLabel()
        self._form_labels["contract"] = QLabel()
        form.addRow(self._form_labels["title"], self.ed_title)
        form.addRow(self._form_labels["description"], self.ed_desc)
        form.addRow(self._form_labels["analyst"], self.ed_analyst)
        form.addRow(self._form_labels["contract"], self.cmb_contract)
        lay.addLayout(form)
        self.lbl_contract_explain = QLabel()
        self.lbl_contract_explain.setWordWrap(True)
        self.lbl_contract_explain.setObjectName("readiness_contract_explain")
        lay.addWidget(self.lbl_contract_explain)
        self.lbl_contract_note = QLabel()
        self.lbl_contract_note.setWordWrap(True)
        self.lbl_contract_note.setObjectName("readiness_contract_note")
        lay.addWidget(self.lbl_contract_note)
        self.cmb_contract.currentIndexChanged.connect(self._on_contract_changed)

        split = QHBoxLayout()
        self.list_cohorts = QListWidget()
        self.list_cohorts.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.list_saved = QListWidget()
        self.list_saved.setObjectName("readiness_saved_list")
        self.list_saved.itemSelectionChanged.connect(self._on_saved_selected)
        self.box_cohorts = QGroupBox()
        cl = QVBoxLayout(self.box_cohorts)
        cl.addWidget(self.list_cohorts)
        self.box_saved = QGroupBox()
        sl = QVBoxLayout(self.box_saved)
        sl.addWidget(self.list_saved)
        split.addWidget(self.box_cohorts)
        split.addWidget(self.box_saved)
        lay.addLayout(split, 1)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton()
        self.btn_preview = QPushButton()
        self.btn_freeze = QPushButton()
        self.btn_export = QPushButton()
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_freeze.clicked.connect(self._on_freeze)
        self.btn_export.clicked.connect(self._on_export)
        for b in (self.btn_refresh, self.btn_preview, self.btn_freeze, self.btn_export):
            btns.addWidget(b)
        lay.addLayout(btns)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setObjectName("readiness_preview")
        lay.addWidget(self.preview_text)
        self.tabs.addTab(w, "Select")

    def _build_overview_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.overview_text = QTextEdit()
        self.overview_text.setReadOnly(True)
        self.overview_text.setObjectName("readiness_overview")
        lay.addWidget(self.overview_text)
        self.warn_adjacent = QLabel()
        self.warn_adjacent.setWordWrap(True)
        self.warn_adjacent.setObjectName("readiness_correlation_warn")
        lay.addWidget(self.warn_adjacent)
        self.tech_details = QGroupBox()
        self.tech_details.setCheckable(True)
        self.tech_details.setChecked(False)
        tl = QVBoxLayout(self.tech_details)
        self.tech_text = QTextEdit()
        self.tech_text.setReadOnly(True)
        self.tech_text.setObjectName("readiness_technical_details")
        tl.addWidget(self.tech_text)
        lay.addWidget(self.tech_details)
        self.tabs.addTab(w, "Overview")

    def _build_class_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.lbl_class_contract = QLabel()
        self.lbl_class_contract.setWordWrap(True)
        self.lbl_class_contract.setObjectName("readiness_class_contract")
        lay.addWidget(self.lbl_class_contract)
        self.tbl_class = QTableWidget(0, 2)
        self.tbl_class.setObjectName("readiness_class_table")
        lay.addWidget(self.tbl_class)
        self.tabs.addTab(w, "Class")

    def _build_sources_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tbl_sources = QTableWidget(0, 4)
        self.tbl_sources.setObjectName("readiness_sources_table")
        lay.addWidget(self.tbl_sources)
        self.lbl_sources_note = QLabel()
        self.lbl_sources_note.setWordWrap(True)
        lay.addWidget(self.lbl_sources_note)
        self.tabs.addTab(w, "Sources")

    def _build_review_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.review_text = QTextEdit()
        self.review_text.setReadOnly(True)
        self.review_text.setObjectName("readiness_review")
        lay.addWidget(self.review_text)
        self.tabs.addTab(w, "Review")

    def _build_missing_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tbl_missing = QTableWidget(0, 2)
        self.tbl_missing.setObjectName("readiness_missing_table")
        lay.addWidget(self.tbl_missing)
        self.tabs.addTab(w, "Missing")

    def _build_contam_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.contam_text = QTextEdit()
        self.contam_text.setReadOnly(True)
        self.contam_text.setObjectName("readiness_contam")
        lay.addWidget(self.contam_text)
        self.tabs.addTab(w, "Contamination")

    def _build_holdout_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.btn_holdout = QPushButton()
        self.btn_holdout.clicked.connect(self._on_holdout)
        lay.addWidget(self.btn_holdout)
        self.holdout_text = QTextEdit()
        self.holdout_text.setReadOnly(True)
        self.holdout_text.setObjectName("readiness_holdout")
        lay.addWidget(self.holdout_text)
        self.tabs.addTab(w, "Holdout")

    def _build_gate_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.lbl_gate_outcome = QLabel()
        lay.addWidget(self.lbl_gate_outcome)
        self.cmb_outcome = QComboBox()
        lay.addWidget(self.cmb_outcome)
        self.lbl_gate_blockers = QLabel()
        lay.addWidget(self.lbl_gate_blockers)
        self.lbl_blocker_evidence = QLabel()
        self.lbl_blocker_evidence.setWordWrap(True)
        self.lbl_blocker_evidence.setObjectName("readiness_blocker_evidence")
        lay.addWidget(self.lbl_blocker_evidence)
        self.blockers_box = QVBoxLayout()
        self._blocker_checks: dict[str, QCheckBox] = {}
        for code in sorted(GATE_OUTCOMES):
            if code.startswith("F_"):
                continue
            cb = QCheckBox()
            cb.setProperty("gate_code", code)
            self._blocker_checks[code] = cb
            self.blockers_box.addWidget(cb)
        lay.addLayout(self.blockers_box)
        self.lbl_gate_rationale = QLabel()
        lay.addWidget(self.lbl_gate_rationale)
        self.ed_rationale = QTextEdit()
        lay.addWidget(self.ed_rationale)
        self.btn_gate = QPushButton()
        self.btn_gate.clicked.connect(self._on_gate)
        lay.addWidget(self.btn_gate)
        self.gate_text = QTextEdit()
        self.gate_text.setReadOnly(True)
        self.gate_text.setObjectName("readiness_gate")
        lay.addWidget(self.gate_text)
        self.tabs.addTab(w, "Gate")

    def _retranslate_blocker_checks(self) -> None:
        lang = self._lang()
        for code, cb in self._blocker_checks.items():
            cb.setText(GATE_LABELS.get(code, {}).get(lang) or GATE_LABELS.get(code, {}).get("en") or code)

    def _reload_contract_combo(self) -> None:
        lang = self._lang()
        cur = self.cmb_contract.currentData()
        # Prefer frozen audit contract when viewing a saved audit
        prefer = self._frozen_task_contract or cur
        self.cmb_contract.blockSignals(True)
        self.cmb_contract.clear()
        for cid in sorted(TASK_CONTRACTS):
            self.cmb_contract.addItem(CONTRACT_LABELS[cid].get(lang) or cid, cid)
        if prefer:
            idx = self.cmb_contract.findData(prefer)
            if idx >= 0:
                self.cmb_contract.setCurrentIndex(idx)
        self.cmb_contract.blockSignals(False)
        self._on_contract_changed()

    def _reload_gate_combo(self) -> None:
        lang = self._lang()
        cur = self.cmb_outcome.currentData()
        self.cmb_outcome.clear()
        for code, label in outcome_labels(lang):
            self.cmb_outcome.addItem(label, code)
        if cur:
            idx = self.cmb_outcome.findData(cur)
            if idx >= 0:
                self.cmb_outcome.setCurrentIndex(idx)

    def _on_contract_changed(self) -> None:
        # Display note for the combo selection; frozen audit coverage is never
        # reinterpreted here (coverage always uses _frozen_task_contract / _active).
        cid = self._frozen_task_contract or self.cmb_contract.currentData()
        if not cid:
            return
        desc = contract_descriptor(str(cid))
        note = desc.get("parameter_scaling_status_en") or ""
        if self._lang() == "ru":
            note = desc.get("parameter_scaling_status_ru") or note
        self.lbl_contract_note.setText(note)

    def _active_task_contract(self) -> str:
        if self._frozen_task_contract:
            return self._frozen_task_contract
        data = self.cmb_contract.currentData()
        return str(data or "spread_f_morphology_classification")

    def _update_current_contract_label(self) -> None:
        lang = self._lang()
        cid = self._active_task_contract()
        self.lbl_current_contract.setText(
            f"{self.t('readiness.current_audit_contract')}: {contract_label(cid, lang)}"
        )

    def _set_legacy_date_warning(self, diag: dict[str, Any] | None) -> None:
        lang = self._lang()
        legacy = bool(diag and diag.get("legacy_invalid_date_projection"))
        self.lbl_legacy_date_warn.setVisible(legacy)
        self.btn_corrected_revision.setVisible(legacy and bool(self._audit_id))
        if not legacy:
            self.lbl_legacy_date_warn.setText("")
            return
        self.lbl_legacy_date_warn.setText(
            (diag or {}).get("warning_ru" if lang == "ru" else "warning_en") or ""
        )

    def _refresh_blocker_evidence(self) -> None:
        """Show auto-suggestion evidence; do not auto-check boxes (owner choice)."""
        if not self._last_coverage:
            self.lbl_blocker_evidence.setText("")
            return
        suggestions = suggest_gate_blockers(
            coverage=self._last_coverage,
            missingness=self._last_missingness or {},
            task_contract=self._active_task_contract(),
        )
        if not suggestions:
            self.lbl_blocker_evidence.setText(self.t("readiness.blocker_no_auto"))
            return
        lines = [self.t("readiness.blocker_suggestions")]
        for s in suggestions:
            code = s["code"]
            label = GATE_LABELS.get(code, {}).get(self._lang()) or code
            lines.append(f"• {label} — {s['evidence']}")
        lines.append(self.t("readiness.blocker_manual_ok"))
        self.lbl_blocker_evidence.setText("\n".join(lines))

    def _on_corrected_revision(self) -> None:
        self._bind_stores()
        if self._store is None or self._corpus is None or not self._audit_id:
            QMessageBox.warning(self, "ML", self.t("readiness.select_saved_audit"))
            return
        if self._worker is not None and self._worker.isRunning():
            return
        parent_id = self._audit_id
        try:
            parent = self._store.load_manifest(parent_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self, self.t("readiness.create_corrected_revision"), str(exc)
            )
            return
        self._begin_background_op()
        self._worker = FreezeReadinessWorker(
            self._store,
            self._corpus,
            mode=FreezeReadinessWorker.MODE_REVISION,
            parent_audit_id=parent_id,
            revision_reason=(
                "Correct invalid acquisition date projection "
                "(frame-time must not be acquisition date)"
            ),
            analyst_id=self.ed_analyst.text().strip() or parent.analyst_id,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_revision_ok)
        self._worker.failed.connect(self._on_fail)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.finished.connect(self._on_worker_finished)
        self.status.setText(self.t("readiness.freezing"))
        self._worker.start()

    def _on_refresh_clicked(self) -> None:
        self._refresh_cohort_list()
        self._refresh_saved()

    def _refresh_cohort_list(self) -> None:
        self._bind_stores()
        self.list_cohorts.clear()
        if self._corpus is None:
            return
        try:
            for cid in self._corpus.list_cohorts():
                rev = ""
                try:
                    m = self._corpus.load_manifest(cid)
                    rev = f" (rev {m.revision_number})"
                except Exception:
                    rev = ""
                item = QListWidgetItem(f"{cid}{rev}")
                item.setData(256, cid)
                self.list_cohorts.addItem(item)
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("cohort list failed: %s", exc)

    def _refresh_saved(self) -> None:
        """Scan project ml_readiness/ and populate Saved Audits (no corpus needed)."""
        prev = self._audit_id
        self.list_saved.clear()
        self._bind_stores()
        if self._store is None:
            return
        lang = self._lang()
        try:
            audits = self._store.list_audits()
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("saved audit list failed: %s", exc)
            return
        # Most recently used / created first when timestamps available
        try:
            audits = sorted(
                audits,
                key=lambda m: str(getattr(m, "frozen_at", "") or getattr(m, "created_at", "")),
                reverse=True,
            )
        except Exception:
            pass
        select_row = -1
        for i, m in enumerate(audits):
            life = lifecycle_label(m.lifecycle_state, lang)
            title = m.title or m.audit_id
            ts = m.frozen_at or m.created_at or ""
            item = QListWidgetItem(f"{title} — {life} — {ts} — {m.audit_id}")
            item.setData(256, m.audit_id)
            self.list_saved.addItem(item)
            if prev and m.audit_id == prev:
                select_row = i
        if select_row < 0 and audits:
            select_row = 0
        if select_row >= 0:
            self.list_saved.blockSignals(True)
            self.list_saved.setCurrentRow(select_row)
            self.list_saved.blockSignals(False)
            # Load selection if not already showing this audit's rows
            aid = audits[select_row].audit_id
            if aid != prev or not self._rows:
                self._load_saved_audit(aid)

    def _selected_cohort_ids(self) -> list[str]:
        ids: list[str] = []
        for item in self.list_cohorts.selectedItems():
            cid = item.data(256)
            if cid:
                ids.append(str(cid))
        return ids

    def _on_preview(self) -> None:
        self._bind_stores()
        if self._store is None or self._corpus is None:
            QMessageBox.warning(self, "ML", self.t("readiness.no_project"))
            return
        cids = self._selected_cohort_ids()
        if not cids:
            return
        try:
            # Preview uses form contract (not a frozen audit reinterpretation)
            self._frozen_task_contract = ""
            contract = str(self.cmb_contract.currentData())
            self._preview = self._store.preview(
                self._corpus,
                task_contract=contract,
                cohort_ids=cids,
            )
            self._rows = list(self._preview.get("rows") or [])
            cov = self._preview.get("coverage") or {}
            miss = self._preview.get("missingness") or {}
            dens = cov.get("denominators") or {}
            lang = self._lang()
            lines = [
                f"{denom_label('unique_current_items', lang)}: {dens.get('unique_current_items')}",
                f"{denom_label('unique_related_frame_groups', lang)}: {dens.get('unique_related_frame_groups')}",
                f"{denom_label('unique_sequences', lang)}: {dens.get('unique_sequences')}",
                f"{denom_label('unique_source_dates', lang)}: {dens.get('unique_source_dates')}",
                f"{denom_label('independent_second_reviews', lang)}: {dens.get('independent_second_reviews')}",
                f"{denom_label('development_exposed_items', lang)}: {dens.get('development_exposed_items')}",
                f"{denom_label('untouched_eligible_items', lang)}: {dens.get('untouched_eligible_items')}",
            ]
            for w in (self._preview.get("warnings") or [])[:12]:
                lines.append(f"{self.t('readiness.warning_prefix')}: {w}")
            self.preview_text.setPlainText("\n".join(lines))
            self._populate_from_coverage(cov, miss, task_contract=contract)
            self.status.setText(self.t("readiness.preview_done"))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.t("readiness.preview"), str(exc))

    def _begin_background_op(self) -> None:
        self._op_terminal = ""
        self._last_progress_pct = 0
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setVisible(True)

    def _mark_success_progress(self, status_key: str) -> None:
        """Successful completion must always show 100% with success status."""
        self.progress.setVisible(True)
        self.progress.setValue(100)
        self._last_progress_pct = 100
        self.status.setText(self.t(status_key))
        self.btn_cancel.setEnabled(False)

    def _on_freeze(self) -> None:
        self._bind_stores()
        if self._store is None or self._corpus is None:
            QMessageBox.warning(self, "ML", self.t("readiness.no_project"))
            return
        cids = self._selected_cohort_ids()
        if not cids:
            return
        if self._worker is not None and self._worker.isRunning():
            return
        try:
            draft = self._store.create_draft(
                title=self.ed_title.text().strip() or self.t("readiness.default_title"),
                description=self.ed_desc.text().strip(),
                task_contract=str(self.cmb_contract.currentData()),
                cohort_ids=cids,
                analyst_id=self.ed_analyst.text().strip(),
            )
            self._audit_id = draft.audit_id
            self._begin_background_op()
            self._worker = FreezeReadinessWorker(
                self._store,
                self._corpus,
                mode=FreezeReadinessWorker.MODE_FREEZE,
                audit_id=draft.audit_id,
            )
            self._worker.progress.connect(self._on_progress)
            self._worker.finished_ok.connect(self._on_frozen)
            self._worker.failed.connect(self._on_fail)
            self._worker.cancelled.connect(self._on_cancelled)
            self._worker.finished.connect(self._on_worker_finished)
            self.status.setText(self.t("readiness.freezing"))
            self._worker.start()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.t("readiness.freeze"), str(exc))

    def _on_progress(self, pct: int, msg: str) -> None:
        if self._op_terminal in ("cancelled", "failed"):
            return
        value = max(0, min(100, int(pct)))
        self._last_progress_pct = value
        self.progress.setValue(value)
        # Do not overwrite a finalized success message with intermediate worker text.
        if self._op_terminal != "success":
            text = str(msg or "").strip()
            if text and text not in ("complete", "Frozen"):
                self.status.setText(text)

    def _on_frozen(self, manifest) -> None:
        if self._op_terminal:
            return  # ignore duplicate finished_ok
        self._op_terminal = "success"
        self._mark_success_progress("readiness.frozen_ok")
        self._audit_id = manifest.audit_id
        self._frozen_task_contract = manifest.task_contract
        self._rows = self._store.load_inventory(manifest.audit_id) if self._store else []
        cov = build_coverage_summary(self._rows, task_contract=manifest.task_contract)
        miss = build_missingness_report(self._rows, task_contract=manifest.task_contract)
        self._populate_from_coverage(cov, miss, task_contract=manifest.task_contract)
        self._refresh_saved()
        self._mark_success_progress("readiness.frozen_ok")
        QMessageBox.information(self, "OK", self.t("readiness.frozen_ok"))

    def _on_revision_ok(self, manifest) -> None:
        if self._op_terminal:
            return
        self._op_terminal = "success"
        self._mark_success_progress("readiness.corrected_revision_ok")
        self._audit_id = manifest.audit_id
        self._frozen_task_contract = manifest.task_contract
        self._rows = self._store.load_inventory(manifest.audit_id) if self._store else []
        cov = build_coverage_summary(self._rows, task_contract=manifest.task_contract)
        miss = build_missingness_report(self._rows, task_contract=manifest.task_contract)
        self._populate_from_coverage(cov, miss, task_contract=manifest.task_contract)
        self._refresh_saved()
        self._mark_success_progress("readiness.corrected_revision_ok")
        QMessageBox.information(
            self,
            self.t("readiness.create_corrected_revision"),
            f"{self.t('readiness.corrected_revision_ok')}\n{manifest.audit_id}",
        )

    def _on_fail(self, msg: str) -> None:
        if self._op_terminal == "success":
            return
        self._op_terminal = "failed"
        # Preserve last real progress; never force 100% on failure.
        self.progress.setValue(self._last_progress_pct)
        self.btn_cancel.setEnabled(False)
        self.status.setText(self.t("readiness.freeze_failed"))
        QMessageBox.warning(
            self, self.t("readiness.freeze"), msg or self.t("readiness.freeze_failed")
        )

    def _on_cancelled(self, msg: str = "") -> None:
        if self._op_terminal == "success":
            return
        self._op_terminal = "cancelled"
        # Cancellation must not show 100% / success.
        if self.progress.value() >= 100:
            self.progress.setValue(min(self._last_progress_pct, 99) if self._last_progress_pct < 100 else 0)
        self.btn_cancel.setEnabled(False)
        self.status.setText(self.t("readiness.cancel_requested"))
        self.preview_text.append(self.t("readiness.cancel_requested"))

    def _on_worker_finished(self) -> None:
        w = self._worker
        self._worker = None
        if w is not None:
            for sig_name in ("progress", "finished_ok", "failed", "cancelled"):
                try:
                    getattr(w, sig_name).disconnect()
                except Exception:
                    pass
            try:
                w.finished.disconnect()
            except Exception:
                pass
            w.deleteLater()
        # After successful completion keep 100% visible; cancel/fail leave non-100.
        if self._op_terminal == "success":
            self.progress.setValue(100)
            self.btn_cancel.setEnabled(False)

    def _on_cancel(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            if self._op_terminal != "success":
                self.status.setText(self.t("readiness.cancel_requested"))
                self.preview_text.append(self.t("readiness.cancel_requested"))

    def _on_saved_selected(self) -> None:
        items = self.list_saved.selectedItems()
        if not items or self._store is None:
            return
        aid = items[0].data(256)
        if not aid:
            return
        self._load_saved_audit(str(aid))

    def _load_saved_audit(self, audit_id: str) -> None:
        if self._store is None:
            return
        self._audit_id = audit_id
        try:
            m = self._store.load_manifest(audit_id)
            self._frozen_task_contract = m.task_contract
            self.ed_title.setText(m.title or "")
            self.ed_desc.setText(m.description or "")
            self.ed_analyst.setText(m.analyst_id or "")
            idx = self.cmb_contract.findData(m.task_contract)
            if idx >= 0:
                self.cmb_contract.blockSignals(True)
                self.cmb_contract.setCurrentIndex(idx)
                self.cmb_contract.blockSignals(False)
            desc = contract_descriptor(m.task_contract)
            note = desc.get("parameter_scaling_status_ru" if self._lang() == "ru" else "parameter_scaling_status_en") or ""
            self.lbl_contract_note.setText(note)
            if m.lifecycle_state == "draft":
                self._rows = []
                self._last_coverage = {}
                self._last_missingness = {}
                return
            self._rows = self._store.load_inventory(audit_id)
            cov = build_coverage_summary(self._rows, task_contract=m.task_contract)
            miss = build_missingness_report(self._rows, task_contract=m.task_contract)
            self._populate_from_coverage(cov, miss, task_contract=m.task_contract)
            # Restore holdout/gate if present
            d = self._store.path_for(audit_id)
            import json

            hf = d / "holdout_feasibility.json"
            if hf.exists():
                self._last_holdout = json.loads(hf.read_text(encoding="utf-8"))
                self._render_holdout(self._last_holdout)
            rg = d / "readiness_gate.json"
            if rg.exists():
                self._last_gate = json.loads(rg.read_text(encoding="utf-8"))
                self._render_gate(self._last_gate)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.t("readiness.saved_audits"), str(exc))

    def _populate_from_coverage(
        self,
        cov: dict[str, Any],
        miss: dict[str, Any],
        *,
        task_contract: str,
    ) -> None:
        self._last_coverage = cov
        self._last_missingness = miss
        dens = cov.get("denominators") or {}
        lang = self._lang()
        ru = lang == "ru"

        # Human-readable overview sections
        lines: list[str] = []
        lines.append(
            f"{self.t('readiness.current_audit_contract')}: "
            f"{contract_label(task_contract, lang)}"
        )
        lines.append("")
        self._update_current_contract_label()
        for section_key, keys in _OVERVIEW_SECTIONS:
            title = _SECTION_TITLES[section_key].get(lang) or section_key
            lines.append(f"—— {title} ——")
            for k in keys:
                if k not in dens:
                    continue
                lines.append(f"{denom_label(k, lang)}: {dens[k]}")
            lines.append("")
        # Holdout eligibility from dens
        lines.append(f"—— {_SECTION_TITLES['holdout'].get(lang)} ——")
        lines.append(
            f"{denom_label('untouched_eligible_items', lang)}: "
            f"{dens.get('untouched_eligible_items')}"
        )
        lines.append(
            f"{denom_label('development_exposed_items', lang)}: "
            f"{dens.get('development_exposed_items')}"
        )
        overlap = (cov.get("overlap_note") or {}).get(lang) or ""
        if overlap:
            lines.append("")
            lines.append(overlap)
        self.overview_text.setPlainText("\n".join(lines))

        warns = (cov.get("correlation_warnings") or {}).get(lang) or []
        if dens.get("unique_sequences", 0) == 1 and dens.get("raw_frame_count", 0) > 1:
            note = SEQUENCE_CORRELATION_NOTE[lang]
            if note not in warns:
                warns = list(warns) + [note]
        if dens.get("synthetic_related_frame_groups"):
            note = SYNTHETIC_GROUP_NOTE[lang]
            if note not in warns:
                warns = list(warns) + [note]
        self.warn_adjacent.setText("\n".join(warns))

        # Technical details (raw keys) — collapsed
        self.tech_text.setPlainText("\n".join(f"{k}: {v}" for k, v in dens.items()))

        # Class coverage — contract-specific
        self.lbl_class_contract.setText(
            f"{self.t('readiness.class_target')}: {contract_label(task_contract, lang)}"
        )
        self.tbl_class.setRowCount(0)
        if cov.get("target_unsupported"):
            note = (
                cov.get("target_unsupported_note_ru")
                if ru
                else cov.get("target_unsupported_note_en")
            ) or self.t("readiness.unsupported_labels")
            r = self.tbl_class.rowCount()
            self.tbl_class.insertRow(r)
            self.tbl_class.setItem(r, 0, QTableWidgetItem(note))
            self.tbl_class.setItem(r, 1, QTableWidgetItem("—"))
        else:
            targets = cov.get("target_label_counts") or {}
            for cls, n in sorted(targets.items()):
                r = self.tbl_class.rowCount()
                self.tbl_class.insertRow(r)
                code = str(cls)
                if code.startswith("ambiguity:"):
                    label = f"{self.t('readiness.ambiguity_prefix')}: {class_label(code.split(':', 1)[1], lang)}"
                else:
                    label = class_label(code, lang) if code != "(empty)" else "—"
                self.tbl_class.setItem(r, 0, QTableWidgetItem(label))
                self.tbl_class.setItem(r, 1, QTableWidgetItem(str(n)))
            absent = cov.get("absent_target_classes") or []
            if absent:
                r = self.tbl_class.rowCount()
                self.tbl_class.insertRow(r)
                absent_labels = ", ".join(class_label(c, lang) for c in absent)
                self.tbl_class.setItem(
                    r, 0, QTableWidgetItem(f"{self.t('readiness.absent_classes')}: {absent_labels}")
                )
                self.tbl_class.setItem(r, 1, QTableWidgetItem("0"))

        # Sources and Dates — source / acquisition date / frame time / count
        self.tbl_sources.setRowCount(0)
        sd_rows = cov.get("source_date_rows") or []
        missing_date = MISSING_DATE_LABEL.get(lang) or MISSING_DATE_LABEL["en"]
        for row in sd_rows:
            times = row.get("frame_times") or []
            # Prefer one table row per frame time when times differ (owner clarity)
            if len(times) > 1 and row.get("label_count") == len(times):
                for ft in times:
                    details = row.get("source") or ""
                    r = self.tbl_sources.rowCount()
                    self.tbl_sources.insertRow(r)
                    self.tbl_sources.setItem(r, 0, QTableWidgetItem(details))
                    date_val = str(row.get("source_date") or "")
                    if not is_valid_acquisition_date(date_val):
                        date_val = missing_date
                    self.tbl_sources.setItem(r, 1, QTableWidgetItem(date_val))
                    self.tbl_sources.setItem(r, 2, QTableWidgetItem(ft))
                    self.tbl_sources.setItem(r, 3, QTableWidgetItem("1"))
            else:
                times_disp = ", ".join(times[:8])
                if len(times) > 8:
                    times_disp += "…"
                details = row.get("source") or ""
                r = self.tbl_sources.rowCount()
                self.tbl_sources.insertRow(r)
                self.tbl_sources.setItem(r, 0, QTableWidgetItem(details))
                date_val = str(row.get("source_date") or "")
                if not is_valid_acquisition_date(date_val):
                    date_val = missing_date
                self.tbl_sources.setItem(r, 1, QTableWidgetItem(date_val))
                self.tbl_sources.setItem(r, 2, QTableWidgetItem(times_disp or "—"))
                self.tbl_sources.setItem(
                    r, 3, QTableWidgetItem(str(row.get("label_count") or 0))
                )
        self.lbl_sources_note.setText(
            f"{denom_label('unique_sources', lang)}: {dens.get('unique_sources')} · "
            f"{denom_label('unique_source_dates', lang)}: {dens.get('unique_source_dates')} · "
            f"{denom_label('unique_frame_times', lang)}: {dens.get('unique_frame_times')} · "
            f"{denom_label('unique_sequences', lang)}: {dens.get('unique_sequences')}"
        )
        diag = cov.get("acquisition_date_diagnostics") or diagnose_invalid_date_projection(
            self._rows
        )
        self._set_legacy_date_warning(diag)
        self._refresh_blocker_evidence()

        # Review quality
        ri = cov.get("reviewer_independence") or {}
        rev_lines: list[str] = []
        for key in (
            "first_review_count",
            "independent_second_review_count",
            "items_with_paired_independent_reviews",
            "arbitration_count",
            "corrected_first_reviews",
            "corrected_second_reviews",
            "classes_one_expert_only",
            "classes_multiple_independent_experts",
            "classes_with_arbitration",
        ):
            if key not in ri:
                continue
            val = ri[key]
            if isinstance(val, list):
                val = ", ".join(class_label(x, lang) for x in val) or "—"
            rev_lines.append(f"{review_field_label(key, lang)}: {val}")
        rev_lines.append("")
        rev_lines.append(REVIEW_NOTE[lang])
        self.review_text.setPlainText("\n".join(rev_lines))

        # Missingness
        cats = miss.get("categories") or {}
        self.tbl_missing.setRowCount(0)
        for cat, n in sorted(cats.items()):
            r = self.tbl_missing.rowCount()
            self.tbl_missing.insertRow(r)
            self.tbl_missing.setItem(r, 0, QTableWidgetItem(missingness_label(str(cat), lang)))
            self.tbl_missing.setItem(r, 1, QTableWidgetItem(str(n)))

        # Contamination
        self.contam_text.setPlainText(
            f"{denom_label('development_exposed_items', lang)}: "
            f"{dens.get('development_exposed_items')}\n"
            f"{denom_label('untouched_eligible_items', lang)}: "
            f"{dens.get('untouched_eligible_items')}\n"
        )

    def _render_holdout(self, report: dict[str, Any]) -> None:
        lang = self._lang()
        appears = report.get("class_aware_group_separated_holdout_appears_possible")
        untouched = report.get("untouched_eligible_groups") or []
        exposed = report.get("development_exposed_groups") or []
        absent = report.get("classes_absent_from_untouched") or []
        yes = self.t("readiness.yes") if appears else self.t("readiness.no")
        lines = [
            self.t("readiness.holdout_heading"),
            f"{self.t('readiness.holdout_appears_possible')}: {yes}",
            f"{self.t('readiness.holdout_untouched_groups')}: {len(untouched)}",
            f"{self.t('readiness.holdout_exposed_groups')}: {len(exposed)}",
            f"{self.t('readiness.holdout_absent_classes')}: "
            + (", ".join(class_label(c, lang) for c in absent) or "—"),
            "",
            self.t("readiness.holdout_not_completed"),
        ]
        for w in (report.get("warnings") or [])[:8]:
            lines.append(f"{self.t('readiness.warning_prefix')}: {w}")
        # Never dump note_en in RU mode
        if lang == "en":
            note = report.get("note_en") or ""
            if note:
                lines.append("")
                lines.append(note)
        self.holdout_text.setPlainText("\n".join(lines))

    def _render_gate(self, rec: dict[str, Any]) -> None:
        lang = self._lang()
        outcome = str(rec.get("outcome") or "")
        blockers = rec.get("blockers") or []
        auth_train = bool(rec.get("authorizes_training"))
        auth_mlb = bool(rec.get("authorizes_mlb_manifest_planning_only"))
        lines = [
            f"{self.t('readiness.gate_outcome')}: {gate_outcome_label(outcome, lang)}",
            f"{self.t('readiness.gate_authorizes_training')}: "
            f"{self.t('readiness.yes') if auth_train else self.t('readiness.no')}",
            f"{self.t('readiness.gate_authorizes_mlb')}: "
            f"{self.t('readiness.yes') if auth_mlb else self.t('readiness.no')}",
            f"{self.t('readiness.gate_blockers')}: "
            + (
                ", ".join(gate_outcome_label(b, lang) for b in blockers)
                if blockers
                else "—"
            ),
        ]
        self.gate_text.setPlainText("\n".join(lines))

    def _on_holdout(self) -> None:
        if not self._store or not self._audit_id:
            QMessageBox.warning(self, "ML", self.t("readiness.select_saved_audit"))
            return
        try:
            report = self._store.run_holdout_feasibility(self._audit_id)
            self._last_holdout = report.to_dict()
            self._render_holdout(self._last_holdout)
            self._refresh_saved()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.t("readiness.run_holdout"), str(exc))

    def _on_gate(self) -> None:
        if not self._store or not self._audit_id:
            QMessageBox.warning(self, "ML", self.t("readiness.select_saved_audit"))
            return
        blockers = [c for c, cb in self._blocker_checks.items() if cb.isChecked()]
        try:
            rec = self._store.record_gate(
                self._audit_id,
                outcome=str(self.cmb_outcome.currentData()),
                analyst_id=self.ed_analyst.text().strip() or "analyst",
                analyst_rationale=self.ed_rationale.toPlainText().strip(),
                blockers=blockers,
            )
            self._last_gate = rec.to_dict()
            self._render_gate(self._last_gate)
            self._refresh_saved()
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            # Keep domain English message for tests/logs; show localized next-action UX.
            if "explicit analyst rationale" in msg.lower():
                msg = self.t("readiness.gate_f_needs_rationale")
            elif "holdout feasibility" in msg.lower() and "outcome f" in msg.lower():
                msg = self.t("readiness.gate_f_needs_holdout")
            QMessageBox.warning(self, self.t("readiness.record_gate"), msg)

    def _on_export(self) -> None:
        """Export requires an existing selected saved audit; never creates a new audit."""
        self._bind_stores()
        if self._store is None:
            QMessageBox.warning(self, "ML", self.t("readiness.no_project"))
            return
        if not self._audit_id:
            QMessageBox.warning(self, "ML", self.t("readiness.export_requires_audit"))
            return
        try:
            m = self._store.load_manifest(self._audit_id)
            if m.lifecycle_state == "draft":
                QMessageBox.warning(self, "ML", self.t("readiness.export_requires_frozen"))
                return
            self._begin_background_op()
            self.progress.setValue(40)
            self._last_progress_pct = 40
            self.status.setText(self.t("readiness.export"))
            before = len(self._store.list_audits())
            out = self._store.export_report(self._audit_id)
            after = len(self._store.list_audits())
            if after != before:
                _LOG.error("export unexpectedly changed audit count %s -> %s", before, after)
            self._op_terminal = "success"
            self._mark_success_progress("readiness.export_ok")
            self._refresh_saved()
            QMessageBox.information(
                self,
                self.t("readiness.export"),
                f"{self.t('readiness.export_ok')}\n{out.name}",
            )
        except ReadinessStoreError as exc:
            self._op_terminal = "failed"
            self.progress.setValue(self._last_progress_pct)
            self.btn_cancel.setEnabled(False)
            self.status.setText(self.t("readiness.export_failed"))
            QMessageBox.warning(self, self.t("readiness.export"), str(exc))
        except Exception as exc:  # noqa: BLE001
            self._op_terminal = "failed"
            self.progress.setValue(self._last_progress_pct)
            self.btn_cancel.setEnabled(False)
            self.status.setText(self.t("readiness.export_failed"))
            QMessageBox.warning(self, self.t("readiness.export"), str(exc))

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        self._on_worker_finished()
        super().closeEvent(event)

    def normal_ui_text(self) -> str:
        """Aggregate normal (non-technical) UI text for localization tests."""
        parts = [
            self.banner.text(),
            self.overview_text.toPlainText(),
            self.warn_adjacent.text(),
            self.review_text.toPlainText(),
            self.contam_text.toPlainText(),
            self.holdout_text.toPlainText(),
            self.gate_text.toPlainText(),
            self.preview_text.toPlainText(),
            self.lbl_class_contract.text(),
            self.lbl_sources_note.text(),
            self.lbl_contract_note.text(),
            self.box_saved.title(),
            self.box_cohorts.title(),
        ]
        for i in range(self.list_saved.count()):
            parts.append(self.list_saved.item(i).text())
        for tbl in (self.tbl_class, self.tbl_sources, self.tbl_missing):
            for r in range(tbl.rowCount()):
                for c in range(tbl.columnCount()):
                    it = tbl.item(r, c)
                    if it:
                        parts.append(it.text())
            for c in range(tbl.columnCount()):
                h = tbl.horizontalHeaderItem(c)
                if h:
                    parts.append(h.text())
        for cb in self._blocker_checks.values():
            parts.append(cb.text())
        for i in range(self.cmb_outcome.count()):
            parts.append(self.cmb_outcome.itemText(i))
        for i in range(self.cmb_contract.count()):
            parts.append(self.cmb_contract.itemText(i))
        # Explicitly exclude collapsed technical details
        return "\n".join(parts)
