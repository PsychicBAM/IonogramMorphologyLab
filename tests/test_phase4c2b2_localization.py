"""Phase 4C.2b.2 — RU localization closure for Guided/Review strings."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_corpus.constants import (
    REVEAL_PER_ITEM,
    REVEAL_STRICT_COHORT,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.protocol import CohortProtocol


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _page(tmp_path: Path, lang: str = "ru"):
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
    session.project = create_project("I18n4C2B2", language=lang, workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n(lang))
    page.retranslate()
    return page


def test_ru_no_raw_policy_or_draft_english(qapp, tmp_path: Path):
    page = _page(tmp_path, "ru")
    store = page._ensure_store()
    assert store is not None
    proto = CohortProtocol(reveal_policy=REVEAL_PER_ITEM)
    store.create_cohort(
        items=[{
            "source_sha256": f"{0x11223301:064x}"[-64:],
            "frame_index": 1,
            "source_display_name": "i18n.mat",
            "source_inventory_id": "i18n1",
        }],
        sampling_method="manual",
        cohort_id="i18n_pol",
        protocol=proto,
    )
    items = store.load_items("i18n_pol")
    store.freeze_cohort(
        "i18n_pol",
        candidate_snapshots=[
            CandidateSnapshot(
                cohort_id="i18n_pol",
                item_id=items[0].item_id,
                source_sha256=items[0].source_sha256,
                frame_index=items[0].frame_index,
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
        ],
    )
    store.save_blind_review(
        "i18n_pol",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="i18n_pol",
            item_id=items[0].item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="ru pol",
        ),
    )
    page._cohort_id = "i18n_pol"
    page._sync_guided_and_refresh()
    page._load_item(items[0].item_id)
    surface = "\n".join(
        [
            page.guided_cohort_line.text(),
            page.guided_action.text(),
            page.btn_save_draft_rapid.text(),
            page.review_locked_badge.text(),
            page.tabs.tabText(4),
        ]
    )
    assert REVEAL_PER_ITEM not in surface
    assert REVEAL_STRICT_COHORT not in surface
    assert "Save draft" not in surface
    assert "Draft saved" not in surface
    assert "Сохранить черновик" in page.btn_save_draft_rapid.text()
    page._save_rapid_draft()
    assert "Черновик сохранён" in page.validation_label.text()
    assert "Покадровый" in page.guided_cohort_line.text() or "показ" in page.guided_cohort_line.text().lower()


def test_runtime_ru_en_retranslate(qapp, tmp_path: Path):
    page = _page(tmp_path, "en")
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[{
            "source_sha256": f"{0x11223302:064x}"[-64:],
            "frame_index": 2,
            "source_display_name": "sw.mat",
            "source_inventory_id": "sw1",
        }],
        sampling_method="manual",
        cohort_id="swlang",
    )
    items = store.load_items("swlang")
    store.freeze_cohort(
        "swlang",
        candidate_snapshots=[
            CandidateSnapshot(
                cohort_id="swlang",
                item_id=items[0].item_id,
                source_sha256=items[0].source_sha256,
                frame_index=items[0].frame_index,
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
        ],
    )
    store.save_blind_review(
        "swlang",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="swlang",
            item_id=items[0].item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="lang",
        ),
    )
    page._cohort_id = "swlang"
    page._sync_guided_and_refresh()
    assert (
        "Reveal Candidates" in page.guided_action.text()
        or "Start comparison" in page.guided_action.text()
    )
    page.i18n = get_i18n("ru")
    page.retranslate()
    page._sync_guided_and_refresh()
    page._load_item(items[0].item_id)
    assert (
        "Показать кандидатов" in page.guided_action.text()
        or "Начать сравнение" in page.guided_action.text()
    )
    assert "Слепая оценка зафиксирована" in page.review_locked_badge.text()
    assert "Подробности" in page.tabs.tabText(4) or "оценк" in page.tabs.tabText(4).lower()
