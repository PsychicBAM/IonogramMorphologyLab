"""Phase 4C.1e.3 — embedded Sequence Results readability, columns, palette, candidate mode."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.ui.sequence_table_presentation import (
    COMPACT_VISIBLE_COLUMNS,
    ESSENTIAL_COLUMNS,
    FULL_VISIBLE_COLUMNS,
    SEQ_COL_CANDIDATE,
    SEQ_COL_FRAME,
    SEQ_COL_TIME,
    SEQ_COLUMN_COUNT,
    default_min_widths,
    marker_colors,
    preferred_widths,
    profile_label,
    visible_columns_for_profile,
)
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.ui.theme import apply_app_theme

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
    s.project = create_project("P4C1E3", language="en", workspace_parent=tmp_path / "ws")
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


def _row(frame: int, *, sha: str = "a" * 64, status: str = "cached") -> dict:
    return {
        "frame_index": frame,
        "status": status,
        "source_sha256": sha,
        "request_generation_id": "gen-follow",
        "result": {
            "frame_index": frame,
            "source_mat_sha256": sha,
            "feature_version": "iml2-0.2.0",
            "quality_status": "ok",
            "features": {
                "v2_interference_fraction": {"value": 0.1},
                "v2_width_h_median": {"value": 1.2},
                "v2_width_v_median": {"value": 3.4},
            },
            "centerlines": [{"id": 1}],
        },
        "morph_candidate": {
            "candidate": "spread_F",
            "assessability": "assessable",
            "evidence_strength": "moderate",
            "frame_index": frame,
            "result_hash": f"h{frame}",
        },
        "morph_status": "cached",
    }


def _enter_sequence(page, frames: list[int], *, current: int | None = None) -> None:
    idx = page.mode_combo.findData("sequence")
    page.mode_combo.setCurrentIndex(idx)
    page._sequence_frames = list(frames)
    page._sequence_results = []
    page._sequence_last_completed_frame = None
    page._sequence_follow = True
    page._sequence_follow_paused_manual = False
    page._running = True
    page._job_state = "computing"
    page._v2_generation_id = "gen-follow"
    page._sequence_generation_id = "gen-follow"
    page._schedule_frame_load = lambda *_a, **_k: None  # type: ignore[method-assign]
    page.wait_until_frame_ready = lambda *_a, **_k: True  # type: ignore[method-assign]
    max_frame = max(frames + ([current] if current else []))
    page._n_frames = max(int(page._n_frames or 1), max_frame)
    page.frame_spin.setMaximum(page._n_frames)
    page.frame_slider.setMaximum(page._n_frames)
    target = int(current) if current is not None else int(frames[0])
    page._suppress_follow_pause = True
    try:
        page._goto_frame(target, immediate=True, pause_follow=False, reason="sequence_start")
    finally:
        page._suppress_follow_pause = False
    page._raw = np.zeros((16, 16), dtype=np.float32)
    page._loaded_frame = int(page._intended_frame)
    page._source_sha = "a" * 64


def test_compact_and_full_profiles_constants():
    assert SEQ_COL_FRAME in COMPACT_VISIBLE_COLUMNS
    assert SEQ_COL_TIME in COMPACT_VISIBLE_COLUMNS
    assert set(ESSENTIAL_COLUMNS) <= set(COMPACT_VISIBLE_COLUMNS)
    assert len(FULL_VISIBLE_COLUMNS) == SEQ_COLUMN_COUNT
    assert set(COMPACT_VISIBLE_COLUMNS) < set(FULL_VISIBLE_COLUMNS)
    assert visible_columns_for_profile("compact") == COMPACT_VISIBLE_COLUMNS
    assert visible_columns_for_profile("full") == FULL_VISIBLE_COLUMNS
    assert "Compact" in profile_label("compact", "en")
    assert "Компактная" in profile_label("compact", "ru")


def test_marker_colors_dark_theme_strong_foreground():
    dark = marker_colors(
        displayed=True,
        failed=False,
        processing=False,
        last_completed=False,
        cached=False,
        theme="dark",
    )
    # Foreground must be light (readable on dark marker bg), not washed grey.
    assert dark.foreground.lightness() > 160
    assert dark.background.lightness() < 120
    light = marker_colors(
        displayed=True,
        failed=False,
        processing=False,
        last_completed=False,
        cached=False,
        theme="light",
    )
    assert light.foreground.lightness() < 80


def test_min_widths_use_font_metrics(qtbot):
    from PySide6.QtWidgets import QLabel

    lab = QLabel("M")
    qtbot.addWidget(lab)
    mins = default_min_widths(lab.font())
    prefs = preferred_widths(lab.font())
    assert mins[SEQ_COL_FRAME] >= 36
    assert prefs[SEQ_COL_CANDIDATE] >= mins[SEQ_COL_CANDIDATE]


def test_embedded_table_enabled_while_running_and_after_completion(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20, 30], current=10)
    page._sequence_results = [_row(10)]
    page._fill_sequence_table()
    QApplication.processEvents()
    assert page._running is True
    assert page.seq_table.isEnabled()
    assert page._seq_pane is None or page._seq_pane.isEnabled()
    # Simulate completion
    page._running = False
    page._job_state = "completed"
    page._sequence_results = [_row(10), _row(20), _row(30)]
    page._fill_sequence_table()
    page._ensure_sequence_table_interactive()
    QApplication.processEvents()
    assert page.seq_table.isEnabled()
    assert page.seq_table.graphicsEffect() is None
    # Walk parents — none should disable the table
    w = page.seq_table.parentWidget()
    while w is not None and w is not page:
        assert w.isEnabled(), f"parent disabled: {w}"
        w = w.parentWidget()


def test_embedded_compact_hides_nonessential_frame_time_visible(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._running = False
    page._sequence_results = [_row(10), _row(20)]
    page._seq_table_profile = "compact"
    page._seq_column_profile_applied = False
    page._fill_sequence_table()
    QApplication.processEvents()
    assert not page.seq_table.isColumnHidden(SEQ_COL_FRAME)
    assert not page.seq_table.isColumnHidden(SEQ_COL_TIME)
    # A full-only column must be hidden in compact
    full_only = next(c for c in FULL_VISIBLE_COLUMNS if c not in COMPACT_VISIBLE_COLUMNS)
    assert page.seq_table.isColumnHidden(full_only)
    for c in COMPACT_VISIBLE_COLUMNS:
        assert not page.seq_table.isColumnHidden(c)


def test_detached_uses_full_profile(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._running = False
    page._sequence_results = [_row(10)]
    page._fill_sequence_table()
    page._open_sequence_detach()
    QApplication.processEvents()
    assert page._seq_detach_table is not None
    for c in FULL_VISIBLE_COLUMNS:
        assert not page._seq_detach_table.isColumnHidden(c)
    # Embedded remains compact
    assert page._seq_table_profile == "compact"
    full_only = next(c for c in FULL_VISIBLE_COLUMNS if c not in COMPACT_VISIBLE_COLUMNS)
    assert page.seq_table.isColumnHidden(full_only)


def test_horizontal_scroll_and_readable_min_widths(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._running = False
    page._sequence_results = [_row(10)]
    page._seq_table_profile = "full"
    page._seq_column_profile_applied = False
    page._fill_sequence_table()
    page.seq_table.resize(280, 180)
    QApplication.processEvents()
    assert (
        page.seq_table.horizontalScrollBarPolicy()
        == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    mins = default_min_widths(page.seq_table.font())
    for c in COMPACT_VISIBLE_COLUMNS:
        if page.seq_table.isColumnHidden(c):
            continue
        assert page.seq_table.columnWidth(c) >= mins[c] - 1


def test_reset_columns_restores_profile(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._running = False
    page._sequence_results = [_row(10)]
    page._fill_sequence_table()
    page.seq_table.setColumnWidth(SEQ_COL_FRAME, 200)
    page._seq_column_widths_user[SEQ_COL_FRAME] = 200
    page._reset_sequence_column_widths()
    QApplication.processEvents()
    prefs = preferred_widths(page.seq_table.font())
    assert page.seq_table.columnWidth(SEQ_COL_FRAME) == prefs[SEQ_COL_FRAME]
    assert SEQ_COL_FRAME not in page._seq_column_widths_user


def test_columns_menu_checked_states(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._running = False
    page._sequence_results = [_row(10)]
    page._fill_sequence_table()
    page._rebuild_sequence_columns_menu()
    assert page._seq_columns_menu is not None
    actions = [a for a in page._seq_columns_menu.actions() if a.isCheckable()]
    assert actions
    # Frame essential is checked and disabled
    frame_acts = [a for a in actions if a.text() in {"frame", "кадр"}]
    assert frame_acts
    assert frame_acts[0].isChecked()
    assert not frame_acts[0].isEnabled()


def test_tooltips_expose_cell_values(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._running = False
    page._sequence_results = [_row(10)]
    page._fill_sequence_table()
    item = page.seq_table.item(0, SEQ_COL_FRAME)
    assert item is not None
    assert "10" in (item.toolTip() or "")


def test_embedded_text_uses_readable_foreground(qtbot, session):
    app = QApplication.instance()
    assert app is not None
    apply_app_theme(app, "dark")
    page = _page(qtbot, session)
    page.apply_theme("dark")
    _enter_sequence(page, [10], current=10)
    page._running = False
    page._sequence_results = [_row(10, status="cached")]
    page._fill_sequence_table()
    QApplication.processEvents()
    item = page.seq_table.item(0, SEQ_COL_FRAME)
    assert item is not None
    fg = item.foreground().color()
    assert fg.lightness() > 160
    assert item.flags() & Qt.ItemFlag.ItemIsEnabled
    # Restore default theme for other tests
    apply_app_theme(app, "system")


def test_manual_selection_pauses_follow_and_stale_ignored(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10, 20], current=10)
    page._running = False
    page._source_sha = "a" * 64
    page._sequence_results = [_row(10), _row(20)]
    page._sequence_last_completed_frame = 20
    page._fill_sequence_table()
    # Production path: cell click → open row pauses Follow then hydrates.
    page._open_sequence_row(0, 0)
    QApplication.processEvents()
    assert page._sequence_follow_paused_manual or not page._sequence_follow
    assert int(page._intended_frame) == 10
    page._on_sequence_frame_done(_row(20))
    QApplication.processEvents()
    assert int(page._intended_frame) == 10
    page._resume_sequence_follow()
    QApplication.processEvents()
    assert page._sequence_follow is True
    assert int(page._intended_frame) == 20


def test_automatic_candidate_sequence_only_contract(qtbot, session):
    page = _page(qtbot, session)
    # Sequence path may call hydrate/evaluate
    calls = {"hydrate": 0, "calc": 0}

    def _hyd(r, update_panel=False):
        calls["hydrate"] += 1
        r["morph_candidate"] = {"candidate": "spread_F", "frame_index": r.get("frame_index")}
        r["morph_status"] = "new"

    page._hydrate_sequence_row_candidate = _hyd  # type: ignore[method-assign]
    page._calculate_morphology_candidate = lambda force=False: calls.__setitem__(  # type: ignore[method-assign]
        "calc", calls["calc"] + 1
    )
    _enter_sequence(page, [10], current=10)
    page._running = False
    row = _row(10)
    row["morph_candidate"] = {}
    page._sequence_results = [row]
    page._enrich_sequence_morph_candidates()
    assert calls["hydrate"] == 1

    # Single-frame: worker-finished path must not enrich when mode is single + one result
    idx = page.mode_combo.findData("single")
    if idx < 0:
        # fallback data name
        for i in range(page.mode_combo.count()):
            if page.mode_combo.itemData(i) in {"single", "frame", "single_frame"}:
                idx = i
                break
    assert idx >= 0
    page.mode_combo.setCurrentIndex(idx)
    calls["hydrate"] = 0
    # Simulate single-frame completion apply (cache lookup only, no enrich)
    page._apply_frame_result(_row(10))
    assert calls["hydrate"] == 0
    assert calls["calc"] == 0


def test_build_identity_phase_4c1e3():
    from ionogram_morphology_lab.ui.build_identity import collect_build_identity, format_build_identity

    ident = collect_build_identity()
    assert ident.get("release_phase") == "4C.1e.3"
    assert "4C.1e.3" in format_build_identity(ident, "en")


def test_ru_en_retranslate_column_headers(qtbot, session):
    page = _page(qtbot, session)
    page.i18n = get_i18n("ru")
    page.retranslate_ui()
    assert page.seq_table.horizontalHeaderItem(0).text() == "кадр"
    page.i18n = get_i18n("en")
    page.retranslate_ui()
    assert page.seq_table.horizontalHeaderItem(0).text() == "frame"


def test_show_all_columns_profile(qtbot, session):
    page = _page(qtbot, session)
    _enter_sequence(page, [10], current=10)
    page._running = False
    page._sequence_results = [_row(10)]
    page._fill_sequence_table()
    page._set_sequence_table_profile("full")
    QApplication.processEvents()
    assert page._seq_table_profile == "full"
    for c in FULL_VISIBLE_COLUMNS:
        assert not page.seq_table.isColumnHidden(c)
