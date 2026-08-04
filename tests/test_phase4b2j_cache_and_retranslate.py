"""Phase 4B.2j — production cache root + visible-only language switch + skeleton FD."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.app.cache_root import (
    looks_like_test_cache_path,
    production_cache_root,
    resolve_cache_root,
)
from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.cache.v2_feature_cache import V2FeatureCache, make_cache_key
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.session import AppSession


def test_looks_like_test_cache_path():
    assert looks_like_test_cache_path(
        r"C:\Users\abdal\AppData\Local\Temp\pytest-of-abdal\pytest-158\test_cache_cleanup_never_delet0\cache"
    )
    assert looks_like_test_cache_path("/tmp/pytest-of-x/test_cache_foo/cache")
    assert not looks_like_test_cache_path(str(production_cache_root()))


def test_frozen_rejects_pytest_cache_root(tmp_path):
    leaked = tmp_path / "pytest-of-abdal" / "pytest-1" / "test_cache_x" / "cache"
    leaked.mkdir(parents=True)
    res = resolve_cache_root(leaked, force_frozen=True)
    assert res.production_mode is True
    assert looks_like_test_cache_path(res.path) is False
    assert res.rejected_path
    assert "pytest" in res.rejected_path.lower() or "test_cache" in res.rejected_path.lower()
    assert res.resolution_source == "production_fallback_rejected_test_path"


def test_dev_allows_pytest_cache(tmp_path):
    cache = tmp_path / "cache"
    res = resolve_cache_root(cache, force_frozen=False)
    assert res.path.resolve() == cache.resolve()
    assert res.production_mode is False


def test_settings_cache_dir_uses_resolver(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    store.set("performance", "cache_location", str(tmp_path / "mycache"))
    store.save()
    p = store.cache_dir()
    assert p == (tmp_path / "mycache").resolve()
    info = store.cache_root_info()
    assert "resolved_cache_root" in info


def test_production_cache_persists_conceptually():
    r1 = resolve_cache_root("", force_frozen=True)
    r2 = resolve_cache_root("", force_frozen=True)
    assert r1.path == r2.path
    assert r1.path.name == "cache"


def test_cache_diagnose_explains_miss(tmp_path):
    cache = V2FeatureCache(tmp_path / "cache")
    key = make_cache_key(
        source_mat_sha256="abc",
        frame_index=1,
        profile_id="p",
        signal_contract_id="s",
        profile={},
    )
    diag = cache.diagnose_lookup(key)
    assert diag["status"] == "not_computed"
    assert diag["miss_reason"] == "no_cache_directory"
    assert diag["cache_key"]
    # Bare directory is not a hit
    d = cache._dir(key)
    d.mkdir(parents=True)
    diag2 = cache.diagnose_lookup(key)
    assert diag2["status"] != "cached"
    assert diag2["miss_reason"] == "directory_without_key_json"


def test_language_switch_visible_only(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    win._navigate_key("home")
    win._navigate_key("feature_diagnostics")
    assert win._page_materialized.get("feature_diagnostics")
    win._navigate_key("home")
    calls = {"fd": 0}
    page = win._feature_diagnostics_page

    def _spy():
        calls["fd"] += 1

    monkeypatch.setattr(page, "retranslate_ui", _spy)
    win.set_language("ru")
    assert calls["fd"] == 0
    assert win._page_language_dirty.get("feature_diagnostics") is True
    win._navigate_key("feature_diagnostics")
    assert calls["fd"] == 1
    assert win._page_language_dirty.get("feature_diagnostics") is False


def test_language_switch_does_not_apply_theme(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    theme_calls = {"n": 0}
    monkeypatch.setattr(win, "_apply_theme", lambda *a, **k: theme_calls.__setitem__("n", theme_calls["n"] + 1))
    win.set_language("ru")
    assert theme_calls["n"] == 0


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


def test_fd_constructor_creates_skeleton_only(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage
    from PySide6.QtWidgets import QListWidget, QTableView

    session.project = create_project("P42j", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    assert page._layers_built is False
    assert page._features_tab_built is False
    assert page._review_tab_built is False
    assert page._tech_tab_built is False
    assert page._help_body_loaded is False
    assert page.feature_list.isHidden()
    assert page.tech_details.isHidden()
    page._ensure_features_tab()
    assert page._features_tab_built is True
    # Features tab uses QTableView model/view (legacy QListWidget stays hidden).
    # With no bound V2 result the table may stay hidden while the empty-state label shows.
    assert page._features_view is not None
    assert isinstance(page._features_view, QTableView)
    assert page._features_model is not None
    assert page._features_empty_label is not None
    assert page.feature_list.isHidden()
    assert not isinstance(page._features_view, QListWidget)
    has_rows = page._features_model.rowCount() > 0
    if has_rows:
        assert page._features_view.isHidden() is False
        assert page._features_empty_label.isHidden() is True
    else:
        assert page._features_empty_label.isHidden() is False
        assert page._features_view.isHidden() is True
        assert (page._features_empty_label.text() or "").strip()
    page._ensure_review_tab()
    assert page._review_tab_built is True
    page._ensure_tech_tab()
    assert page._tech_tab_built is True
    page._ensure_layer_checks()
    assert page._layers_built is True
    assert len(page._layer_checks) == len(page.LAYER_KEYS)


def test_navigation_no_global_retranslate(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    calls = {"n": 0}
    monkeypatch.setattr(win, "retranslate", lambda *a, **k: calls.__setitem__("n", calls["n"] + 1))
    win._navigate_key("viewer")
    win._navigate_key("import")
    assert calls["n"] == 0


def test_navigation_no_theme_apply(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    theme_calls = {"n": 0}
    monkeypatch.setattr(win, "_apply_theme", lambda *a, **k: theme_calls.__setitem__("n", theme_calls["n"] + 1))
    win._navigate_key("viewer")
    win._navigate_key("feature_diagnostics")
    assert theme_calls["n"] == 0


def test_profiler_file_io_hooks(tmp_path):
    from ionogram_morphology_lab.ui.packaged_exe_profiler import start_profiler, stop_profiler

    out = tmp_path / "perf"
    prof = start_profiler(out, identity={"test": True})
    try:
        p = tmp_path / "sample.txt"
        p.write_text("hello", encoding="utf-8")
        with open(p, encoding="utf-8") as fh:
            assert fh.read() == "hello"
        assert prof.file_io_tracer_active
        assert prof.intercepted_operation_count >= 1
        fio = (out / "file_io.jsonl").read_text(encoding="utf-8")
        assert "sample.txt" in fio
    finally:
        stop_profiler()


def test_profiler_child_spans_explain_parent(tmp_path):
    import importlib.util
    import json

    from ionogram_morphology_lab.ui.packaged_exe_profiler import span_timer, start_profiler, stop_profiler

    out = tmp_path / "perf2"
    start_profiler(out, identity={})
    try:
        with span_timer("language_switch"):
            with span_timer("lang.chrome"):
                pass
            with span_timer("lang.visible_page"):
                pass
            with span_timer("lang.mark_dirty"):
                pass
    finally:
        stop_profiler()
    rows = [
        json.loads(line)
        for line in (out / "timeline.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    names = {r.get("event") for r in rows}
    assert "language_switch" in names
    assert "lang.chrome" in names
    assert any(r.get("parent") == "language_switch" for r in rows if "duration_s" in r)
    # Import validator by path (scripts/ is not a package)
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "validate_packaged_perf_trace",
        root / "scripts" / "validate_packaged_perf_trace.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    errs = mod.validate_session(out, frozen_expected=False)
    assert not any("language_switch" in e and "explained" in e for e in errs)


def test_v2_shadow_ruleengine():
    from ionogram_morphology_lab.rules import engine as re

    assert "run_feature_pipeline_v2" not in Path(re.__file__).read_text(encoding="utf-8")
    assert FEATURE_VERSION.startswith("iml2-")
