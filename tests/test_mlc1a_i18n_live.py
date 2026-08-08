"""ML-C.1a — live RU/EN localization and state preservation."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from ionogram_morphology_lab.i18n.loader import I18n
from ionogram_morphology_lab.ml_offline_baselines.constants import BASELINE_NEAREST_CENTROID
from ionogram_morphology_lab.ml_offline_baselines.display_labels import (
    baseline_label,
    state_label,
)
from ionogram_morphology_lab.ml_offline_baselines.models import ExperimentConfig
from ionogram_morphology_lab.ml_offline_baselines.store import OfflineBaselineStore
from ionogram_morphology_lab.ui.ml_offline_baselines_page import MLOfflineBaselinesPage
from tests.mlc1_fixtures import build_mlc1_fixture

_EN_ACTION_SNIPPETS = (
    "Duplicate Experiment",
    "Open Artifact Folder",
    "Export JSON",
    "Copy Experiment ID",
    "Revalidate",
    "Validate Setup",
    "Run Baseline",
)
_RU_BODY_SNIPPETS = (
    "Перед запуском проверьте настройки",
    "Завершённый эксперимент",
    "Проверить настройки",
)


class _Sess:
    def __init__(self, root: Path) -> None:
        self.project_path = root
        self.active_project_path = root


@pytest.fixture
def page(qtbot, tmp_path: Path):
    root, mid, _index, _r, _m = build_mlc1_fixture(tmp_path)
    i18n = I18n()
    i18n.set_language("en")
    p = MLOfflineBaselinesPage(_Sess(root), i18n)
    qtbot.addWidget(p)
    p.on_project_changed()
    store = OfflineBaselineStore(root)
    draft = store.create_draft(
        ExperimentConfig(
            "i18n_exp",
            "tester",
            mid,
            "spread_f_morphology_classification",
            BASELINE_NEAREST_CENTROID,
            seed=9,
        )
    )
    p._refresh_experiments(prefer=draft.experiment_id)
    p._load(draft.experiment_id)
    p._tabs.setCurrentIndex(2)
    return p, root, mid, draft.experiment_id


def test_display_labels_localized():
    assert state_label("completed", "en") == "Completed"
    assert state_label("completed", "ru") == "Завершён"
    assert baseline_label(BASELINE_NEAREST_CENTROID, "en") == "Nearest Centroid"
    assert baseline_label(BASELINE_NEAREST_CENTROID, "ru") == "Ближайший центроид"


def test_ru_more_menu_has_no_english_actions(page):
    p, *_ = page
    p.i18n.set_language("ru")
    p.retranslate()
    texts = [a.text() for a in p._more_actions.values() if a.isVisible()]
    joined = " | ".join(texts)
    for snippet in (
        "Duplicate Experiment",
        "Open Artifact Folder",
        "Export JSON",
        "Copy Experiment ID",
        "Copy Manifest ID",
        "Revalidate",
        "Reset Layout",
        "Open Technical Details",
        "Archive Experiment",
    ):
        assert snippet not in joined
    assert any("Дублировать" in t for t in texts) or "Дублировать как новый" in joined


def test_en_has_no_russian_setup_body(page):
    p, *_ = page
    p.i18n.set_language("ru")
    p.retranslate()
    p.i18n.set_language("en")
    p.retranslate()
    body = p._texts[4].toPlainText()
    assert "Перед запуском" not in body
    assert "Validate setup" in body or "Ready to run" in body or body


def test_live_switch_preserves_selection(page):
    p, root, mid, eid = page
    p._baseline.setCurrentIndex(p._baseline.findData(BASELINE_NEAREST_CENTROID))
    p._tabs.setCurrentIndex(3)
    p._main_split.setSizes([200, 680])
    p._panel_visible["technical"] = False
    p._apply_panel_visible("technical", False)
    p.i18n.set_language("ru")
    p.retranslate()
    assert p._current_id == eid
    assert p._manifest.currentData() == mid
    assert p._baseline.currentData() == BASELINE_NEAREST_CENTROID
    assert p._tabs.currentIndex() == 3
    assert not p._technical.isVisible() or p._panel_visible["technical"] is False
    # Experiment list uses localized state, not raw token
    item = p._experiments.currentItem()
    assert item is not None
    assert "completed" not in item.text()
    assert "draft" not in item.text().lower() or "Черновик" in item.text()
    assert "Черновик" in item.text()
    p.i18n.set_language("en")
    p.retranslate()
    assert p._current_id == eid
    assert p._manifest.currentData() == mid
    assert p._baseline.currentData() == BASELINE_NEAREST_CENTROID
    assert p._tabs.currentIndex() == 3


def test_lifecycle_not_raw_token_in_status(page):
    p, root, mid, eid = page
    p.i18n.set_language("ru")
    p.retranslate()
    assert "completed" not in p._status.text()
    assert "draft" not in p._status.text()
    # list row localized
    row = p._experiments.currentItem().text()
    assert "Черновик" in row


def test_layout_language_does_not_change_hash(page):
    p, root, mid, eid = page
    store = OfflineBaselineStore(root)
    before = store.load_experiment(eid).config_hash
    p.i18n.set_language("ru")
    p.retranslate()
    p._reset_layout()
    p.i18n.set_language("en")
    p.retranslate()
    after = store.load_experiment(eid).config_hash
    assert before == after
