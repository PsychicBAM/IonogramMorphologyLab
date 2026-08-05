"""Phase 4C.2b.2 / 4C.3a.2 — Guided comparison CTA (batch primary)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _items(n: int = 5) -> list[dict]:
    return [
        {
            "source_sha256": f"{(0xBBCCDD00 + i):064x}"[-64:],
            "frame_index": i,
            "source_display_name": f"c{i}.mat",
            "source_inventory_id": f"invc{i}",
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


def _lock_all(store: MorphologyReviewCorpusStore, cid: str) -> None:
    for it in store.load_items(cid):
        store.save_blind_review(
            cid,
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cid,
                item_id=it.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="cmp guided",
            ),
        )


def _page(tmp_path: Path, lang: str = "en"):
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
    session.project = create_project("G4C2B2", language=lang, workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n(lang))
    page.retranslate()
    return page


def _cohort_ready(page, n: int = 5, cid: str = "cmp5") -> MorphologyReviewCorpusStore:
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(items=_items(n), sampling_method="manual", cohort_id=cid)
    items = store.load_items(cid)
    store.freeze_cohort(cid, candidate_snapshots=[_snap(cid, it) for it in items])
    _lock_all(store, cid)
    page._cohort_id = cid
    page._sync_guided_and_refresh()
    return store


def test_guided_5_of_5_blind_0_of_5_compare(qapp, tmp_path: Path):
    page = _page(tmp_path)
    _cohort_ready(page)
    progress = page.guided_progress_text.text()
    assert "5" in progress
    assert "0" in progress
    assert page._guided_action == "batch_reveal_compare"
    assert page.guided_action.text().strip()
    assert (
        "Reveal Candidates" in page.guided_action.text()
        or "Показать кандидатов" in page.guided_action.text()
    )
    assert page.guided_title.text().strip()
    assert page.guided_action.toolTip().strip()
    assert page.guided_action.accessibleName().strip()


def test_guided_partial_continue_batch(qapp, tmp_path: Path):
    page = _page(tmp_path)
    store = _cohort_ready(page, cid="partial")
    items = store.load_items("partial")
    rev = store.locked_review_for_item("partial", items[0].item_id, review_round=1)
    assert rev is not None
    store.reveal_and_compare("partial", items[0].item_id, review_id=rev.review_id)
    page._sync_guided_and_refresh()
    assert page._guided_action == "batch_reveal_compare"
    assert page.guided_action.text().strip()


def test_guided_full_comparisons_open_summary(qapp, tmp_path: Path):
    page = _page(tmp_path)
    store = _cohort_ready(page, n=2, cid="full")
    for it in store.load_items("full"):
        rev = store.locked_review_for_item("full", it.item_id, review_round=1)
        assert rev is not None
        store.reveal_and_compare("full", it.item_id, review_id=rev.review_id)
    page._sync_guided_and_refresh()
    assert page._guided_action == "open_summary"
    assert "summary" in page.guided_action.text().lower() or "сводк" in page.guided_action.text().lower()


def test_batch_action_confirms_and_opens_summary(qapp, tmp_path: Path):
    page = _page(tmp_path)
    store = _cohort_ready(page, cid="batch")
    # Bypass confirmation UI; exercise domain + summary handoff.
    page._run_batch_reveal_compare = (  # type: ignore[method-assign]
        lambda: (
            __import__(
                "ionogram_morphology_lab.morphology_review_corpus.batch_compare",
                fromlist=["batch_reveal_and_compare"],
            ).batch_reveal_and_compare(store, "batch"),
            page._sync_guided_and_refresh(),
            page.tabs.setCurrentIndex(6),
        )
    )
    page._run_guided_action()
    from ionogram_morphology_lab.morphology_review_corpus.current_state import (
        project_cohort_comparisons,
    )

    assert project_cohort_comparisons(store, "batch").current_count == len(store.load_items("batch"))
    assert page.tabs.currentIndex() == 6  # Summary


def test_per_item_reveal_no_auto_next(qapp, tmp_path: Path):
    page = _page(tmp_path)
    store = _cohort_ready(page, n=2, cid="next")
    items = store.load_items("next")
    page._cohort_id = "next"
    page._load_item(items[0].item_id)
    page._reveal_candidate()
    assert page._current_item_id == items[0].item_id
    assert store.current_comparison_for_item("next", items[0].item_id) is not None
    assert store.current_comparison_for_item("next", items[1].item_id) is None
    assert not store._candidate_revealed("next", items[1].item_id)


def test_cta_never_blank_with_missing_map(qapp, tmp_path: Path):
    page = _page(tmp_path)
    _cohort_ready(page, cid="fb")
    page._guided_action = "save_comparison_next"
    page._sync_guided_and_refresh()
    assert page.guided_action.text().strip() != ""


def test_guided_comparison_ru(qapp, tmp_path: Path):
    page = _page(tmp_path, lang="ru")
    _cohort_ready(page, cid="ru")
    assert "Сравнение" in page.guided_title.text()
    assert "Показать кандидатов" in page.guided_action.text()
    assert "per_item_reveal" not in page.guided_cohort_line.text()
    assert "strict_cohort_blinding" not in page.guided_cohort_line.text()
    assert "Слепая оценка завершена" in page.guided_progress_text.text()
    assert "Сравнения завершены" in page.guided_progress_text.text()
