"""Regression: Ionogram Viewer navigation must never abort the process."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QThread, Signal

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.main_window import MainWindow


@pytest.fixture
def syn_mat(tmp_path: Path):
    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    return syn / "demo_horizontally_diffuse.mat"


@pytest.fixture
def viewer_window(qtbot, tmp_path: Path, syn_mat: Path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    store = SettingsStore(settings_path)
    store.set("performance", "automatic_cache_creation", False)
    store.set("general", "show_onboarding", False)
    store.set("performance", "cache_location", str(tmp_path / "cache"))
    store.save()

    win = MainWindow(language="en")
    win.settings = SettingsStore(settings_path)
    win.session.settings = win.settings
    win.settings.set("general", "show_onboarding", False)
    win.settings.set("performance", "automatic_cache_creation", False)
    qtbot.addWidget(win)
    win.show()
    return win, syn_mat


def _import_and_prepare(win: MainWindow, mat: Path) -> None:
    win.session.profile.update(
        {
            "amplitude_variable_name": "Amp_all",
            "height_bins": 256,
            "frequency_bins": 400,
            "frames_per_file": 3,
            "matrix_layout": "frames_stacked_rows",
            "profile_verification_status": "user-defined-unverified",
            "time_mapping": "matlab_index_minus_1_minute",
            "profile_id": "syn_test_profile",
        }
    )
    win.session.profile_id = "syn_test_profile"
    win.session.set_active_mat(mat)
    win._viewer_ready = False
    win._set_viewer_controls_enabled(False)
    store = win.session.ensure_store()
    st = store.build_cache()
    assert st.valid
    assert win._activate_viewer_if_ready(render=False) is True
    assert win._viewer_ready is True
    assert win.frame_slider.isEnabled()


def test_viewer_controls_safe_without_mat(viewer_window):
    win, _ = viewer_window
    assert win._viewer_ready is False
    assert not win.frame_slider.isEnabled()
    text = win.viewer_status.text().lower()
    assert "not loaded" in text or "не загруж" in text
    assert win.go_to_frame(5) is False
    win._on_frame_slider_moved(10)
    win._on_frame_slider_released()
    win._on_frame_spin(2)
    win.btn_next.click()
    assert win.session.current_frame == 1


def test_slider_updates_frame_safely(viewer_window):
    win, mat = viewer_window
    _import_and_prepare(win, mat)
    assert win.go_to_frame(2, render=True) is True
    assert win.session.current_frame == 2
    assert win.frame_slider.value() == 2
    assert win.frame_spin.value() == 2
    assert "2" in win.viewer_status.text()
    win._on_frame_slider_moved(3)
    assert win.session.current_frame == 3
    win._on_frame_slider_released()
    assert win.session.current_frame == 3
    assert win.frame_spin.value() == 3


def test_out_of_range_clamped(viewer_window):
    win, mat = viewer_window
    _import_and_prepare(win, mat)
    n = win._viewer_n_frames
    assert n == 3
    assert win.go_to_frame(0) is True
    assert win.session.current_frame == 1
    assert win.go_to_frame(999) is True
    assert win.session.current_frame == n
    assert win.frame_slider.value() == n
    assert win.frame_spin.value() == n


def test_slider_spin_stay_synchronized(viewer_window):
    win, mat = viewer_window
    _import_and_prepare(win, mat)
    for fid in (1, 2, 3, 1):
        assert win.go_to_frame(fid, render=False) is True
        assert win.frame_slider.value() == fid
        assert win.frame_spin.value() == fid
        assert win.session.current_frame == fid


def test_no_recursive_signal_storm(viewer_window):
    win, mat = viewer_window
    _import_and_prepare(win, mat)
    calls = {"n": 0}
    original = win.set_current_frame_from_ui

    def counted(frame_id, *, render=True):
        calls["n"] += 1
        return original(frame_id, render=render)

    win.set_current_frame_from_ui = counted  # type: ignore[method-assign]
    win.go_to_frame = lambda frame_id, *, render=True: win.set_current_frame_from_ui(
        frame_id, render=render
    )
    for v in (1, 2, 3, 2, 1, 3):
        win._on_frame_slider_moved(v)
    assert calls["n"] == 6
    assert win.session.current_frame == 3


def test_render_failure_shows_controlled_error(viewer_window, monkeypatch):
    win, mat = viewer_window
    _import_and_prepare(win, mat)

    def boom(*_a, **_k):
        raise RuntimeError("simulated_render_failure")

    monkeypatch.setattr(win, "_render_current_frame", boom)
    ok = win.go_to_frame(2, render=True)
    assert ok is False
    status = win.viewer_status.text().lower()
    assert "error" in status or "ошиб" in status
    assert win.isVisible()
    assert win.go_to_frame(1, render=False) is True


def test_duplicate_cache_build_rejected(viewer_window, tmp_path, monkeypatch):
    win, mat = viewer_window
    win.session.profile.update(
        {
            "amplitude_variable_name": "Amp_all",
            "height_bins": 256,
            "frequency_bins": 400,
            "frames_per_file": 3,
            "matrix_layout": "frames_stacked_rows",
            "profile_id": "syn_dup_cache",
        }
    )
    win.session.profile_id = "syn_dup_cache"
    win.session.set_active_mat(mat)
    win.settings.set("performance", "cache_location", str(tmp_path / "cache_dup"))
    starts = {"n": 0}

    class FakeWorker(QThread):
        progress = Signal(dict)
        finished_ok = Signal(dict)
        failed = Signal(str)

        def __init__(self, store):
            super().__init__()
            self.store = store
            self._running = False

        def start(self, *args, **kwargs):
            starts["n"] += 1
            self._running = True

        def isRunning(self):
            return self._running

    from ionogram_morphology_lab.ui import main_window as mw

    monkeypatch.setattr(mw, "CacheBuildWorker", FakeWorker)
    win._cache_worker = None
    win._build_cache_async()
    assert starts["n"] == 1
    win._build_cache_async()
    assert starts["n"] == 1
    text = win.viewer_status.text().lower()
    assert "cache" in text or "кэш" in text
    # FakeWorker never starts a real OS thread; clear the running flag so Qt
    # session teardown does not wait forever on a phantom QThread.
    worker = getattr(win, "_cache_worker", None)
    if worker is not None:
        worker._running = False
        win._cache_worker = None
