"""Phase 4C.2b.1 — Guided Review never-blank stage card and actions."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
from ionogram_morphology_lab.ui.corpus_display import guided_step_indicator


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _page(tmp_path: Path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import create_project
    from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
    from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage
    from ionogram_morphology_lab.ui.session import AppSession

    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    session = AppSession(settings=settings)
    session.project = create_project("G4C2B1", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n("en"))
    page.refresh_cohorts()
    page._sync_guided_and_refresh()
    return page, session


def _items(n: int = 2) -> list[dict]:
    return [
        {
            "source_sha256": f"{(0xAABBCC00 + i):064x}"[-64:],
            "frame_index": i,
            "source_display_name": f"g{i}.mat",
            "source_inventory_id": f"invg{i}",
        }
        for i in range(n)
    ]


def _snap(cid, it):
    return CandidateSnapshot(
        cohort_id=cid,
        item_id=it.item_id,
        source_sha256=it.source_sha256,
        frame_index=it.frame_index,
        candidate_engine_version="iml-morph-candidate-0.1.1",
        ruleset_id="iml-morph-candidate-rules",
        ruleset_hash="x",
        result_contract_version=2,
        diagnostics_cache_id="n/a",
        candidate_state="frequency_spread_candidate",
        ordinal_strength="moderate",
        assessability_state="assessable",
        evidence_ledger=[],
        result_hash="c" * 64,
        ledger_hash="d" * 64,
        generated_or_cached="cached",
    )


def test_guided_never_blank_no_cohort(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    assert page.guided_title.text().strip()
    assert page.guided_explain.text().strip()
    assert page.guided_action.text().strip()
    assert page.guided_action.isEnabled()
    assert page.guided_steps_header.text().strip()
    assert "1." in page.guided_steps_header.text()


def test_guided_draft_empty_primary_add_frames(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(items=[], sampling_method="manual", cohort_id="empty_d")
    page._cohort_id = "empty_d"
    page._sync_guided_and_refresh()
    assert page._guided_action == "add_frames"
    assert "Add frames" in page.guided_action.text() or "кадр" in page.guided_action.text().lower()
    assert page.guided_title.text().strip()
    assert page.guided_progress_text.text().strip()


def test_guided_draft_with_items_freeze_start(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(items=_items(2), sampling_method="manual", cohort_id="draft_d")
    page._cohort_id = "draft_d"
    page._sync_guided_and_refresh()
    assert page._guided_action == "freeze_and_start"
    assert "Freeze" in page.guided_action.text() or "Зафиксир" in page.guided_action.text()


def test_guided_frozen_pending_continue(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(items=_items(2), sampling_method="manual", cohort_id="frz")
    items = store.load_items("frz")
    store.freeze_cohort("frz", candidate_snapshots=[_snap("frz", it) for it in items])
    page._cohort_id = "frz"
    page._sync_guided_and_refresh()
    assert page._guided_action == "continue_blind"
    assert "Continue" in page.guided_action.text() or "Продолжить" in page.guided_action.text()
    assert "2" in page.guided_progress_text.text() or "of" in page.guided_progress_text.text().lower()


def test_guided_after_blind_go_comparison(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(items=_items(2), sampling_method="manual", cohort_id="cmp")
    items = store.load_items("cmp")
    store.freeze_cohort("cmp", candidate_snapshots=[_snap("cmp", it) for it in items])
    for it in items:
        store.save_blind_review(
            "cmp",
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="cmp",
                item_id=it.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="guided",
            ),
        )
    page._cohort_id = "cmp"
    page._sync_guided_and_refresh()
    assert page._guided_action in (
        "batch_reveal_compare",
        "go_to_comparison",
        "save_comparison_next",
        "start_comparison",
        "continue_comparison",
    )
    assert page.guided_action.text().strip()


def test_guided_action_navigates_cohorts(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    page._cohort_id = ""
    page._sync_guided_and_refresh()
    page._run_guided_action()
    assert page.tabs.currentIndex() == 1


def test_guided_action_opens_rapid_for_continue(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(items=_items(2), sampling_method="manual", cohort_id="nav")
    items = store.load_items("nav")
    store.freeze_cohort("nav", candidate_snapshots=[_snap("nav", it) for it in items])
    page._cohort_id = "nav"
    page._sync_guided_and_refresh()
    page._run_guided_action()
    assert page.tabs.currentIndex() == 2
    assert page._current_item_id


def test_guided_ru_en_retranslation(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(items=_items(1), sampling_method="manual", cohort_id="i18n")
    page._cohort_id = "i18n"
    page.i18n = get_i18n("ru")
    page.retranslate()
    page._sync_guided_and_refresh()
    assert "Зафиксир" in page.guided_action.text() or "Слепая" in page.guided_title.text()
    page.i18n = get_i18n("en")
    page.retranslate()
    page._sync_guided_and_refresh()
    assert "Freeze" in page.guided_action.text() or "composition" in page.guided_title.text().lower() or "Cohort" in page.guided_title.text()


def test_guided_step_indicator_marks():
    text = guided_step_indicator({"guided_step": "blind_review"}, "ru")
    assert "Слепая оценка" in text
    assert "●" in text
    assert "Состав корпуса" in text
    assert "Сводка и экспорт" in text
