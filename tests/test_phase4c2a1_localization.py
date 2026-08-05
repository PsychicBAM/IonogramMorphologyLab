"""Phase 4C.2a.1 — RU/EN localization for corpus lifecycle strings."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _I18n:
    def __init__(self, lang: str):
        self.lang = lang
        self.language = lang
        self._real = get_i18n(lang)

    def t(self, key: str, default: str | None = None, **_kwargs):
        return self._real.t(key, default=default)


def test_i18n_key_parity_expert_corpus():
    root = Path(__file__).resolve().parents[1] / "src" / "ionogram_morphology_lab" / "i18n"
    en = json.loads((root / "en.json").read_text(encoding="utf-8"))
    ru = json.loads((root / "ru.json").read_text(encoding="utf-8"))
    en_ec = {k for k in en if k.startswith("expert_corpus.")}
    ru_ec = {k for k in ru if k.startswith("expert_corpus.")}
    assert en_ec == ru_ec
    assert "Yes" not in ru["expert_corpus.freeze_ok_btn"]
    assert ru["expert_corpus.freeze_ok_btn"] == "Зафиксировать"
    assert ru["expert_corpus.cancel_btn"] == "Отмена"
    assert "зафиксировать" in ru["expert_corpus.must_freeze_review"].lower()
    assert ru["expert_corpus.meta.frozen"] == "Зафиксирован"
    assert ru["expert_corpus.meta.draft"] == "Черновик"
    assert ru["expert_corpus.meta.manual"] == "Ручная"
    assert ru["expert_corpus.meta.random"] == "Случайная"
    assert ru["expert_corpus.meta.item_pending"] == "Ожидает оценки"
    assert "Зерно" in ru["expert_corpus.field_seed"]
    assert en["expert_corpus.remove_current"].startswith("Remove")


def test_runtime_retranslate_meta_and_buttons(qapp, tmp_path: Path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import create_project
    from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
    from ionogram_morphology_lab.ui.session import AppSession
    from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
    from ionogram_morphology_lab.morphology_review_corpus.project_items import (
        current_viewer_frame_item,
    )

    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    session = AppSession(settings=settings)
    session.project = create_project("Loc", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    session.current_frame = 1
    store = MorphologyReviewCorpusStore(session.project.root)
    store.create_cohort(
        items=[current_viewer_frame_item(session)],
        sampling_method="manual",
        cohort_id="loc1",
    )

    page = ExpertReviewCorpusPage(session, _I18n("en"))
    page.refresh_cohorts()
    page._cohort_id = "loc1"
    page._refresh_cohort_info()
    assert "Cohort ID" in page.cohort_info.toPlainText() or "cohort" in page.cohort_info.toPlainText().lower()
    assert "Draft" in page.cohort_info.toPlainText() or "draft" in page.btn_add_current.text().lower()
    page._update_action_enablement()
    assert "Freeze" in page.btn_freeze.text() and "blind" in page.btn_freeze.text().lower()

    page.i18n = _I18n("ru")
    page.retranslate()
    page._refresh_cohort_info()
    page._update_action_enablement()
    text = page.cohort_info.toPlainText()
    assert "ID корпуса" in text
    assert "Черновик" in text
    assert "Ручная" in text
    assert "Зафиксировать" in page.btn_freeze.text() and "слепую" in page.btn_freeze.text()
    assert page.btn_remove_current.text() == "Убрать текущий кадр Viewer из черновика"
    assert page.btn_create_revision.text() == "Создать редактируемую ревизию"
    # no raw codes as primary labels
    assert "cohort_id:" not in text
    assert "item_pending" not in text
    freeze_msg = page.t("expert_corpus.freeze_confirm").format(
        cohort_id="x",
        item_count=1,
        source_scope="s",
        unavailable=0,
        manifest_preview="p",
    )
    assert "Yes" not in freeze_msg
    assert "No" not in freeze_msg
    assert "нельзя будет изменить" in freeze_msg
