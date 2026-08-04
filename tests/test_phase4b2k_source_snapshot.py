"""Phase 4B.2k — in-memory ActiveSourceSnapshot; zero MAT I/O on warm UI."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.active_source import (
    rebuild_active_source_snapshot,
    resolve_active_source,
)
from ionogram_morphology_lab.ui.compact_source_strip import CompactSourceStrip
from ionogram_morphology_lab.ui.session import AppSession


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


def _ready_session(session: AppSession, mat: Path, tmp_path: Path) -> AppSession:
    session.project = create_project("P4k", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mat, make_active=True)
    # Snapshot built at activation
    assert session._active_source_snap is not None
    return session


def test_source_strip_reads_snapshot_only(qtbot, session, syn_mats, tmp_path):
    session = _ready_session(session, syn_mats[0], tmp_path)
    snap = resolve_active_source(session, force_rebuild=False)
    strip = CompactSourceStrip(get_i18n("en"))
    qtbot.addWidget(strip)
    with mock.patch(
        "ionogram_morphology_lab.ui.source_roles.classify_mat_source",
        side_effect=AssertionError("MAT classify must not run"),
    ):
        strip.apply_snapshot(snap)
        strip.retranslate()
    assert snap.mat_filename in strip.summary.text()


def test_source_strip_never_invokes_mat_adapter(qtbot, session, syn_mats, tmp_path):
    session = _ready_session(session, syn_mats[0], tmp_path)
    strip = CompactSourceStrip(get_i18n("en"))
    qtbot.addWidget(strip)
    strip.apply_snapshot(resolve_active_source(session))
    with mock.patch(
        "ionogram_morphology_lab.importers.mat_inventory.inventory_mat",
        side_effect=AssertionError("inventory_mat"),
    ):
        strip.retranslate()


def test_language_switch_zero_mat_opens(qtbot, session, syn_mats, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    session = _ready_session(session, syn_mats[0], tmp_path)
    win = MainWindow(language="en")
    qtbot.addWidget(win)
    win.session = session
    # Seed strip caches
    win._refresh_source_cards(light=True)
    opens = {"n": 0}

    def _boom(*a, **k):
        opens["n"] += 1
        raise AssertionError("inventory during language")

    monkeypatch.setattr(
        "ionogram_morphology_lab.importers.mat_inventory.inventory_mat",
        _boom,
    )
    monkeypatch.setattr(
        "ionogram_morphology_lab.ui.source_roles.classify_mat_source",
        _boom,
    )
    win.set_language("ru")
    win.set_language("en")
    assert opens["n"] == 0


def test_navigation_zero_mat_opens(qtbot, tmp_path, monkeypatch, syn_mats):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    win.session.settings = settings
    win.session.project = create_project("Nav", language="en", workspace_parent=tmp_path / "ws")
    win.session.add_to_inventory(syn_mats[0], make_active=True)
    opens = {"n": 0}

    def _boom(*a, **k):
        opens["n"] += 1
        raise AssertionError("mat during nav")

    monkeypatch.setattr(
        "ionogram_morphology_lab.importers.mat_inventory.inventory_mat",
        _boom,
    )
    win._navigate_key("viewer")
    win._navigate_key("feature_diagnostics")
    win._navigate_key("settings")
    win._navigate_key("feature_diagnostics")
    assert opens["n"] == 0


def test_context_validation_uses_snapshot(qtbot, session, syn_mats, tmp_path, monkeypatch):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session = _ready_session(session, syn_mats[0], tmp_path)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    monkeypatch.setattr(
        "ionogram_morphology_lab.importers.mat_inventory.inventory_mat",
        mock.Mock(side_effect=AssertionError("inventory")),
    )
    ok, code = page._check_prerequisites()
    assert ok is True
    assert code == ""


def test_cache_key_uses_snapshot_identity(session, syn_mats, tmp_path, qtbot, monkeypatch):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session = _ready_session(session, syn_mats[0], tmp_path)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page._source_sha = "abc123"
    monkeypatch.setattr(
        "ionogram_morphology_lab.importers.mat_inventory.inventory_mat",
        mock.Mock(side_effect=AssertionError("inventory")),
    )
    key = page._cache_key()
    assert key.source_mat_sha256 == "abc123"
    assert key.profile_id == session.profile_id


def test_post_result_does_not_resolve_rebuild(qtbot, session, syn_mats, tmp_path, monkeypatch):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session = _ready_session(session, syn_mats[0], tmp_path)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page._source_sha = "sha"
    page._v2_generation_id = "gen1"
    page._raw = __import__("numpy").zeros((8, 8), dtype="float32")
    rebuilds = {"n": 0}
    real = rebuild_active_source_snapshot

    def _wrap(sess):
        rebuilds["n"] += 1
        return real(sess)

    monkeypatch.setattr(
        "ionogram_morphology_lab.ui.active_source.rebuild_active_source_snapshot",
        _wrap,
    )
    page._on_worker_finished(
        {
            "request_generation_id": "gen1",
            "source_sha": "sha",
            "results": [
                {
                    "frame_index": int(page.frame_spin.value()),
                    "status": "cached",
                    "result": {"features": {}, "centerlines": [], "source_mat_sha256": "sha"},
                    "masks": {},
                }
            ],
            "cache_hits": 1,
            "recomputed": 0,
            "failures": 0,
            "elapsed_s": 0.1,
        }
    )
    assert rebuilds["n"] == 0


def test_summary_formatting_pure(qtbot, session, syn_mats, tmp_path, monkeypatch):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session = _ready_session(session, syn_mats[0], tmp_path)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page._result_ser = {"features": {}, "centerlines": [], "quality_status": "ok"}
    page._loaded_mat_path = str(syn_mats[0])
    monkeypatch.setattr(
        "ionogram_morphology_lab.importers.mat_inventory.inventory_mat",
        mock.Mock(side_effect=AssertionError("inventory")),
    )
    page._populate_summary_from_ser()
    assert page.summary_view.toPlainText()


def test_one_source_service_per_session(session, syn_mats, tmp_path):
    session = _ready_session(session, syn_mats[0], tmp_path)
    assert session.source_service is not None
    c1 = session.source_service.counters.active_source_service_instances
    assert c1 == 1


def test_source_refresh_updates_snapshot(session, syn_mats, tmp_path):
    session = _ready_session(session, syn_mats[0], tmp_path)
    g0 = session._active_source_snap.snapshot_generation
    snap = session.refresh_active_source_snapshot()
    assert snap.snapshot_generation > g0


def test_source_switch_invalidates_snapshot(session, syn_mats, tmp_path):
    session = _ready_session(session, syn_mats[0], tmp_path)
    old = session._active_source_snap
    session.set_active_mat(syn_mats[1])
    new = session._active_source_snap
    assert new is not None
    assert new.mat_filename == syn_mats[1].name
    assert new.snapshot_generation != old.snapshot_generation or new.mat_filename != old.mat_filename


def test_profiler_distinguishes_file_size_from_bytes_read(tmp_path):
    from ionogram_morphology_lab.ui.packaged_exe_profiler import start_profiler, stop_profiler
    import json

    out = tmp_path / "perf"
    start_profiler(out, identity={})
    try:
        p = tmp_path / "big.bin"
        p.write_bytes(b"x" * 2048)
        with open(p, "rb") as fh:
            _ = fh
        rows = [
            json.loads(line)
            for line in (out / "file_io.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        opens = [r for r in rows if r.get("op") == "open" and "big.bin" in r.get("path", "")]
        assert opens
        assert opens[-1].get("bytes_read", 0) == 0
        assert opens[-1].get("file_size", 0) >= 2048
        assert opens[-1].get("bytes_unknown") is True
    finally:
        stop_profiler()


def test_v2_shadow_ruleengine_unchanged():
    from ionogram_morphology_lab.rules import engine as re

    assert "run_feature_pipeline_v2" not in Path(re.__file__).read_text(encoding="utf-8")
    assert FEATURE_VERSION.startswith("iml2-")


def test_warm_resolve_does_not_rebuild(session, syn_mats, tmp_path, monkeypatch):
    session = _ready_session(session, syn_mats[0], tmp_path)
    rebuilds = {"n": 0}
    real = rebuild_active_source_snapshot

    def _wrap(sess):
        rebuilds["n"] += 1
        return real(sess)

    monkeypatch.setattr(
        "ionogram_morphology_lab.ui.active_source.rebuild_active_source_snapshot",
        _wrap,
    )
    resolve_active_source(session, force_rebuild=False)
    resolve_active_source(session, force_rebuild=False)
    assert rebuilds["n"] == 0
