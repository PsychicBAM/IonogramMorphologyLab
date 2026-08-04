"""Phase 4C.1e / 4C.1e.1 — layout defaults, Features overflow, shortcuts Help, sequence state.

These tests are for owner verification. The implementation session must not execute them
when the phase brief forbids verification commands.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QSplitter

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.ui.sequence_frame_state import (
    DIAGNOSTICS_SHORTCUTS,
    FD_LAYOUT_SCHEMA_VERSION,
    SEQUENCE_FRAME_STATES,
    SEQUENCE_STATE_CONTRACT_VERSION,
    assert_sequence_state_catalog_complete,
    candidate_controls_for_state,
    format_shortcuts_help,
    resolve_sequence_frame_state,
    sequence_state_message,
)
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
    s.project = create_project("P4C1E", language="en", workspace_parent=tmp_path / "ws")
    s.add_to_inventory(syn_mats[0], make_active=True)
    return s


def _page(qtbot, session):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    page._use_process_v2 = False
    qtbot.addWidget(page)
    page.show()
    page.resize(1400, 900)
    page._apply_responsive_layout()
    # Deterministic layout authority (do not rely on deferred QTimer ordering).
    page._restore_layout_and_layers()
    QApplication.processEvents()
    return page


def test_sequence_state_catalog_complete():
    assert_sequence_state_catalog_complete()
    assert SEQUENCE_STATE_CONTRACT_VERSION >= 1
    assert FD_LAYOUT_SCHEMA_VERSION >= 2
    for state in SEQUENCE_FRAME_STATES:
        ctrl = candidate_controls_for_state(state)
        assert "calc_enabled" in ctrl
        assert "severity" in ctrl
        assert sequence_state_message(state, "ru")
        assert sequence_state_message(state, "en")
        assert not sequence_state_message(state, "en").startswith("sequence_")


def test_preferred_default_layout_keeps_layers_visible(qtbot, session):
    page = _page(qtbot, session)
    assert isinstance(page.split, QSplitter)
    assert page.split.count() >= 3
    assert page.split.childrenCollapsible() is False
    sizes = page.split.sizes()
    assert sizes[0] >= 100  # Layers pane not collapsed
    assert page.layers_panel.isVisible()
    assert page.layers_toggle.isChecked()


def test_layout_schema_migrates_old_collapsed_layers(qtbot, session):
    # Simulate 4C.1d persisted collapsed-layers layout (schema absent / 0).
    session.settings.set("ux", "fd_layout_schema_version", 0)
    session.settings.set("general", "splitter_states", {"feature_diagnostics": "obsolete"})
    session.settings.save()
    page = _page(qtbot, session)
    assert int(page._settings_get("fd_layout_schema_version", 0)) >= FD_LAYOUT_SCHEMA_VERSION
    assert page.split.sizes()[0] >= 100
    assert page.layers_toggle.isChecked()


def test_ctrl0_restores_layers_canvas_inspector_ratios(qtbot, session):
    page = _page(qtbot, session)
    page.split.setSizes([40, 200, 800])
    page._set_layers_drawer_visible(False)
    page._reset_diagnostics_layout()
    QApplication.processEvents()
    sizes = page.split.sizes()
    total = sum(sizes) or 1
    layers_pct = sizes[0] / total
    canvas_pct = sizes[1] / total
    insp_pct = sizes[2] / total
    assert 0.10 <= layers_pct <= 0.25
    assert 0.45 <= canvas_pct <= 0.65
    assert 0.20 <= insp_pct <= 0.40
    assert page.layers_toggle.isChecked()
    assert page.layers_panel.isVisible()


def test_three_pane_splitter_sizes_persist(qtbot, session):
    page = _page(qtbot, session)
    page.split.setSizes([160, 540, 320])
    page._persist_splitter()
    states = page._settings.get("general", "splitter_states", {}) or {}
    assert "feature_diagnostics" in states


def test_narrow_features_toolbar_no_truncated_primary_labels(qtbot, session):
    page = _page(qtbot, session)
    page._ensure_features_tab()
    page.split.setSizes([150, 400, 280])
    page._update_features_action_visibility()
    assert page._btn_features_more is not None
    assert page._btn_features_more.text() in {"⋯", "..."}
    if page._btn_detach_features.isVisible():
        assert "…" not in page._btn_detach_features.text()
        assert len(page._btn_detach_features.text()) <= 12


def test_secondary_actions_move_to_more_menu(qtbot, session):
    page = _page(qtbot, session)
    page._ensure_features_tab()
    assert page._features_more_menu is not None
    assert page._act_features_expand is not None
    assert page._act_features_collapse is not None
    assert page._act_features_reset is not None
    assert page._btn_features_expand.isHidden()
    assert page._btn_features_collapse_explain.isHidden()


def test_shortcuts_appear_in_ru_en_help():
    en = format_shortcuts_help("en")
    ru = format_shortcuts_help("ru")
    assert "Keyboard shortcuts" in en
    assert "Быстрые команды" in ru
    assert "Ctrl+0" in en and "Ctrl+0" in ru
    assert "Ctrl+Shift+F" in en and "Ctrl+Shift+F" in ru
    assert "Ctrl+Shift+R" in en and "Ctrl+Shift+R" in ru
    assert "Escape" in en and "Escape" in ru
    assert "Reset Diagnostics layout" in en
    assert "Сбросить расположение Diagnostics" in ru
    assert "Follow processing" in en
    assert "Следовать за обработкой" in ru
    assert "only for the selected frame" in en


def test_registered_shortcuts_match_documented(qtbot, session):
    keys = {k for k, _, _ in DIAGNOSTICS_SHORTCUTS}
    assert keys == {"Ctrl+0", "Ctrl+Shift+F", "Ctrl+Shift+R", "Escape"}
    page = _page(qtbot, session)
    assert page._sc_detach_features is not None
    assert page._sc_detach_sequence is not None
    assert page._sc_reset_layout is not None
    det = (ROOT / "src/ionogram_morphology_lab/ui/detachable_table_window.py").read_text(
        encoding="utf-8"
    )
    assert "_esc_shortcut" in det


def test_help_content_lists_shortcuts():
    from ionogram_morphology_lab.help.content import get_help_section, search_help

    sec = get_help_section("feature_diagnostics")
    assert sec is not None
    assert "Ctrl+0" in sec["body_en"] and "Ctrl+0" in sec["body_ru"]
    assert "Быстрые команды" in sec["body_ru"]
    assert "Keyboard shortcuts" in sec["body_en"]
    hits = search_help("быстрые команды", "ru")
    assert any(h.get("id") == "feature_diagnostics" for h in hits)


def test_sequence_v2_pending_message():
    state = resolve_sequence_frame_state(
        sequence_mode=True,
        running=True,
        job_state="computing",
        generation_id="g1",
        active_generation_id="g1",
        current_frame=5,
        sequence_frames=[1, 5, 9],
        sequence_results=[],
        progress_frame=1,
        v2_ready=False,
        candidate_present=False,
        candidate_cached=False,
        candidate_running=False,
        cancelled=False,
    )
    assert state in {"sequence_v2_pending", "sequence_frame_not_yet_processed"}
    msg = sequence_state_message("sequence_v2_pending", "ru")
    assert "Последовательность обрабатывается" in msg


def test_current_frame_not_yet_processed_message():
    msg = sequence_state_message("sequence_frame_not_yet_processed", "ru")
    assert "ещё не обработан" in msg
    msg_en = sequence_state_message("sequence_frame_not_yet_processed", "en")
    assert "not been processed" in msg_en


def test_candidate_controls_enable_when_v2_ready():
    ctrl = candidate_controls_for_state("sequence_v2_ready_candidate_pending")
    assert ctrl["calc_enabled"] is True
    ctrl_pending = candidate_controls_for_state("sequence_v2_pending")
    assert ctrl_pending["calc_enabled"] is False


def test_sequence_callback_other_frame_does_not_overwrite(qtbot, session):
    page = _page(qtbot, session)
    idx = page.mode_combo.findData("sequence")
    page.mode_combo.setCurrentIndex(idx)
    page._v2_generation_id = "gen-a"
    page._sequence_generation_id = "gen-a"
    page._sequence_frames = [3, 7]
    page._sequence_follow = False
    page._sequence_follow_paused_manual = True
    page.frame_spin.setValue(3)
    page._morph_result_dict = {"frame_index": 3, "candidate": "none", "result_hash": "x"}
    page._on_sequence_frame_done(
        {
            "frame_index": 7,
            "status": "cached",
            "result": {"features": {}, "source_mat_sha256": page._source_sha or "a" * 64},
            "request_generation_id": "gen-a",
            "source_sha256": page._source_sha or "",
        }
    )
    assert page._morph_result_dict.get("frame_index") == 3
    assert int(page.frame_spin.value()) == 3


def test_cancelled_generation_callback_discarded(qtbot, session):
    page = _page(qtbot, session)
    page._v2_generation_id = "new-gen"
    page._sequence_results = []
    page._on_sequence_frame_done(
        {
            "frame_index": 1,
            "status": "cached",
            "result": {"features": {}},
            "request_generation_id": "old-gen",
            "source_sha256": page._source_sha or "",
        }
    )
    assert page._sequence_results == []


def test_selecting_sequence_row_hydrates_candidate(qtbot, session):
    page = _page(qtbot, session)
    idx = page.mode_combo.findData("sequence")
    page.mode_combo.setCurrentIndex(idx)
    cand = {
        "frame_index": 2,
        "candidate": "frequency_spread_candidate",
        "result_hash": "abc",
        "source_sha256": "b" * 64,
        "diagnostics_cache_id": "d1",
        "ruleset_hash": "r1",
        "evidence_ledger": [],
    }
    page._sequence_results = [
        {
            "frame_index": 2,
            "status": "cached",
            "result": {
                "quality_status": "ok",
                "features": {},
                "centerlines": [],
                "source_mat_sha256": "b" * 64,
            },
            "morph_candidate": cand,
            "morph_status": "cached",
            "request_generation_id": page._v2_generation_id,
        }
    ]
    page._fill_sequence_table()
    r = page._sequence_results[0]
    page.frame_spin.setValue(2)
    page._apply_frame_result(r)
    page._morph_result_dict = r["morph_candidate"]
    page._morph_cache_status = "cached"
    page._refresh_sequence_frame_state()
    assert page._morph_result_dict["result_hash"] == "abc"


def test_show_results_table_action(qtbot, session):
    page = _page(qtbot, session)
    idx = page.mode_combo.findData("sequence")
    page.mode_combo.setCurrentIndex(idx)
    assert page._btn_show_seq_table is not None
    assert page._btn_show_seq_table.isVisible()
    page._show_sequence_results_table()
    assert page._seq_pane is not None
    assert page._seq_pane.isVisible()
    sizes = page._mid_vsplit.sizes()
    assert sizes[1] >= 120


def test_sequence_table_reachable_at_1280x720(qtbot, session):
    page = _page(qtbot, session)
    page.resize(1280, 720)
    idx = page.mode_combo.findData("sequence")
    page.mode_combo.setCurrentIndex(idx)
    page._sequence_results = [
        {"frame_index": 1, "result": {"quality_status": "ok", "features": {}, "centerlines": []}}
    ]
    page._fill_sequence_table()
    assert page._outer_scroll is not None
    assert page._seq_pane.isVisible()
    assert page.seq_table.minimumHeight() >= 120


def test_language_switch_retranslates_sequence_status(qtbot, session):
    page = _page(qtbot, session)
    idx = page.mode_combo.findData("sequence")
    page.mode_combo.setCurrentIndex(idx)
    page._running = True
    page._job_state = "computing"
    page._sequence_generation_id = page._v2_generation_id = "g"
    page._sequence_frames = [1, 2]
    page._refresh_sequence_frame_state()
    page.i18n.set_language("ru")
    page.retranslate_ui()
    text = page.morph_status.text() + "\n" + page.morph_summary.toPlainText()
    assert "Последовательность" in text or "кадр" in text.lower()


def test_no_science_from_layout_help_actions():
    text = (ROOT / "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py").read_text(
        encoding="utf-8"
    )
    for name in (
        "_reset_diagnostics_layout",
        "_open_shortcuts_help",
        "_show_sequence_results_table",
        "_apply_preferred_layout_defaults",
        "_migrate_layout_schema_if_needed",
    ):
        idx = text.index(f"def {name}")
        chunk = text[idx : idx + 1200]
        assert "run_feature_pipeline" not in chunk
        assert "evaluate_morphology_candidate" not in chunk
        assert "loadmat" not in chunk.lower()


def test_production_rule_engine_unchanged():
    engine = ROOT / "src/ionogram_morphology_lab/rules/engine.py"
    assert "morphology_candidate" not in engine.read_text(encoding="utf-8")


def test_v2_and_candidate_remain_shadow_only():
    page_src = (
        ROOT / "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py"
    ).read_text(encoding="utf-8")
    assert "shadow" in page_src.lower()
    types = (
        ROOT / "src/ionogram_morphology_lab/morphology_candidate/types.py"
    ).read_text(encoding="utf-8")
    assert "production_applied" in types
    assert "scientifically_validated" in types


def test_close_button_still_localized_ru():
    from PySide6.QtWidgets import QDialogButtonBox

    from ionogram_morphology_lab.ui.dialog_buttons import localize_dialog_buttons

    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    localize_dialog_buttons(box, "ru")
    btn = box.button(QDialogButtonBox.StandardButton.Close)
    assert btn is not None
    assert btn.text() == "Закрыть"


def test_worker_emits_frame_done_signal():
    from ionogram_morphology_lab.ui.v2_diagnostics_worker import V2DiagnosticsWorker

    assert hasattr(V2DiagnosticsWorker, "frame_done")


def test_build_identity_includes_phase_4c1e2d():
    from ionogram_morphology_lab.ui.build_identity import collect_build_identity, format_build_identity

    ident = collect_build_identity(compute_sha=False)
    assert ident.get("release_phase") == "4C.1e.3"
    assert ident.get("fd_layout_schema_version") == FD_LAYOUT_SCHEMA_VERSION
    assert ident.get("sequence_state_contract_version") == SEQUENCE_STATE_CONTRACT_VERSION
    text = format_build_identity(ident, "en")
    assert "4C.1e.3" in text
