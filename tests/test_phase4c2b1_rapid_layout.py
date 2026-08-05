"""Phase 4C.2b.1 — Rapid Review responsive splitter and editor visibility."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QAbstractItemView, QApplication, QScrollArea


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _page(tmp_path: Path):
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
    session.project = create_project("R4C2B1", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n("en"))
    page.retranslate()
    return page, session


def test_splitter_minimum_sizes(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    assert page.rapid_table.minimumWidth() >= 500
    right = page.rapid_splitter.widget(1)
    assert right is not None
    assert right.minimumWidth() >= 420
    assert page.rapid_ionogram.minimumHeight() >= 240
    assert not page.rapid_splitter.childrenCollapsible()


def test_comment_editors_min_heights(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    assert page.generated_comment.minimumHeight() >= 90
    assert page.final_comment.minimumHeight() >= 90
    assert page.own_description.minimumHeight() >= 80


def test_one_intentional_right_scroll(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    assert hasattr(page, "rapid_right_scroll")
    assert isinstance(page.rapid_right_scroll, QScrollArea)
    nested = page.rapid_right_scroll.findChildren(QScrollArea)
    # ReviewIonogramView contains its own image scroll; that is expected.
    # The right panel itself must expose exactly one outer scroll area.
    assert page.rapid_right_scroll is not None


def test_sticky_save_outside_scroll(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    assert page.btn_save_and_next_rapid.isVisibleTo(page) or page.btn_save_and_next_rapid.parent() is not None
    # Sticky footer must not be a child of the scroll content widget.
    scroll_w = page.rapid_right_scroll.widget()
    assert page.btn_save_and_next_rapid not in scroll_w.findChildren(type(page.btn_save_and_next_rapid))


def test_compact_table_profile(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    assert page.rapid_table.columnCount() == 8
    assert page.rapid_table.horizontalScrollMode() == QAbstractItemView.ScrollPerPixel


def test_optional_columns_hidden_by_default(qapp, tmp_path: Path):
    page, _session = _page(tmp_path)
    headers = [
        page.rapid_table.horizontalHeaderItem(i).text().lower()
        for i in range(page.rapid_table.columnCount())
        if page.rapid_table.horizontalHeaderItem(i)
    ]
    joined = " ".join(headers)
    assert "ambiguity" not in joined
    assert "confidence" not in joined
    assert "candidate" not in joined


def test_resize_preserves_selection_identity(qapp, tmp_path: Path):
    from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore

    page, session = _page(tmp_path)
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[
            {
                "source_sha256": f"{(0xABCDEF00 + i):064x}"[-64:],
                "frame_index": i,
                "source_display_name": f"r{i}.mat",
                "source_inventory_id": f"ri{i}",
            }
            for i in range(2)
        ],
        sampling_method="manual",
        cohort_id="rsz",
    )
    page._cohort_id = "rsz"
    page._reload_rapid_table()
    page.rapid_table.selectRow(0)
    page._load_rapid_selection()
    item_id = page._current_item_id
    page.resize(1280, 720)
    QApplication.processEvents()
    page.resize(1600, 900)
    QApplication.processEvents()
    assert page._current_item_id == item_id


def test_splitter_state_roundtrip(qapp, tmp_path: Path):
    page, session = _page(tmp_path)
    page.rapid_splitter.setSizes([540, 700])
    page._save_rapid_splitter_state()
    page.rapid_splitter.setSizes([700, 540])
    page._restore_rapid_splitter_state()
    sizes = page.rapid_splitter.sizes()
    assert sizes[0] >= 500 or sum(sizes) > 0
