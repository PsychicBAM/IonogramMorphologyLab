"""ML Dataset Manifests workspace (Phase ML-B.1) — planning/governance only."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.ml_dataset_manifests.constants import (
    DEFAULT_GROUPING_POLICY,
    GATE_F,
    GROUPING_POLICIES,
    MANIFEST_PROTOCOL_VERSION,
    NO_CLAIM_STATEMENT_EN,
    NO_CLAIM_STATEMENT_RU,
    WORKFLOW_SEAL_NOTE_EN,
    WORKFLOW_SEAL_NOTE_RU,
)
from ionogram_morphology_lab.ml_dataset_manifests.display_labels import (
    contamination_label,
    contract_compact_label,
    contract_label,
    coverage_field_label,
    flag_label,
    format_blocker,
    format_blockers,
    gate_compact_label,
    gate_outcome_label,
    lifecycle_label,
    policy_label,
    role_label,
    short_source_id,
)
from ionogram_morphology_lab.ml_dataset_manifests.store import (
    MLDatasetManifestStore,
    ManifestStoreError,
)
from ionogram_morphology_lab.ml_dataset_readiness.store import MLDatasetReadinessStore

_LOG = logging.getLogger(__name__)

_ROLE_USER = Qt.ItemDataRole.UserRole

# Tab indices (stable for retranslate / leakage success switch)
_TAB_INPUT = 0
_TAB_POLICY = 1
_TAB_GROUPS = 2
_TAB_ROLES = 3
_TAB_COVERAGE = 4
_TAB_LEAKAGE = 5
_TAB_HOLDOUT = 6
_TAB_VALIDATION = 7
_TAB_SUMMARY = 8


class ManifestWorker(QThread):
    """Background worker with ML-A.1a.2 lifecycle: success @ 100%, cancel ≠ success."""

    progress = Signal(int, str)
    finished_ok = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    MODE_DRAFT = "draft"
    MODE_LEAKAGE = "leakage"
    MODE_PROPOSE = "propose"
    MODE_VALIDATE = "validate"
    MODE_FREEZE = "freeze"
    MODE_EXPORT = "export"

    def __init__(
        self,
        *,
        mode: str,
        manifest_store: MLDatasetManifestStore,
        readiness_store: MLDatasetReadinessStore | None = None,
        audit_id: str = "",
        manifest_set_id: str = "",
        title: str = "",
        description: str = "",
        analyst_id: str = "",
        grouping_policy: str = DEFAULT_GROUPING_POLICY,
        seed: int = 42,
        train_share: float | None = None,
        development_share: float | None = None,
        holdout_share: float | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self.manifest_store = manifest_store
        self.readiness_store = readiness_store
        self.audit_id = audit_id
        self.manifest_set_id = manifest_set_id
        self.title = title
        self.description = description
        self.analyst_id = analyst_id
        self.grouping_policy = grouping_policy
        self.seed = seed
        self.train_share = train_share
        self.development_share = development_share
        self.holdout_share = holdout_share
        self._cancel = False
        self._emitted_terminal = False

    def cancel(self) -> None:
        self._cancel = True

    def _cb_progress(self, pct: int, msg: str) -> None:
        self.progress.emit(int(pct), str(msg))

    def _cb_cancel(self) -> bool:
        return bool(self._cancel)

    def run(self) -> None:
        try:
            if self.mode == self.MODE_DRAFT:
                assert self.readiness_store is not None
                result = self.manifest_store.create_draft_from_readiness(
                    self.readiness_store,
                    audit_id=self.audit_id,
                    title=self.title,
                    description=self.description,
                    analyst_id=self.analyst_id,
                    grouping_policy=self.grouping_policy,
                    seed=self.seed,
                    progress_cb=self._cb_progress,
                    cancel_cb=self._cb_cancel,
                )
            elif self.mode == self.MODE_LEAKAGE:
                result = self.manifest_store.build_leakage(
                    self.manifest_set_id,
                    grouping_policy=self.grouping_policy,
                    progress_cb=self._cb_progress,
                    cancel_cb=self._cb_cancel,
                )
            elif self.mode == self.MODE_PROPOSE:
                result = self.manifest_store.propose_split(
                    self.manifest_set_id,
                    seed=self.seed,
                    train_share=self.train_share,
                    development_share=self.development_share,
                    holdout_share=self.holdout_share,
                    progress_cb=self._cb_progress,
                    cancel_cb=self._cb_cancel,
                )
            elif self.mode == self.MODE_VALIDATE:
                result = self.manifest_store.validate(
                    self.manifest_set_id,
                    progress_cb=self._cb_progress,
                    cancel_cb=self._cb_cancel,
                )
            elif self.mode == self.MODE_FREEZE:
                result = self.manifest_store.freeze(
                    self.manifest_set_id,
                    progress_cb=self._cb_progress,
                    cancel_cb=self._cb_cancel,
                )
            elif self.mode == self.MODE_EXPORT:
                result = self.manifest_store.export_bundle(
                    self.manifest_set_id,
                    progress_cb=self._cb_progress,
                    cancel_cb=self._cb_cancel,
                )
            else:
                raise ManifestStoreError(f"Unknown mode: {self.mode}")
            if self._cancel:
                self.cancelled.emit("cancelled")
                return
            self.progress.emit(100, "complete")
            if not self._emitted_terminal:
                self._emitted_terminal = True
                self.finished_ok.emit(result)
        except ManifestStoreError as exc:
            msg = str(exc)
            if "cancel" in msg.lower() or self._cancel:
                if not self._emitted_terminal:
                    self._emitted_terminal = True
                    self.cancelled.emit(msg)
            else:
                if not self._emitted_terminal:
                    self._emitted_terminal = True
                    self.failed.emit(msg)
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("Manifest worker failed")
            if not self._emitted_terminal:
                self._emitted_terminal = True
                self.failed.emit(str(exc))


class MLDatasetManifestsPage(QWidget):
    def __init__(self, session: Any, i18n: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self._manifest_store: MLDatasetManifestStore | None = None
        self._readiness_store: MLDatasetReadinessStore | None = None
        self._worker: ManifestWorker | None = None
        self._op_terminal: str | None = None
        self._active_mode: str = ""
        self._current_id: str = ""
        self._form_labels: dict[str, QLabel] = {}
        # Session-only UI prefs (not persisted into scientific snapshots)
        self._context_expanded: bool = False
        self._tech_expanded: bool = False
        self._lifecycle_state: str = ""
        self._build_ui()
        self.retranslate()

    def _t(self, key: str, fallback: str = "") -> str:
        try:
            return self.i18n.t(key, default=fallback or key)
        except Exception:  # noqa: BLE001
            return fallback or key

    def _lang(self) -> str:
        try:
            lang = str(getattr(self.i18n, "language", "en") or "en")
        except Exception:  # noqa: BLE001
            lang = "en"
        return "ru" if lang.lower().startswith("ru") else "en"

    def _yes_no(self, value: bool) -> str:
        if self._lang() == "ru":
            return "да" if value else "нет"
        return "yes" if value else "no"

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setObjectName("manifests_status")
        root.addWidget(self._status)

        self._alert = QLabel()
        self._alert.setWordWrap(True)
        self._alert.setObjectName("manifests_alert")
        self._alert.hide()
        root.addWidget(self._alert)

        self._compact_summary = QLabel()
        self._compact_summary.setWordWrap(True)
        self._compact_summary.setObjectName("manifests_compact_summary")
        root.addWidget(self._compact_summary)

        self._context_box = QGroupBox()
        self._context_box.setCheckable(True)
        self._context_box.setChecked(False)
        self._context_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        ctx_outer = QVBoxLayout(self._context_box)
        ctx_outer.setContentsMargins(8, 4, 8, 4)
        self._context_body = QWidget()
        ctx_lay = QVBoxLayout(self._context_body)
        ctx_lay.setContentsMargins(0, 0, 0, 0)
        self._claim = QLabel()
        self._claim.setWordWrap(True)
        ctx_lay.addWidget(self._claim)
        self._hdr_manifest = QLabel()
        self._hdr_audit = QLabel()
        self._hdr_gate = QLabel()
        self._hdr_contract = QLabel()
        self._hdr_auth_mlb = QLabel()
        self._hdr_auth_train = QLabel()
        self._hdr_auth_mlc = QLabel()
        self._hdr_protocol = QLabel()
        for w in (
            self._hdr_manifest,
            self._hdr_audit,
            self._hdr_gate,
            self._hdr_contract,
            self._hdr_auth_mlb,
            self._hdr_auth_train,
            self._hdr_auth_mlc,
            self._hdr_protocol,
        ):
            w.setWordWrap(True)
            ctx_lay.addWidget(w)
        self._context_body.hide()
        ctx_outer.addWidget(self._context_body)
        self._context_box.toggled.connect(self._on_context_toggled)
        root.addWidget(self._context_box)

        form = QFormLayout()
        self._title = QLineEdit()
        self._desc = QLineEdit()
        self._analyst = QLineEdit()
        self._seed = QSpinBox()
        self._seed.setRange(0, 2_000_000_000)
        self._seed.setValue(42)
        self._policy = QComboBox()
        for key, widget in (
            ("title", self._title),
            ("description", self._desc),
            ("analyst", self._analyst),
            ("seed", self._seed),
            ("policy", self._policy),
        ):
            lbl = QLabel()
            self._form_labels[key] = lbl
            form.addRow(lbl, widget)
        root.addLayout(form)

        lists = QHBoxLayout()
        self._box_audits = QGroupBox()
        self._box_audits.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        left = QVBoxLayout(self._box_audits)
        self._audit_list = QListWidget()
        self._audit_list.setMaximumHeight(110)
        left.addWidget(self._audit_list)
        self._box_saved = QGroupBox()
        self._box_saved.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        right = QVBoxLayout(self._box_saved)
        self._saved_list = QListWidget()
        self._saved_list.setMaximumHeight(110)
        self._saved_list.currentItemChanged.connect(self._on_saved_selected)
        right.addWidget(self._saved_list)
        lists.addWidget(self._box_audits, 1)
        lists.addWidget(self._box_saved, 1)
        root.addLayout(lists)

        btns = QHBoxLayout()
        self._btn_draft = QPushButton()
        self._btn_leakage = QPushButton()
        self._btn_propose = QPushButton()
        self._btn_validate = QPushButton()
        self._btn_freeze = QPushButton()
        self._btn_export = QPushButton()
        self._btn_cancel = QPushButton()
        self._btn_refresh = QPushButton()
        for b in (
            self._btn_draft,
            self._btn_leakage,
            self._btn_propose,
            self._btn_validate,
            self._btn_freeze,
            self._btn_export,
            self._btn_cancel,
            self._btn_refresh,
        ):
            btns.addWidget(b)
        root.addLayout(btns)

        self._btn_draft.clicked.connect(self._on_create_draft)
        self._btn_leakage.clicked.connect(self._on_leakage)
        self._btn_propose.clicked.connect(self._on_propose)
        self._btn_validate.clicked.connect(self._on_validate)
        self._btn_freeze.clicked.connect(self._on_freeze)
        self._btn_export.clicked.connect(self._on_export)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._btn_refresh.clicked.connect(self.on_project_changed)

        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._progress.setMaximumHeight(18)
        root.addWidget(self._progress)

        self._tabs = QTabWidget()
        self._tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._txt_input = QTextEdit()
        self._txt_input.setReadOnly(True)
        self._txt_policy = QTextEdit()
        self._txt_policy.setReadOnly(True)
        self._tbl_groups = QTableWidget(0, 6)
        self._tbl_roles = QTableWidget(0, 5)
        self._configure_table_columns()
        self._txt_coverage = QTextEdit()
        self._txt_coverage.setReadOnly(True)
        self._txt_leakage = QTextEdit()
        self._txt_leakage.setReadOnly(True)
        self._txt_holdout = QTextEdit()
        self._txt_holdout.setReadOnly(True)
        self._txt_validation = QTextEdit()
        self._txt_validation.setReadOnly(True)
        self._txt_summary = QTextEdit()
        self._txt_summary.setReadOnly(True)
        self._tech = QTextEdit()
        self._tech.setReadOnly(True)
        self._tech.setMaximumHeight(220)

        self._tabs.addTab(self._txt_input, "")
        self._tabs.addTab(self._txt_policy, "")
        self._tabs.addTab(self._tbl_groups, "")
        self._tabs.addTab(self._tbl_roles, "")
        self._tabs.addTab(self._txt_coverage, "")
        self._tabs.addTab(self._txt_leakage, "")
        self._tabs.addTab(self._txt_holdout, "")
        self._tabs.addTab(self._txt_validation, "")
        self._tabs.addTab(self._txt_summary, "")

        self._tech_box = QGroupBox()
        self._tech_box.setCheckable(True)
        self._tech_box.setChecked(False)
        self._tech_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        tech_outer = QVBoxLayout(self._tech_box)
        tech_outer.setContentsMargins(8, 4, 8, 4)
        self._tech_body = QWidget()
        tech_l = QVBoxLayout(self._tech_body)
        tech_l.setContentsMargins(0, 0, 0, 0)
        tech_l.addWidget(self._tech)
        self._tech_body.hide()
        tech_outer.addWidget(self._tech_body)
        self._tech_box.toggled.connect(self._on_tech_toggled)

        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(4)
        wl.addWidget(self._tabs, 1)
        wl.addWidget(self._tech_box, 0)
        root.addWidget(wrap, 1)

        self._update_headers()
        self._set_compact_summary()

    def retranslate(self) -> None:
        """Refresh all UI chrome without project reload; preserve selection state."""
        lang = self._lang()
        tab_idx = self._tabs.currentIndex()
        current_id = self._current_id
        audit_id = self._selected_audit_id()
        ctx_exp = self._context_expanded
        tech_exp = self._tech_expanded

        self._claim.setText(
            NO_CLAIM_STATEMENT_RU if lang == "ru" else NO_CLAIM_STATEMENT_EN
        )
        if self._manifest_store is None:
            self._status.setText(
                self._t("manifests.no_project", "Open a project to plan dataset manifests.")
            )
        elif not current_id:
            self._status.setText(
                self._t(
                    "manifests.ready",
                    "Select a frozen readiness audit, then create a draft manifest set.",
                )
            )

        self._form_labels["title"].setText(self._t("manifests.title", "Title"))
        self._form_labels["description"].setText(
            self._t("manifests.description", "Description")
        )
        self._form_labels["analyst"].setText(self._t("manifests.analyst", "Analyst"))
        self._form_labels["seed"].setText(self._t("manifests.seed", "Seed"))
        self._form_labels["policy"].setText(
            self._t("manifests.grouping_policy", "Grouping policy")
        )

        self._box_audits.setTitle(
            self._t("manifests.saved_audits", "Frozen readiness audits")
        )
        self._box_saved.setTitle(self._t("manifests.saved_sets", "Saved manifest sets"))

        self._btn_draft.setText(
            self._t("manifests.create_draft", "Create draft from audit")
        )
        self._btn_leakage.setText(
            self._t("manifests.build_leakage", "Build leakage graph")
        )
        self._btn_propose.setText(
            self._t("manifests.propose", "Deterministic proposal")
        )
        self._btn_validate.setText(self._t("manifests.validate", "Validate"))
        self._btn_freeze.setText(self._t("manifests.freeze", "Freeze manifest set"))
        self._btn_export.setText(self._t("manifests.export", "Export"))
        self._btn_cancel.setText(self._t("manifests.cancel", "Cancel"))
        self._btn_refresh.setText(self._t("manifests.refresh", "Refresh"))

        tab_keys = [
            ("manifests.tab_input", "Input Audit"),
            ("manifests.tab_policy", "Grouping Policy"),
            ("manifests.tab_groups", "Atomic Groups"),
            ("manifests.tab_roles", "Role Assignment"),
            ("manifests.tab_coverage", "Coverage"),
            ("manifests.tab_leakage", "Leakage and Contamination"),
            ("manifests.tab_holdout", "Holdout Reservation"),
            ("manifests.tab_validation", "Validation"),
            ("manifests.tab_summary", "Manifest Summary"),
        ]
        for i, (key, fb) in enumerate(tab_keys):
            self._tabs.setTabText(i, self._t(key, fb))

        self._context_box.setTitle(
            self._t(
                "manifests.context_panel",
                "Manifest context and scientific status",
            )
        )
        self._tech_box.setTitle(self._t("manifests.technical", "Technical Details"))
        self._set_table_headers()
        self._reload_policy_combo(preserve=True)
        self._update_headers()

        self._current_id = current_id
        self._refresh_audits(prefer_audit_id=audit_id)
        self._refresh_saved()
        if audit_id:
            self._select_audit(audit_id)
        if self._current_id and self._manifest_store is not None:
            path = self._manifest_store.path_for(self._current_id) / "manifest_set.json"
            if path.is_file():
                self._load_saved(self._current_id)
            else:
                # Preserve selection id across language switch even if list not yet synced
                self._select_saved(self._current_id)
        self._tabs.setCurrentIndex(tab_idx)
        # Restore session expand prefs after load (load must not force-open panels)
        self._context_box.blockSignals(True)
        self._tech_box.blockSignals(True)
        self._context_box.setChecked(ctx_exp)
        self._tech_box.setChecked(tech_exp)
        self._context_body.setVisible(ctx_exp)
        self._tech_body.setVisible(tech_exp)
        self._context_expanded = ctx_exp
        self._tech_expanded = tech_exp
        self._context_box.blockSignals(False)
        self._tech_box.blockSignals(False)

    def _on_context_toggled(self, expanded: bool) -> None:
        self._context_expanded = bool(expanded)
        self._context_body.setVisible(self._context_expanded)

    def _on_tech_toggled(self, expanded: bool) -> None:
        self._tech_expanded = bool(expanded)
        self._tech_body.setVisible(self._tech_expanded)

    def _configure_table_columns(self) -> None:
        """Prefer readable role/date columns over opaque IDs."""
        for tbl, stretch_cols, content_cols, id_cols in (
            (self._tbl_groups, (4, 5), (1, 2, 3), (0,)),
            (self._tbl_roles, (4,), (1, 2), (0, 3)),
        ):
            tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            tbl.setTextElideMode(Qt.TextElideMode.ElideMiddle)
            tbl.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
            hdr = tbl.horizontalHeader()
            hdr.setStretchLastSection(False)
            for c in id_cols:
                hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
                tbl.setColumnWidth(c, 110)
            for c in content_cols:
                hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
            for c in stretch_cols:
                hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
            tbl.verticalHeader().setVisible(False)

    def _set_table_headers(self) -> None:
        lang = self._lang()
        if lang == "ru":
            self._tbl_groups.setHorizontalHeaderLabels(
                [
                    "ID группы",
                    "Элементы",
                    "Роль",
                    "Пригодна для holdout",
                    "Последовательности",
                    "Даты",
                ]
            )
            self._tbl_roles.setHorizontalHeaderLabels(
                ["ID элемента", "Роль", "Цель", "Группа", "Контаминация"]
            )
        else:
            self._tbl_groups.setHorizontalHeaderLabels(
                [
                    "Group ID",
                    "Items",
                    "Role",
                    "Holdout eligible",
                    "Sequences",
                    "Dates",
                ]
            )
            self._tbl_roles.setHorizontalHeaderLabels(
                ["Item", "Role", "Target", "Group", "Contamination"]
            )

    def _reload_policy_combo(self, *, preserve: bool = True) -> None:
        prev = str(self._policy.currentData() or DEFAULT_GROUPING_POLICY)
        self._policy.blockSignals(True)
        self._policy.clear()
        lang = self._lang()
        for pid in sorted(GROUPING_POLICIES):
            self._policy.addItem(policy_label(pid, lang), pid)
        idx = self._policy.findData(prev if preserve else DEFAULT_GROUPING_POLICY)
        if idx < 0:
            idx = self._policy.findData(DEFAULT_GROUPING_POLICY)
        if idx >= 0:
            self._policy.setCurrentIndex(idx)
        self._policy.blockSignals(False)

    def _update_headers(
        self,
        *,
        manifest_id: str = "",
        audit_id: str = "",
        gate: str = "",
        contract: str = "",
        authorizes_mlb: bool | None = None,
        authorizes_train: bool | None = None,
        authorizes_mlc: bool | None = None,
        item_count: int | None = None,
        group_count: int | None = None,
        lifecycle_state: str = "",
    ) -> None:
        lang = self._lang()
        mid = manifest_id or self._current_id or "—"
        aid = audit_id or "—"
        gate_txt = gate_outcome_label(gate, lang) if gate else "—"
        contract_txt = contract_label(contract, lang) if contract else "—"
        self._hdr_manifest.setText(
            f"{self._t('manifests.hdr_manifest', 'Current manifest')}: {mid}"
        )
        self._hdr_audit.setText(
            f"{self._t('manifests.hdr_audit', 'Source readiness audit')}: {aid}"
        )
        self._hdr_gate.setText(
            f"{self._t('manifests.hdr_gate', 'Gate')}: {gate_txt}"
        )
        self._hdr_contract.setText(
            f"{self._t('manifests.hdr_contract', 'Task contract')}: {contract_txt}"
        )
        mlb = False if authorizes_mlb is None else bool(authorizes_mlb)
        train = False if authorizes_train is None else bool(authorizes_train)
        mlc = False if authorizes_mlc is None else bool(authorizes_mlc)
        self._hdr_auth_mlb.setText(
            f"{flag_label('authorizes_mlb_planning', lang)}: {self._yes_no(mlb)}"
        )
        self._hdr_auth_train.setText(
            f"{flag_label('authorizes_training', lang)}: {self._yes_no(train)}"
        )
        self._hdr_auth_mlc.setText(
            f"{flag_label('authorizes_mlc', lang)}: {self._yes_no(mlc)}"
        )
        self._hdr_protocol.setText(
            f"{self._t('manifests.protocol', 'Protocol')}: {MANIFEST_PROTOCOL_VERSION}"
        )
        self._set_compact_summary(
            lifecycle_state=lifecycle_state or self._lifecycle_state,
            gate=gate,
            contract=contract,
            item_count=item_count,
            group_count=group_count,
        )

    def _set_compact_summary(
        self,
        *,
        lifecycle_state: str = "",
        gate: str = "",
        contract: str = "",
        item_count: int | None = None,
        group_count: int | None = None,
    ) -> None:
        lang = self._lang()
        state = lifecycle_state or self._lifecycle_state
        if not state and not gate and item_count is None:
            self._compact_summary.setText(
                self._t("manifests.compact_empty", "No manifest selected")
            )
            return
        life = lifecycle_label(state, lang) if state else "—"
        gate_c = gate_compact_label(gate, lang) if gate else "—"
        contract_c = contract_compact_label(contract, lang) if contract else "—"
        items = "—" if item_count is None else str(item_count)
        groups = "—" if group_count is None else str(group_count)
        if lang == "ru":
            counts = f"{items} элементов / {groups} групп"
        else:
            counts = f"{items} items / {groups} groups"
        self._compact_summary.setText(f"{life} · {gate_c} · {contract_c} · {counts}")

    def _set_alert_visible(self, text: str) -> None:
        msg = (text or "").strip()
        if msg:
            self._alert.setText(msg)
            self._alert.show()
        else:
            self._alert.clear()
            self._alert.hide()

    def _holdout_lock_is_valid(self, manifest_set_id: str, ms: Any) -> bool:
        """Authoritative frozen holdout lock presence (fail closed)."""
        if not self._manifest_store or not manifest_set_id:
            return False
        if not str(getattr(ms, "holdout_lock_hash", "") or "").strip():
            return False
        path = self._manifest_store.path_for(manifest_set_id) / "holdout_lock.json"
        if not path.is_file():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return False
        if not isinstance(data, dict) or not data:
            return False
        lock_hash = str(data.get("lock_hash") or data.get("holdout_lock_hash") or "")
        if lock_hash and ms.holdout_lock_hash and lock_hash != ms.holdout_lock_hash:
            return False
        return True

    def _holdout_status_lines(
        self,
        ms: Any,
        items: list[Any],
        *,
        lang: str,
        include_blockers: bool = True,
    ) -> list[str]:
        holdout_n = sum(1 for it in items if it.role == "untouched_holdout")
        holdout_g = len(
            {
                it.atomic_group_id
                for it in items
                if it.role == "untouched_holdout" and it.atomic_group_id
            }
        )
        seal = WORKFLOW_SEAL_NOTE_RU if lang == "ru" else WORKFLOW_SEAL_NOTE_EN
        if ms.lifecycle_state == "frozen":
            if self._holdout_lock_is_valid(ms.manifest_set_id, ms):
                items_lbl = coverage_field_label("unique_items", lang)
                groups_lbl = coverage_field_label("atomic_groups", lang)
                return [
                    self._t("manifests.holdout_reserved_title", "Holdout reserved"),
                    f"{items_lbl}: {holdout_n}",
                    f"{groups_lbl}: {holdout_g}",
                    self._t(
                        "manifests.holdout_ref_labels_sealed",
                        "Reference labels: sealed",
                    ),
                    self._t(
                        "manifests.holdout_unlock_unavailable",
                        "Unlock in ML-B: unavailable",
                    ),
                    "",
                    seal,
                ]
            return [
                self._t(
                    "manifests.holdout_lock_corrupt",
                    "Integrity warning: frozen holdout lock is missing or corrupt. "
                    "Do not treat holdout as reserved.",
                ),
                self._t(
                    "manifests.holdout_counts_observed",
                    "Observed holdout assignment (not authoritative): "
                    "items={items}, groups={groups}",
                ).format(items=holdout_n, groups=holdout_g),
            ]
        lines = [
            self._t(
                "manifests.holdout_draft",
                "Draft holdout assignment (not reserved): items={items}, groups={groups}",
            ).format(items=holdout_n, groups=holdout_g),
            self._t(
                "manifests.holdout_needs_gate_f",
                "Final holdout reservation requires Gate F freeze.",
            ),
        ]
        if include_blockers:
            holdout_related = [
                b
                for b in (ms.freeze_blockers or [])
                if any(k in b for k in ("holdout", "untouched", "gate", "readiness"))
            ]
            lines.extend(
                f"{self._t('manifests.blocker', 'Blocker')}: {format_blocker(b, lang)}"
                for b in holdout_related
            )
        return lines

    def _apply_lifecycle_editability(self, ms: Any) -> None:
        frozen = str(getattr(ms, "lifecycle_state", "") or "") == "frozen"
        for w in (self._title, self._desc, self._analyst, self._seed, self._policy):
            w.setEnabled(not frozen)
        # Creating a new draft from an audit is allowed while viewing a frozen set.
        self._btn_draft.setEnabled(True)
        self._btn_leakage.setEnabled(not frozen)
        self._btn_propose.setEnabled(not frozen)
        self._btn_validate.setEnabled(not frozen)
        if frozen:
            self._btn_freeze.setEnabled(False)
        self._btn_export.setEnabled(True)
        self._btn_refresh.setEnabled(True)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.on_project_changed()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._teardown_worker(cancel=True)
        super().closeEvent(event)

    def on_project_changed(self) -> None:
        keep_id = self._current_id
        self._bind_stores()
        self._refresh_audits()
        self._refresh_saved()
        if keep_id and self._manifest_store:
            try:
                self._manifest_store.load_manifest_set(keep_id)
                self._current_id = keep_id
                self._select_saved(keep_id)
                self._load_saved(keep_id)
                return
            except Exception:  # noqa: BLE001
                pass
        item = self._saved_list.currentItem()
        if item is not None:
            mid = item.data(_ROLE_USER)
            if mid:
                self._load_saved(str(mid))
        else:
            self._current_id = ""
            self._update_headers()

    def _bind_stores(self) -> None:
        project = getattr(self.session, "project_path", None) or getattr(
            self.session, "active_project_path", None
        )
        if not project:
            try:
                project = (
                    self.session.project.root
                    if getattr(self.session, "project", None)
                    else None
                )
            except Exception:  # noqa: BLE001
                project = None
        if not project:
            self._manifest_store = None
            self._readiness_store = None
            self._status.setText(
                self._t("manifests.no_project", "Open a project to plan dataset manifests.")
            )
            return
        root = Path(project)
        self._manifest_store = MLDatasetManifestStore(root)
        self._readiness_store = MLDatasetReadinessStore(root)
        self._status.setText(
            self._t(
                "manifests.ready",
                "Select a frozen readiness audit, then create a draft manifest set.",
            )
        )

    def _selected_audit_id(self) -> str:
        item = self._audit_list.currentItem()
        return str(item.data(_ROLE_USER)) if item else ""

    def _select_audit(self, audit_id: str) -> None:
        if not audit_id:
            return
        for i in range(self._audit_list.count()):
            item = self._audit_list.item(i)
            if item is not None and str(item.data(_ROLE_USER)) == audit_id:
                self._audit_list.blockSignals(True)
                self._audit_list.setCurrentRow(i)
                self._audit_list.blockSignals(False)
                return

    def _select_saved(self, manifest_set_id: str) -> None:
        if not manifest_set_id:
            return
        for i in range(self._saved_list.count()):
            item = self._saved_list.item(i)
            if item is not None and str(item.data(_ROLE_USER)) == manifest_set_id:
                self._saved_list.blockSignals(True)
                self._saved_list.setCurrentRow(i)
                self._saved_list.blockSignals(False)
                return

    def _refresh_audits(self, *, prefer_audit_id: str = "") -> None:
        prev = prefer_audit_id or self._selected_audit_id()
        self._audit_list.blockSignals(True)
        self._audit_list.clear()
        if not self._readiness_store:
            self._audit_list.blockSignals(False)
            return
        lang = self._lang()
        for m in self._readiness_store.list_audits():
            if m.lifecycle_state not in {"frozen", "gate_recorded", "reviewed"}:
                continue
            gate = gate_outcome_label(m.gate_outcome or "", lang)
            contract = contract_label(m.task_contract or "", lang)
            label = f"{m.title} · {gate} · {contract}"
            item = QListWidgetItem(label)
            item.setData(_ROLE_USER, m.audit_id)
            item.setToolTip(m.audit_id)
            self._audit_list.addItem(item)
        self._audit_list.blockSignals(False)
        if prev:
            self._select_audit(prev)

    def _refresh_saved(self) -> None:
        prev = self._current_id
        self._saved_list.blockSignals(True)
        self._saved_list.clear()
        if not self._manifest_store:
            self._saved_list.blockSignals(False)
            return
        sets = self._manifest_store.list_manifest_sets()
        sets.sort(key=lambda s: s.frozen_at or s.created_at, reverse=True)
        lang = self._lang()
        select_row = -1
        for i, ms in enumerate(sets):
            gate = gate_outcome_label(ms.source_readiness_gate_outcome or "", lang)
            label = (
                f"{ms.title} · {lifecycle_label(ms.lifecycle_state, lang)} · {gate}"
            )
            item = QListWidgetItem(label)
            item.setData(_ROLE_USER, ms.manifest_set_id)
            item.setToolTip(ms.manifest_set_id)
            self._saved_list.addItem(item)
            if ms.manifest_set_id == prev:
                select_row = i
        if select_row < 0 and sets:
            select_row = 0
        if select_row >= 0:
            self._saved_list.setCurrentRow(select_row)
            if not prev:
                self._current_id = sets[select_row].manifest_set_id
        self._saved_list.blockSignals(False)

    def _on_saved_selected(self, cur: QListWidgetItem | None, _prev=None) -> None:
        if cur is None:
            return
        mid = cur.data(_ROLE_USER)
        if mid:
            self._load_saved(str(mid))

    def _begin_background_op(self) -> None:
        self._op_terminal = None
        self._progress.setValue(0)
        self._btn_cancel.setEnabled(True)

    def _mark_success_progress(self, msg: str) -> None:
        self._progress.setValue(100)
        self._status.setText(msg)
        self._btn_cancel.setEnabled(False)
        self._op_terminal = "success"

    def _teardown_worker(self, *, cancel: bool = False) -> None:
        w = self._worker
        if w is None:
            return
        if cancel and w.isRunning():
            w.cancel()
            w.wait(3000)
        try:
            w.progress.disconnect()
            w.finished_ok.disconnect()
            w.failed.disconnect()
            w.cancelled.disconnect()
            w.finished.disconnect()
        except Exception:  # noqa: BLE001
            pass
        w.deleteLater()
        self._worker = None

    def _start_worker(self, worker: ManifestWorker) -> None:
        self._teardown_worker(cancel=True)
        self._begin_background_op()
        self._active_mode = worker.mode
        self._worker = worker
        worker.progress.connect(self._on_progress)
        worker.finished_ok.connect(self._on_finished_ok)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(self._on_worker_finished)
        worker.start()

    def _on_progress(self, pct: int, msg: str) -> None:
        if self._op_terminal == "success":
            return
        self._progress.setValue(max(0, min(99, int(pct))))
        text = str(msg or "").strip()
        if text and text not in ("complete",):
            self._status.setText(text)

    def _on_finished_ok(self, result: object) -> None:
        mode = self._active_mode or (
            getattr(self._worker, "mode", "") if self._worker else ""
        )
        self._mark_success_progress(self._t("manifests.op_ok", "Operation complete"))

        mid = ""
        if hasattr(result, "manifest_set_id"):
            mid = str(getattr(result, "manifest_set_id") or "")
        elif isinstance(result, dict) and result.get("manifest_set_id"):
            mid = str(result.get("manifest_set_id") or "")
        if mid:
            self._current_id = mid

        if mode == ManifestWorker.MODE_LEAKAGE:
            self._show_leakage_graph_summary(result)

        self._refresh_saved()
        self._select_saved(self._current_id)
        if self._current_id:
            self._load_saved(self._current_id)

        if mode == ManifestWorker.MODE_LEAKAGE:
            self._tabs.setCurrentIndex(_TAB_GROUPS)
        elif mode == ManifestWorker.MODE_VALIDATE:
            self._show_validation_summary(result)
            self._tabs.setCurrentIndex(_TAB_VALIDATION)

    def _show_leakage_graph_summary(self, result: object) -> None:
        groups: list[Any] = []
        meta: dict[str, Any] = {}
        if isinstance(result, tuple) and len(result) >= 2:
            groups = list(result[0] or [])
            meta = dict(result[1] or {})
        items_n = int(meta.get("item_count") or 0)
        groups_n = int(meta.get("group_count") or len(groups))
        if not items_n and self._manifest_store and self._current_id:
            try:
                items_n = len(self._manifest_store.load_items(self._current_id))
            except Exception:  # noqa: BLE001
                items_n = 0
        seqs: set[str] = set()
        eligible = 0
        for g in groups:
            for sid in getattr(g, "sequence_ids", None) or []:
                if sid:
                    seqs.add(str(sid))
            if getattr(g, "eligible_untouched_holdout", False):
                eligible += 1
        body = self._t(
            "manifests.graph_built_body",
            "Leakage graph built.\n"
            "Items: {items}\n"
            "Atomic groups: {groups}\n"
            "Sequences: {sequences}\n"
            "Untouched-holdout-eligible groups: {eligible}",
        ).format(
            items=items_n,
            groups=groups_n,
            sequences=len(seqs),
            eligible=eligible,
        )
        title = self._t("manifests.graph_built_title", "Leakage graph built")
        self._status.setText(body.replace("\n", " · "))
        QMessageBox.information(self, title, body)

    def _show_validation_summary(self, result: object) -> None:
        report = result if isinstance(result, dict) else {}
        ok = bool(report.get("integrity_ok", report.get("ok")))
        blockers = list(report.get("freeze_blockers") or report.get("blockers") or [])
        items_n = int(report.get("item_count") or 0)
        groups_n = int(report.get("group_count") or 0)
        overlaps = int(report.get("overlap_error_count") or 0)
        conflicts = int(report.get("holdout_conflict_count") or 0)
        holdout_g = int(report.get("holdout_group_count") or 0)
        if ok:
            title = self._t("manifests.validate_ok_title", "Manifest validation complete")
            body = self._t(
                "manifests.validate_ok_body",
                "Manifest validation complete.\n"
                "Integrity: PASS\n"
                "Items: {items}\n"
                "Atomic groups: {groups}\n"
                "Role overlaps: {overlaps}\n"
                "Leakage conflicts: {conflicts}\n"
                "Holdout groups: {holdout_groups}\n"
                "Manifest is ready to freeze.",
            ).format(
                items=items_n,
                groups=groups_n,
                overlaps=overlaps,
                conflicts=conflicts,
                holdout_groups=holdout_g,
            )
            self._status.setText(body.replace("\n", " · "))
            self._btn_freeze.setEnabled(self._lifecycle_state != "frozen")
            QMessageBox.information(self, title, body)
        else:
            title = self._t(
                "manifests.validate_fail_title",
                "Manifest validation finished with errors",
            )
            body = self._t(
                "manifests.validate_fail_body",
                "Manifest validation finished with errors.\n"
                "Integrity: FAIL\n"
                "Problems found: {n}\n"
                "Open the Validation tab for details.",
            ).format(n=len(blockers) or overlaps or 1)
            lang = self._lang()
            detail_lines = [format_blocker(b, lang) for b in blockers[:12]]
            if detail_lines:
                body = body + "\n\n" + "\n".join(f"• {line}" for line in detail_lines)
            self._status.setText(body.split("\n")[0])
            self._btn_freeze.setEnabled(False)
            QMessageBox.warning(self, title, body)

    def _on_failed(self, msg: str) -> None:
        if self._op_terminal == "success":
            return
        self._op_terminal = "failed"
        self._btn_cancel.setEnabled(False)
        self._status.setText(msg)
        QMessageBox.warning(self, self._t("manifests.error", "Error"), msg)

    def _on_cancelled(self, msg: str) -> None:
        if self._op_terminal == "success":
            return
        self._op_terminal = "cancelled"
        self._btn_cancel.setEnabled(False)
        if self._progress.value() >= 100:
            self._progress.setValue(99)
        self._status.setText(msg or self._t("manifests.cancelled", "Cancelled"))

    def _on_worker_finished(self) -> None:
        if self._op_terminal == "success":
            self._progress.setValue(100)
            self._btn_cancel.setEnabled(False)
        w = self._worker
        if w is not None:
            try:
                w.progress.disconnect()
                w.finished_ok.disconnect()
                w.failed.disconnect()
                w.cancelled.disconnect()
            except Exception:  # noqa: BLE001
                pass
            w.deleteLater()
        self._worker = None
        self._active_mode = ""

    def _on_cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._status.setText(
                self._t("manifests.cancel_requested", "Cancellation requested…")
            )
            self._worker.cancel()

    def _on_create_draft(self) -> None:
        if not self._manifest_store or not self._readiness_store:
            return
        aid = self._selected_audit_id()
        if not aid:
            QMessageBox.information(
                self,
                self._t("manifests.need_audit", "Select audit"),
                self._t(
                    "manifests.need_audit_msg",
                    "Select a frozen readiness audit first.",
                ),
            )
            return
        title = self._title.text().strip() or f"Manifest from {aid}"
        worker = ManifestWorker(
            mode=ManifestWorker.MODE_DRAFT,
            manifest_store=self._manifest_store,
            readiness_store=self._readiness_store,
            audit_id=aid,
            title=title,
            description=self._desc.text().strip(),
            analyst_id=self._analyst.text().strip(),
            grouping_policy=str(self._policy.currentData() or DEFAULT_GROUPING_POLICY),
            seed=int(self._seed.value()),
        )
        self._start_worker(worker)

    def _require_current(self) -> str:
        if not self._current_id:
            raise ManifestStoreError(
                self._t("manifests.need_set", "Select a saved manifest set.")
            )
        return self._current_id

    def _on_leakage(self) -> None:
        if not self._manifest_store:
            return
        try:
            mid = self._require_current()
        except ManifestStoreError as exc:
            QMessageBox.information(self, "ML-B.1", str(exc))
            return
        worker = ManifestWorker(
            mode=ManifestWorker.MODE_LEAKAGE,
            manifest_store=self._manifest_store,
            manifest_set_id=mid,
            grouping_policy=str(self._policy.currentData() or DEFAULT_GROUPING_POLICY),
        )
        self._start_worker(worker)

    def _on_propose(self) -> None:
        if not self._manifest_store:
            return
        try:
            mid = self._require_current()
        except ManifestStoreError as exc:
            QMessageBox.information(self, "ML-B.1", str(exc))
            return
        worker = ManifestWorker(
            mode=ManifestWorker.MODE_PROPOSE,
            manifest_store=self._manifest_store,
            manifest_set_id=mid,
            seed=int(self._seed.value()),
        )
        self._start_worker(worker)

    def _on_validate(self) -> None:
        if not self._manifest_store:
            return
        try:
            mid = self._require_current()
        except ManifestStoreError as exc:
            QMessageBox.information(self, "ML-B.1", str(exc))
            return
        worker = ManifestWorker(
            mode=ManifestWorker.MODE_VALIDATE,
            manifest_store=self._manifest_store,
            manifest_set_id=mid,
        )
        self._start_worker(worker)

    def _on_freeze(self) -> None:
        if not self._manifest_store:
            return
        try:
            mid = self._require_current()
        except ManifestStoreError as exc:
            QMessageBox.information(self, "ML-B.1", str(exc))
            return
        worker = ManifestWorker(
            mode=ManifestWorker.MODE_FREEZE,
            manifest_store=self._manifest_store,
            manifest_set_id=mid,
        )
        self._start_worker(worker)

    def _on_export(self) -> None:
        if not self._manifest_store:
            return
        try:
            mid = self._require_current()
        except ManifestStoreError as exc:
            QMessageBox.information(self, "ML-B.1", str(exc))
            return
        root = self._manifest_store.root
        before = {p.name for p in root.iterdir()} if root.exists() else set()
        worker = ManifestWorker(
            mode=ManifestWorker.MODE_EXPORT,
            manifest_store=self._manifest_store,
            manifest_set_id=mid,
        )

        def _after(result: object) -> None:
            after = {p.name for p in root.iterdir()} if root.exists() else set()
            created = after - before
            if created:
                _LOG.error("Export created unexpected manifest dirs: %s", created)
            self._mark_success_progress(
                self._t(
                    "manifests.export_ok",
                    "Export written (no new manifest set created)",
                )
                + f": {result}"
            )
            self._refresh_saved()
            self._select_saved(mid)
            if self._current_id:
                self._load_saved(self._current_id)

        self._teardown_worker(cancel=True)
        self._begin_background_op()
        self._active_mode = ManifestWorker.MODE_EXPORT
        self._worker = worker
        worker.progress.connect(self._on_progress)
        worker.finished_ok.connect(_after)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(self._on_worker_finished)
        worker.start()

    def _load_saved(self, manifest_set_id: str) -> None:
        if not self._manifest_store:
            return
        self._current_id = manifest_set_id
        ms = self._manifest_store.load_manifest_set(manifest_set_id)
        items = self._manifest_store.load_items(manifest_set_id)
        groups = self._manifest_store.load_groups(manifest_set_id)
        policy = self._manifest_store.load_policy(manifest_set_id)
        snap: dict[str, Any] = {}
        snap_path = (
            self._manifest_store.path_for(manifest_set_id) / "input_readiness_snapshot.json"
        )
        if snap_path.exists():
            snap = json.loads(snap_path.read_text(encoding="utf-8"))

        self._title.setText(ms.title)
        self._desc.setText(ms.description)
        self._analyst.setText(ms.analyst_id)
        self._seed.setValue(int(ms.seed))
        idx = self._policy.findData(ms.grouping_policy)
        if idx >= 0:
            self._policy.setCurrentIndex(idx)

        lang = self._lang()
        self._lifecycle_state = str(ms.lifecycle_state or "")
        authorizes_mlb = bool(
            snap.get("authorizes_mlb_manifest_planning_only")
            or ms.source_readiness_gate_outcome == GATE_F
        )
        authorizes_train = bool(snap.get("authorizes_training", False))
        self._update_headers(
            manifest_id=ms.manifest_set_id,
            audit_id=ms.source_readiness_audit_id,
            gate=ms.source_readiness_gate_outcome or "",
            contract=ms.task_contract or "",
            authorizes_mlb=authorizes_mlb,
            authorizes_train=authorizes_train,
            authorizes_mlc=False,
            item_count=int(ms.item_count or len(items)),
            group_count=int(ms.group_count or len(groups)),
            lifecycle_state=ms.lifecycle_state,
        )
        self._select_audit(ms.source_readiness_audit_id)

        blockers = list(ms.freeze_blockers or [])
        self._txt_input.setPlainText(
            "\n".join(
                [
                    f"{self._t('manifests.hdr_gate', 'Gate')}: "
                    f"{gate_outcome_label(ms.source_readiness_gate_outcome or '', lang)}",
                    f"{self._t('manifests.hdr_contract', 'Task contract')}: "
                    f"{contract_label(ms.task_contract, lang)}",
                    f"{flag_label('authorizes_mlb_planning', lang)}: "
                    f"{self._yes_no(authorizes_mlb)}",
                    f"{flag_label('authorizes_training', lang)}: "
                    f"{self._yes_no(authorizes_train)}",
                    f"{flag_label('authorizes_mlc', lang)}: {self._yes_no(False)}",
                    "",
                    *self._freeze_status_lines(ms, lang=lang),
                ]
            )
        )

        self._txt_policy.setPlainText(
            "\n".join(
                [
                    f"{self._t('manifests.grouping_policy', 'Grouping policy')}: "
                    f"{policy_label(policy.policy_id, lang)}",
                    f"{self._t('manifests.policy_version', 'Version')}: "
                    f"{policy.policy_version}",
                    f"{self._t('manifests.seed', 'Seed')}: {policy.seed}",
                    f"{self._t('manifests.included_relations', 'Included')}: "
                    f"{', '.join(policy.included_relations)}",
                    f"{self._t('manifests.unavailable_relations', 'Unavailable')}: "
                    f"{', '.join(policy.unavailable_relations)}",
                    f"{self._t('manifests.fallbacks', 'Fallbacks')}: "
                    f"{', '.join(policy.fallback_decisions) or '—'}",
                    f"{self._t('manifests.limitations', 'Limitations')}: "
                    f"{', '.join(format_blockers(policy.limitations, lang)) or '—'}",
                    "",
                    self._t(
                        "manifests.no_frame_split",
                        "No random frame-level assignment is offered.",
                    ),
                ]
            )
        )

        self._tbl_groups.setRowCount(len(groups))
        for r, g in enumerate(groups):
            vals = [
                g.group_id,
                str(len(g.item_identity_keys)),
                role_label(g.role, lang),
                self._yes_no(bool(g.eligible_untouched_holdout)),
                ",".join(g.sequence_ids[:3]),
                ",".join(g.source_dates[:3]),
            ]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                if c == 0:
                    cell.setToolTip(g.group_id)
                self._tbl_groups.setItem(r, c, cell)

        self._tbl_roles.setRowCount(len(items))
        for r, it in enumerate(items):
            target = it.target_label
            if ms.lifecycle_state == "frozen" and it.role == "untouched_holdout":
                target = self._t("manifests.sealed", "(sealed)")
            vals = [
                it.item_id,
                role_label(it.role, lang),
                target,
                it.atomic_group_id,
                contamination_label(str(it.contamination_state or ""), lang),
            ]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(str(v))
                if c in (0, 3):
                    cell.setToolTip(str(v))
                self._tbl_roles.setItem(r, c, cell)

        cov_path = self._manifest_store.path_for(manifest_set_id) / "group_coverage.json"
        if cov_path.exists():
            cov = json.loads(cov_path.read_text(encoding="utf-8"))
            self._txt_coverage.setPlainText(
                self._format_coverage(cov, lang, items=items, groups=groups)
            )
        else:
            self._txt_coverage.setPlainText(
                self._t(
                    "manifests.coverage_pending",
                    "(run proposal or validation)",
                )
            )

        eligible_g = sum(1 for g in groups if g.eligible_untouched_holdout)
        exposed = sum(
            1 for it in items if it.contamination_state == "development_exposed"
        )
        lim_lines = [
            format_blocker(x, lang) for x in (ms.limitations or []) if str(x).strip()
        ]
        self._txt_leakage.setPlainText(
            "\n".join(
                [
                    f"{self._t('manifests.groups_count', 'Groups')}: {len(groups)}",
                    f"{self._t('manifests.eligible_untouched', 'Eligible untouched groups')}: "
                    f"{eligible_g}",
                    f"{self._t('manifests.dev_exposed', 'Development-exposed items')}: "
                    f"{exposed}",
                    "",
                    *lim_lines,
                ]
            )
        )

        holdout_txt = self._holdout_status_lines(ms, items, lang=lang)
        self._txt_holdout.setPlainText("\n".join(holdout_txt))

        integ_path = (
            self._manifest_store.path_for(manifest_set_id) / "integrity_report.json"
        )
        validation_stale = False
        integrity_fail = False
        if ms.lifecycle_state == "validated" and ms.validated_content_hash:
            try:
                cur_hash = self._manifest_store.assignment_content_hash(
                    items, groups, grouping_policy=ms.grouping_policy, seed=ms.seed
                )
                validation_stale = cur_hash != ms.validated_content_hash
            except Exception:  # noqa: BLE001
                validation_stale = True
        if validation_stale:
            self._txt_validation.setPlainText(
                self._t(
                    "manifests.validation_stale",
                    "Manifest changed after the last validation. Run Validate again.",
                )
            )
            self._btn_freeze.setEnabled(False)
        elif integ_path.exists():
            report = json.loads(integ_path.read_text(encoding="utf-8"))
            self._txt_validation.setPlainText(
                self._format_validation(
                    report, lang, lifecycle_state=ms.lifecycle_state
                )
            )
            integrity_fail = not bool(report.get("integrity_ok", report.get("ok")))
            self._btn_freeze.setEnabled(
                bool(report.get("can_freeze"))
                and ms.lifecycle_state in {"validated", "draft"}
                and not integrity_fail
            )
        else:
            self._txt_validation.setPlainText(
                self._t("manifests.validation_pending", "(run Validate)")
            )
            self._btn_freeze.setEnabled(False)

        role_parts = [
            f"{role_label(k, lang)}={v}" for k, v in sorted((ms.role_counts or {}).items())
        ]
        group_role_parts = [
            f"{role_label(k, lang)}={v}"
            for k, v in sorted((ms.group_role_counts or {}).items())
        ]
        integ_line = ""
        if integ_path.exists() and not validation_stale:
            try:
                irep = json.loads(integ_path.read_text(encoding="utf-8"))
                iok = bool(irep.get("integrity_ok", irep.get("ok")))
                integ_line = (
                    f"{self._t('manifests.validation_ok', 'Integrity OK')}: "
                    f"{self._yes_no(iok)}"
                )
            except Exception:  # noqa: BLE001
                integ_line = ""
        self._txt_summary.setPlainText(
            "\n".join(
                [
                    ms.title,
                    f"{self._t('manifests.state', 'State')}: "
                    f"{lifecycle_label(ms.lifecycle_state, lang)}",
                    integ_line,
                    f"{self._t('manifests.protocol', 'Protocol')}: "
                    f"{MANIFEST_PROTOCOL_VERSION}",
                    f"{self._t('manifests.items_groups', 'Items')}: {ms.item_count}; "
                    f"{self._t('manifests.groups_count', 'groups')}: {ms.group_count}",
                    f"{self._t('manifests.roles', 'Roles')}: {', '.join(role_parts)}",
                    f"{self._t('manifests.groups_count', 'Groups')}/role: "
                    f"{', '.join(group_role_parts)}",
                    "",
                    NO_CLAIM_STATEMENT_RU if lang == "ru" else NO_CLAIM_STATEMENT_EN,
                ]
            ).replace("\n\n\n", "\n\n")
        )

        tech_lines = [
            f"manifest_set_id={ms.manifest_set_id}",
            f"parent={ms.parent_manifest_set_id}",
            f"revision={ms.revision_number}",
            f"source_readiness_audit_id={ms.source_readiness_audit_id}",
            f"source_readiness_manifest_hash={ms.source_readiness_manifest_hash}",
            f"source_readiness_gate_outcome={ms.source_readiness_gate_outcome}",
            f"task_contract={ms.task_contract}",
            f"grouping_policy={ms.grouping_policy}",
            f"lifecycle_state={ms.lifecycle_state}",
            f"manifest_set_hash={ms.manifest_set_hash}",
            f"train_hash={ms.train_manifest_hash}",
            f"dev_hash={ms.development_manifest_hash}",
            f"holdout_public_hash={ms.holdout_public_manifest_hash}",
            f"holdout_ref_hash={ms.holdout_reference_labels_hash}",
            f"lock_hash={ms.holdout_lock_hash}",
            f"authorizes_mlb_planning_only={authorizes_mlb}",
            f"authorizes_training={authorizes_train}",
            "freeze_blockers:",
            *[f"  {b}" for b in (blockers or ["(none)"])],
        ]
        if cov_path.exists():
            tech_lines.extend(
                [
                    "",
                    "group_coverage.json:",
                    cov_path.read_text(encoding="utf-8"),
                ]
            )
        if integ_path.exists():
            tech_lines.extend(
                [
                    "",
                    "integrity_report.json:",
                    integ_path.read_text(encoding="utf-8"),
                ]
            )
        self._tech.setPlainText("\n".join(tech_lines))

        self._status.setText(
            f"{lifecycle_label(ms.lifecycle_state, lang)} · {ms.manifest_set_id}"
        )

        alert_parts: list[str] = []
        if ms.lifecycle_state == "frozen" and not self._holdout_lock_is_valid(
            ms.manifest_set_id, ms
        ):
            alert_parts.append(
                self._t(
                    "manifests.holdout_lock_corrupt",
                    "Integrity warning: frozen holdout lock is missing or corrupt. "
                    "Do not treat holdout as reserved.",
                )
            )
        if validation_stale:
            alert_parts.append(
                self._t(
                    "manifests.validation_stale",
                    "Manifest changed after the last validation. Run Validate again.",
                )
            )
        if integrity_fail:
            alert_parts.append(
                self._t(
                    "manifests.integrity_alert",
                    "Integrity validation failed. Freeze is blocked.",
                )
            )
        if ms.source_readiness_gate_outcome and ms.source_readiness_gate_outcome != GATE_F:
            alert_parts.append(
                format_blocker(
                    f"readiness_gate_not_F:outcome={ms.source_readiness_gate_outcome}",
                    lang,
                )
            )
        if blockers and ms.lifecycle_state != "frozen":
            # Surface first few blockers even when context panel is collapsed
            alert_parts.extend(format_blockers(blockers[:4], lang))
        elif blockers and any("freeze" in b or "gate" in b for b in blockers):
            alert_parts.extend(format_blockers(blockers[:3], lang))
        # Deduplicate while preserving order
        seen: set[str] = set()
        uniq: list[str] = []
        for p in alert_parts:
            if p and p not in seen:
                seen.add(p)
                uniq.append(p)
        self._set_alert_visible("\n".join(uniq))
        self._apply_lifecycle_editability(ms)

    def _freeze_status_lines(self, ms: Any, *, lang: str) -> list[str]:
        """Lifecycle-aware freeze status for Input Audit (never stale 'run Validate' when Frozen)."""
        life = str(getattr(ms, "lifecycle_state", "") or "")
        blockers = [b for b in (ms.freeze_blockers or []) if str(b).strip()]
        header = self._t("manifests.freeze_status", "Freeze status")
        if life == "frozen":
            return [
                f"{header}:",
                self._t(
                    "manifests.freeze_status_frozen",
                    "Manifest is already frozen. No further freeze action is required.",
                ),
            ]
        if blockers:
            return [
                self._t("manifests.freeze_blockers", "Freeze blockers") + ":",
                *[f"- {format_blocker(str(b), lang)}" for b in blockers],
            ]
        if life == "validated":
            return [
                f"{header}:",
                self._t(
                    "manifests.freeze_status_validated",
                    "Validation passed. Manifest is eligible for freeze.",
                ),
            ]
        # Draft (or unknown) before a successful validation
        return [
            f"{header}:",
            self._t(
                "manifests.freeze_status_draft",
                "Validation has not been completed.",
            ),
        ]

    def _format_coverage(
        self,
        cov: dict[str, Any],
        lang: str,
        *,
        items: list[Any] | None = None,
        groups: list[Any] | None = None,
    ) -> str:
        """Human-readable Coverage tab. Raw keys/full hashes remain in Technical Details."""
        del groups  # reserved for future group-level detail; item-level is authoritative
        if not isinstance(cov, dict):
            return str(cov)
        role_cov = (
            cov.get("item_level")
            or cov.get("by_role")
            or cov.get("role_coverage")
            or cov
        )
        if not isinstance(role_cov, dict):
            return self._t("manifests.coverage_pending", "(run proposal or validation)")

        role_order = ("train", "development", "untouched_holdout", "excluded")
        lines: list[str] = []
        for role in role_order:
            payload = role_cov.get(role)
            if not isinstance(payload, dict):
                continue
            role_items = [it for it in (items or []) if getattr(it, "role", "") == role]
            n_items = int(payload.get("unique_items") or len(role_items) or 0)
            n_groups = int(payload.get("atomic_groups") or 0)
            seqs = list(payload.get("sequences") or [])
            dates = list(payload.get("acquisition_dates") or [])
            sources = list(payload.get("sources") or [])
            targets = payload.get("target_distribution") or {}
            if not isinstance(targets, dict):
                targets = {}

            # Skip empty excluded unless it has content
            if role == "excluded" and n_items == 0 and n_groups == 0:
                continue

            lines.append(role_label(role, lang))
            lines.append(f"{coverage_field_label('unique_items', lang)}: {n_items}")
            lines.append(f"{coverage_field_label('atomic_groups', lang)}: {n_groups}")
            lines.append(f"{coverage_field_label('sequences', lang)}: {len(seqs)}")
            lines.append(f"{coverage_field_label('acquisition_dates', lang)}: {len(dates)}")
            lines.append(f"{coverage_field_label('sources', lang)}: {len(sources)}")
            if targets:
                class_bits = [
                    f"{cls} ({cnt})" for cls, cnt in sorted(targets.items(), key=lambda x: str(x[0]))
                ]
                lines.append(
                    f"{coverage_field_label('target_classes', lang)}: "
                    + (", ".join(class_bits) if class_bits else "—")
                )
            else:
                lines.append(f"{coverage_field_label('target_classes', lang)}: —")

            # Compact detail table from items when available
            if role_items:
                lines.append("")
                lines.append(
                    f"{coverage_field_label('sequence', lang)} | "
                    f"{coverage_field_label('acquisition_date', lang)} | "
                    f"{coverage_field_label('source', lang)}"
                )
                # One row per unique (sequence, date, source) to avoid noise
                seen_rows: set[tuple[str, str, str]] = set()
                for it in role_items:
                    seq = str(getattr(it, "sequence_id", "") or "—")
                    date = str(getattr(it, "source_date", "") or "—")
                    sha = str(getattr(it, "source_sha256", "") or "")
                    key = (seq, date, sha)
                    if key in seen_rows:
                        continue
                    seen_rows.add(key)
                    lines.append(f"{seq} | {date} | {short_source_id(sha)}")
            elif seqs or dates or sources:
                # Fallback without item rows: list shortened sources / dates
                if dates:
                    lines.append(
                        f"{coverage_field_label('acquisition_dates', lang)}: "
                        + ", ".join(str(d) for d in dates)
                    )
                if sources:
                    lines.append(
                        f"{coverage_field_label('sources', lang)}: "
                        + ", ".join(short_source_id(s) for s in sources)
                    )

            if targets:
                lines.append("")
                lines.append(
                    f"{coverage_field_label('target_class', lang)} | "
                    f"{coverage_field_label('unique_items', lang)}"
                )
                for cls, cnt in sorted(targets.items(), key=lambda x: str(x[0])):
                    lines.append(f"{cls} | {cnt}")

            lines.append("")
            lines.append("─" * 40)
            lines.append("")

        text = "\n".join(lines).rstrip("─\n ").rstrip()
        if not text:
            return self._t("manifests.coverage_pending", "(run proposal or validation)")
        return text

    def _format_validation(
        self,
        report: dict[str, Any],
        lang: str,
        *,
        lifecycle_state: str = "",
    ) -> str:
        lines: list[str] = []
        ok = report.get("integrity_ok", report.get("ok"))
        if ok is not None:
            label = (
                self._t("manifests.integrity_pass", "PASS")
                if ok
                else self._t("manifests.integrity_fail", "FAIL")
            )
            lines.append(
                f"{self._t('manifests.validation_ok', 'Integrity OK')}: "
                f"{self._yes_no(bool(ok))} ({label})"
            )
        life = lifecycle_state or str(report.get("lifecycle_state") or "")
        lines.append(
            f"{self._t('manifests.state', 'State')}: {lifecycle_label(life, lang)}"
        )
        if report.get("holdout_item_count") is not None:
            items_n = report.get("holdout_item_count")
            groups_n = report.get("holdout_group_count")
            if life == "frozen":
                # Prefer reserved wording; if lock missing, fail closed via holdout tab/alert.
                lock_ok = True
                if self._current_id and self._manifest_store:
                    try:
                        ms = self._manifest_store.load_manifest_set(self._current_id)
                        lock_ok = self._holdout_lock_is_valid(self._current_id, ms)
                    except Exception:  # noqa: BLE001
                        lock_ok = False
                if lock_ok:
                    lines.append(
                        self._t(
                            "manifests.holdout_reserved",
                            "Holdout reserved: items={items}, groups={groups}",
                        ).format(items=items_n, groups=groups_n)
                    )
                else:
                    lines.append(
                        self._t(
                            "manifests.holdout_lock_corrupt",
                            "Integrity warning: frozen holdout lock is missing or corrupt. "
                            "Do not treat holdout as reserved.",
                        )
                    )
            else:
                lines.append(
                    self._t(
                        "manifests.holdout_draft",
                        "Draft holdout assignment (not reserved): "
                        "items={items}, groups={groups}",
                    ).format(items=items_n, groups=groups_n)
                )
        errors = (
            report.get("freeze_blockers")
            or report.get("blockers")
            or report.get("errors")
            or []
        )
        if isinstance(errors, list) and errors:
            lines.append(self._t("manifests.freeze_blockers", "Freeze blockers") + ":")
            for e in errors:
                lines.append(f"- {format_blocker(str(e), lang)}")
        warnings = report.get("warnings") or []
        if isinstance(warnings, list) and warnings:
            lines.append(self._t("manifests.warnings", "Warnings") + ":")
            for w in warnings:
                lines.append(f"- {format_blocker(str(w), lang)}")
        if not lines:
            lines.append(self._t("manifests.validation_pending", "(run Validate)"))
        return "\n".join(lines)
