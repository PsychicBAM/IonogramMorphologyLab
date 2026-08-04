"""Phase 4B.2g — lazy Feature Diagnostics UI and real-archive profiling hooks."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.active_source import ActiveSourceCard
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


def _page(session: AppSession, qtbot, syn_mats, tmp_path: Path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("P42g", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    return page


def test_slider_release_only_schedules_one_load(qtbot, session, syn_mats, tmp_path, monkeypatch):
    page = _page(session, qtbot, syn_mats, tmp_path)
    calls: list[int] = []
    monkeypatch.setattr(page, "_goto_frame", lambda frame, **_kw: calls.append(int(frame)))

    target = min(2, page._n_frames)
    page._on_frame_slider_moved(target)
    assert calls == []
    assert page.frame_spin.value() == target

    page._on_frame_slider_released()
    assert calls == [target]


def test_frame_change_does_not_auto_run_v2(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path)
    runs = page._v2_pipeline_runs
    target = min(2, page._n_frames)
    page._goto_frame(target)
    assert page.wait_until_frame_ready(30000)
    assert page._v2_pipeline_runs == runs
    assert page._worker is None or not page._worker.isRunning()


def test_try_load_cache_uses_summary_not_all_masks(qtbot, session, syn_mats, tmp_path, monkeypatch):
    page = _page(session, qtbot, syn_mats, tmp_path)
    calls = {"summary": 0, "layers": 0}

    monkeypatch.setattr(page._cache, "status_for", lambda _key: "cached")

    def load_summary(_key):
        calls["summary"] += 1
        return {
            "result": {
                "features": {},
                "centerlines": [],
                "source_mat_sha256": page._source_sha,
            },
            "masks": {},
            "available_layers": ["interference"],
        }

    monkeypatch.setattr(page._cache, "load_summary", load_summary)
    monkeypatch.setattr(page._cache, "load_layers", lambda *_a, **_k: calls.__setitem__("layers", calls["layers"] + 1) or {})

    assert page._try_load_cache()
    assert calls["summary"] == 1
    assert calls["layers"] == 0
    assert page._masks == {}


def test_cancel_immediate_ack(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path)

    class Worker:
        requested = False

        def request_cancel(self):
            self.requested = True

    worker = Worker()
    page._worker = worker
    page._running = True
    page.btn_cancel.setEnabled(True)
    old_gen = page._v2_generation_id = "old"

    page._cancel_run()
    assert worker.requested
    assert page._running is False
    assert page._v2_generation_id != old_gen
    assert "Cancel requested" in page.inline_note.text() or "Отмена" in page.inline_note.text()


def test_compact_strip_used_except_import_card():
    import ionogram_morphology_lab.ui.feature_diagnostics_page as fd_page
    import ionogram_morphology_lab.ui.main_window as main_window

    assert fd_page.CompactSourceStrip is CompactSourceStrip
    source = inspect.getsource(main_window.MainWindow)
    assert "self.import_source_card = ActiveSourceCard" in source
    for attr in ("viewer_source_card", "batch_source_card", "raw_signals_source_card", "matlab_source_card"):
        assert f"self.{attr} = CompactSourceStrip" in source
    assert ActiveSourceCard is not CompactSourceStrip


def test_help_first_visit_expands_then_persists_closed(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path)
    page.show()
    qtbot.waitExposed(page)
    assert session.settings.get("ux", "fd_help_expanded_once") is True
    assert page.help_drawer.isVisible()

    page._set_help_drawer_visible(False, persist=True)
    assert session.settings.get("ux", "fd_help_drawer_open") is False

    page2 = _page(session, qtbot, syn_mats, tmp_path)
    page2.show()
    qtbot.waitExposed(page2)
    assert not page2.help_drawer.isVisible()


def test_ruleengine_and_shadow_unchanged():
    from ionogram_morphology_lab.features.v2.pipeline import LABEL_EN
    from ionogram_morphology_lab.rules.engine import RuleEngine

    assert FEATURE_VERSION == "iml2-0.2.0"
    assert "shadow" in LABEL_EN.lower() or "experimental" in LABEL_EN.lower()
    assert RuleEngine() is not None


def test_nav_stats_sha_not_incremented_on_peek(tmp_path):
    from ionogram_morphology_lab.ui.fd_frame_loader import cached_source_sha, nav_stats, reset_nav_stats

    p = tmp_path / "sample.mat"
    p.write_bytes(b"not a real mat")
    reset_nav_stats()
    assert cached_source_sha(p, allow_compute=False) == ""
    assert nav_stats()["sha_calcs"] == 0
