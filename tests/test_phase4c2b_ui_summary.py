"""Phase 4C.2b — localized comparison, summary dashboard, overflow UI."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QToolButton

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_corpus.labels import display_label
from ionogram_morphology_lab.morphology_review_corpus.models import BlindReviewRecord
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
from ionogram_morphology_lab.ui.corpus_display import (
    format_comparison_cards,
    format_summary_dashboard,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_comparison_cards_localized_no_raw_codes():
    text = format_comparison_cards(
        human_morphology="range_spread",
        candidate_state="frequency_spread_candidate",
        ordinal_strength="moderate",
        agreement_status="morphology_disagreement",
        engine="iml-morph-candidate-0.1.1",
        lang="ru",
    )
    assert "Экспертная оценка" in text
    assert "Частотное расплывание" in text
    assert "Морфологическое расхождение" in text
    assert "frequency_spread_candidate" not in text
    assert "morphology_disagreement" not in text
    assert "Human:" not in text
    assert "moderate" not in text or "Средн" in text
    assert "Технические сведения" in text


def test_summary_human_readable_no_accuracy(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(
        items=[
            {
                "source_sha256": f"{(0x11223344 + i):064x}"[-64:],
                "frame_index": i,
                "source_display_name": f"s{i}.mat",
                "source_inventory_id": f"i{i}",
            }
            for i in range(2)
        ],
        cohort_id="sum",
    )
    store.freeze_cohort("sum")
    items = store.load_items("sum")
    for it in items:
        store.save_blind_review(
            "sum",
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="sum",
                item_id=it.item_id,
                morphology="range_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="summary test",
            ),
        )
    text = format_summary_dashboard(store, "sum", "ru")
    assert "Всего кадров" in text
    assert "Слепая оценка завершена" in text
    assert "{" not in text.split("\n")[0]
    assert "accuracy" not in text.lower() or "не accuracy" in text.lower()
    assert "f1" not in text.lower() or "не accuracy" in text.lower()
    assert "не определено" in text.lower() or "нет независимых" in text.lower()


def test_display_label_candidate_strength():
    assert "кандидат" in display_label("frequency_spread_candidate", "ru").lower()
    assert display_label("moderate", "ru") == "Средняя"


def test_overflow_and_guided_widgets(qapp, tmp_path: Path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import create_project
    from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
    from ionogram_morphology_lab.ui.session import AppSession
    from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage

    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    session = AppSession(settings=settings)
    session.project = create_project("UI4C2B", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n("en"))
    assert hasattr(page, "btn_overflow")
    assert isinstance(page.btn_overflow, QToolButton)
    assert page.btn_overflow.menu() is not None
    # Visible primary actions limited — overflow holds the rest
    menu_texts = [a.text() for a in page.btn_overflow.menu().actions() if a.text()]
    assert menu_texts
    page.i18n = get_i18n("ru")
    page.retranslate()
    assert "Пошаговая" in page.tabs.tabText(0) or page.t("expert_corpus.tab_guided") == "Пошагово"
    assert page.t("expert_corpus.technical_json") == "Технический JSON"
    # Rapid table has no candidate column headers
    page.refresh_cohorts()
    headers = []
    if page.rapid_table.columnCount():
        headers = [
            page.rapid_table.horizontalHeaderItem(i).text()
            for i in range(page.rapid_table.columnCount())
            if page.rapid_table.horizontalHeaderItem(i)
        ]
    assert not any("candidate" in h.lower() for h in headers)
