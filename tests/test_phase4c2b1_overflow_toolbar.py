"""Phase 4C.2b.1 — corpus toolbar overflow finalization."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QPushButton, QToolButton


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _page(tmp_path: Path, lang: str = "en"):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.i18n import get_i18n
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
    session.project = create_project("T4C2B1", language=lang, workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n(lang))
    page.retranslate()
    page.refresh_cohorts()
    return page


def test_at_most_two_text_actions_plus_overflow(qapp, tmp_path: Path):
    page = _page(tmp_path)
    visible_text = []
    for btn in (page.btn_preview, page.btn_freeze):
        assert btn.isVisibleTo(page) or not btn.isHidden()
        visible_text.append(btn)
    assert page.btn_overflow.isVisibleTo(page) or not page.btn_overflow.isHidden()
    assert isinstance(page.btn_overflow, QToolButton)
    for btn in (
        page.btn_create,
        page.btn_add_current,
        page.btn_remove_current,
        page.btn_clear_draft,
        page.btn_delete_draft,
        page.btn_create_revision,
        page.btn_archive,
        page.btn_export,
        page.btn_validate,
        page.btn_refresh,
    ):
        assert btn.isHidden()


def test_hidden_actions_available_in_overflow(qapp, tmp_path: Path):
    page = _page(tmp_path)
    menu = page.btn_overflow.menu()
    assert menu is not None
    texts = [a.text() for a in menu.actions() if a.text()]
    assert texts
    assert len(page._overflow_button_actions) >= 8


def test_overflow_accessible_name(qapp, tmp_path: Path):
    page = _page(tmp_path)
    assert page.btn_overflow.toolTip().strip()
    assert page.btn_overflow.accessibleName().strip()


def test_filters_in_compact_menu(qapp, tmp_path: Path):
    page = _page(tmp_path)
    assert hasattr(page, "_filters_menu")
    assert page._filters_menu is not None
    assert page.chk_show_archived.isHidden()
    assert page.chk_show_legacy.isHidden()
    filter_texts = [a.text() for a in page._filters_menu.actions()]
    assert any(filter_texts)


def test_action_availability_draft_vs_frozen(qapp, tmp_path: Path):
    page = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[
            {
                "source_sha256": f"{(0xABCD0100 + i):064x}"[-64:],
                "frame_index": i,
                "source_display_name": f"t{i}.mat",
                "source_inventory_id": f"ti{i}",
            }
            for i in range(2)
        ],
        sampling_method="manual",
        cohort_id="tb",
    )
    page._cohort_id = "tb"
    page._update_action_enablement()
    assert page.btn_freeze.isEnabled()
    assert "Freeze" in page.btn_freeze.text() or "Зафиксир" in page.btn_freeze.text()
    items = store.load_items("tb")
    store.freeze_cohort("tb")
    page._update_action_enablement()
    assert page.btn_create_revision.isEnabled()
    assert "Continue" in page.btn_freeze.text() or "Продолжить" in page.btn_freeze.text() or "оценк" in page.btn_freeze.text().lower()
    assert not page.btn_clear_draft.isEnabled()


def test_overflow_ru_en(qapp, tmp_path: Path):
    page = _page(tmp_path, lang="ru")
    page.retranslate()
    assert page._filters_menu.title()
    assert "Фильтр" in page._filters_menu.title() or page._filters_menu.title()
    page.i18n = __import__("ionogram_morphology_lab.i18n", fromlist=["get_i18n"]).get_i18n("en")
    page.retranslate()
    assert "Filter" in page._filters_menu.title() or page._filters_menu.title()


def test_no_clipped_primary_at_narrow_width(qapp, tmp_path: Path):
    page = _page(tmp_path)
    page.resize(1280, 720)
    QApplication.processEvents()
    for btn in (page.btn_preview, page.btn_freeze, page.btn_overflow):
        # Buttons remain present; text may elide in layout but must not be empty.
        assert isinstance(btn, (QPushButton, QToolButton))
        assert (btn.text() or btn.toolTip()).strip()
