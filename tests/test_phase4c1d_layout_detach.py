"""Phase 4C.1d — splitters, detachable tables, scroll, localization."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.ui.detachable_table_window import DetachableTableWindow
from ionogram_morphology_lab.ui.dialog_buttons import localize_dialog_buttons
from ionogram_morphology_lab.ui.session import AppSession

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def syn_mats(tmp_path):
    from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library

    return write_synthetic_mat_library(tmp_path / "mats")


@pytest.fixture
def session(tmp_path, syn_mats):
    from ionogram_morphology_lab.app.settings_store import SettingsStore

    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    s = AppSession(settings=settings)
    s.project = create_project("P4C1D", language="en", workspace_parent=tmp_path / "ws")
    s.add_to_inventory(syn_mats[0], make_active=True)
    return s


def _page(qtbot, session):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    page._use_process_v2 = False
    qtbot.addWidget(page)
    page.show()
    return page


def test_main_horizontal_splitter_exists(qtbot, session):
    page = _page(qtbot, session)
    page.resize(1400, 900)
    page._apply_responsive_layout()
    assert isinstance(page.split, QSplitter)
    assert page.split.orientation() == Qt.Orientation.Horizontal
    assert page.split.count() >= 3
    assert page.split.childrenCollapsible() is False


def test_mid_vertical_splitter_for_sequence(qtbot, session):
    page = _page(qtbot, session)
    assert page._mid_vsplit is not None
    assert page._mid_vsplit.orientation() == Qt.Orientation.Vertical
    assert page._seq_pane is not None


def test_reset_layout_restores_defaults(qtbot, session):
    page = _page(qtbot, session)
    page.split.setSizes([0, 200, 800])
    page._reset_diagnostics_layout()
    sizes = page.split.sizes()
    assert sizes[1] >= sizes[2]  # canvas >= inspector after reset (~65/35)


def test_splitter_persist_keys(qtbot, session):
    page = _page(qtbot, session)
    page.split.setSizes([0, 500, 400])
    page._persist_splitter()
    states = page._settings.get("general", "splitter_states", {}) or {}
    assert "feature_diagnostics" in states


def test_features_internal_splitter_and_detach(qtbot, session):
    page = _page(qtbot, session)
    page._result_ser = {
        "features": {"v2_trace_present": {"value": True, "valid": True, "unit": ""}},
        "feature_version": "iml2-0.2.0",
        "source_mat_sha256": "a" * 64,
    }
    page._ensure_features_tab()
    assert page._features_splitter is not None
    assert page._btn_detach_features is not None
    page._open_features_detach()
    assert page._features_detach_win is not None
    assert isinstance(page._features_detach_win, DetachableTableWindow)
    # Shares the same proxy/model — no second registry path required
    assert page._features_model is not None
    page._features_detach_win.close()


def test_features_pin_keeps_identity(qtbot, session):
    page = _page(qtbot, session)
    page._result_ser = {
        "features": {"v2_trace_present": {"value": True, "valid": True, "unit": ""}},
        "feature_version": "iml2-0.2.0",
        "source_mat_sha256": "b" * 64,
    }
    page._ensure_features_tab()
    page._populate_features()
    page._open_features_detach()
    win = page._features_detach_win
    assert win is not None
    win.chk_pin.setChecked(True)
    pinned_frame = win._identity.get("frame_index")
    page.frame_spin.setValue(min(10, page._n_frames))
    page._sync_features_detach_on_frame()
    assert win.pinned
    assert win.stale_label.isHidden() is False or win._identity.get("frame_index") == pinned_frame


def test_sequence_pane_and_detach(qtbot, session):
    page = _page(qtbot, session)
    idx = page.mode_combo.findData("sequence")
    page.mode_combo.setCurrentIndex(idx)
    page._sequence_results = [
        {"frame_index": 1, "result": {"quality_status": "ok", "features": {}, "centerlines": []}},
        {"frame_index": 2, "result": {"quality_status": "ok", "features": {}, "centerlines": []}},
    ]
    page._fill_sequence_table()
    assert page._seq_pane is not None and page._seq_pane.isVisible()
    assert page.seq_table.rowCount() == 2
    page._open_sequence_detach()
    assert page._seq_detach_win is not None
    assert page._seq_detach_table is not None
    assert page._seq_detach_table.rowCount() == 2
    page._seq_detach_win.close()


def test_outer_scroll_exists(qtbot, session):
    page = _page(qtbot, session)
    assert hasattr(page, "_outer_scroll")
    assert page._outer_scroll.widget() is page._page_content
    page.resize(1280, 720)
    assert page._page_content.minimumHeight() >= 600


def test_close_button_localizes_ru():
    from PySide6.QtWidgets import QDialogButtonBox

    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    localize_dialog_buttons(box, "ru")
    btn = box.button(QDialogButtonBox.StandardButton.Close)
    assert btn is not None
    assert btn.text() == "Закрыть"


def test_detachable_window_retranslate():
    win = DetachableTableWindow(kind="features", title="Features")
    win.retranslate("ru")
    assert "Закрепить" in win.chk_pin.text()
    win.retranslate("en")
    assert "Pin" in win.chk_pin.text()
    win.close()


def test_page_source_has_shortcuts_and_no_science_on_layout():
    text = (ROOT / "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py").read_text(
        encoding="utf-8"
    )
    assert "Ctrl+Shift+F" in text
    assert "Ctrl+Shift+R" in text
    assert "Ctrl+0" in text
    assert "_reset_diagnostics_layout" in text
    assert "DetachableTableWindow" in text
    # Layout reset must not call V2 pipeline
    idx = text.index("def _reset_diagnostics_layout")
    chunk = text[idx : idx + 800]
    assert "run_feature_pipeline" not in chunk
    assert "evaluate_morphology" not in chunk


def test_production_rule_engine_untouched():
    engine = ROOT / "src/ionogram_morphology_lab/rules/engine.py"
    assert "morphology_candidate" not in engine.read_text(encoding="utf-8")
