"""Phase 4C.1e.2 — sequence Follow processing, per-frame Features hydration, shortcut clarity.

These tests are for owner verification. The implementation session must not execute them
when the phase brief forbids verification commands.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.ui.sequence_frame_state import (
    SEQUENCE_STATE_CONTRACT_VERSION,
    features_empty_message,
    format_sequence_progress_status,
    format_shortcuts_help,
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
    s.project = create_project("P4C1E2", language="en", workspace_parent=tmp_path / "ws")
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
    page._restore_layout_and_layers()
    QApplication.processEvents()
    return page


def _ensure_frame_spin_range(page, frames: list[int], current: int | None) -> None:
    """Expand QSpinBox/slider maxima so sequence tests are not clamped by synthetic MAT size."""
    needed = list(frames)
    if current is not None:
        needed.append(int(current))
    max_frame = max(int(f) for f in needed) if needed else int(page._n_frames or 1)
    max_frame = max(max_frame, 1)
    page._n_frames = max(int(page._n_frames or 1), max_frame)
    page.frame_spin.setMinimum(1)
    page.frame_spin.setMaximum(page._n_frames)
    page.frame_slider.setMinimum(1)
    page.frame_slider.setMaximum(page._n_frames)
    if hasattr(page, "seq_start"):
        page.seq_start.setMaximum(page._n_frames)
    if hasattr(page, "seq_end"):
        page.seq_end.setMaximum(page._n_frames)


def _enter_sequence(page, frames: list[int], *, current: int | None = None) -> None:
    idx = page.mode_combo.findData("sequence")
    page.mode_combo.setCurrentIndex(idx)
    page._sequence_frames = list(frames)
    page._sequence_results = []
    page._sequence_last_completed_frame = None
    page._sequence_follow = True
    page._sequence_follow_paused_manual = False
    page._sequence_cancelled = False
    page._running = True
    page._job_state = "computing"
    page._v2_generation_id = "gen-follow"
    page._sequence_generation_id = "gen-follow"
    if page._chk_seq_follow is not None:
        page._chk_seq_follow.blockSignals(True)
        page._chk_seq_follow.setChecked(True)
        page._chk_seq_follow.blockSignals(False)
    # Patch loads before intent bump so deferred workers are not started.
    page._schedule_frame_load = lambda *_a, **_k: None  # type: ignore[method-assign]
    page.wait_until_frame_ready = lambda *_a, **_k: True  # type: ignore[method-assign]
    _ensure_frame_spin_range(page, frames, current)
    target = int(current) if current is not None else int(page.frame_spin.value())
    page._suppress_follow_pause = True
    try:
        page._goto_frame(
            target,
            immediate=True,
            pause_follow=False,
            reason="sequence_start",
        )
    finally:
        page._suppress_follow_pause = False
    assert int(page.frame_spin.value()) == target, (
        f"frame_spin clamped to {page.frame_spin.value()} "
        f"(max={page.frame_spin.maximum()}); wanted {target}"
    )
    assert int(page._intended_frame) == target
    assert int(page.frame_slider.value()) == target
    page._raw = np.zeros((16, 16), dtype=np.float32)
    page._loaded_frame = int(page._intended_frame)
    page._set_sequence_pane_visible(True)
    page._update_sequence_follow_ui()


def _activate_features_tab(page) -> None:
    """Select Features inspector tab so presentation visibility is meaningful."""
    page._ensure_features_tab()
    page.inspector_tabs.setCurrentIndex(1)
    page.show()
    QApplication.processEvents()


def _row(frame: int, *, gen: str = "gen-follow", status: str = "cached", sha: str = "", cand=None):
    return {
        "frame_index": frame,
        "status": status,
        "result": {
            "quality_status": "ok",
            "features": {
                "v2_width_h_median": {"value": 1.0, "valid": True, "unit": "px"},
            },
            "centerlines": [{"points": [[0, 0], [1, 1]]}],
            "source_mat_sha256": sha or ("a" * 64),
            "feature_version": "iml2-0.2.0",
            "signal_contract_id": "c1",
        },
        "morph_candidate": cand or {},
        "morph_status": "cached" if cand else "candidate_not_calculated",
        "request_generation_id": gen,
        "source_sha256": sha or ("a" * 64),
    }


def test_sequence_starts_on_first_selected_when_current_outside(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20, 30], current=2)
    assert int(page.frame_spin.value()) == 2
    # Mirror sequence-start outside-frame correction (run_shadow sequence branch).
    frames = page._sequence_frames
    cur = int(page.frame_spin.value())
    if cur not in frames:
        page._suppress_follow_pause = True
        try:
            page._goto_frame(int(frames[0]), immediate=True, pause_follow=False)
        finally:
            page._suppress_follow_pause = False
    page._loaded_frame = int(page.frame_spin.value())
    assert int(page.frame_spin.value()) == 10
    assert page._sequence_follow is True
    assert page._sequence_follow_paused_manual is False


def test_follow_processing_enabled_by_default(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [1, 2, 3], current=1)
    assert page._sequence_follow is True
    assert page._chk_seq_follow is not None
    assert page._chk_seq_follow.isChecked()
    assert "Follow processing" in page._chk_seq_follow.text()


def test_frame_done_selects_latest_when_follow_enabled(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._source_sha = "a" * 64
    page._on_sequence_frame_done(_row(20, sha=page._source_sha))
    QApplication.processEvents()
    assert page._sequence_last_completed_frame == 20
    assert int(page.frame_spin.value()) == 20
    assert any(int(r["frame_index"]) == 20 for r in page._sequence_results)


def test_manual_row_selection_disables_follow(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._source_sha = "a" * 64
    page._sequence_results = [_row(10, sha=page._source_sha), _row(20, sha=page._source_sha)]
    page._sequence_last_completed_frame = 20
    page._fill_sequence_table()
    page._open_sequence_row(0, 0)
    QApplication.processEvents()
    assert page._sequence_follow is False
    assert page._sequence_follow_paused_manual is True
    assert page._btn_resume_follow is not None
    assert page._btn_resume_follow.isVisible()
    assert "manually" in (page._seq_follow_status.text() or "").lower()


def test_resume_follow_selects_latest_completed(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._source_sha = "a" * 64
    page._sequence_results = [_row(10, sha=page._source_sha), _row(20, sha=page._source_sha)]
    page._sequence_last_completed_frame = 20
    page._pause_sequence_follow_manual()
    page.frame_spin.setValue(10)
    page._loaded_frame = 10
    page._resume_sequence_follow()
    QApplication.processEvents()
    assert page._sequence_follow is True
    assert page._sequence_follow_paused_manual is False
    assert int(page.frame_spin.value()) == 20


def test_other_frame_result_does_not_overwrite_manual_selection(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    assert int(page.frame_spin.value()) == 10
    assert int(page._intended_frame) == 10
    assert int(page._loaded_frame) == 10
    assert page._sequence_frames == [10, 20]
    page._source_sha = "a" * 64
    page._sequence_follow = False
    page._sequence_follow_paused_manual = True
    page._morph_result_dict = {"frame_index": 10, "result_hash": "keep"}
    page._features_populated = False
    page._ensure_features_tab()
    page._update_features_identity_line()
    identity_before = page._features_identity_label.text() if page._features_identity_label else ""
    nav_before = int(page._frame_navigation_generation)
    page._on_sequence_frame_done(_row(20, sha=page._source_sha))
    # Allow deferred activate/refresh callbacks to run — they must not rewind intent.
    QApplication.processEvents()
    assert int(page.frame_spin.value()) == 10
    assert int(page.frame_slider.value()) == 10
    assert int(page._intended_frame) == 10
    assert int(page._loaded_frame) == 10
    assert int(page._frame_navigation_generation) == nav_before
    assert page._morph_result_dict.get("frame_index") == 10
    assert page._morph_result_dict.get("result_hash") == "keep"
    assert len(page._sequence_results) == 1
    assert int(page._sequence_results[0]["frame_index"]) == 20
    if page._features_identity_label is not None and identity_before:
        assert "10" in page._features_identity_label.text()
        assert page._features_identity_label.text() == identity_before


def test_features_empty_pending_and_outside():
    ru_p = features_empty_message("pending", "ru")
    en_p = features_empty_message("pending", "en")
    assert "ещё не завершён" in ru_p
    assert "not finished" in en_p.lower()
    ru_o = features_empty_message("outside_sequence", "ru", frame=2)
    en_o = features_empty_message("outside_sequence", "en", frame=2)
    assert "Кадр 2" in ru_o
    assert "Frame 2" in en_o
    assert "Следовать" in ru_o
    assert "Follow processing" in en_o


def test_features_empty_state_pending_on_page(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._result = None
    page._result_ser = None
    page._features_populated = False
    page._ensure_features_tab()
    page._update_features_empty_state()
    assert page._features_empty_label is not None
    # Unit-level: use isHidden — isVisible() is false under an inactive tab parent.
    assert page._features_empty_label.isHidden() is False
    assert page._features_view is not None
    assert page._features_view.isHidden() is True
    assert "not finished" in page._features_empty_label.text().lower()


def test_features_empty_state_outside_sequence(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=2)
    page._ensure_features_tab()
    page._update_features_empty_state()
    assert page._features_empty_label.isHidden() is False
    assert "not part of the selected sequence" in page._features_empty_label.text().lower()


def test_completed_row_selection_hydrates_features(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._source_sha = "a" * 64
    page._running = False
    row = _row(20, sha=page._source_sha)
    page._sequence_results = [row]
    page._sequence_last_completed_frame = 20
    page._hydrate_sequence_row_to_inspector(row, reason="manual")
    QApplication.processEvents()
    page._ensure_features_tab()
    page._populate_features()
    assert page._features_model is not None
    assert page._features_model.rowCount() >= 1
    assert "Frame: 20" in page._features_identity_label.text() or "20" in page._features_identity_label.text()


def test_completed_row_selection_hydrates_candidate_cache(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._source_sha = "a" * 64
    page._running = False
    cand = {
        "frame_index": 10,
        "candidate": "frequency_spread_candidate",
        "result_hash": "cand-hash",
        "source_sha256": page._source_sha,
        "diagnostics_cache_id": "d1",
        "ruleset_hash": "r1",
        "evidence_ledger": [],
    }
    row = _row(10, sha=page._source_sha, cand=cand)
    page._sequence_results = [row]
    page.frame_spin.setValue(10)
    page._loaded_frame = 10
    page._bind_sequence_row_candidate(row)
    assert page._morph_result_dict is not None
    assert page._morph_result_dict.get("result_hash") == "cand-hash"
    assert page._morph_cache_status == "cached"


def test_pending_row_does_not_rerun_v2(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    assert int(page.frame_spin.value()) == 10
    page._source_sha = "a" * 64
    calls = {"n": 0}
    page.run_shadow = lambda *a, **k: calls.__setitem__("n", calls["n"] + 1)  # type: ignore[method-assign]
    pending = {
        "frame_index": 10,
        "status": "pending",
        "result": None,
        "request_generation_id": "gen-follow",
        "source_sha256": page._source_sha,
    }
    page._hydrate_sequence_row_to_inspector(pending, reason="manual")
    QApplication.processEvents()
    assert calls["n"] == 0
    page._ensure_features_tab()
    page._update_features_empty_state()
    assert page._features_empty_label.isHidden() is False
    assert page._features_view is not None
    assert page._features_view.isHidden() is True
    assert (page._features_model is None) or (page._features_model.rowCount() == 0)


def test_failed_row_shows_failure_reason(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._source_sha = "a" * 64
    failed = _row(10, sha=page._source_sha, status="failed")
    failed["result"] = None
    page._sequence_results = [failed]
    page._hydrate_sequence_row_to_inspector(failed, reason="manual")
    QApplication.processEvents()
    page._ensure_features_tab()
    page._update_features_empty_state()
    text = page._features_empty_label.text().lower()
    assert "could not obtain" in text or "не удалось" in text


def test_sequence_completion_clears_running_message():
    text = format_sequence_progress_status(
        lang="en",
        completed=6,
        total=6,
        progress_frame=None,
        last_completed_frame=31,
        running=False,
        cancelled=False,
        finished=True,
    )
    assert "complete" in text.lower()
    assert "running" not in text.lower()
    ru = format_sequence_progress_status(
        lang="ru",
        completed=6,
        total=6,
        progress_frame=None,
        last_completed_frame=31,
        running=False,
        cancelled=False,
        finished=True,
    )
    assert "завершена" in ru.lower()


def test_features_identity_line_updates_per_selected_row(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._ensure_features_tab()
    page._update_features_identity_line()
    t10 = page._features_identity_label.text()
    assert "Frame: 10" in t10 or "Кадр: 10" in t10
    nav_before = int(page._frame_navigation_generation)
    # Real navigation API — never mutate _loaded_frame as a substitute for intent.
    page._goto_frame(20, immediate=True, pause_follow=True, reason="user_frame_entry")
    QApplication.processEvents()
    assert int(page._intended_frame) == 20
    assert int(page.frame_spin.value()) == 20
    assert int(page.frame_slider.value()) == 20
    assert int(page._frame_navigation_generation) > nav_before
    assert page._sequence_follow_paused_manual is True or page._sequence_follow is False
    page._update_features_identity_line()
    t20 = page._features_identity_label.text()
    assert "Frame: 20" in t20 or "Кадр: 20" in t20
    assert "00:19" in t20  # frame 20 → minute 19
    assert "pending" in t20.lower() or "ожидание" in t20.lower() or "not ready" in t20.lower()
    assert t10 != t20


def test_shortcut_control_has_readable_text(qtbot, session):
    page = _page(qtbot, session)
    page.resize(1400, 900)
    page._update_shortcuts_help_button()
    assert page._btn_shortcuts_help is not None
    assert page._btn_shortcuts_help.text() == "Shortcuts"
    assert page._btn_shortcuts_help.accessibleName()
    assert "shortcut" in page._btn_shortcuts_help.toolTip().lower()
    page.i18n.set_language("ru")
    page.retranslate_ui()
    assert page._btn_shortcuts_help.text() == "Команды"


def test_shortcut_help_explains_per_frame_features():
    en = format_shortcuts_help("en")
    ru = format_shortcuts_help("ru")
    assert "Follow processing" in en
    assert "only for the selected frame" in en
    assert "Следовать за обработкой" in ru
    assert "только для выбранного кадра" in ru


def test_old_generation_callback_discarded(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._v2_generation_id = "new-gen"
    page._on_sequence_frame_done(_row(10, gen="old-gen", sha="a" * 64))
    assert page._sequence_results == []


def test_cancel_remains_safe(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._worker = None
    page._cancel_run()
    assert page._running is False
    assert page._sequence_cancelled is True
    assert page.btn_run.isEnabled()


def test_production_rule_engine_unchanged():
    engine = ROOT / "src/ionogram_morphology_lab/rules/engine.py"
    assert "morphology_candidate" not in engine.read_text(encoding="utf-8")


def test_shadow_only_contracts_unchanged():
    assert SEQUENCE_STATE_CONTRACT_VERSION == 1
    types = (
        ROOT / "src/ionogram_morphology_lab/morphology_candidate/types.py"
    ).read_text(encoding="utf-8")
    assert "production_applied" in types
    assert "scientifically_validated" in types
    page_src = (
        ROOT / "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py"
    ).read_text(encoding="utf-8")
    assert "shadow" in page_src.lower()


def test_build_identity_phase_4c1e2d():
    from ionogram_morphology_lab.ui.build_identity import collect_build_identity

    ident = collect_build_identity(compute_sha=False)
    assert ident.get("release_phase") == "4C.1e.3"


def test_progress_status_while_running():
    text = format_sequence_progress_status(
        lang="en",
        completed=3,
        total=6,
        progress_frame=31,
        last_completed_frame=30,
        running=True,
        cancelled=False,
        finished=False,
    )
    assert "3" in text and "6" in text
    assert "31" in text
    assert "Feature Pipeline V2 is running" not in text


def test_active_features_tab_pending_then_hydrated(qtbot, session):
    """Real UX: pending empty state on the active Features tab, then table after hydrate."""
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    assert int(page.frame_spin.value()) == 10
    assert int(page._intended_frame) == 10
    page._source_sha = "a" * 64
    page._result = None
    page._result_ser = None
    page._features_populated = False
    _activate_features_tab(page)
    page._update_features_empty_state()
    QApplication.processEvents()
    assert int(page._intended_frame) == 10
    assert int(page.frame_spin.value()) == 10
    assert page._features_empty_label is not None
    assert page._features_empty_label.isVisible()
    empty = page._features_empty_label.text().lower()
    assert "not finished" in empty
    assert "not part of the selected sequence" not in empty
    assert page._features_view is not None
    assert page._features_view.isHidden() is True
    assert page._features_model is not None
    assert page._features_model.rowCount() == 0
    assert "10" in (page._features_identity_label.text() or "")

    page._running = False
    row = _row(10, sha=page._source_sha)
    page._sequence_results = [row]
    page._sequence_last_completed_frame = 10
    page._apply_frame_result(row)
    page._populate_features()
    page._update_features_empty_state()
    QApplication.processEvents()
    assert int(page._intended_frame) == 10
    assert page._features_empty_label.isHidden() is True
    assert page._features_view.isHidden() is False
    assert page._features_view.isVisible()
    assert page._features_model.rowCount() >= 1
    assert "10" in (page._features_identity_label.text() or "")


def test_enter_sequence_configures_valid_frame_range(qtbot, session):
    page = _page(qtbot, session)
    # Synthetic sources may refresh to a small n_frames; helper must expand the range.
    page._n_frames = 1
    page.frame_spin.setMaximum(1)
    _enter_sequence(page, [10, 20, 30], current=10)
    assert page.frame_spin.maximum() >= 30
    assert int(page.frame_spin.value()) == 10
    assert int(page._loaded_frame) == 10


def test_stale_deferred_refresh_does_not_reset_intended_frame(qtbot, session):
    """Root-cause regression: deferred refresh must not rewind selector after intent=10."""
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    page._use_process_v2 = False
    qtbot.addWidget(page)
    page.show()
    # Capture the navigation generation that the constructor-scheduled activate will use.
    scheduled_nav = int(page._frame_navigation_generation)
    _ensure_frame_spin_range(page, [10, 20], 10)
    page._schedule_frame_load = lambda *_a, **_k: None  # type: ignore[method-assign]
    page.wait_until_frame_ready = lambda *_a, **_k: True  # type: ignore[method-assign]
    idx = page.mode_combo.findData("sequence")
    page.mode_combo.setCurrentIndex(idx)
    page._sequence_frames = [10, 20]
    page._running = True
    page._suppress_follow_pause = True
    try:
        page._goto_frame(10, immediate=True, pause_follow=False, reason="sequence_start")
    finally:
        page._suppress_follow_pause = False
    assert int(page._intended_frame) == 10
    assert page._frame_navigation_generation > scheduled_nav
    # Run the stale deferred refresh path explicitly (as the queued callback would).
    page._run_deferred_refresh(scheduled_nav, reason="initial_page_activation")
    QApplication.processEvents()
    assert int(page.frame_spin.value()) == 10
    assert int(page.frame_slider.value()) == 10
    assert int(page._intended_frame) == 10
    assert int(page._loaded_frame) == 10 or int(page._loaded_frame) == -1
    page._loaded_frame = 10
    page._result = None
    page._result_ser = None
    page._features_populated = False
    _activate_features_tab(page)
    page._update_features_empty_state()
    text = (page._features_empty_label.text() or "").lower()
    assert "not finished" in text
    assert "not part of the selected sequence" not in text
    assert "frame 10" in (page._features_identity_label.text() or "").lower() or "10" in (
        page._features_identity_label.text() or ""
    )


def test_stale_frame_load_completion_does_not_rewrite_intent(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    nav = int(page._frame_navigation_generation)
    page._active_generation_id = "old-load"
    page._pending_frame_request = {
        "request_generation_id": "old-load",
        "navigation_generation": max(0, nav - 1),
        "frame_index": 1,
        "source_sha": "",
        "reason": "initial_page_activation",
    }
    # Fake a late frame-1 completion after intent moved to 10.
    class _Ctx:
        frame_index = 1
        raw_frame_sha256 = "r"
        source_sha256 = "a" * 64
        source_mat_path = "x.mat"
        interpreted_time = "00:00"

    page._on_frame_loaded(
        {
            "request_generation_id": "old-load",
            "context": _Ctx(),
            "raw": np.zeros((4, 4), dtype=np.float32),
            "timings": {},
        }
    )
    assert int(page.frame_spin.value()) == 10
    assert int(page._intended_frame) == 10
    assert int(page._loaded_frame) != 1


def test_viewer_sync_stale_event_discarded(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._sync_auto = True
    page._viewer_sync_accept = False
    page.session.current_frame = 1
    page._on_session_frame_changed()
    assert int(page._intended_frame) == 10
    assert int(page.frame_spin.value()) == 10


def test_frame_done_follow_on_selects_completed_frame(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._source_sha = "a" * 64
    page._sequence_follow = True
    page._sequence_follow_paused_manual = False
    page._on_sequence_frame_done(_row(20, sha=page._source_sha))
    QApplication.processEvents()
    assert int(page._intended_frame) == 20
    assert int(page.frame_spin.value()) == 20


def test_spin_slider_atomic_after_intent(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    assert int(page.frame_spin.value()) == int(page.frame_slider.value()) == 10
    page._apply_selector_frame(20)
    assert int(page.frame_spin.value()) == 20
    assert int(page.frame_slider.value()) == 20


def test_source_sha_mismatch_frame_done_discarded(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._source_sha = "a" * 64
    before = list(page._sequence_results)
    page._on_sequence_frame_done(_row(10, sha="b" * 64))
    assert page._sequence_results == before
    assert int(page._intended_frame) == 10


def test_user_spin_navigation_updates_intended_and_identity(qtbot, session):
    """Genuine frame_spin user path (valueChanged → commit), not _loaded_frame mutation."""
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._source_sha = "a" * 64
    _activate_features_tab(page)
    page._result = None
    page._result_ser = None
    page._features_populated = False
    page._update_features_empty_state()
    page._update_features_identity_line()
    assert int(page._intended_frame) == 10
    nav_before = int(page._frame_navigation_generation)
    # Simulate user changing the spin (fires valueChanged → debounce pending).
    page.frame_spin.setValue(20)
    QApplication.processEvents()
    assert page._pending_spin_frame == 20 or int(page.frame_spin.value()) == 20
    # editingFinished / commit path used by real UI after spin edit.
    page._commit_spin_edit()
    QApplication.processEvents()
    assert int(page._intended_frame) == 20
    assert int(page.frame_spin.value()) == 20
    assert int(page.frame_slider.value()) == 20
    assert int(page._frame_navigation_generation) > nav_before
    assert page._sequence_follow is False or page._sequence_follow_paused_manual is True
    ident = page._features_identity_label.text()
    assert "Frame: 20" in ident or "Кадр: 20" in ident
    empty = (page._features_empty_label.text() or "").lower()
    assert "not finished" in empty or "pending" in empty or "ещё не" in empty
    assert "frame 10" not in empty
    # Stale frame-10 callback cannot revert identity.
    page._on_sequence_frame_done(_row(10, sha=page._source_sha))
    QApplication.processEvents()
    assert int(page._intended_frame) == 20
    assert "Frame: 20" in page._features_identity_label.text() or "Кадр: 20" in (
        page._features_identity_label.text()
    )


def test_result_hydration_identity_ignores_stale_other_frame(qtbot, session):
    """Full sequence-row hydration path — not a partial _apply_frame_result-only probe."""
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=20)
    page._source_sha = "a" * 64
    page._running = False
    page._sequence_follow = False
    page._sequence_follow_paused_manual = True
    page._ensure_features_tab()
    page._result = None
    page._result_ser = None
    page._cache_status = "not_computed"
    page._update_features_identity_line()
    pending = page._features_identity_label.text()
    assert "Frame: 20" in pending or "Кадр: 20" in pending
    assert "not ready" in pending.lower() or "не готов" in pending.lower() or "pending" in pending.lower()

    row20 = _row(20, sha=page._source_sha)
    # Nested result intentionally omits frame_index — wrapper frame must stamp it.
    assert "frame_index" not in row20["result"]
    page._sequence_results = [row20]
    page._sequence_last_completed_frame = 20
    page._hydrate_sequence_row_to_inspector(row20, reason="manual")
    QApplication.processEvents()

    assert int(page._intended_frame) == 20
    assert int(page.frame_spin.value()) == 20
    assert page._result_ser is not None
    assert int(page._result_ser.get("frame_index", -1)) == 20
    assert page._cache_status in {"cached", "recomputed"}
    assert page._features_model is not None
    assert page._features_model.rowCount() >= 1
    ready = page._features_identity_label.text()
    assert "Frame: 20" in ready or "Кадр: 20" in ready
    assert "cached" in ready.lower() or "new" in ready.lower() or "кэш" in ready.lower() or "новый" in ready.lower()
    assert "ready" in ready.lower() or "готово" in ready.lower()
    assert page._features_empty_label is None or page._features_empty_label.isHidden()
    cand_hash = (page._morph_result_dict or {}).get("result_hash")

    # Stale other-frame completion with Follow off — row may update; inspector stays on 20.
    page._on_sequence_frame_done(_row(10, sha=page._source_sha))
    QApplication.processEvents()
    assert int(page._intended_frame) == 20
    assert int(page.frame_spin.value()) == 20
    assert int((page._result_ser or {}).get("frame_index", -1)) == 20
    after_stale = page._features_identity_label.text()
    assert "Frame: 20" in after_stale or "Кадр: 20" in after_stale
    assert "Frame: 10" not in after_stale and "Кадр: 10" not in after_stale
    assert page._features_model.rowCount() >= 1
    if cand_hash is not None:
        assert (page._morph_result_dict or {}).get("result_hash") == cand_hash
    assert any(int(r["frame_index"]) == 10 for r in page._sequence_results)


def test_compatible_cached_row_hydrates_ready_identity(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [20], current=20)
    page._source_sha = "a" * 64
    page._running = False
    row = _row(20, sha=page._source_sha, status="cached")
    page._sequence_results = [row]
    page._hydrate_sequence_row_to_inspector(row, reason="manual")
    QApplication.processEvents()
    assert page._cache_status == "cached"
    text = page._features_identity_label.text().lower()
    assert "frame: 20" in text or "кадр: 20" in text
    assert "cached" in text or "кэш" in text
    assert page._result_matches_intended_frame(page._result_ser)


def test_compatible_recomputed_row_hydrates_new_identity(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [20], current=20)
    page._source_sha = "a" * 64
    page._running = False
    row = _row(20, sha=page._source_sha, status="recomputed")
    page._sequence_results = [row]
    page._hydrate_sequence_row_to_inspector(row, reason="manual")
    QApplication.processEvents()
    assert page._cache_status == "recomputed"
    text = page._features_identity_label.text().lower()
    assert "new" in text or "новый" in text or "recomputed" in text


def test_row_source_mismatch_rejected(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [20], current=20)
    page._source_sha = "a" * 64
    page._running = False
    bad = _row(20, sha="b" * 64)
    page._hydrate_sequence_row_to_inspector(bad, reason="manual")
    QApplication.processEvents()
    # Source guard: inspector must not adopt foreign-source result as ready.
    assert page._result_ser is None or not page._result_matches_intended_frame(page._result_ser) or (
        str((page._result_ser or {}).get("source_mat_sha256") or "") == page._source_sha
    )
    # Hydrate returns early on source mismatch before bind.
    assert page._cache_status in {"not_computed", "cached", "recomputed"}
    if page._result_ser is None:
        text = page._features_identity_label.text().lower() if page._features_identity_label else ""
        assert "not ready" in text or "pending" in text or "не готов" in text or text == ""


def test_old_generation_row_rejected(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [20], current=20)
    page._source_sha = "a" * 64
    page._running = False
    page._v2_generation_id = "gen-follow"
    page._sequence_generation_id = "gen-follow"
    old = _row(20, sha=page._source_sha, gen="old-gen")
    before = page._result_ser
    page._hydrate_sequence_row_to_inspector(old, reason="manual")
    QApplication.processEvents()
    assert page._result_ser is before


def test_wrapper_frame_stamped_when_nested_result_lacks_frame(qtbot, session):
    page = _page(qtbot, session)
    payload = page._extract_sequence_row_payload(
        {
            "frame_index": 31,
            "status": "cached",
            "source_sha256": "a" * 64,
            "result": {"features": {"x": {"value": 1}}, "source_mat_sha256": "a" * 64},
        }
    )
    assert payload["frame_index"] == 31
    assert payload["result"]["frame_index"] == 31


def test_identity_never_ready_for_incompatible_result(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [20], current=20)
    page._source_sha = "a" * 64
    page._ensure_features_tab()
    page._result_ser = {
        "frame_index": 10,
        "features": {"x": {"value": 1}},
        "source_mat_sha256": page._source_sha,
    }
    page._cache_status = "cached"
    page._update_features_identity_line()
    text = page._features_identity_label.text()
    assert "Frame: 20" in text or "Кадр: 20" in text
    assert "cached" not in text.lower() or "frame: 10" not in text.lower()
    assert "Frame: 10" not in text


def test_manual_frame_change_pauses_follow_resume_restores(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._source_sha = "a" * 64
    page._sequence_results = [_row(10, sha=page._source_sha), _row(20, sha=page._source_sha)]
    page._sequence_last_completed_frame = 20
    page.frame_spin.setValue(20)
    page._commit_spin_edit()
    QApplication.processEvents()
    assert page._sequence_follow_paused_manual is True or page._sequence_follow is False
    assert int(page._intended_frame) == 20
    page._resume_sequence_follow()
    QApplication.processEvents()
    assert page._sequence_follow is True
    assert int(page._intended_frame) == 20
    assert "20" in (page._features_identity_label.text() if page._features_identity_label else "20")
