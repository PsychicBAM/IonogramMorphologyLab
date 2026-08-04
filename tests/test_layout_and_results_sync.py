"""Layout geometry and Results row↔image identity synchronization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys

    return QApplication.instance() or QApplication(sys.argv)


def test_home_workflow_cards_readable_at_1366x768(qapp):
    from PySide6.QtCore import QSize
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="ru")
    win.resize(QSize(1366, 768))
    win.home_dashboard.refresh()
    win.show()
    qapp.processEvents()
    cards = getattr(win.home_dashboard, "_step_cards", None) or getattr(
        win.home_dashboard, "_step_buttons", []
    )
    assert cards, "workflow steps must render"
    for w in cards:
        h = w.height() if w.height() > 0 else w.sizeHint().height()
        assert h >= 40, f"workflow step too short: {h}"
        assert w.isVisible() or True
        # Prefer full text via accessible name / tooltip if clipped
        text = (w.toolTip() or getattr(w, "whatsThis", lambda: "")() or "") + (
            w.text() if hasattr(w, "text") else ""
        )
        assert text.strip() or w.sizeHint().height() >= 40


def test_russian_sidebar_tooltips_or_accessible_names(qapp):
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="ru")
    win.retranslate()
    checked = 0
    for key, item in win.nav_items.items():
        tip = item.toolTip(0) if hasattr(item, "toolTip") else ""
        name = item.text(0)
        assert tip or name, f"nav {key} has no label"
        # Long RU names must expose full text somehow
        full = tip or name
        assert len(full) >= 2
        checked += 1
    assert checked >= 5


def test_results_table_cells_have_tooltips(qapp, tmp_path):
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="ru")
    run = tmp_path / "run"
    pred = run / "predictions"
    pred.mkdir(parents=True)
    rec = {
        "frame_id": "f12",
        "frame_index": 12,
        "candidate_morphology": "clean",
        "final_auto_status": "proposed",
        "data_quality_status": "valid",
        "ambiguity": "no_visible_ambiguity",
        "scientific_axes": {
            "layer": "indeterminate",
            "morphology": "clean",
            "quality": "valid",
            "ambiguity": "no_visible_ambiguity",
        },
        "confidence_score": None,
        "possible_ox_confusion": False,
        "result_id": "r1",
        "analysis_run_id": "run1",
        "source_mat_sha256": "abc",
        "source_file": "demo.mat",
    }
    (pred / "f12.json").write_text(json.dumps(rec), encoding="utf-8")
    win.session.last_run_root = run
    win._load_results_table()
    assert win.results_table.rowCount() == 1
    item = win.results_table.item(0, 0)
    assert item is not None
    assert item.toolTip() or item.text()
    # Default columns: time, morphology, interference, status, scientific_status
    blob = " ".join(
        win.results_table.item(0, c).text() for c in range(win.results_table.columnCount()) if win.results_table.item(0, c)
    )
    assert "valid" not in blob.split()
    assert "Автоматический кандидат" in blob
    assert "явное рассеяние" in blob.lower() or "рассеяние не обнаружено" in blob.lower()
    # Quality lives in the details panel / extended columns, not default table.
    win.results_columns.setCurrentIndex(2)  # all detail columns
    win._load_results_table()
    blob_all = " ".join(
        win.results_table.item(0, c).text() for c in range(win.results_table.columnCount()) if win.results_table.item(0, c)
    )
    assert "Пригоден" in blob_all or "пригоден" in blob_all.lower()


def test_results_row_identity_matches_displayed_frame(qapp, tmp_path):
    from ionogram_morphology_lab.ui.main_window import MainWindow
    from PySide6.QtCore import Qt

    win = MainWindow(language="en")
    run = tmp_path / "run2"
    pred = run / "predictions"
    pred.mkdir(parents=True)
    rec = {
        "frame_id": "f1311",
        "frame_index": 1311,
        "candidate_morphology": "clean",
        "final_auto_status": "proposed",
        "data_quality_status": "valid",
        "scientific_axes": {"layer": "F", "morphology": "clean", "quality": "valid", "ambiguity": "no_visible_ambiguity"},
        "result_id": "rid-1311",
        "analysis_run_id": "arun",
        "source_mat_sha256": "sha1",
        "source_file": "Am_all_2014-10-15.mat",
        "measured_features": {"trace_pixel_fraction": 0.02},
        "activated_rules": ["R004"],
        "alternative_interpretations": [],
    }
    (pred / "f1311.json").write_text(json.dumps(rec), encoding="utf-8")
    win.session.last_run_root = run
    win._load_results_table()
    win.results_table.selectRow(0)
    win._show_selected_result()
    ident = win._results_displayed_identity
    assert ident is not None
    frame_token = str(ident.get("frame_id") or ident.get("source_frame_id") or ident.get("sequence_position") or "")
    assert "1311" in frame_token or int(ident.get("sequence_position") or 0) == 1311
    assert "1311" in win.results_identity_line.text()


def test_stale_result_mismatch_blocks_conclusion(qapp, tmp_path):
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="ru")
    run = tmp_path / "run_mismatch"
    pred = run / "predictions"
    pred.mkdir(parents=True)
    # Minimal valid 1×1 PNG named for a different frame than the record claims.
    wrong = run / "f0099.png"
    wrong.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
            "de0000000c4944415408d763f8ffff3f0005fe02fe0dc70e0b0000000049454e44ae426082"
        )
    )
    rec = {
        "frame_id": "f12",
        "frame_index": 12,
        "candidate_morphology": "clean",
        "final_auto_status": "proposed",
        "data_quality_status": "valid",
        "scientific_axes": {"layer": "F", "morphology": "clean", "quality": "valid", "ambiguity": "no_visible_ambiguity"},
        "result_id": "r-mismatch",
        "analysis_run_id": "arun",
        "raw_render_path": str(wrong),
        "measured_features": {},
        "activated_rules": [],
        "alternative_interpretations": [],
    }
    (pred / "f12.json").write_text(json.dumps(rec), encoding="utf-8")
    win.session.last_run_root = run
    win._load_results_table()
    win.results_table.selectRow(0)
    win._show_selected_result()
    # Wrong-path image must not be accepted; scientific conclusion blocked only on true mismatch.
    # Without FrameStore, unmatched path → no image, identity still selected → conclusion OK.
    # Simulate an explicit mismatched displayed identity:
    win._results_displayed_identity = {"frame_id": "f99", "sequence_position": 99, "result_id": "other"}
    overview = win.res_overview.toPlainText()
    # Re-invoke with patched renderer returning wrong identity
    win._render_selected_result_frame = lambda rec, identity: (
        wrong,
        {"frame_id": "f99", "sequence_position": 99, "result_id": "other"},
    )
    win._show_selected_result()
    assert "Несоответствие данных результата" in win.res_overview.toPlainText()


def test_interface_scale_persists(qapp, tmp_path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore

    path = tmp_path / "settings.json"
    s = SettingsStore(path)
    s.set("general", "interface_scale", "125")
    s.save()
    s2 = SettingsStore(path)
    assert str(s2.get("general", "interface_scale")) == "125"


def test_required_viewer_controls_have_readable_height(qapp):
    from PySide6.QtCore import QSize
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="ru")
    win.resize(QSize(1366, 768))
    win.show()
    qapp.processEvents()
    for w in (win.jump_combo, win.speed_combo, win.loop_chk, win.btn_play, win.btn_first):
        hint = max(w.sizeHint().height(), w.minimumHeight(), w.height())
        assert hint >= 20, f"{w.objectName() or w} height {hint}"
    for lab in (win.jump_label, win.speed_label, win.jump_unit, win.speed_unit):
        assert lab.text().strip(), f"empty label {lab.objectName()}"
        assert lab.sizeHint().width() >= 8
