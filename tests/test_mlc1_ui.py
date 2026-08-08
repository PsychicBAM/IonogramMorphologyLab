import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.ml_offline_baselines.models import ExperimentConfig
from ionogram_morphology_lab.ui.ml_offline_baselines_page import MLOfflineBaselinesPage
from tests.test_mlb1c_layout_holdout_ui import _I18n, _Sess


def _page(qtbot, root: Path):
    page = MLOfflineBaselinesPage(_Sess(root), _I18n("en"))
    qtbot.addWidget(page); page.show(); page.on_project_changed(); QApplication.processEvents()
    return page


def test_page_compact_menus_and_critical_holdout_warning(qtbot, tmp_path: Path):
    page = _page(qtbot, tmp_path)
    assert page._technical.expanded is False
    assert page._view.menu() is not None and page._more.menu() is not None
    assert page._holdout.isVisible()
    page._set_all_panels(False); QApplication.processEvents()
    assert page._holdout.isVisible()
    visible_primary = sum(
        1
        for button in (
            page._btn_new,
            page._btn_validate,
            page._btn_run,
            page._btn_export,
            page._btn_cancel,
        )
        if not button.isHidden()
    )
    assert visible_primary <= 4
    assert page._more.isVisible() and page._view.isVisible()


def test_retranslate_preserves_selection_and_ui_prefs_do_not_affect_config_hash(qtbot, tmp_path: Path):
    page = _page(qtbot, tmp_path)
    record = page._store.create_draft(ExperimentConfig("keep", "qa", "manifest", "spread_f_morphology_classification", "iml-majority-class-baseline-0.1.0"))
    page._current_id = record.experiment_id; page._tabs.setCurrentIndex(2)
    config_hash = record.config_hash
    before = page._tabs.currentIndex()
    page.i18n.set_language("ru"); page.retranslate(); QApplication.processEvents()
    assert page._current_id == record.experiment_id and page._tabs.currentIndex() == before
    page.i18n.set_language("en"); page.retranslate()
    assert page._current_id == record.experiment_id
    page._set_panel_visible("features", False)
    page._set_panel_visible("features", True)
    assert page._store.load_experiment(record.experiment_id).config_hash == config_hash
