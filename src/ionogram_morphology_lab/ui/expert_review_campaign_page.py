"""Expert Review Campaigns — planning, dashboard, resume (Phase 4C.3a.1)."""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from ionogram_morphology_lab.morphology_review_campaign.analytics import (
    campaign_descriptive_summary,
    explain_metrics_unavailable,
)
from ionogram_morphology_lab.morphology_review_campaign.constants import (
    CAMPAIGN_DESIGNATION_EN,
    CAMPAIGN_DESIGNATION_RU,
)
from ionogram_morphology_lab.morphology_review_campaign.exports import (
    export_campaign_readiness,
)
from ionogram_morphology_lab.morphology_review_campaign.models import (
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.progress import campaign_progress
from ionogram_morphology_lab.morphology_review_campaign.project_sources import (
    RegisteredProjectSource,
    format_date_display,
    list_registered_project_sources,
    localize_campaign_state,
    localize_validation_issue,
    validate_selected_sources,
)
from ionogram_morphology_lab.morphology_review_campaign.repair import (
    inspect_campaign_source_bindings,
    repair_campaign_source_mapping,
)
from ionogram_morphology_lab.morphology_review_campaign.resume import resume_work
from ionogram_morphology_lab.morphology_review_campaign.store import (
    CampaignError,
    MorphologyReviewCampaignStore,
)
from ionogram_morphology_lab.ui.active_source_authority import (
    active_source_label,
    authoritative_active_source,
)
from ionogram_morphology_lab.ui.theme import resolve_theme_name, source_card_tokens

_LOG = logging.getLogger(__name__)
_SHA_RE = re.compile(r"^[0-9a-f]{64}$", re.I)

_METHOD_CODES = (
    "deterministic_random",
    "all_eligible",
    "stratified",
    "manual",
)


def _wizard_stylesheet(theme: str | None = None) -> str:
    """Theme-aware wizard QSS — never pale text on a white Aero background."""
    t = source_card_tokens(resolve_theme_name(theme))
    return f"""
    QWizard, QWizardPage {{
        background-color: {t['bg']};
        color: {t['text']};
    }}
    QWizard QWidget {{
        color: {t['text']};
        background-color: {t['bg']};
    }}
    QLabel {{
        color: {t['text']};
        background: transparent;
    }}
    QLineEdit, QSpinBox, QComboBox, QTextEdit, QTableWidget, QAbstractItemView {{
        background-color: {t['bg_alt']};
        color: {t['text']};
        border: 1px solid {t['border']};
        selection-background-color: {t['accent']};
        selection-color: #ffffff;
    }}
    QHeaderView::section {{
        background-color: {t['bg']};
        color: {t['text']};
        border: 1px solid {t['border']};
        padding: 4px;
        font-weight: 600;
    }}
    QTableWidget {{
        gridline-color: {t['border']};
        outline: none;
    }}
    QTableWidget::item {{
        color: {t['text']};
        background-color: {t['bg_alt']};
    }}
    QTableWidget::item:selected {{
        background-color: {t['accent']};
        color: #ffffff;
    }}
    QPushButton {{
        background-color: {t['btn_bg']};
        color: {t['btn_fg']};
        border: 1px solid {t['btn_border']};
        padding: 6px 12px;
        min-height: 24px;
    }}
    QPushButton:hover {{ background-color: {t['btn_hover']}; }}
    QPushButton:pressed {{ background-color: {t['btn_pressed']}; }}
    QPushButton:disabled {{
        background-color: {t['btn_disabled_bg']};
        color: {t['btn_disabled_fg']};
    }}
    QCheckBox {{ color: {t['text']}; background: transparent; }}
    QGroupBox {{ color: {t['text']}; border: 1px solid {t['border']}; }}
    """


class ExpertReviewCampaignPage(QWidget):
    """Campaign list + dashboard coordinating existing corpus workflows."""

    def __init__(self, session: Any, i18n: Any, *, main_window: Any = None) -> None:
        super().__init__()
        self.session = session
        self.i18n = i18n
        self._main_window = main_window
        self._campaign_id: str | None = None
        self._build_ui()
        self._connect_session_events()
        self.retranslate()

    def t(self, key: str, default: str | None = None) -> str:
        try:
            return self.i18n.t(key, default=default) if default is not None else self.i18n.t(key)
        except Exception:
            return default if default is not None else key

    def _lang(self) -> str:
        lang = getattr(self.i18n, "language", None) or getattr(self.i18n, "lang", "en") or "en"
        return "ru" if str(lang).startswith("ru") else "en"

    def project_root(self) -> Path | None:
        proj = getattr(self.session, "project", None)
        if proj is None:
            return None
        root = getattr(proj, "root", None) or getattr(proj, "path", None)
        return Path(root) if root else None

    def _store(self) -> MorphologyReviewCampaignStore | None:
        root = self.project_root()
        if root is None:
            return None
        return MorphologyReviewCampaignStore(root)

    def _connect_session_events(self) -> None:
        ev = getattr(self.session, "events", None)
        if ev is None:
            return
        for sig_name in ("project_changed", "active_mat_changed", "inventory_changed"):
            sig = getattr(ev, sig_name, None)
            if sig is not None:
                sig.connect(self._on_session_context_changed)

    def _on_session_context_changed(self) -> None:
        self._campaign_id = None
        self.refresh()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setObjectName("campaignTitle")
        self.title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(self.title)

        self.active_source_lbl = QLabel()
        self.active_source_lbl.setWordWrap(True)
        self.active_source_lbl.setObjectName("campaignActiveSource")
        root.addWidget(self.active_source_lbl)

        self.designation = QLabel()
        self.designation.setWordWrap(True)
        self.designation.setObjectName("campaignDesignation")
        root.addWidget(self.designation)

        bar = QHBoxLayout()
        self.btn_new = QPushButton()
        self.btn_new.clicked.connect(self._open_wizard)
        self.btn_repair = QPushButton()
        self.btn_repair.clicked.connect(self._repair_source_mapping)
        self.btn_resume = QPushButton()
        self.btn_resume.clicked.connect(self._resume_work)
        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self._export_readiness)
        self.btn_open_corpus = QPushButton()
        self.btn_open_corpus.clicked.connect(self._open_corpora)
        self.btn_refresh = QPushButton()
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_advanced = QPushButton()
        adv_menu = QMenu(self.btn_advanced)
        self.act_import_manifest = adv_menu.addAction("")
        self.act_import_manifest.triggered.connect(self._import_manifest)
        self.btn_advanced.setMenu(adv_menu)
        for b in (
            self.btn_new,
            self.btn_repair,
            self.btn_resume,
            self.btn_export,
            self.btn_open_corpus,
            self.btn_refresh,
            self.btn_advanced,
        ):
            bar.addWidget(b)
        bar.addStretch(1)
        root.addLayout(bar)

        body = QHBoxLayout()
        left = QVBoxLayout()
        self.list_label = QLabel()
        left.addWidget(self.list_label)
        self.campaign_table = QTableWidget(0, 3)
        self.campaign_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.campaign_table.setSelectionMode(QTableWidget.SingleSelection)
        self.campaign_table.itemSelectionChanged.connect(self._on_select_campaign)
        self.campaign_table.cellDoubleClicked.connect(lambda *_: self._resume_work())
        left.addWidget(self.campaign_table, 1)
        body.addLayout(left, 1)

        self.dashboard = QGroupBox()
        self.dashboard.setMinimumWidth(680)
        self.dashboard.setMaximumWidth(960)
        dash_l = QVBoxLayout(self.dashboard)
        self.dash_title = QLabel()
        self.dash_title.setStyleSheet("font-weight: 700; font-size: 15px;")
        dash_l.addWidget(self.dash_title)
        self.card_progress = QLabel()
        self.card_progress.setWordWrap(True)
        self.card_progress.setObjectName("campaignProgressCard")
        dash_l.addWidget(self.card_progress)
        self.card_current = QLabel()
        self.card_current.setWordWrap(True)
        dash_l.addWidget(self.card_current)
        self.card_optional = QLabel()
        self.card_optional.setWordWrap(True)
        dash_l.addWidget(self.card_optional)
        self.card_science = QLabel()
        self.card_science.setWordWrap(True)
        dash_l.addWidget(self.card_science)
        self.summary_view = QTextEdit()
        self.summary_view.setReadOnly(True)
        dash_l.addWidget(self.summary_view, 1)
        body.addWidget(self.dashboard, 2)
        root.addLayout(body, 1)

        self.queue_label = QLabel()
        root.addWidget(self.queue_label)
        self.queue = QTableWidget(0, 10)
        self.queue.setMinimumHeight(160)
        root.addWidget(self.queue)

    def _refresh_active_source_label(self) -> None:
        auth = authoritative_active_source(self.session)
        text = active_source_label(auth, self._lang())
        if auth.short_sha:
            text += f" | SHA {auth.short_sha}"
        self.active_source_lbl.setText(text)

    def retranslate(self) -> None:
        ru = self._lang() == "ru"
        self.title.setText(
            self.t("campaign.title", "Expert Review Campaigns" if not ru else "Кампании экспертной оценки")
        )
        self._refresh_active_source_label()
        self.designation.setText(CAMPAIGN_DESIGNATION_RU if ru else CAMPAIGN_DESIGNATION_EN)
        self.list_label.setText(self.t("campaign.list", "Campaigns" if not ru else "Кампании"))
        self.btn_new.setText(self.t("campaign.new", "New Expert Review Campaign" if not ru else "Новая кампания экспертной оценки"))
        self.btn_repair.setText(self.t("campaign.repair_sources", "Repair Source Mapping" if not ru else "Исправить привязку источников"))
        self.btn_refresh.setText(self.t("campaign.refresh", "Refresh" if not ru else "Обновить"))
        self.btn_resume.setText(self.t("campaign.resume", "Resume Work" if not ru else "Продолжить работу"))
        self.btn_export.setText(self.t("campaign.export_readiness", "Export readiness report" if not ru else "Экспорт отчёта готовности"))
        self.btn_open_corpus.setText(self.t("campaign.open_corpora", "Open Corpora" if not ru else "Открыть корпуса"))
        self.btn_advanced.setText(self.t("campaign.advanced", "Advanced" if not ru else "Дополнительно"))
        self.act_import_manifest.setText(
            self.t("campaign.import_manifest", "Import Manifest" if not ru else "Импортировать manifest")
        )
        self.dashboard.setTitle(self.t("campaign.dashboard", "Campaign dashboard" if not ru else "Панель кампании"))
        self.queue_label.setText(self.t("campaign.queue", "Campaign queue" if not ru else "Очередь кампании"))
        self.campaign_table.setHorizontalHeaderLabels([
            self.t("campaign.col_id", "ID" if not ru else "ID"),
            self.t("campaign.col_name", "Name" if not ru else "Название"),
            self.t("campaign.col_state", "State" if not ru else "Состояние"),
        ])
        self.queue.setHorizontalHeaderLabels([
            self.t("campaign.q_pos", "Position" if not ru else "Позиция"),
            self.t("campaign.q_cohort", "Cohort" if not ru else "Корпус"),
            self.t("campaign.q_source", "Source/date" if not ru else "Источник/дата"),
            self.t("campaign.q_frame", "Frame" if not ru else "Кадр"),
            self.t("campaign.q_time", "Time" if not ru else "Время"),
            self.t("expert_corpus.queue_first_blind", "First blind review"),
            self.t("expert_corpus.queue_candidate_reveal", "Candidate reveal"),
            self.t("expert_corpus.queue_comparison", "Comparison"),
            self.t("expert_corpus.queue_second", "Second independent review"),
            self.t("campaign.q_blocked", "Blocked reason" if not ru else "Причина блокировки"),
        ])
        self.card_optional.setText(self.t("campaign.second_optional", ""))
        self.card_science.setText(self.t("campaign.science_note", ""))
        self.refresh()

    def refresh(self) -> None:
        self._refresh_active_source_label()
        store = self._store()
        self.campaign_table.setRowCount(0)
        self.queue.setRowCount(0)
        if not store:
            self.dash_title.setText(self.t("campaign.no_project", "Open a project first." if self._lang() != "ru" else "Сначала откройте проект."))
            self.card_progress.clear()
            self.card_current.clear()
            self.summary_view.clear()
            return
        ids = store.list_campaigns()
        for i, cid in enumerate(ids):
            m = store.load_manifest(cid)
            self.campaign_table.insertRow(i)
            self.campaign_table.setItem(i, 0, QTableWidgetItem(cid))
            self.campaign_table.setItem(i, 1, QTableWidgetItem(m.display_name))
            state_item = QTableWidgetItem(localize_campaign_state(m.state, lang=self._lang()))
            state_item.setData(Qt.UserRole, m.state)
            state_item.setToolTip(m.state)
            self.campaign_table.setItem(i, 2, state_item)
        if self._campaign_id and self._campaign_id in ids:
            self._render_dashboard(self._campaign_id)
        elif ids:
            self.campaign_table.selectRow(0)
        else:
            self.dash_title.setText(self.t("campaign.list", "Campaigns"))

    def _on_select_campaign(self) -> None:
        rows = self.campaign_table.selectionModel().selectedRows()
        if not rows:
            return
        item = self.campaign_table.item(rows[0].row(), 0)
        if item:
            self._campaign_id = item.text()
            self._render_dashboard(self._campaign_id)

    def _render_dashboard(self, campaign_id: str) -> None:
        store = self._store()
        if not store:
            return
        try:
            m = store.load_manifest(campaign_id)
            prog = campaign_progress(store, campaign_id)
            resume = resume_work(store, campaign_id)
            summary = campaign_descriptive_summary(store, campaign_id)
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("dashboard render failed")
            self.dash_title.setText(str(exc))
            return
        ru = self._lang() == "ru"
        state_lbl = localize_campaign_state(m.state, lang=self._lang())
        self.dash_title.setText(f"{m.display_name} ({state_lbl})")
        self.dash_title.setToolTip(f"state={m.state}")
        self.card_progress.setText(
            (
                f"Planned: {prog['planned_items']}\n"
                f"Unique items: {prog['unique_real_items']}\n"
                f"First blind: {prog['first_blind_progress']['completed']} / {prog['first_blind_progress']['total']}\n"
                f"Comparisons: {prog['comparison_progress']['completed']} / {prog['comparison_progress']['total']}\n"
                f"Second reviews (optional): {prog['second_review_progress']['completed']} / {prog['second_review_progress']['total']}\n"
                f"Adjudications: {prog['adjudication_progress']['completed']}\n"
                f"Unavailable: {prog['unavailable_items']}\n"
                f"Integrity: {'OK' if prog['integrity_ok'] else 'ISSUES'}"
            )
            if not ru
            else (
                f"План: {prog['planned_items']}\n"
                f"Уникальных: {prog['unique_real_items']}\n"
                f"Первая слепая: {prog['first_blind_progress']['completed']} / {prog['first_blind_progress']['total']}\n"
                f"Сравнения: {prog['comparison_progress']['completed']} / {prog['comparison_progress']['total']}\n"
                f"Вторые оценки (необяз.): {prog['second_review_progress']['completed']} / {prog['second_review_progress']['total']}\n"
                f"Арбитраж: {prog['adjudication_progress']['completed']}\n"
                f"Недоступно: {prog['unavailable_items']}\n"
                f"Целостность: {'OK' if prog['integrity_ok'] else 'ПРОБЛЕМЫ'}"
            )
        )
        msg = resume.get("message_ru") if ru else resume.get("message_en")
        self.card_current.setText(
            f"{self.t('campaign.current_work', 'Current work' if not ru else 'Текущая работа')}: {msg}\n"
            f"→ {resume.get('action')} / {resume.get('cohort_id') or '—'} / "
            f"{resume.get('item_id') or '—'}"
        )
        lines = [
            summary.get("note_ru" if ru else "note_en", ""),
            "",
            f"blind={summary.get('completed_blind_reviews')} "
            f"cmp={summary.get('completed_comparisons')} "
            f"second={summary.get('optional_second_reviews')}",
        ]
        if not summary.get("integrity_ok", True):
            lines.append(self.t("campaign.integrity_bad", ""))
        self.summary_view.setPlainText("\n".join(lines))
        self._reload_queue(store, campaign_id)

    def _reload_queue(self, store: MorphologyReviewCampaignStore, campaign_id: str) -> None:
        self.queue.setRowCount(0)
        pos = 0
        for link in store.list_cohort_links(campaign_id):
            if link.cohort_id not in store.corpus.list_cohorts():
                continue
            for it in sorted(store.corpus.load_items(link.cohort_id), key=lambda x: x.manifest_position):
                r1 = store.corpus.locked_review_for_item(link.cohort_id, it.item_id, review_round=1)
                r2 = store.corpus.locked_review_for_item(link.cohort_id, it.item_id, review_round=2)
                revealed = store.corpus._candidate_revealed(link.cohort_id, it.item_id)
                comparison = store.corpus.current_comparison_for_item(link.cohort_id, it.item_id)
                first = (
                    self.t("expert_corpus.status_locked_first", "Locked")
                    if r1
                    else self.t("expert_corpus.status_waiting", "Pending")
                )
                rev = (
                    self.t("expert_corpus.status_revealed", "Revealed")
                    if revealed
                    else self.t("expert_corpus.status_not_revealed", "Not revealed")
                )
                if comparison:
                    cmp = self.t("expert_corpus.status_cmp_done", "Completed")
                elif revealed:
                    cmp = self.t("expert_corpus.status_cmp_revealed_unsaved", "Candidate revealed — comparison not saved")
                else:
                    cmp = self.t("expert_corpus.status_cmp_not_started", "Not started")
                second = (
                    self.t("expert_corpus.status_locked_first", "Locked")
                    if r2
                    else self.t("expert_corpus.status_second_none", "Not assigned")
                )
                vals = [
                    str(pos + 1),
                    link.cohort_id,
                    it.source_display_name or it.datetime_metadata,
                    str(it.frame_index),
                    it.frame_time,
                    first,
                    rev,
                    cmp,
                    second,
                    it.unavailable_reason or "",
                ]
                self.queue.insertRow(pos)
                for c, v in enumerate(vals):
                    self.queue.setItem(pos, c, QTableWidgetItem(v))
                pos += 1

    def _open_wizard(self, *, preselected_shas: list[str] | None = None) -> None:
        store = self._store()
        if not store:
            QMessageBox.warning(
                self,
                self.t("campaign.dialog", "Campaign"),
                self.t("campaign.no_project", "Open a project first."),
            )
            return
        wiz = CampaignCreationWizard(
            self.session, self.i18n, store, parent=self, preselected_shas=preselected_shas
        )
        if wiz.exec() == QWizard.Accepted:
            self._campaign_id = wiz.created_campaign_id
            self.refresh()

    def _repair_source_mapping(self) -> None:
        store = self._store()
        if not store or not self._campaign_id:
            return
        inspection = inspect_campaign_source_bindings(store, self._campaign_id, self.session)
        if not inspection.get("needs_repair"):
            QMessageBox.information(
                self,
                self.t("campaign.dialog", "Campaign"),
                self.t("campaign.repair_not_needed", "No invalid source bindings detected." if self._lang() != "ru" else "Недействительных привязок источников не обнаружено."),
            )
            return
        dlg = _SourceRepairDialog(self, self.session, self.i18n, inspection)
        if dlg.exec() != QDialog.Accepted:
            return
        mapped = dlg.selected_shas()
        if not mapped:
            return
        try:
            result = repair_campaign_source_mapping(
                store, self._campaign_id, self.session, mapped_shas=mapped
            )
            self._campaign_id = result.get("corrected_campaign_id") or self._campaign_id
            QMessageBox.information(
                self,
                self.t("campaign.dialog", "Campaign"),
                self.t("campaign.repair_ok", "Corrected campaign created." if self._lang() != "ru" else "Создана исправленная кампания.")
                + f"\n{result.get('corrected_campaign_id', '')}",
            )
            self.refresh()
        except CampaignError as exc:
            QMessageBox.warning(self, self.t("campaign.dialog", "Campaign"), str(exc))

    def _import_manifest(self) -> None:
        if not self.project_root():
            QMessageBox.warning(self, self.t("campaign.dialog", "Campaign"), self.t("campaign.no_project", ""))
            return
        ru = self._lang() == "ru"
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("campaign.import_manifest", "Import Manifest" if not ru else "Импортировать manifest"),
            "",
            self.t("campaign.import_filter", "Manifest (*.json *.csv);;All files (*)" if not ru else "Manifest (*.json *.csv);;Все файлы (*)"),
        )
        if not path:
            return
        shas = _shas_from_manifest(Path(path))
        if not shas:
            QMessageBox.warning(
                self,
                self.t("campaign.dialog", "Campaign"),
                self.t("campaign.import_no_sha", "No source SHA-256 found in manifest." if not ru else "В manifest не найдено SHA-256 источников."),
            )
            return
        result = validate_selected_sources(self.session, shas)
        if not result.ok:
            QMessageBox.warning(
                self,
                self.t("campaign.dialog", "Campaign"),
                self.t("campaign.import_invalid", "Manifest sources do not match project inventory." if not ru else "Источники manifest не соответствуют инвентарю проекта.")
                + "\n" + "; ".join(result.issues),
            )
            return
        self._open_wizard(preselected_shas=[s.source_sha256 for s in result.sources])

    def _resume_work(self) -> None:
        store = self._store()
        if not store or not self._campaign_id:
            return
        plan = resume_work(store, self._campaign_id)
        if plan["action"] == "no_cohort":
            QMessageBox.information(
                self,
                self.t("campaign.dialog", "Campaign"),
                plan.get("message_ru" if self._lang() == "ru" else "message_en", ""),
            )
            return
        mw = self._main_window
        if mw is None:
            return
        if hasattr(mw, "_navigate_key"):
            mw._navigate_key("expert")
        page = getattr(mw, "_expert_review_corpus_page", None)
        if page is None:
            return
        cohort_id = plan.get("cohort_id")
        if cohort_id and hasattr(page, "_select_cohort"):
            try:
                page._select_cohort(cohort_id)
            except Exception:
                page._cohort_id = cohort_id
        elif cohort_id:
            page._cohort_id = cohort_id
        item_id = plan.get("item_id")
        if item_id and hasattr(page, "_load_item"):
            page._load_item(item_id)
        tab_hint = plan.get("tab_hint")
        tab_map = {"guided": 0, "rapid": 2, "review": 4, "comparison": 5, "summary": 6}
        if hasattr(page, "tabs") and tab_hint in tab_map:
            page.tabs.setCurrentIndex(tab_map[tab_hint])
        if hasattr(page, "_sync_guided_and_refresh"):
            page._sync_guided_and_refresh()
        # Route Resume Work to the batch reveal CTA (owner confirms in corpus UI).
        if plan.get("action") == "batch_reveal_compare" and hasattr(page, "guided_action"):
            page._guided_action = "batch_reveal_compare"
            if hasattr(page, "guided_action"):
                page.guided_action.setText(
                    page.t(
                        "expert_corpus.batch_reveal_compare",
                        "Reveal Candidates and Calculate Comparisons",
                    )
                )

    def _export_readiness(self) -> None:
        store = self._store()
        if not store or not self._campaign_id:
            return
        try:
            result = export_campaign_readiness(store, self._campaign_id)
            QMessageBox.information(
                self,
                self.t("campaign.dialog", "Campaign"),
                self.t("campaign.export_ok", "Readiness report exported.") + f"\n{result['md_path']}",
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.t("campaign.dialog", "Campaign"), str(exc))

    def _open_corpora(self) -> None:
        mw = self._main_window
        if mw is not None and hasattr(mw, "_navigate_key"):
            mw._navigate_key("expert")

    def explain_metrics(self) -> str:
        return explain_metrics_unavailable(self._lang())


