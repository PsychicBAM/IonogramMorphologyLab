"""Phase 4C.2b.2 — locked Review detail display and empty states."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_corpus.comments import CommentRecord
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


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
    session.project = create_project("L4C2B2", language=lang, workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n(lang))
    page.retranslate()
    return page


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


def test_locked_review_loads_read_only(qapp, tmp_path: Path):
    page = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[{
            "source_sha256": f"{0xABCDEF01:064x}"[-64:],
            "frame_index": 1,
            "source_display_name": "lock.mat",
            "source_inventory_id": "invl",
        }],
        sampling_method="manual",
        cohort_id="lk",
    )
    items = store.load_items("lk")
    store.freeze_cohort("lk", candidate_snapshots=[_snap("lk", it) for it in items])
    rec = BlindReviewRecord.create(
        reviewer_id="owner",
        reviewer_role="reviewer",
        review_round=1,
        cohort_id="lk",
        item_id=items[0].item_id,
        morphology="range_spread",
        assessability="assessable",
        interference=["none_supported"],
        ambiguity="low",
        confidence="high",
        rationale="locked detail",
    )
    store.save_blind_review("lk", rec)
    store.save_comment(
        "lk",
        CommentRecord.create(
            comment_type="decision_rationale",
            cohort_id="lk",
            item_id=items[0].item_id,
            reviewer_id="owner",
            review_id=rec.review_id,
            structured_codes=["primary_f_trace_clear"],
            generated_text="gen",
            final_text="final expert note",
            expert_own_description="own desc",
            ui_language="en",
        ),
    )
    page._cohort_id = "lk"
    page._load_item(items[0].item_id)
    text = page.review_detail_view.toPlainText()
    assert "Range" in text or "range" in text.lower() or "расплыв" in text.lower() or display_ok(text)
    assert "locked detail" in text
    assert "final expert note" in text
    assert "own desc" in text
    assert page.review_locked_badge.isVisible() or page.review_locked_badge.text()
    assert not page.btn_save_blind.isVisible()
    assert page.review_detail_view.isReadOnly()
    assert not page.morph_combo.isEnabled()
    assert "item_id=" in page.review_tech_view.toPlainText()
    assert "item_id=" not in page.item_identity.text()


def display_ok(text: str) -> bool:
    return "Morphology" in text or "morphology" in text.lower()


def test_pending_item_empty_state(qapp, tmp_path: Path):
    page = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[{
            "source_sha256": f"{0xABCDEF02:064x}"[-64:],
            "frame_index": 2,
            "source_display_name": "pend.mat",
            "source_inventory_id": "invp",
        }],
        sampling_method="manual",
        cohort_id="pend",
    )
    items = store.load_items("pend")
    store.freeze_cohort("pend", candidate_snapshots=[_snap("pend", it) for it in items])
    page._cohort_id = "pend"
    page._load_item(items[0].item_id)
    assert "not been saved" in page.review_state_banner.text().lower() or "не сохранена" in page.review_state_banner.text().lower() or "pending" in page.review_state_banner.text().lower()
    assert not page.btn_create_review_revision.isVisible()


def test_no_item_state(qapp, tmp_path: Path):
    page = _page(tmp_path)
    page._clear_stale_views()
    assert page.review_state_banner.text().strip()


def test_switch_items_clears_stale(qapp, tmp_path: Path):
    page = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[
            {
                "source_sha256": f"{(0xABCDEF10 + i):064x}"[-64:],
                "frame_index": i,
                "source_display_name": f"s{i}.mat",
                "source_inventory_id": f"is{i}",
            }
            for i in range(2)
        ],
        sampling_method="manual",
        cohort_id="sw",
    )
    items = store.load_items("sw")
    store.freeze_cohort("sw", candidate_snapshots=[_snap("sw", it) for it in items])
    store.save_blind_review(
        "sw",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="sw",
            item_id=items[0].item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="first only",
        ),
    )
    page._cohort_id = "sw"
    page._load_item(items[0].item_id)
    assert "first only" in page.review_detail_view.toPlainText()
    page._load_item(items[1].item_id)
    assert "first only" not in page.review_detail_view.toPlainText()
    assert page.btn_save_blind.isHidden()


def test_child_revision_does_not_load_parent(qapp, tmp_path: Path):
    page = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[{
            "source_sha256": f"{0xABCDEF99:064x}"[-64:],
            "frame_index": 3,
            "source_display_name": "par.mat",
            "source_inventory_id": "invpar",
        }],
        sampling_method="manual",
        cohort_id="par",
    )
    items = store.load_items("par")
    store.freeze_cohort("par", candidate_snapshots=[_snap("par", it) for it in items])
    store.save_blind_review(
        "par",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="par",
            item_id=items[0].item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="parent review text",
        ),
    )
    child = store.create_editable_revision("par", reason="owner correction cohort")
    page._cohort_id = child.cohort_id
    child_items = store.load_items(child.cohort_id)
    page._load_item(child_items[0].item_id)
    assert "parent review text" not in page.review_detail_view.toPlainText()
    assert not page.review_locked_badge.isVisible() or page.review_detail_view.toPlainText() == ""
