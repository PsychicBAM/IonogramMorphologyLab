"""Phase 4C.2b.3 — Guided density, comparison panel, queue, tech collapse."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_corpus.labels import comparison_status_display
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.ui.corpus_display import format_summary_dashboard


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
    session.project = create_project("U4C2B3", language=lang, workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n(lang))
    page.retranslate()
    return page


def test_guided_card_wider(qapp, tmp_path: Path):
    page = _page(tmp_path)
    assert page.guided_card.maximumWidth() >= 800
    assert hasattr(page, "guided_section_optional")
    assert hasattr(page, "guided_section_science")


def test_tech_details_collapsed_by_default(qapp, tmp_path: Path):
    page = _page(tmp_path)
    assert page.review_tech_box.isCheckable()
    assert page.review_tech_box.isChecked() is False


def test_before_reveal_shows_pending_not_abstained(qapp, tmp_path: Path):
    page = _page(tmp_path, "ru")
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[{
            "source_sha256": f"{0xCC01:064x}"[-64:],
            "frame_index": 1,
            "source_display_name": "u.mat",
            "source_inventory_id": "iu",
        }],
        cohort_id="pendr",
    )
    items = store.load_items("pendr")
    store.freeze_cohort(
        "pendr",
        candidate_snapshots=[
            CandidateSnapshot(
                cohort_id="pendr",
                item_id=items[0].item_id,
                source_sha256=items[0].source_sha256,
                frame_index=1,
                candidate_engine_version="iml-morph-candidate-0.1.1",
                ruleset_id="r",
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
        ],
    )
    store.save_blind_review(
        "pendr",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="pendr",
            item_id=items[0].item_id,
            morphology="indeterminate",
            assessability="partially_assessable",
            interference=["none_supported"],
            ambiguity="high",
            confidence="low",
            rationale="indet",
        ),
    )
    page._cohort_id = "pendr"
    page._load_item(items[0].item_id)
    text = page.compare_view.toPlainText() + page.compare_state_label.text()
    pending = comparison_status_display("comparison_pending_reveal", "ru")
    assert "воздерж" not in text.lower() or pending.lower() in text.lower()
    assert "не показан" in text.lower() or "не выполнен" in text.lower() or pending in text


def test_queue_no_generic_yes_for_comparison(qapp, tmp_path: Path):
    page = _page(tmp_path, "ru")
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[{
            "source_sha256": f"{0xCC09:064x}"[-64:],
            "frame_index": 9,
            "source_display_name": "q.mat",
            "source_inventory_id": "iq",
        }],
        cohort_id="qhdr",
    )
    page._cohort_id = "qhdr"
    page._reload_queue()
    headers = [
        page.queue_table.horizontalHeaderItem(i).text()
        for i in range(page.queue_table.columnCount())
        if page.queue_table.horizontalHeaderItem(i)
    ]
    joined = " | ".join(headers)
    assert "Сравнение" in joined or "Comparison" in joined
    assert "Первая" in joined or "First" in joined
    assert "Yes" not in joined


def test_summary_optional_second_and_consistency(qapp, tmp_path: Path):
    page = _page(tmp_path, "ru")
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[{
            "source_sha256": f"{0xCC02:064x}"[-64:],
            "frame_index": 2,
            "source_display_name": "s.mat",
            "source_inventory_id": "is",
        }],
        cohort_id="sumu",
    )
    text = format_summary_dashboard(store, "sumu", "ru")
    assert "не обязателен" in text.lower() or "второ" in text.lower()
    assert "accuracy" not in text.lower() or "не accuracy" in text.lower()


def test_second_reviewer_optional_in_guided(qapp, tmp_path: Path):
    page = _page(tmp_path, "ru")
    page._sync_guided_and_refresh()
    # After cohort sync optional section may fill when cohort selected
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[{
            "source_sha256": f"{0xCC03:064x}"[-64:],
            "frame_index": 3,
            "source_display_name": "g.mat",
            "source_inventory_id": "ig",
        }],
        cohort_id="gopt",
    )
    page._cohort_id = "gopt"
    page._sync_guided_and_refresh()
    assert "не обязателен" in page.guided_section_optional.text().lower()