def _shas_from_manifest(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    found: list[str] = []
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("sources") or data.get("items") or [data]
        for row in rows:
            if isinstance(row, str) and _SHA_RE.match(row):
                found.append(row.lower())
            elif isinstance(row, dict):
                sha = str(row.get("source_sha256") or row.get("sha256") or "")
                if _SHA_RE.match(sha):
                    found.append(sha.lower())
    else:
        for row in csv.DictReader(text.splitlines()):
            sha = str(row.get("source_sha256") or row.get("sha256") or "")
            if _SHA_RE.match(sha):
                found.append(sha.lower())
    return list(dict.fromkeys(found))


class _SourceRepairDialog(QDialog):
    def __init__(self, parent: QWidget, session: Any, i18n: Any, inspection: dict[str, Any]) -> None:
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self._inspection = inspection
        self._checks: list[tuple[QCheckBox, str]] = []
        ru = str(getattr(i18n, "language", "en")).startswith("ru")
        self.setWindowTitle(i18n.t("campaign.repair_sources", default="Repair Source Mapping" if not ru else "Исправить привязку источников"))
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(i18n.t("campaign.repair_prompt", default="Select registered sources to map:" if not ru else "Выберите зарегистрированные источники для привязки:")))
        invalid_txt = "\n".join(
            f"{b.get('source_display_name', '?')} ({b.get('source_sha256', '')[:12]})"
            for b in inspection.get("invalid_sources") or []
        )
        lay.addWidget(QLabel(invalid_txt))
        for inv in inspection.get("inventory_available") or []:
            cb = QCheckBox(f"{inv['display_name']} ({inv['short_sha']})")
            sha = inv["source_sha256"]
            self._checks.append((cb, sha))
            lay.addWidget(cb)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def selected_shas(self) -> list[str]:
        return [sha for cb, sha in self._checks if cb.isChecked()]


