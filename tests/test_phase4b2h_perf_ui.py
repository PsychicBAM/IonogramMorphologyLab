"""Phase 4B.2h — persistent pages, language I/O guard, lazy cache, process V2 hooks."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.cache.v2_feature_cache import V2FeatureCache, make_cache_key
from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.active_source import ActiveSourceCard
from ionogram_morphology_lab.ui.build_identity import collect_build_identity, format_build_identity
from ionogram_morphology_lab.ui.compact_source_strip import CompactSourceStrip
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.ui.source_service import SourceService


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


def _fd_page(session: AppSession, qtbot, syn_mats, tmp_path: Path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("P42h", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    page._use_process_v2 = False  # keep unit tests in-process / deterministic
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    return page


def test_build_identity_fields():
    ident = collect_build_identity(cache_root="/tmp/c", workspace_root="/tmp/w")
    assert ident["application_version"]
    assert ident["feature_version"] == FEATURE_VERSION
    assert ident["display_transform_version"]
    text = format_build_identity(ident, "en")
    assert "SHA-256" in text
    assert "Build Identity" in text


def test_source_service_single_instance(session):
    assert isinstance(session.source_service, SourceService)
    assert session.source_service.counters.active_source_service_instances == 1


def test_persistent_page_instances(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    assert win.page_instance_created_count.get("feature_diagnostics", 0) == 0
    assert win._page_materialized.get("feature_diagnostics") is False
    win._navigate_key("feature_diagnostics")
    assert win.page_instance_created_count["feature_diagnostics"] == 1
    assert hasattr(win, "_feature_diagnostics_page")
    page1 = win._feature_diagnostics_page
    win._navigate_key("import")
    win._navigate_key("feature_diagnostics")
    assert win.page_instance_created_count["feature_diagnostics"] == 1
    assert win._feature_diagnostics_page is page1
    assert win.page_activation_count["feature_diagnostics"] >= 2


def test_page_switch_does_not_recreate_diagnostics(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    win._navigate_key("feature_diagnostics")
    created = win.page_instance_created_count["feature_diagnostics"]
    for _ in range(3):
        win._navigate_key("home")
        win._navigate_key("feature_diagnostics")
    assert win.page_instance_created_count["feature_diagnostics"] == created


def test_language_switch_no_fd_refresh(qtbot, session, syn_mats, tmp_path, monkeypatch):
    page = _fd_page(session, qtbot, syn_mats, tmp_path)
    calls = {"refresh": 0}
    monkeypatch.setattr(page, "refresh", lambda *a, **k: calls.__setitem__("refresh", calls["refresh"] + 1))
    page.retranslate_ui()
    assert calls["refresh"] == 0


def test_language_switch_preserves_frame(qtbot, session, syn_mats, tmp_path):
    page = _fd_page(session, qtbot, syn_mats, tmp_path)
    frame = int(page.frame_spin.value())
    raw_ptr = page._raw
    page.i18n.set_language("ru")
    page.retranslate_ui()
    assert int(page.frame_spin.value()) == frame
    assert page._raw is raw_ptr


def test_constructor_defers_data_work(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("P42h2", language="en", workspace_parent=tmp_path / "ws2")
    session.add_to_inventory(syn_mats[0], make_active=True)
    # Construction must not require wait — page paints with preparing state.
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    assert page.state_label.text()
    assert hasattr(page, "inspector_tabs")
    assert page.inspector_tabs.count() == 5


def test_help_drawer_on_right(qtbot, session, syn_mats, tmp_path):
    page = _fd_page(session, qtbot, syn_mats, tmp_path)
    page.show()
    # Help is a sibling of the splitter in a horizontal work layout, not above canvas permanently.
    assert page.help_drawer.maximumWidth() >= 280
    page._set_help_drawer_visible(True, persist=False)
    assert not page.help_drawer.isHidden()
    page._set_help_drawer_visible(False, persist=False)
    assert page.help_drawer.isHidden()
    page.btn_help.click()
    assert not page.help_drawer.isHidden()


def test_duplicate_title_removed_banner_is_badge(qtbot, session, syn_mats, tmp_path):
    page = _fd_page(session, qtbot, syn_mats, tmp_path)
    # Badge must not repeat the full page title
    assert "Trace and Geometry Diagnostics" not in page.banner.text()
    assert "shadow" in page.banner.text().lower() or "тенев" in page.banner.text().lower()


def test_inspector_tabs_default_summary(qtbot, session, syn_mats, tmp_path):
    page = _fd_page(session, qtbot, syn_mats, tmp_path)
    assert page.inspector_tabs.currentIndex() == 0


def test_features_tab_lazy(qtbot, session, syn_mats, tmp_path, monkeypatch):
    page = _fd_page(session, qtbot, syn_mats, tmp_path)
    page._result_ser = {
        "features": {
            "trace_present": {"value": True, "valid": True, "unit": ""},
        },
        "centerlines": [],
        "quality_status": "ok",
    }
    page._features_populated = False
    if page._features_model is not None:
        page._features_model.clear()
    page.feature_list.clear()
    assert page.feature_list.count() == 0
    page.inspector_tabs.setCurrentIndex(1)
    assert page._features_populated
    assert page._features_model is not None and page._features_model.rowCount() > 0


def test_source_index_direct_lookup(tmp_path, syn_mats):
    cache = V2FeatureCache(tmp_path / "cache")
    from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent

    loaded = load_amplitude_matrix(syn_mats[0], variable="Amp_all")
    frame, _ = extract_frame_consistent(loaded.data, 1, height_bins=256, frequency_bins=400)
    v2 = run_feature_pipeline_v2(
        np.asarray(frame),
        signal_contract_id="kfu_amp_all_v1",
        profile_id="kfu_cyclone_2013_2014",
        frame_index=1,
        source_mat_sha256="abc123",
    )
    key = make_cache_key(
        source_mat_sha256="abc123",
        frame_index=1,
        profile_id="kfu_cyclone_2013_2014",
        signal_contract_id="kfu_amp_all_v1",
        profile={"amplitude_variable_name": "Amp_all", "height_bins": 256, "frequency_bins": 400},
    )
    cache.save(key, v2)
    idx = cache.load_source_index("abc123")
    assert idx is not None
    assert "1" in idx["frames"]
    entry = cache.lookup_frame_in_index(key)
    assert entry is not None
    assert entry["digest"] == key.digest()
    # No recursive scan counter bump on lookup
    assert cache.status_for(key) == "cached"
    summary = cache.load_summary(key)
    assert summary is not None
    assert summary.get("summary_only") is True
    assert summary.get("masks") == {}


def test_cached_summary_does_not_load_all_masks(qtbot, session, syn_mats, tmp_path, monkeypatch):
    page = _fd_page(session, qtbot, syn_mats, tmp_path)
    monkeypatch.setattr(page._cache, "status_for", lambda _k: "cached")

    def load_summary(_k):
        return {
            "result": {"features": {}, "centerlines": [], "source_mat_sha256": page._source_sha},
            "masks": {},
            "available_layers": ["interference", "trace_accepted"],
            "summary_only": True,
        }

    loads = {"layers": 0}
    monkeypatch.setattr(page._cache, "load_summary", load_summary)
    monkeypatch.setattr(
        page._cache,
        "load_layers",
        lambda *_a, **_k: loads.__setitem__("layers", loads["layers"] + 1) or {},
    )
    assert page._try_load_cache()
    assert loads["layers"] == 0
    assert page._masks == {}


def test_cancel_invalidates_immediately(qtbot, session, syn_mats, tmp_path):
    page = _fd_page(session, qtbot, syn_mats, tmp_path)
    page._running = True
    page.btn_cancel.setEnabled(True)
    old_gen = page._v2_generation_id
    page._cancel_run()
    assert "Cancel" in page.stage_label.text() or "Отмена" in page.stage_label.text()
    assert page._v2_generation_id != old_gen
    assert page._running is False


def test_work_pages_use_compact_strip(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("IML_DISABLE_ONBOARDING", "1")
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    qtbot.addWidget(win)
    win._navigate_key("feature_diagnostics")
    assert isinstance(win._feature_diagnostics_page.source_card, CompactSourceStrip)
    # Import keeps full card
    win._ensure_page_materialized("import")
    assert hasattr(win, "import_source_card")
    assert isinstance(win.import_source_card, ActiveSourceCard)


def test_v2_remains_shadow_and_ruleengine_untouched():
    from ionogram_morphology_lab.rules import engine as rule_engine_mod

    src = Path(rule_engine_mod.__file__).read_text(encoding="utf-8")
    assert "run_feature_pipeline_v2" not in src
    assert FEATURE_VERSION.startswith("iml2-")


def test_process_worker_flag_detected():
    from ionogram_morphology_lab.ui.v2_process_worker import WORKER_FLAG, is_worker_argv

    assert is_worker_argv(["prog", WORKER_FLAG])
    assert not is_worker_argv(["prog"])
