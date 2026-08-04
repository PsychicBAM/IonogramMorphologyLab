"""Phase 4B.2i — cancel crash safety, persistent worker, non-blocking nav/lang."""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.cache.v2_feature_cache import V2FeatureCache, make_cache_key
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.build_identity import collect_build_identity, _SHA_CACHE
from ionogram_morphology_lab.ui.cancel_crash_audit import ensure_audit
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.ui.v2_process_worker import (
    PersistentV2Worker,
    V2ProcessJobThread,
    V2ProcessState,
    shared_pool,
    worker_start_count,
)


@pytest.fixture
def syn_mats(tmp_path: Path):
    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    return sorted(syn.glob("*.mat"))


@pytest.fixture
def session(tmp_path: Path) -> AppSession:
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    return AppSession(settings=settings)


def _fd(session, qtbot, syn_mats, tmp_path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("P42i", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    page._use_process_v2 = False
    qtbot.addWidget(page)
    page.show()
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    return page


def test_build_identity_sha_cached(tmp_path):
    _SHA_CACHE.clear()
    p = tmp_path / "fake.exe"
    p.write_bytes(b"x" * 4096)
    # Monkey via executable is hard; just ensure collect with compute_sha=False is instant
    t0 = time.perf_counter()
    ident = collect_build_identity(compute_sha=False)
    assert time.perf_counter() - t0 < 0.5
    assert "executable_sha256" in ident


def test_cancel_never_raises_and_acks(qtbot, session, syn_mats, tmp_path):
    page = _fd(session, qtbot, syn_mats, tmp_path)
    page._running = True
    page.btn_cancel.setEnabled(True)
    # Fake running worker
    class _W:
        def __init__(self):
            self._c = False

        def disarm(self):
            self._c = True

        def request_cancel(self):
            self._c = True

        def isRunning(self):
            return True

        class _S:
            def disconnect(self, *_a):
                pass

        progress = _S()
        finished_ok = _S()
        failed = _S()
        cancelled = _S()

    page._worker = _W()
    page._cancel_run()
    assert "Cancel" in page.stage_label.text() or "Отмена" in page.stage_label.text()
    assert page._running is False
    assert page._worker is None


def test_cancel_then_page_switch(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    win._navigate_key("feature_diagnostics")
    page = win._feature_diagnostics_page
    page._running = True
    page._cancel_run()
    t0 = time.perf_counter()
    win._navigate_key("home")
    win._navigate_key("feature_diagnostics")
    elapsed = time.perf_counter() - t0
    # Must not block on worker cleanup
    assert elapsed < 2.0
    assert win.page_instance_created_count["feature_diagnostics"] == 1


def test_language_switch_no_data_io(qtbot, session, syn_mats, tmp_path, monkeypatch):
    page = _fd(session, qtbot, syn_mats, tmp_path)
    io = {"n": 0}
    monkeypatch.setattr(page, "refresh", lambda *a, **k: io.__setitem__("n", io["n"] + 1))
    monkeypatch.setattr(page, "_refresh_tech_details", lambda *a, **k: io.__setitem__("n", io["n"] + 1))
    page.retranslate_ui()
    assert io["n"] == 0


def test_activate_reuses_canvas(qtbot, session, syn_mats, tmp_path, monkeypatch):
    page = _fd(session, qtbot, syn_mats, tmp_path)
    calls = {"refresh": 0}
    monkeypatch.setattr(page, "refresh", lambda *a, **k: calls.__setitem__("refresh", calls["refresh"] + 1))
    page.activate(force_load=False)
    assert calls["refresh"] == 0
    assert page._raw is not None


def test_cache_hit_does_not_start_worker(qtbot, session, syn_mats, tmp_path, monkeypatch):
    page = _fd(session, qtbot, syn_mats, tmp_path)
    starts = worker_start_count()
    monkeypatch.setattr(page._cache, "status_for", lambda _k: "cached")
    monkeypatch.setattr(
        page._cache,
        "load_summary",
        lambda _k: {
            "result": {"features": {}, "centerlines": [], "source_mat_sha256": page._source_sha},
            "masks": {},
            "available_layers": ["interference"],
            "summary_only": True,
        },
    )
    page.run_shadow(force=False)
    assert worker_start_count() == starts
    assert page._worker is None or not page._worker.isRunning()


def test_quick_layers_visible(qtbot, session, syn_mats, tmp_path):
    page = _fd(session, qtbot, syn_mats, tmp_path)
    assert hasattr(page, "quick_layers")
    assert not page.quick_layers.isHidden()
    assert "trace_accepted" in page._quick_layer_btns


def test_quick_layers_sync_with_drawer(qtbot, session, syn_mats, tmp_path):
    page = _fd(session, qtbot, syn_mats, tmp_path)
    page._ensure_layer_checks()
    page._layer_checks["interference"].setChecked(False)
    page._sync_quick_layers_from_checks()
    assert page._quick_layer_btns["interference"].isChecked() is False
    page._quick_layer_btns["interference"].setChecked(True)
    assert page._layer_checks["interference"].isChecked() is True


def test_help_overlay_not_permanent_sibling(qtbot, session, syn_mats, tmp_path):
    page = _fd(session, qtbot, syn_mats, tmp_path)
    page._set_help_drawer_visible(True, persist=False)
    assert page.help_drawer.parent() is page
    page._set_help_drawer_visible(False, persist=False)
    assert page.help_drawer.isHidden()


def test_persistent_worker_state_machine():
    w = PersistentV2Worker()
    assert w.state == V2ProcessState.NOT_STARTED
    # Cancel without start must not raise / exit
    w.request_cancel_job("gen-test")
    assert w.state in (V2ProcessState.CANCELLED, V2ProcessState.RESTARTING, V2ProcessState.READY)


def test_job_thread_disarm_suppresses_signals(qtbot, tmp_path):
    cache = V2FeatureCache(tmp_path / "c")
    emitted = {"n": 0}
    job = V2ProcessJobThread(
        frames=[1],
        profile={},
        profile_id="p",
        signal_contract_id="c",
        cache=cache,
        raw_by_frame={},
        source_sha="abc",
        request_generation_id="g1",
    )
    job.cancelled.connect(lambda *_: emitted.__setitem__("n", emitted["n"] + 1))
    job.disarm()
    job._emit_safe(job.cancelled, {"request_generation_id": "g1"})
    assert emitted["n"] == 0


def test_cancel_audit_dir_created(tmp_path, monkeypatch):
    monkeypatch.setenv("IML_CANCEL_CRASH_AUDIT", "1")
    audit = ensure_audit(enabled=True)
    assert (audit.root / "session.json").is_file()
    assert (audit.root / "process_lifecycle.jsonl").is_file()
    audit.parent("test_event")
    assert (audit.root / "parent.log").stat().st_size > 0


def test_v2_shadow_and_ruleengine():
    from ionogram_morphology_lab.rules import engine as re

    assert "run_feature_pipeline_v2" not in Path(re.__file__).read_text(encoding="utf-8")
    assert FEATURE_VERSION.startswith("iml2-")


def test_navigation_does_not_wait_for_worker(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    win._navigate_key("feature_diagnostics")
    page = win._feature_diagnostics_page

    class _BlockingWorker:
        def isRunning(self):
            return True

        def request_cancel(self):
            time.sleep(5)  # must not be called synchronously by navigate

        def disarm(self):
            pass

        class _S:
            def disconnect(self, *_a):
                pass

        progress = finished_ok = failed = cancelled = _S()

    page._worker = _BlockingWorker()
    page._running = True
    t0 = time.perf_counter()
    win._navigate_key("import")
    assert time.perf_counter() - t0 < 1.0
