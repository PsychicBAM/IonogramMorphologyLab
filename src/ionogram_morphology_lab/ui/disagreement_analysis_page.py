"""Disagreement Analysis workspace (Phase 4C.4a) — descriptive, shadow-only."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
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
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.morphology_disagreement_analysis.analytics import (
    descriptive_dashboard,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.constants import (
    DECISION_OUTCOMES,
    HYPOTHESIS_CATEGORIES,
    PILOT_DESIGNATION_EN,
    PILOT_DESIGNATION_RU,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.decision_gate import (
    outcome_labels,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.models import (
    AnalystHypothesis,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.store import (
    AnalysisStoreError,
    MorphologyDisagreementAnalysisStore,
    propose_holdout_from_rows,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import display_label
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore

_LOG = logging.getLogger(__name__)


class FreezeAnalysisWorker(QThread):
    progress = Signal(int, str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        analysis_store: MorphologyDisagreementAnalysisStore,
        corpus_store: MorphologyReviewCorpusStore,
        analysis_id: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._analysis_store = analysis_store
        self._corpus_store = corpus_store
        self._analysis_id = analysis_id
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            manifest = self._analysis_store.freeze_snapshot(
                self._analysis_id,
                self._corpus_store,
                progress_cb=lambda pct, msg: self.progress.emit(int(pct), str(msg)),
                cancel_cb=lambda: self._cancel,
            )
            self.finished_ok.emit(manifest)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DisagreementAnalysisPage(QWidget):
    def __init__(self, session, i18n, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self._analysis_store: MorphologyDisagreementAnalysisStore | None = None
        self._corpus_store: MorphologyReviewCorpusStore | None = None
        self._current_analysis_id = ""
        self._rows: list[Any] = []
        self._worker: FreezeAnalysisWorker | None = None

        root = QVBoxLayout(self)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        root.addWidget(self.banner)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self._build_select_tab()
        self._build_dashboard_tab()
        self._build_cases_tab()
        self._build_hypotheses_tab()
        self._build_decision_tab()

        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.btn_cancel = QPushButton()
        self.btn_cancel.clicked.connect(self._cancel_worker)
        self.status = QLabel()
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.btn_cancel)
        bottom.addWidget(self.status, 2)
        root.addLayout(bottom)

        self.retranslate()
        try:
            self.session.project_changed.connect(self._on_project_changed)
        except Exception:
            pass

    def t(self, key: str, **kwargs) -> str:
        try:
            return self.i18n.t(key, **kwargs)
        except Exception:
            return key

    def project_root(self) -> Path | None:
        proj = getattr(self.session, "project", None)
        if proj is None:
            return None
        path = getattr(proj, "path", None) or getattr(proj, "root", None)
        return Path(path) if path else None

    def _ensure_stores(self) -> bool:
        root = self.project_root()
        if root is None:
            return False
        self._analysis_store = MorphologyDisagreementAnalysisStore(root)
        self._corpus_store = MorphologyReviewCorpusStore(root)
        return True

    def _on_project_changed(self, *_args) -> None:
        self._analysis_store = None
        self._corpus_store = None
        self._current_analysis_id = ""
        self._rows = []
        self.refresh_lists()

    def _build_select_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        split = QSplitter()
        left = QWidget()
        ll = QVBoxLayout(left)
        self.lbl_cohorts = QLabel()
        self.cohort_list = QListWidget()
        self.cohort_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        ll.addWidget(self.lbl_cohorts)
        ll.addWidget(self.cohort_list)
        right = QWidget()
        rl = QVBoxLayout(right)
        self.lbl_analyses = QLabel()
        self.analysis_list = QListWidget()
        self.analysis_list.currentItemChanged.connect(self._on_analysis_selected)
        rl.addWidget(self.lbl_analyses)
        rl.addWidget(self.analysis_list)
        split.addWidget(left)
        split.addWidget(right)
        lay.addWidget(split, 1)

        form = QFormLayout()
        self.title_edit = QLineEdit()
        self.desc_edit = QLineEdit()
        self.analyst_edit = QLineEdit()
        form.addRow(QLabel(), self.title_edit)
        self.lbl_title = form.labelForField(self.title_edit)
        form.addRow(QLabel(), self.desc_edit)
        self.lbl_desc = form.labelForField(self.desc_edit)
        form.addRow(QLabel(), self.analyst_edit)
        self.lbl_analyst = form.labelForField(self.analyst_edit)
        lay.addLayout(form)

        actions = QHBoxLayout()
        self.btn_refresh = QPushButton()
        self.btn_preview = QPushButton()
        self.btn_freeze = QPushButton()
        self.btn_export = QPushButton()
        self.btn_refresh.clicked.connect(self.refresh_lists)
        self.btn_preview.clicked.connect(self._preview)
        self.btn_freeze.clicked.connect(self._freeze)
        self.btn_export.clicked.connect(self._export)
        for b in (self.btn_refresh, self.btn_preview, self.btn_freeze, self.btn_export):
            actions.addWidget(b)
        lay.addLayout(actions)

        self.preview_box = QTextEdit()
        self.preview_box.setReadOnly(True)
        lay.addWidget(self.preview_box, 1)
        self.tabs.addTab(w, "")

    def _build_dashboard_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.small_sample_lbl = QLabel()
        self.small_sample_lbl.setStyleSheet("color: #8a5a00; font-weight: 600;")
        lay.addWidget(self.small_sample_lbl)
        self.dash_text = QTextEdit()
        self.dash_text.setReadOnly(True)
        lay.addWidget(self.dash_text, 1)
        self.matrix_table = QTableWidget()
        lay.addWidget(self.matrix_table, 1)
        filt = QHBoxLayout()
        self.filter_expert = QComboBox()
        self.filter_expert.currentIndexChanged.connect(self._apply_filters)
        filt.addWidget(self.filter_expert)
        lay.addLayout(filt)
        self.tabs.addTab(w, "")

    def _build_cases_tab(self) -> None:
        w = QWidget()
        lay = QHBoxLayout(w)
        self.case_list = QListWidget()
        self.case_list.currentItemChanged.connect(self._on_case_selected)
        self.case_detail = QTextEdit()
        self.case_detail.setReadOnly(True)
        lay.addWidget(self.case_list, 1)
        lay.addWidget(self.case_detail, 2)
        self.tabs.addTab(w, "")

    def _build_hypotheses_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QFormLayout()
        self.hyp_category = QComboBox()
        for c in sorted(HYPOTHESIS_CATEGORIES):
            self.hyp_category.addItem(c, c)
        self.hyp_confidence = QComboBox()
        for c in ("low", "medium", "high"):
            self.hyp_confidence.addItem(c, c)
        self.hyp_note = QTextEdit()
        self.hyp_note.setMaximumHeight(100)
        form.addRow(self.hyp_category)
        form.addRow(self.hyp_confidence)
        form.addRow(self.hyp_note)
        lay.addLayout(form)
        self.btn_add_hyp = QPushButton()
        self.btn_add_hyp.clicked.connect(self._add_hypothesis)
        lay.addWidget(self.btn_add_hyp)
        self.hyp_history = QTextEdit()
        self.hyp_history.setReadOnly(True)
        lay.addWidget(self.hyp_history, 1)
        self.tabs.addTab(w, "")

    def _build_decision_tab(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.decision_outcome = QComboBox()
        for code in sorted(DECISION_OUTCOMES):
            self.decision_outcome.addItem(code, code)
        self.decision_rationale = QTextEdit()
        self.decision_alt = QTextEdit()
        self.decision_alt.setMaximumHeight(80)
        self.btn_holdout = QPushButton()
        self.btn_record_decision = QPushButton()
        self.btn_holdout.clicked.connect(self._make_holdout_stub)
        self.btn_record_decision.clicked.connect(self._record_decision)
        lay.addWidget(self.decision_outcome)
        lay.addWidget(self.decision_rationale, 1)
        lay.addWidget(self.decision_alt)
        row = QHBoxLayout()
        row.addWidget(self.btn_holdout)
        row.addWidget(self.btn_record_decision)
        lay.addLayout(row)
        self.decision_status = QLabel()
        lay.addWidget(self.decision_status)
        self.tabs.addTab(w, "")

    def retranslate(self) -> None:
        ru = getattr(self.i18n, "language", "en") == "ru"
        self.banner.setText(PILOT_DESIGNATION_RU if ru else PILOT_DESIGNATION_EN)
        self.tabs.setTabText(0, self.t("disagreement.tab_select"))
        self.tabs.setTabText(1, self.t("disagreement.tab_dashboard"))
        self.tabs.setTabText(2, self.t("disagreement.tab_cases"))
        self.tabs.setTabText(3, self.t("disagreement.tab_hypotheses"))
        self.tabs.setTabText(4, self.t("disagreement.tab_decision"))
        self.lbl_cohorts.setText(self.t("disagreement.select_cohorts"))
        self.lbl_analyses.setText(self.t("disagreement.saved_analyses"))
        self.title_edit.setPlaceholderText(self.t("disagreement.title"))
        self.desc_edit.setPlaceholderText(self.t("disagreement.description"))
        self.analyst_edit.setPlaceholderText(self.t("disagreement.analyst_id"))
        self.btn_refresh.setText(self.t("disagreement.refresh"))
        self.btn_preview.setText(self.t("disagreement.preview"))
        self.btn_freeze.setText(self.t("disagreement.freeze"))
        self.btn_export.setText(self.t("disagreement.export"))
        self.btn_cancel.setText(self.t("disagreement.cancel"))
        self.btn_add_hyp.setText(self.t("disagreement.add_hypothesis"))
        self.btn_holdout.setText(self.t("disagreement.create_holdout"))
        self.btn_record_decision.setText(self.t("disagreement.record_decision"))
        labels = outcome_labels("ru" if ru else "en")
        cur = self.decision_outcome.currentData()
        self.decision_outcome.clear()
        for code in sorted(DECISION_OUTCOMES):
            self.decision_outcome.addItem(labels.get(code, code), code)
        if cur:
            idx = self.decision_outcome.findData(cur)
            if idx >= 0:
                self.decision_outcome.setCurrentIndex(idx)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh_lists()

    def refresh_lists(self) -> None:
        self.cohort_list.clear()
        self.analysis_list.clear()
        if not self._ensure_stores():
            self.status.setText(self.t("disagreement.no_project"))
            return
        assert self._corpus_store is not None
        assert self._analysis_store is not None
        try:
            for cid in self._corpus_store.list_cohorts():
                try:
                    m = self._corpus_store.load_manifest(cid)
                    label = f"{cid} ({'frozen' if m.frozen else 'draft'})"
                except Exception:
                    label = cid
                item = QListWidgetItem(label)
                item.setData(256, cid)
                self.cohort_list.addItem(item)
        except Exception as exc:
            _LOG.exception("list cohorts")
            self.status.setText(str(exc))
        for m in self._analysis_store.list_analyses():
            item = QListWidgetItem(f"{m.title} [{m.lifecycle_state}]")
            item.setData(256, m.analysis_id)
            self.analysis_list.addItem(item)

    def _selected_cohort_ids(self) -> list[str]:
        out = []
        for it in self.cohort_list.selectedItems():
            cid = it.data(256)
            if cid:
                out.append(str(cid))
        return out

    def _preview(self) -> None:
        if not self._ensure_stores():
            return
        ids = self._selected_cohort_ids()
        if not ids:
            QMessageBox.information(self, "IML", self.t("disagreement.select_cohorts"))
            return
        try:
            prev = self._analysis_store.preview(self._corpus_store, ids)
            dash = prev["dashboard"]
            lines = [
                f"items={dash['selected_unique_items']}",
                f"comparable={dash['eligible_comparable_items']}",
                f"matches={dash['exact_label_matches']}",
                f"disagreements={dash['morphology_disagreements']}",
                f"exclusions={dash.get('exclusion_counts')}",
                f"warnings={prev.get('warnings')}",
                f"compat={prev.get('compatibility')}",
            ]
            if dash.get("small_sample"):
                ru = getattr(self.i18n, "language", "en") == "ru"
                lines.append(
                    dash["small_sample_warning_ru"]
                    if ru
                    else dash["small_sample_warning_en"]
                )
            self.preview_box.setPlainText("\n".join(lines))
            self._rows = prev["rows"]
            self.status.setText(self.t("disagreement.preview_ready"))
        except Exception as exc:
            QMessageBox.warning(self, "IML", self._user_error(exc))

    def _freeze(self) -> None:
        if not self._ensure_stores():
            return
        ids = self._selected_cohort_ids()
        if not ids:
            QMessageBox.information(self, "IML", self.t("disagreement.select_cohorts"))
            return
        title = self.title_edit.text().strip() or "Disagreement analysis"
        try:
            draft = self._analysis_store.create_draft(
                title=title,
                description=self.desc_edit.text().strip(),
                cohort_ids=ids,
                analyst_id=self.analyst_edit.text().strip() or "analyst",
            )
        except Exception as exc:
            QMessageBox.warning(self, "IML", self._user_error(exc))
            return
        self._current_analysis_id = draft.analysis_id
        self.progress.setValue(0)
        self._worker = FreezeAnalysisWorker(
            self._analysis_store, self._corpus_store, draft.analysis_id, self
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_frozen)
        self._worker.failed.connect(self._on_freeze_failed)
        self._worker.start()
        self.status.setText(self.t("disagreement.freezing"))

    def _cancel_worker(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.status.setText(self.t("disagreement.cancel_requested"))

    def _on_progress(self, pct: int, msg: str) -> None:
        self.progress.setValue(pct)
        self.status.setText(msg)

    def _on_frozen(self, manifest) -> None:
        self.progress.setValue(100)
        self._current_analysis_id = manifest.analysis_id
        self.status.setText(self.t("disagreement.frozen_ok"))
        self.refresh_lists()
        self._load_analysis(manifest.analysis_id)
        self.tabs.setCurrentIndex(1)

    def _on_freeze_failed(self, message: str) -> None:
        self.status.setText(self.t("disagreement.freeze_failed"))
        QMessageBox.warning(self, "IML", message)

    def _on_analysis_selected(self, cur, _prev) -> None:
        if cur is None:
            return
        aid = cur.data(256)
        if aid:
            self._load_analysis(str(aid))

    def _load_analysis(self, analysis_id: str) -> None:
        if not self._ensure_stores():
            return
        self._current_analysis_id = analysis_id
        self._rows = self._analysis_store.load_snapshot_rows(analysis_id)
        self._render_dashboard()
        self._render_cases()
        self._render_hypotheses()
        decision = self._analysis_store.load_decision(analysis_id)
        if decision:
            self.decision_status.setText(
                f"{decision.outcome} @ {decision.created_at}"
            )

    def _apply_filters(self) -> None:
        self._render_dashboard()

    def _render_dashboard(self) -> None:
        filt: dict[str, Any] = {}
        expert = self.filter_expert.currentData()
        if expert:
            filt["expert_morphology"] = expert
        # populate filter choices once
        if self.filter_expert.count() <= 1:
            self.filter_expert.blockSignals(True)
            self.filter_expert.clear()
            self.filter_expert.addItem(self.t("disagreement.filter_all"), "")
            morphs = sorted({r.expert_morphology for r in self._rows if r.expert_morphology})
            lang = getattr(self.i18n, "language", "en")
            for m in morphs:
                self.filter_expert.addItem(display_label(m, lang), m)
            self.filter_expert.blockSignals(False)

        dash = descriptive_dashboard(self._rows, filters=filt or None)
        ru = getattr(self.i18n, "language", "en") == "ru"
        self.small_sample_lbl.setText(
            dash["small_sample_warning_ru"]
            if dash.get("small_sample") and ru
            else dash.get("small_sample_warning_en") or ""
        )
        lines = [
            f"{self.t('disagreement.den_selected')}: {dash['selected_unique_items']}",
            f"{self.t('disagreement.den_comparable')}: {dash['eligible_comparable_items']}",
            f"{self.t('disagreement.den_matches')}: {dash['exact_label_matches']}",
            f"{self.t('disagreement.den_disagreements')}: {dash['morphology_disagreements']}",
            f"{self.t('disagreement.den_expert_abs')}: {dash['expert_abstentions']}",
            f"{self.t('disagreement.den_cand_abs')}: {dash['candidate_abstentions']}",
            f"{self.t('disagreement.den_both_abs')}: {dash['both_abstained']}",
            f"{self.t('disagreement.den_noncomp')}: {dash['non_comparable_items']}",
            f"{self.t('disagreement.den_unavail')}: {dash['unavailable_items']}",
            "",
            self.t("disagreement.matrix_title"),
            str(dash.get("expert_to_candidate_transitions")),
        ]
        self.dash_text.setPlainText("\n".join(lines))
        matrix = dash.get("transition_matrix") or {}
        experts = sorted(matrix.keys())
        cands: set[str] = set()
        for row in matrix.values():
            cands.update(row.keys())
        cands_l = sorted(cands)
        self.matrix_table.clear()
        self.matrix_table.setRowCount(len(experts))
        self.matrix_table.setColumnCount(len(cands_l))
        self.matrix_table.setHorizontalHeaderLabels(cands_l)
        self.matrix_table.setVerticalHeaderLabels(experts)
        for i, h in enumerate(experts):
            for j, c in enumerate(cands_l):
                self.matrix_table.setItem(
                    i, j, QTableWidgetItem(str(matrix.get(h, {}).get(c, 0)))
                )

    def _render_cases(self) -> None:
        self.case_list.clear()
        lang = getattr(self.i18n, "language", "en")
        for r in self._rows:
            if r.eligibility_bucket != "eligible_comparable" and r.comparison_status != "morphology_disagreement":
                # still list disagreements and abstentions
                pass
            title = (
                f"{display_label(r.expert_morphology, lang)} → "
                f"{display_label(r.candidate_state, lang)} "
                f"[{r.comparison_status}] {r.source_display_name}#{r.frame_index}"
            )
            item = QListWidgetItem(title)
            item.setData(256, f"{r.cohort_id}:{r.item_id}")
            self.case_list.addItem(item)

    def _on_case_selected(self, cur, _prev) -> None:
        if cur is None:
            return
        key = str(cur.data(256) or "")
        row = next((r for r in self._rows if f"{r.cohort_id}:{r.item_id}" == key), None)
        if row is None:
            return
        tech = (
            f"cohort={row.cohort_id}\n"
            f"item={row.item_id}\n"
            f"review={row.expert_review_id}\n"
            f"comparison={row.comparison_id}\n"
            f"snapshot={row.candidate_snapshot_hash}\n"
            f"engine={row.candidate_engine_version}\n"
            f"ruleset={row.candidate_ruleset_id}\n"
        )
        body = (
            f"source={row.source_display_name}\n"
            f"sha={row.source_sha256}\n"
            f"frame={row.frame_index} time={row.frame_time}\n"
            f"expert={row.expert_morphology}\n"
            f"candidate={row.candidate_state}\n"
            f"status={row.comparison_status}\n"
            f"assessability={row.expert_assessability}\n"
            f"interference={row.expert_interference}\n"
            f"support={row.candidate_strength}\n"
            f"second={row.second_morphology or '—'}\n"
            f"comment={row.expert_comment}\n"
            f"post_note={row.post_comparison_note}\n"
            f"\n--- {self.t('disagreement.technical_details')} ---\n{tech}"
        )
        self.case_detail.setPlainText(body)

    def _render_hypotheses(self) -> None:
        if not self._current_analysis_id or not self._analysis_store:
            self.hyp_history.clear()
            return
        notes = self._analysis_store.load_hypotheses(self._current_analysis_id)
        self.hyp_history.setPlainText(
            "\n\n".join(
                f"[{n.created_at}] {n.category}/{n.confidence}\n{n.note}" for n in notes
            )
        )

    def _add_hypothesis(self) -> None:
        if not self._ensure_stores() or not self._current_analysis_id:
            return
        before_counts = descriptive_dashboard(self._rows)
        note = AnalystHypothesis.create(
            analysis_id=self._current_analysis_id,
            category=str(self.hyp_category.currentData()),
            analyst_id=self.analyst_edit.text().strip() or "analyst",
            note=self.hyp_note.toPlainText().strip() or "(empty)",
            confidence=str(self.hyp_confidence.currentData()),
        )
        self._analysis_store.append_hypothesis(note)
        after_counts = descriptive_dashboard(self._rows)
        assert before_counts["exact_label_matches"] == after_counts["exact_label_matches"]
        self.hyp_note.clear()
        self._render_hypotheses()
        self.status.setText(self.t("disagreement.hypothesis_saved"))

    def _make_holdout_stub(self) -> None:
        if not self._ensure_stores() or not self._current_analysis_id:
            return
        # Prefer empty holdout keys that do not overlap exposed items → will error;
        # for UI smoke, create a plan from zero keys to show rejection path when
        # selecting exposed keys. Here we intentionally try exposed keys to demo warning.
        keys = [f"{r.cohort_id}:{r.item_id}" for r in self._rows[:1]]
        plan = propose_holdout_from_rows(
            self._analysis_store,
            analysis_id=self._current_analysis_id,
            title="Pilot holdout plan",
            holdout_case_keys=keys,
        )
        msg = (
            self.t("disagreement.holdout_errors")
            + ": "
            + ", ".join(plan.overlap_errors or plan.overlap_warnings or ["ok"])
        )
        self.decision_status.setText(msg)

    def _record_decision(self) -> None:
        if not self._ensure_stores() or not self._current_analysis_id:
            return
        outcome = str(self.decision_outcome.currentData())
        alts = [
            ln.strip()
            for ln in self.decision_alt.toPlainText().splitlines()
            if ln.strip()
        ] or ["Alternative explanations not provided beyond descriptive limits."]
        try:
            # Outcome F needs a holdout plan without overlap errors — create empty-holdout
            # untouched plan only when user selected non-exposed keys; otherwise block.
            if outcome == "F_candidate_ruleset_hypothesis_justified":
                plan = self._analysis_store.load_holdout_plan(self._current_analysis_id)
                if plan is None or plan.overlap_errors:
                    raise AnalysisStoreError(self.t("disagreement.outcome_f_needs_holdout"))
            rec = self._analysis_store.record_decision(
                analysis_id=self._current_analysis_id,
                outcome=outcome,
                analyst_id=self.analyst_edit.text().strip() or "analyst",
                analyst_rationale=self.decision_rationale.toPlainText().strip()
                or "See analysis snapshot.",
                alternative_explanations=alts,
            )
            self.decision_status.setText(f"OK: {rec.outcome}")
        except Exception as exc:
            QMessageBox.warning(self, "IML", self._user_error(exc))

    def _export(self) -> None:
        if not self._ensure_stores() or not self._current_analysis_id:
            return
        root = self.project_root()
        dest = Path(root) / "review_dataset" / "exports" / self._current_analysis_id
        try:
            self._analysis_store.export_bundle(self._current_analysis_id, dest)
            self.status.setText(self.t("disagreement.export_ok"))
        except Exception as exc:
            QMessageBox.warning(self, "IML", self._user_error(exc))

    def _user_error(self, exc: Exception) -> str:
        # Never dump raw technical traces as primary message.
        msg = str(exc).strip() or self.t("disagreement.generic_error")
        if len(msg) > 400:
            msg = msg[:400] + "…"
        return msg