class _SourcesWizardPage(QWizardPage):
    """Sources step with Next gated on valid inventory selection."""

    def __init__(self, wizard: "CampaignCreationWizard") -> None:
        super().__init__()
        self._wiz = wizard

    def isComplete(self) -> bool:  # noqa: N802
        return self._wiz.sources_selection_complete()

    def initializePage(self) -> None:  # noqa: N802
        self._wiz._populate_inventory_table(preserve_checks=True)
        self._wiz._update_sources_preview()
        self.completeChanged.emit()


class CampaignCreationWizard(QWizard):
    """Seven-step campaign creation wizard with inventory source picker."""

    def __init__(
        self,
        session: Any,
        i18n: Any,
        store: MorphologyReviewCampaignStore,
        parent=None,
        *,
        preselected_shas: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.store = store
        self._preselected_shas = list(preselected_shas or [])
        self.created_campaign_id: str | None = None
        self._inventory_rows: list[RegisteredProjectSource] = []
        self._validated_sources: list[SourceScopeEntry] = []
        self._last_preview: dict[str, Any] | None = None
        self._inventory_error: str = ""
        self._inventory_loading: bool = False
        self._user_cleared_selection: bool = False

        # ClassicStyle respects QSS; Windows Aero ignores dark text/background pairing.
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setOption(QWizard.HaveHelpButton, False)
        self.setMinimumSize(820, 560)
        self.setStyleSheet(_wizard_stylesheet())

        self._id = QLineEdit(f"pilot_{Path(store.project_root).name[:12]}")
        self._name = QLineEdit()
        self._desc = QTextEdit()
        self._desc.setMaximumHeight(80)
        self._start = QSpinBox()
        self._start.setRange(1, 2000)
        self._start.setValue(300)
        self._end = QSpinBox()
        self._end.setRange(1, 2000)
        self._end.setValue(420)
        self._step = QSpinBox()
        self._step.setRange(1, 120)
        self._step.setValue(10)
        self._target = QSpinBox()
        self._target.setRange(0, 5000)
        self._target.setValue(20)
        self._seed = QSpinBox()
        self._seed.setRange(0, 2_000_000_000)
        self._seed.setValue(42)
        self._method = QComboBox()
        self._keep_adj = QCheckBox()
        self._keep_adj.setChecked(True)
        self._rev1 = QLineEdit("reviewer_1")
        self._alias1 = QLineEdit()
        self._rev2 = QLineEdit("")
        self._alias2 = QLineEdit()
        self._second_opt = QCheckBox()
        self._second_opt.setChecked(True)
        self._preview_summary = QTextEdit()
        self._preview_summary.setReadOnly(True)
        self._preview_summary.setMaximumHeight(120)
        self._preview_table = QTableWidget(0, 8)
        self._active_auto_lbl = QLabel()
        self._active_auto_lbl.setObjectName("campaignActiveAuto")
        self._source_inventory_table = QTableWidget(0, 6)
        self._source_inventory_table.setObjectName("source_inventory_table")
        self._configure_source_table()
        self._btn_only_active = QPushButton()
        self._btn_only_active.setObjectName("btn_only_active")
        self._btn_select_available = QPushButton()
        self._btn_select_available.setObjectName("btn_select_available")
        self._btn_clear_selection = QPushButton()
        self._btn_clear_selection.setObjectName("btn_clear_selection")
        self._btn_retry_inventory = QPushButton()
        self._btn_retry_inventory.setObjectName("btn_retry_inventory")
        self._btn_close_wizard = QPushButton()
        self._btn_close_wizard.setObjectName("btn_close_wizard")
        self._sources_preview = QTextEdit()
        self._sources_preview.setReadOnly(True)
        self._sources_preview.setMaximumHeight(100)
        self._sources_preview.setObjectName("sources_status")
        self._sources_blocker = QLabel()
        self._sources_blocker.setObjectName("sources_blocker")
        self._sources_blocker.setWordWrap(True)
        self._empty_state = QLabel()
        self._empty_state.setObjectName("sources_empty_state")
        self._empty_state.setWordWrap(True)
        self._tech_details = QTextEdit()
        self._tech_details.setReadOnly(True)
        self._tech_details.setMaximumHeight(70)
        self._tech_details.setVisible(False)
        self._tech_toggle = QPushButton()
        self._lbl_basic_id = QLabel()
        self._lbl_basic_name = QLabel()
        self._lbl_basic_desc = QLabel()
        self._lbl_win_start = QLabel()
        self._lbl_win_end = QLabel()
        self._lbl_win_step = QLabel()
        self._lbl_samp_method = QLabel()
        self._lbl_samp_target = QLabel()
        self._lbl_samp_seed = QLabel()
        self._lbl_rev1 = QLabel()
        self._lbl_alias1 = QLabel()
        self._lbl_rev2 = QLabel()
        self._lbl_alias2 = QLabel()
        self._create_note = QLabel()
        self._designation_note = QLabel()
        self._win_note = QLabel()
        self._samp_note = QLabel()
        self._sources_hint = QLabel()
        self._btn_refresh_preview = QPushButton()

        self.page_basic = self._build_page_basic()
        self.page_sources = self._build_page_sources()
        self.page_windows = self._build_page_windows()
        self.page_sampling = self._build_page_sampling()
        self.page_reviewers = self._build_page_reviewers()
        self.page_preview = self._build_page_preview()
        self.page_create = self._build_page_create()
        for p in (
            self.page_basic,
            self.page_sources,
            self.page_windows,
            self.page_sampling,
            self.page_reviewers,
            self.page_preview,
            self.page_create,
        ):
            self.addPage(p)

        self.page_preview.initializePage = self._refresh_preview  # type: ignore[method-assign]
        self._btn_only_active.clicked.connect(self._select_only_active)
        self._btn_select_available.clicked.connect(self._select_available)
        self._btn_clear_selection.clicked.connect(self._clear_source_selection)
        self._btn_retry_inventory.clicked.connect(lambda: self._populate_inventory_table(preserve_checks=False))
        self._btn_close_wizard.clicked.connect(self.reject)
        self._btn_refresh_preview.clicked.connect(self._refresh_preview)
        self._tech_toggle.clicked.connect(self._toggle_tech_details)
        self._source_inventory_table.itemChanged.connect(self._on_source_item_changed)
        self._connect_session_events()
        self.retranslate_wizard()
        self._populate_inventory_table(preserve_checks=False)

    def _configure_source_table(self) -> None:
        tbl = self._source_inventory_table
        tbl.setMinimumHeight(220)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        hdr = tbl.horizontalHeader()
        fm = QFontMetrics(tbl.font())
        tbl.setColumnWidth(0, max(72, fm.horizontalAdvance("Использовать") + 24))
        tbl.setColumnWidth(1, max(180, fm.horizontalAdvance("Am_all_2014-10-15.mat") + 16))
        tbl.setColumnWidth(2, max(90, fm.horizontalAdvance("15.10.2014") + 16))
        tbl.setColumnWidth(3, max(140, fm.horizontalAdvance("Активный · доступен") + 16))
        tbl.setColumnWidth(4, max(100, fm.horizontalAdvance("a19fd113…") + 16))
        tbl.setColumnWidth(5, max(80, fm.horizontalAdvance("1440") + 16))
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hdr.setMinimumSectionSize(48)

    def _connect_session_events(self) -> None:
        ev = getattr(self.session, "events", None)
        if ev is None:
            return
        for sig_name in ("project_changed", "active_mat_changed", "inventory_changed"):
            sig = getattr(ev, sig_name, None)
            if sig is not None:
                sig.connect(self._on_session_inventory_changed)

    def _on_session_inventory_changed(self) -> None:
        # Refresh badges / rows; preserve deliberate multi-source checks by SHA.
        self._populate_inventory_table(preserve_checks=True)

    def wt(self, key: str, en: str, ru: str) -> str:
        ru_lang = self._lang() == "ru"
        try:
            return self.i18n.t(key, default=ru if ru_lang else en)
        except Exception:
            return ru if ru_lang else en

    def _lang(self) -> str:
        lang = getattr(self.i18n, "language", None) or getattr(self.i18n, "lang", "en") or "en"
        return "ru" if str(lang).startswith("ru") else "en"

    def retranslate_wizard(self) -> None:
        ru = self._lang() == "ru"
        self.setWindowTitle(self.wt("campaign.wizard.title", "New Expert Review Campaign", "Новая кампания экспертной оценки"))
        self.setButtonText(QWizard.NextButton, self.wt("campaign.wizard.next", "Next", "Далее"))
        self.setButtonText(QWizard.BackButton, self.wt("campaign.wizard.back", "Back", "Назад"))
        self.setButtonText(QWizard.CancelButton, self.wt("campaign.wizard.cancel", "Cancel", "Отмена"))
        self.setButtonText(QWizard.FinishButton, self.wt("campaign.wizard.create", "Create", "Создать"))

        self.page_basic.setTitle(self.wt("campaign.wizard.step_basic", "1. Basic information", "1. Основные сведения"))
        self.page_sources.setTitle(self.wt("campaign.wizard.step_sources", "2. Sources and dates", "2. Источники и даты"))
        self.page_windows.setTitle(self.wt("campaign.wizard.step_windows", "3. Time windows", "3. Временные окна"))
        self.page_sampling.setTitle(self.wt("campaign.wizard.step_sampling", "4. Sampling strategy", "4. Стратегия выборки"))
        self.page_reviewers.setTitle(self.wt("campaign.wizard.step_reviewers", "5. Experts", "5. Эксперты"))
        self.page_preview.setTitle(self.wt("campaign.wizard.step_preview", "6. Preview", "6. Предпросмотр"))
        self.page_create.setTitle(self.wt("campaign.wizard.step_create", "7. Create", "7. Создание"))

        self._lbl_basic_id.setText(self.wt("campaign.wizard.campaign_id", "Campaign ID", "ID кампании"))
        self._lbl_basic_name.setText(self.wt("campaign.wizard.name", "Name", "Название"))
        self._lbl_basic_desc.setText(self.wt("campaign.wizard.description", "Description", "Описание"))
        self._designation_note.setText(CAMPAIGN_DESIGNATION_RU if ru else CAMPAIGN_DESIGNATION_EN)
        self._active_auto_lbl.setText(
            self.wt(
                "campaign.active_auto_selected",
                "Active source — selected automatically",
                "Активный источник — выбран автоматически",
            )
        )
        self._btn_only_active.setText(self.wt("campaign.wizard.only_active", "Only active", "Только активный"))
        self._btn_select_available.setText(
            self.wt("campaign.wizard.select_available", "Select available", "Выбрать доступные")
        )
        self._btn_clear_selection.setText(
            self.wt("campaign.wizard.clear_selection", "Clear selection", "Снять выбор")
        )
        self._btn_retry_inventory.setText(self.wt("campaign.wizard.retry", "Retry", "Повторить"))
        self._btn_close_wizard.setText(
            self.wt("campaign.wizard.close_wizard", "Close wizard", "Закрыть мастер")
        )
        self._tech_toggle.setText(
            self.wt("campaign.wizard.tech_details", "Technical Details", "Технические подробности")
        )
        self._sources_hint.setText(
            self.wt(
                "campaign.wizard.sources_hint",
                "Select registered project sources from inventory. SHA is not entered manually.",
                "Выберите зарегистрированные источники проекта из инвентаря. SHA вводится вручную не требуется.",
            )
        )
        self._source_inventory_table.setHorizontalHeaderLabels([
            self.wt("campaign.wizard.col_use", "Use", "Использовать"),
            self.wt("campaign.wizard.col_source", "Source", "Источник"),
            self.wt("campaign.wizard.col_date", "Date", "Дата"),
            self.wt("campaign.wizard.col_state", "State", "Состояние"),
            self.wt("campaign.wizard.col_sha", "Source SHA", "SHA источника"),
            self.wt("campaign.wizard.col_coverage", "Coverage", "Диапазон данных"),
        ])
        self._lbl_win_start.setText(self.wt("campaign.wizard.start_frame", "Start frame", "Начальный кадр"))
        self._lbl_win_end.setText(self.wt("campaign.wizard.end_frame", "End frame", "Конечный кадр"))
        self._lbl_win_step.setText(self.wt("campaign.wizard.step_frames", "Step", "Шаг"))
        self._win_note.setText(
            self.wt(
                "campaign.wizard.windows_note",
                "Default may match 05:00–07:00 / 10-minute step when frame index maps to minutes.",
                "По умолчанию может соответствовать 05:00–07:00 / шаг 10 минут при сопоставлении кадра с минутами.",
            )
        )
        self._lbl_samp_method.setText(self.wt("campaign.wizard.method", "Method", "Метод"))
        self._lbl_samp_target.setText(
            self.wt("campaign.wizard.target_count", "Target count (operational)", "Целевое число (операционное)")
        )
        self._lbl_samp_seed.setText(self.wt("campaign.wizard.seed", "Seed", "Seed"))
        self._keep_adj.setText(
            self.wt(
                "campaign.wizard.keep_adjacent",
                "Do not split adjacent frames of one sequence across different experts",
                "Не разделять соседние кадры одной последовательности между экспертами",
            )
        )
        self._samp_note.setText(
            self.wt(
                "campaign.wizard.target_note",
                "Target count is operational planning only — not a required sample size.",
                "Целевое число — только операционное планирование, не требуемый объём выборки.",
            )
        )
        self._method.blockSignals(True)
        self._method.clear()
        method_labels = {
            "deterministic_random": ("Deterministic random", "Детерминированный случайный"),
            "all_eligible": ("All eligible", "Все подходящие"),
            "stratified": ("Stratified", "Стратифицированная"),
            "manual": ("Manual", "Ручная"),
        }
        for code in _METHOD_CODES:
            en, r = method_labels[code]
            self._method.addItem(self.wt(f"campaign.wizard.method.{code}", en, r), code)
        self._method.blockSignals(False)
        self._lbl_rev1.setText(self.wt("campaign.wizard.rev1_id", "First reviewer ID", "ID первого эксперта"))
        self._lbl_alias1.setText(
            self.wt("campaign.wizard.rev1_alias", "First reviewer alias", "Псевдоним первого эксперта")
        )
        self._lbl_rev2.setText(
            self.wt("campaign.wizard.rev2_id", "Second reviewer ID (optional)", "ID второго эксперта (необяз.)")
        )
        self._lbl_alias2.setText(
            self.wt("campaign.wizard.rev2_alias", "Second reviewer alias", "Псевдоним второго эксперта")
        )
        self._second_opt.setText(
            self.wt(
                "campaign.wizard.second_optional",
                "Second independent reviewer is optional for candidate comparison",
                "Второй независимый эксперт необязателен для сравнения с кандидатом",
            )
        )
        self._btn_refresh_preview.setText(
            self.wt("campaign.wizard.refresh_preview", "Refresh preview", "Обновить предпросмотр")
        )
        self._preview_table.setHorizontalHeaderLabels([
            self.wt("campaign.wizard.prev_source", "Source", "Источник"),
            self.wt("campaign.wizard.prev_inv", "Inventory ID", "ID инвентаря"),
            self.wt("campaign.wizard.prev_date", "Date", "Дата"),
            self.wt("campaign.wizard.prev_sha", "SHA", "SHA"),
            self.wt("campaign.wizard.prev_frame", "Frame", "Кадр"),
            self.wt("campaign.wizard.prev_time", "Time", "Время"),
            self.wt("campaign.wizard.prev_avail", "Availability", "Доступность"),
            self.wt("campaign.wizard.prev_reason", "Inclusion reason", "Причина включения"),
        ])
        self._create_note.setText(
            self.wt(
                "campaign.wizard.create_note",
                "Confirm to create the campaign and linked first-review cohort. Nothing is written until Finish.",
                "Подтвердите создание кампании и связанного корпуса первой оценки. Запись выполняется только по «Создать».",
            )
        )
        if not self._name.text():
            self._name.setText(self.wt("campaign.wizard.default_name", "Pilot campaign", "Пилотная кампания"))
        if not self._alias1.text():
            self._alias1.setText(self.wt("campaign.wizard.default_alias", "Expert A", "Эксперт A"))
        self._update_sources_preview()

    def _build_page_basic(self) -> QWizardPage:
        p = QWizardPage()
        form = QFormLayout(p)
        form.addRow(self._lbl_basic_id, self._id)
        form.addRow(self._lbl_basic_name, self._name)
        form.addRow(self._lbl_basic_desc, self._desc)
        self._designation_note.setWordWrap(True)
        form.addRow(self._designation_note)
        return p

    def _build_page_sources(self) -> _SourcesWizardPage:
        p = _SourcesWizardPage(self)
        lay = QVBoxLayout(p)
        lay.addWidget(self._active_auto_lbl)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self._btn_only_active)
        btn_row.addWidget(self._btn_select_available)
        btn_row.addWidget(self._btn_clear_selection)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)
        lay.addWidget(self._source_inventory_table, 1)
        lay.addWidget(self._empty_state)
        empty_btns = QHBoxLayout()
        empty_btns.addWidget(self._btn_retry_inventory)
        empty_btns.addWidget(self._btn_close_wizard)
        empty_btns.addStretch(1)
        lay.addLayout(empty_btns)
        self._sources_hint.setWordWrap(True)
        lay.addWidget(self._sources_hint)
        lay.addWidget(self._sources_blocker)
        lay.addWidget(self._sources_preview)
        lay.addWidget(self._tech_toggle)
        lay.addWidget(self._tech_details)
        return p

    def _build_page_windows(self) -> QWizardPage:
        p = QWizardPage()
        form = QFormLayout(p)
        form.addRow(self._lbl_win_start, self._start)
        form.addRow(self._lbl_win_end, self._end)
        form.addRow(self._lbl_win_step, self._step)
        self._win_note.setWordWrap(True)
        form.addRow(self._win_note)
        return p

    def _build_page_sampling(self) -> QWizardPage:
        p = QWizardPage()
        form = QFormLayout(p)
        form.addRow(self._lbl_samp_method, self._method)
        form.addRow(self._lbl_samp_target, self._target)
        form.addRow(self._lbl_samp_seed, self._seed)
        form.addRow(self._keep_adj)
        self._samp_note.setWordWrap(True)
        form.addRow(self._samp_note)
        return p

    def _build_page_reviewers(self) -> QWizardPage:
        p = QWizardPage()
        form = QFormLayout(p)
        form.addRow(self._lbl_rev1, self._rev1)
        form.addRow(self._lbl_alias1, self._alias1)
        form.addRow(self._lbl_rev2, self._rev2)
        form.addRow(self._lbl_alias2, self._alias2)
        form.addRow(self._second_opt)
        return p

    def _build_page_preview(self) -> QWizardPage:
        p = QWizardPage()
        lay = QVBoxLayout(p)
        lay.addWidget(self._btn_refresh_preview)
        lay.addWidget(self._preview_summary)
        lay.addWidget(self._preview_table, 1)
        return p

    def _build_page_create(self) -> QWizardPage:
        p = QWizardPage()
        lay = QVBoxLayout(p)
        self._create_note.setWordWrap(True)
        lay.addWidget(self._create_note)
        return p

    def _toggle_tech_details(self) -> None:
        self._tech_details.setVisible(not self._tech_details.isVisible())

    def _on_source_item_changed(self, *_args: Any) -> None:
        self._user_cleared_selection = False
        self._update_sources_preview()
        if isinstance(self.page_sources, _SourcesWizardPage):
            self.page_sources.completeChanged.emit()

    def _populate_inventory_table(self, *, preserve_checks: bool = False) -> None:
        prev_checked: set[str] = set()
        if preserve_checks:
            prev_checked = {s.lower() for s in self.selected_source_shas() if s}

        self._inventory_loading = True
        self._inventory_error = ""
        self._empty_state.setText(
            self.wt(
                "campaign.wizard.loading_sources",
                "Loading registered project sources…",
                "Загрузка зарегистрированных источников проекта…",
            )
        )
        self._empty_state.setVisible(True)
        try:
            self._inventory_rows = list_registered_project_sources(self.session, allow_compute_sha=True)
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("inventory populate failed")
            self._inventory_rows = []
            self._inventory_error = str(exc)
            self._empty_state.setText(
                self.wt(
                    "campaign.wizard.inventory_load_failed",
                    "Failed to load the project source inventory.",
                    "Не удалось загрузить список источников проекта.",
                )
            )
            self._tech_details.setPlainText(str(exc))
            self._source_inventory_table.setRowCount(0)
            self._inventory_loading = False
            self._update_sources_preview()
            if isinstance(self.page_sources, _SourcesWizardPage):
                self.page_sources.completeChanged.emit()
            return

        self._inventory_loading = False
        pre = {s.lower() for s in self._preselected_shas}
        tbl = self._source_inventory_table
        tbl.blockSignals(True)
        tbl.setRowCount(0)
        lang = self._lang()
        avail_txt = self.wt("campaign.wizard.available", "available", "доступен")
        unavail_txt = self.wt("campaign.wizard.unavailable", "unavailable", "недоступен")
        active_badge = self.wt("campaign.wizard.active_badge", "Active", "Активный")

        for i, reg in enumerate(self._inventory_rows):
            tbl.insertRow(i)
            if preserve_checks and prev_checked:
                checked = bool(reg.source_sha256 and reg.source_sha256.lower() in prev_checked)
            elif self._user_cleared_selection:
                checked = False
            else:
                checked = bool(reg.is_active or (reg.source_sha256 and reg.source_sha256.lower() in pre))
            # Do not auto-check unavailable rows (no SHA yet)
            if checked and not reg.available:
                checked = False
            use_item = QTableWidgetItem("")
            use_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            use_item.setCheckState(Qt.Checked if checked and reg.available else Qt.Unchecked)
            if not reg.available:
                use_item.setFlags(Qt.ItemIsUserCheckable)
            tbl.setItem(i, 0, use_item)
            name_item = QTableWidgetItem(reg.display_name)
            name_item.setToolTip(
                f"{reg.display_name}\n{reg.source_sha256}\nid={reg.inventory_id}\n{reg.source_path}"
            )
            tbl.setItem(i, 1, name_item)
            tbl.setItem(i, 2, QTableWidgetItem(format_date_display(reg.date_hint, lang=lang)))
            if reg.is_active:
                state = f"{active_badge} · {avail_txt if reg.available else unavail_txt}"
            else:
                state = avail_txt if reg.available else unavail_txt
            if reg.reason_code and not reg.available:
                state = f"{state} ({localize_validation_issue(reg.reason_code, lang=lang)})"
            tbl.setItem(i, 3, QTableWidgetItem(state))
            sha_disp = f"{reg.short_sha}…" if reg.short_sha else "—"
            sha_item = QTableWidgetItem(sha_disp if reg.short_sha else "—")
            sha_item.setToolTip(reg.source_sha256 or reg.reason_code or "")
            tbl.setItem(i, 4, sha_item)
            cov = str(reg.frame_count) if reg.frame_count else "—"
            tbl.setItem(i, 5, QTableWidgetItem(cov))

        tbl.blockSignals(False)

        if not self._inventory_rows:
            self._empty_state.setText(
                self.wt(
                    "campaign.wizard.no_registered_sources",
                    'This project has no registered MAT sources. Add a source under “Projects” or “Data Import”.',
                    "В проекте нет зарегистрированных MAT-источников. Добавьте источник в разделе «Проекты» или «Импорт данных».",
                )
            )
            self._empty_state.setVisible(True)
            self._btn_retry_inventory.setVisible(True)
            self._btn_close_wizard.setVisible(True)
        else:
            self._empty_state.setVisible(False)
            self._btn_retry_inventory.setVisible(False)
            self._btn_close_wizard.setVisible(False)

        # Default active selection message
        active_rows = [r for r in self._inventory_rows if r.is_active]
        if active_rows and any(
            self._source_inventory_table.item(i, 0)
            and self._source_inventory_table.item(i, 0).checkState() == Qt.Checked
            for i, r in enumerate(self._inventory_rows)
            if r.is_active
        ):
            self._active_auto_lbl.setVisible(True)
        else:
            self._active_auto_lbl.setVisible(bool(active_rows))

        self._update_sources_preview()
        if isinstance(self.page_sources, _SourcesWizardPage):
            self.page_sources.completeChanged.emit()

    def selected_source_shas(self) -> list[str]:
        tbl = self._source_inventory_table
        shas: list[str] = []
        for i in range(tbl.rowCount()):
            item = tbl.item(i, 0)
            if item and item.checkState() == Qt.Checked and i < len(self._inventory_rows):
                sha = self._inventory_rows[i].source_sha256
                if sha:
                    shas.append(sha)
        return shas

    def sources_selection_complete(self) -> bool:
        if self._inventory_loading or self._inventory_error:
            return False
        result = validate_selected_sources(self.session, self.selected_source_shas())
        return bool(result.ok and result.sources)

    def has_editable_sha_field(self) -> bool:
        for w in self.findChildren(QLineEdit):
            name = (w.objectName() or "").lower()
            if "sha" in name:
                return True
        return False

    def inventory_row_count(self) -> int:
        return self._source_inventory_table.rowCount()

    def _select_only_active(self) -> None:
        self._user_cleared_selection = False
        for i, reg in enumerate(self._inventory_rows):
            item = self._source_inventory_table.item(i, 0)
            if item:
                item.setCheckState(
                    Qt.Checked if reg.is_active and reg.available else Qt.Unchecked
                )
        self._update_sources_preview()
        if isinstance(self.page_sources, _SourcesWizardPage):
            self.page_sources.completeChanged.emit()

    def _select_available(self) -> None:
        self._user_cleared_selection = False
        for i, reg in enumerate(self._inventory_rows):
            item = self._source_inventory_table.item(i, 0)
            if item:
                item.setCheckState(Qt.Checked if reg.available else Qt.Unchecked)
        self._update_sources_preview()
        if isinstance(self.page_sources, _SourcesWizardPage):
            self.page_sources.completeChanged.emit()

    def _clear_source_selection(self) -> None:
        self._user_cleared_selection = True
        for i in range(self._source_inventory_table.rowCount()):
            item = self._source_inventory_table.item(i, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        self._update_sources_preview()
        if isinstance(self.page_sources, _SourcesWizardPage):
            self.page_sources.completeChanged.emit()

    def _update_sources_preview(self) -> None:
        lang = self._lang()
        result = validate_selected_sources(self.session, self.selected_source_shas())
        if self._inventory_error:
            msg = localize_validation_issue("inventory_load_failed", lang=lang)
            self._sources_blocker.setText(msg)
            self._sources_preview.setPlainText(msg)
            return
        if self._inventory_loading:
            msg = self.wt(
                "campaign.wizard.loading_sources",
                "Loading registered project sources…",
                "Загрузка зарегистрированных источников проекта…",
            )
            self._sources_blocker.setText(msg)
            self._sources_preview.setPlainText(msg)
            return
        if not result.ok:
            localized = [localize_validation_issue(c, lang=lang) for c in result.issues]
            text = "; ".join(localized)
            # Hard guarantee: never show raw no_sources_selected
            text = text.replace("no_sources_selected", localized[0] if localized else "")
            self._sources_blocker.setText(text)
            self._sources_preview.setPlainText(text)
            self._tech_details.setPlainText("\n".join(result.issues))
            return
        self._sources_blocker.clear()
        lines = []
        for s in result.sources:
            lines.append(
                f"{s.source_display_name} | {s.source_inventory_id} | {s.date_hint} | "
                f"{s.source_sha256[:12]} | "
                f"{self.wt('campaign.wizard.available', 'available', 'доступен') if s.available else self.wt('campaign.wizard.unavailable', 'unavailable', 'недоступен')}"
            )
        self._sources_preview.setPlainText(
            "\n".join(lines)
            if lines
            else localize_validation_issue("no_sources_selected", lang=lang)
        )

    def _collect_sources(self) -> list[SourceScopeEntry]:
        result = validate_selected_sources(self.session, self.selected_source_shas())
        return list(result.sources) if result.ok else []

    def _sampling_plan(self) -> SamplingPlan:
        code = self._method.currentData() or self._method.currentText()
        return SamplingPlan(
            method=str(code),
            seed=self._seed.value(),
            target_count=self._target.value(),
            keep_adjacent_frames_together=self._keep_adj.isChecked(),
        )

    def _windows(self) -> list[TimeWindow]:
        return [
            TimeWindow(
                start_frame=self._start.value(),
                end_frame=self._end.value(),
                step=self._step.value(),
                label=f"{self._start.value()}-{self._end.value()}",
            )
        ]

    def _refresh_preview(self) -> None:
        sources = self._collect_sources()
        if not sources:
            self._preview_summary.setPlainText(
                self.wt("campaign.wizard.preview_no_sources", "No valid sources", "Нет действительных источников")
            )
            self._preview_table.setRowCount(0)
            self._last_preview = None
            return
        plan = self._sampling_plan()
        windows = self._windows()
        prev = self.store.preview_sampling(sources=sources, windows=windows, plan=plan)
        self._last_preview = prev
        self._preview_summary.setPlainText(
            "\n".join([
                f"{self.wt('campaign.wizard.prev_sources_count', 'Selected sources', 'Выбрано источников')}: {len(sources)}",
                f"{self.wt('campaign.wizard.prev_available', 'Available frames', 'Доступные кадры')}: {prev['available_count']}",
                f"{self.wt('campaign.wizard.prev_selected', 'Selected frames', 'Выбранные кадры')}: {prev['selected_count']}",
                f"{self.wt('campaign.wizard.prev_unavailable', 'Unavailable', 'Недоступно')}: {prev['unavailable_count']}",
                f"{self.wt('campaign.wizard.prev_seed', 'Seed', 'Seed')}: {plan.seed} | {self.wt('campaign.wizard.target_count', 'Target', 'Цель')}: {plan.target_count}",
            ])
        )
        rows = list(prev.get("selected") or []) + list(prev.get("unavailable") or [])
        self._preview_table.setRowCount(0)
        for i, row in enumerate(rows[:200]):
            self._preview_table.insertRow(i)
            sha = str(row.get("source_sha256") or "")
            vals = [
                str(row.get("source_display_name") or ""),
                str(row.get("source_inventory_id") or row.get("inventory_id") or ""),
                str(row.get("datetime_metadata") or ""),
                sha[:12],
                str(row.get("frame_index") or ""),
                str(row.get("frame_time") or ""),
                str(row.get("item_status") or ""),
                str(row.get("inclusion_reason") or ""),
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 3 and len(sha) == 64:
                    it.setToolTip(sha)
                self._preview_table.setItem(i, c, it)

    def validateCurrentPage(self) -> bool:  # noqa: N802
        page = self.currentPage()
        if page == self.page_sources:
            result = validate_selected_sources(self.session, self.selected_source_shas())
            if not result.ok:
                lang = self._lang()
                QMessageBox.warning(
                    self,
                    self.wt("campaign.dialog", "Campaign", "Кампания"),
                    "; ".join(localize_validation_issue(c, lang=lang) for c in result.issues),
                )
                return False
            self._validated_sources = list(result.sources)
            self._update_sources_preview()
            return True
        if page == self.page_create:
            return self._create()
        return True

    def _create(self) -> bool:
        if self._last_preview is None:
            self._refresh_preview()
        sources = self._validated_sources or self._collect_sources()
        result = validate_selected_sources(
            self.session,
            [s.source_sha256 for s in sources] if sources else self.selected_source_shas(),
        )
        if not result.ok or not result.sources:
            QMessageBox.warning(
                self,
                self.wt("campaign.dialog", "Campaign", "Кампания"),
                self.wt(
                    "campaign.wizard.create_blocked",
                    "Source validation failed",
                    "Проверка источников не пройдена",
                ),
            )
            return False
        sources = list(result.sources)
        if (
            self._last_preview
            and self._last_preview.get("selected_count", 0) == 0
            and self._last_preview.get("unavailable_count", 0) == 0
        ):
            QMessageBox.warning(
                self,
                self.wt("campaign.dialog", "Campaign", "Кампания"),
                self.wt(
                    "campaign.wizard.no_frames",
                    "No eligible frames in preview",
                    "Нет подходящих кадров в предпросмотре",
                ),
            )
            return False
        reviewers = ReviewerPlan(
            first_reviewer_id=self._rev1.text().strip(),
            first_reviewer_alias=self._alias1.text().strip(),
            second_reviewer_id=self._rev2.text().strip(),
            second_reviewer_alias=self._alias2.text().strip(),
            second_reviewer_optional=self._second_opt.isChecked(),
        )
        try:
            m = self.store.create_campaign(
                campaign_id=self._id.text().strip(),
                display_name=self._name.text().strip(),
                description=self._desc.toPlainText().strip(),
                created_by=reviewers.first_reviewer_id,
                project_identity=str(self.store.project_root.name),
                sources=sources,
                windows=self._windows(),
                sampling_plan=self._sampling_plan(),
                reviewer_plan=reviewers,
                create_linked_cohort=True,
                freeze_cohort=False,
                session=self.session,
            )
        except (CampaignError, Exception) as exc:  # noqa: BLE001
            QMessageBox.warning(
                self, self.wt("campaign.dialog", "Campaign", "Кампания"), str(exc)
            )
            return False
        self.created_campaign_id = m.campaign_id
        return True
