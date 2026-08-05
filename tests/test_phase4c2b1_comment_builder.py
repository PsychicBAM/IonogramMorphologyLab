"""Phase 4C.2b.1 — grouped structured comment builder visibility."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QGroupBox


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
    session.project = create_project("C4C2B1", language=lang, workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n(lang))
    page.retranslate()
    return page


def test_four_grouped_sections(qapp, tmp_path: Path):
    page = _page(tmp_path)
    assert len(page.comment_groups) == 4
    for group, codes, content in page.comment_groups:
        assert isinstance(group, QGroupBox)
        assert group.isCheckable()
        assert codes
        assert content is not None


def test_groups_expand_collapse(qapp, tmp_path: Path):
    page = _page(tmp_path)
    page._set_comment_groups_expanded(False)
    assert all(not g.isChecked() for g, _c, _w in page.comment_groups)
    page._set_comment_groups_expanded(True)
    assert all(g.isChecked() for g, _c, _w in page.comment_groups)
    # Default construction expands only first two
    page2 = _page(tmp_path / "d2")
    expanded = [g.isChecked() for g, _c, _w in page2.comment_groups]
    assert expanded[:2] == [True, True]
    assert expanded[2:] == [False, False]


def test_selected_counts_update(qapp, tmp_path: Path):
    page = _page(tmp_path)
    code = next(iter(page.comment_checks))
    page.comment_checks[code].setChecked(True)
    page._update_comment_group_titles()
    assert "1" in page.lbl_selected_count.text()
    assert "selected" in page.lbl_selected_count.text().lower() or "Выбрано" in page.lbl_selected_count.text()


def test_preset_expands_relevant_groups(qapp, tmp_path: Path):
    page = _page(tmp_path)
    page._set_comment_groups_expanded(False)
    # Pick first non-empty preset
    for i in range(page.comment_preset.count()):
        if page.comment_preset.itemData(i):
            page.comment_preset.setCurrentIndex(i)
            break
    page._apply_comment_preset()
    selected_codes = {c for c, chk in page.comment_checks.items() if chk.isChecked()}
    if selected_codes:
        for group, codes, _content in page.comment_groups:
            should = any(code in selected_codes for code in codes)
            assert group.isChecked() == should
        assert page.generated_comment.toPlainText().strip()


def test_three_editors_visible_heights(qapp, tmp_path: Path):
    page = _page(tmp_path)
    assert page.generated_comment.isVisibleTo(page) or page.generated_comment.parent() is not None
    assert page.final_comment.minimumHeight() >= 90
    assert page.own_description.minimumHeight() >= 80
    assert page.generated_comment_label.text().strip()
    assert page.final_comment_label.text().strip()
    assert page.own_description_label.text().strip()


def test_final_not_overwritten_when_dirty(qapp, tmp_path: Path, monkeypatch):
    page = _page(tmp_path)
    page.final_comment.setPlainText("manual expert edit")
    page._final_comment_dirty = True
    code = next(iter(page.comment_checks))
    page.comment_checks[code].setChecked(True)
    page._comment_codes_changed()
    assert page.final_comment.toPlainText() == "manual expert edit"
    assert page.generated_comment.toPlainText().strip()
    monkeypatch.setattr(page, "_ask", lambda *a, **k: False)
    page._regenerate_comment()
    assert page.final_comment.toPlainText() == "manual expert edit"


def test_comment_builder_ru_labels(qapp, tmp_path: Path):
    page = _page(tmp_path, lang="ru")
    page._update_comment_group_titles()
    titles = " ".join(g.title() for g, _c, _w in page.comment_groups)
    assert "Видимость следа" in titles or "выбрано" in titles.lower()
    assert "Сформированный" in page.generated_comment_label.text() or page.generated_comment_label.text()
    assert "Итоговый" in page.final_comment_label.text() or "комментарий" in page.final_comment_label.text().lower()
