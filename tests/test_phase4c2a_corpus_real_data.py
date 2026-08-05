"""Phase 4C.2a — real cohort ingestion; no production pilot_frame placeholders."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_corpus.project_items import (
    current_viewer_frame_item,
    frames_from_time_range,
    items_from_active_source_frames,
)
from ionogram_morphology_lab.morphology_review_corpus.store import (
    FrozenCohortError,
    MorphologyReviewCorpusStore,
)
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.session import AppSession


@pytest.fixture
def syn_mats(tmp_path: Path):
    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    return sorted(syn.glob("*.mat"))


@pytest.fixture
def session(tmp_path: Path, syn_mats) -> AppSession:
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    s = AppSession(settings=settings)
    s.project = create_project("CorpusReal", language="en", workspace_parent=tmp_path / "ws")
    s.add_to_inventory(syn_mats[0], make_active=False)
    s.add_to_inventory(syn_mats[1], make_active=True)
    s.current_frame = 3
    return s


def test_items_from_active_source_use_b_sha(session: AppSession, syn_mats):
    frames = frames_from_time_range(start_frame=1, end_frame=3, step=1)
    items = items_from_active_source_frames(session, frames)
    assert len(items) == 3
    sha = session.get_source_sha(allow_compute=True)
    assert all(it["source_sha256"] == sha for it in items)
    assert all(it["source_display_name"] == syn_mats[1].name for it in items)
    assert not any(str(it["source_display_name"]).startswith("pilot_frame_") for it in items)


def test_viewer_frame_add_and_dedupe(session: AppSession):
    store = MorphologyReviewCorpusStore(session.project.root)
    item = current_viewer_frame_item(session)
    m = store.create_cohort(items=[item], sampling_method="manual", cohort_id="draft1")
    result = store.add_items_to_draft("draft1", [item])
    assert result["added"] == 0
    assert result["duplicates"]
    item2 = current_viewer_frame_item(session)
    # change frame
    session.current_frame = 7
    item2 = current_viewer_frame_item(session)
    result2 = store.add_items_to_draft("draft1", [item2])
    assert result2["added"] == 1
    assert store.load_manifest("draft1").item_count == 2


def test_zero_item_cannot_freeze(session: AppSession):
    store = MorphologyReviewCorpusStore(session.project.root)
    store.create_cohort(items=[], sampling_method="manual", cohort_id="empty")
    with pytest.raises(FrozenCohortError):
        store.freeze_cohort("empty")


def test_frozen_rejects_additions(session: AppSession):
    store = MorphologyReviewCorpusStore(session.project.root)
    items = items_from_active_source_frames(session, [1, 2])
    store.create_cohort(items=items, cohort_id="frz")
    store.freeze_cohort("frz")
    with pytest.raises(FrozenCohortError):
        store.add_items_to_draft("frz", items_from_active_source_frames(session, [3]))


def test_production_ui_create_uses_real_names(qtbot, session: AppSession, syn_mats, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.Ok)

    page = ExpertReviewCorpusPage(session, get_i18n("en"))
    monkeypatch.setattr(page, "_ask", lambda *a, **k: True)
    qtbot.addWidget(page)
    page.start_frame_spin.setValue(1)
    page.end_frame_spin.setValue(2)
    page.step_spin.setValue(1)
    page.count_spin.setValue(2)
    page.cohort_id_edit.setText("real_cohort")
    page._preview_cohort_items()
    assert page._preview_items
    assert not any(
        str(x["source_display_name"]).startswith("pilot_frame_") for x in page._preview_items
    )
    page._create_real_cohort()
    store = MorphologyReviewCorpusStore(session.project.root)
    items = store.load_items("real_cohort")
    assert items
    assert all(it.source_display_name == syn_mats[1].name for it in items)


def test_ru_page_no_english_principal_controls(qtbot, session: AppSession):
    from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage

    page = ExpertReviewCorpusPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.i18n = get_i18n("ru")
    page.retranslate()
    assert page.title.text() == "Корпус экспертной оценки"
    assert page.btn_freeze.text() == "Зафиксировать и начать слепую оценку"
    assert page.btn_save_blind.text() == "Сохранить слепую оценку"
    assert page.btn_reveal.text() == "Показать результат кандидата"
    # Tab 0 is Guided review; Cohorts follows
    assert "Пошагов" in page.tabs.tabText(0)
    assert page.tabs.tabText(1) == "Корпуса"
    assert "Cohort" not in page.tabs.tabText(1)
    # Morphology display labels translated
    texts = [page.morph_combo.itemText(i) for i in range(page.morph_combo.count())]
    assert "Frequency spread" not in texts
    assert any("расплывание" in t.lower() or "Частот" in t for t in texts)


def test_en_to_ru_live_switch(qtbot, session: AppSession):
    from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage

    page = ExpertReviewCorpusPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    assert "Expert Review Corpus" in page.title.text()
    page.i18n = get_i18n("ru")
    page.retranslate()
    assert "Корпус экспертной оценки" in page.title.text()
    page.i18n = get_i18n("en")
    page.retranslate()
    assert "Expert Review Corpus" in page.title.text()
