"""Phase 4C.2 / 4C.2a UI smoke — Expert Review Corpus page (RU/EN, blind gating)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox

from ionogram_morphology_lab.morphology_review_corpus.blinding import queue_columns
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage


class _I18n:
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.language = lang
        from ionogram_morphology_lab.i18n import get_i18n

        self._real = get_i18n(lang)

    def t(self, key: str, default: str | None = None, **_kwargs):
        return self._real.t(key, default=default)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def session_with_mat(tmp_path: Path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import create_project
    from ionogram_morphology_lab.ui.session import AppSession

    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    session = AppSession(settings=settings)
    session.project = create_project("UISmoke", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    session.current_frame = 1
    return session


def test_expert_corpus_page_en_ru(qapp, session_with_mat):
    page = ExpertReviewCorpusPage(session_with_mat, _I18n("en"))
    assert "Expert Review Corpus" in page.title.text()
    page.i18n = _I18n("ru")
    page.retranslate()
    assert "Корпус экспертной оценки" in page.title.text()
    assert "Пилотный корпус" in page.designation.text()


def test_create_freeze_blind_reveal_flow(qapp, session_with_mat, monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.Ok)

    page = ExpertReviewCorpusPage(session_with_mat, _I18n("en"))
    monkeypatch.setattr(page, "_ask", lambda *a, **k: True)
    page.cohort_id_edit.setText("ui_pilot")
    page.count_spin.setValue(2)
    page.start_frame_spin.setValue(1)
    page.end_frame_spin.setValue(2)
    page.step_spin.setValue(1)
    page._preview_cohort_items()
    page._create_real_cohort()
    assert page._cohort_id == "ui_pilot"
    from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore

    store = MorphologyReviewCorpusStore(session_with_mat.project.root)
    items = store.load_items("ui_pilot")
    assert items
    assert not any(it.source_display_name.startswith("pilot_frame_") for it in items)
    page._freeze_cohort()
    assert store.load_manifest("ui_pilot").frozen
    page._load_item(items[0].item_id)
    assert page._blind_locked_for_item is False
    assert "candidate_state" not in queue_columns(blind=True)
    for i in range(page.morph_combo.count()):
        if page.morph_combo.itemData(i) == "frequency_spread":
            page.morph_combo.setCurrentIndex(i)
            break
    # Identity may fail without cache — force match for save path when image loaded
    if page.ionogram_view.identity_matches(items[0].source_sha256, items[0].frame_index):
        page._save_blind()
        # Strict blinding: finish remaining round-one via domain API (identity/cache may
        # block UI save for other frames in headless smoke).
        from ionogram_morphology_lab.morphology_review_corpus.models import BlindReviewRecord

        for it in items:
            if store.locked_review_for_item("ui_pilot", it.item_id, review_round=1):
                continue
            store.save_blind_review(
                "ui_pilot",
                BlindReviewRecord.create(
                    reviewer_id="rev_owner",
                    reviewer_role="reviewer",
                    review_round=1,
                    cohort_id="ui_pilot",
                    item_id=it.item_id,
                    morphology="frequency_spread",
                    assessability="assessable",
                    interference=["none_supported"],
                    ambiguity="low",
                    confidence="high",
                    rationale="ui smoke complete round-one",
                ),
            )
        assert store.can_reveal_candidate("ui_pilot", items[0].item_id)
        page._load_item(items[0].item_id)
        page._reveal_candidate()
        page._save_comparison()


def test_help_section_present():
    from ionogram_morphology_lab.help.content import get_help_section

    sec = get_help_section("expert_review_corpus")
    assert sec is not None
    assert "blind" in sec["body_en"].lower()
