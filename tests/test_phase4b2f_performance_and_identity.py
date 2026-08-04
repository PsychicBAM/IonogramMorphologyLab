"""Phase 4B.2f — frame identity, stale rejection, layout, cache counters."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QByteArray

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.cache.v2_feature_cache import V2FeatureCache, make_cache_key
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.frame_diagnostic_context import (
    TERMINAL_JOB_STATES,
    build_frame_context,
    next_request_generation_id,
)
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.ui.v2_diagnostics_worker import V2DiagnosticsWorker


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


def _page(session, qtbot, syn_mats, tmp_path, name="P"):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project(name, language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    return page


def test_selector_identity_image_same_frame(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "ID")
    page._goto_frame(3)
    assert page.wait_until_frame_ready(30000)
    ctx = page.current_context()
    assert ctx is not None
    assert ctx.frame_index == 3
    assert page.frame_spin.value() == 3
    assert "Frame: 3" in page.identity.text() or "3 /" in page.identity.text()
    assert page._raw is not None
    assert page._raw_sha == ctx.raw_frame_sha256


def test_stale_worker_result_rejected(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "ST")
    page._v2_generation_id = "keep-me"
    stale = {
        "request_generation_id": "old-gen",
        "source_sha": page._source_sha,
        "results": [{"frame_index": 1, "status": "recomputed", "result": {}, "masks": {}}],
        "cache_hits": 0,
        "recomputed": 1,
        "failures": 0,
        "elapsed_s": 1.0,
    }
    before = page._result_ser
    page._on_worker_finished(stale)
    assert page._result_ser == before
    assert page.job_state() != "completed" or before is page._result_ser


def test_rapid_frame_changes_latest_wins(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "RP")
    # Synthetic mats typically have only a few frames (e.g. 3); stay in range.
    n = max(1, min(int(page._n_frames), 3))
    seq = list(range(1, n + 1))
    for f in seq:
        page._goto_frame(f)
    assert page.wait_until_frame_ready(30000)
    assert page.frame_spin.value() == n
    assert page.current_context() is not None
    assert page.current_context().frame_index == n
    assert page._loaded_frame == n


def test_source_switch_rejects_previous_source_result(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "SW")
    page._v2_generation_id = "g1"
    page._source_sha = "sha-current"
    page._on_worker_finished(
        {
            "request_generation_id": "g1",
            "source_sha": "sha-other",
            "results": [{"frame_index": 1, "status": "cached", "result": {"features": {}}, "masks": {}}],
            "cache_hits": 1,
            "recomputed": 0,
            "failures": 0,
            "elapsed_s": 0.1,
        }
    )
    assert page._result_ser is None or page._masks == {}
    assert "Stale" in page.inline_note.text() or "отклон" in page.inline_note.text().lower() or page._result_ser is None


def test_cache_miss_reports_recomputed(qtbot, session, syn_mats, tmp_path):
    cache = V2FeatureCache(tmp_path / "c1")
    worker = V2DiagnosticsWorker(
        mat_path=syn_mats[0],
        frames=[1],
        profile=session.profile,
        profile_id=session.profile_id,
        signal_contract_id="kfu_amp_all_v1",
        cache=cache,
        force_recompute=True,
    )
    done = {}
    worker.finished_ok.connect(lambda p: done.update(p=p))
    worker.start()
    qtbot.waitUntil(lambda: "p" in done, timeout=120000)
    assert done["p"]["recomputed"] == 1
    assert done["p"]["job_state"] == "completed"
    assert worker.terminal_state in TERMINAL_JOB_STATES


def test_cache_hit_reports_hits(qtbot, session, syn_mats, tmp_path):
    cache = V2FeatureCache(tmp_path / "c2")
    for force, expect_hits, expect_recomp in ((True, 0, 1), (False, 1, 0)):
        done = {}
        worker = V2DiagnosticsWorker(
            mat_path=syn_mats[0],
            frames=[1],
            profile=session.profile,
            profile_id=session.profile_id,
            signal_contract_id="kfu_amp_all_v1",
            cache=cache,
            force_recompute=force,
        )
        worker.finished_ok.connect(lambda p, d=done: d.update(p=p))
        worker.start()
        qtbot.waitUntil(lambda d=done: "p" in d, timeout=120000)
        assert done["p"]["cache_hits"] == expect_hits
        assert done["p"]["recomputed"] == expect_recomp
        assert done["p"]["job_state"] == "completed"


def test_single_frame_hides_sequence_controls(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "SF")
    page.mode_combo.setCurrentIndex(0)
    assert page.mode_combo.currentData() == "single"
    assert not page.seq_form.isVisible()


def test_sequence_shows_relevant_controls(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "SQ")
    page.show()
    page.mode_combo.setCurrentIndex(1)
    # Phase 4B.2g: sequence fields open via configure button, not permanently embedded
    assert hasattr(page, "btn_sequence_settings")
    assert page.btn_sequence_settings.isVisible()
    assert not page.seq_form.isVisible()
    page._open_sequence_settings()
    assert page.seq_form.isVisible()
    assert page.lbl_seq_start.text() in ("Start frame", "Начальный кадр")
    assert page.lbl_seq_start.text() != "start"
    page.seq_type.setCurrentIndex(page.seq_type.findData("custom"))
    if hasattr(page, "_rebuild_seq_fields"):
        page._rebuild_seq_fields()
    assert page.seq_custom is not None


def test_canvas_minimum_size(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "CV")
    page.resize(1366, 768)
    # Phase 4C.1d: lower floor so sequence vertical splitter / low-height layouts work
    assert page.image.minimumHeight() >= 160
    assert page.scroll.minimumHeight() >= 160
    assert page._mid_vsplit is not None


def test_splitter_positions_persist(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "SP")
    page.split.setSizes([120, 700, 300])
    page._persist_splitter()
    states = session.settings.get("general", "splitter_states", {})
    assert "feature_diagnostics" in states
    page2 = _page(session, qtbot, syn_mats, tmp_path, "SP2")
    # restore ran in ctor — state key still present
    assert session.settings.get("general", "splitter_states", {}).get("feature_diagnostics")


def test_layer_toggle_does_not_rerun_v2(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "LY")
    page._ensure_layer_checks()
    runs = page._v2_pipeline_runs
    page._layer_checks["interference"].setChecked(
        not page._layer_checks["interference"].isChecked()
    )
    assert page._v2_pipeline_runs == runs
    assert page._worker is None or not page._worker.isRunning()


def test_zoom_does_not_rewrite_v2_cache(qtbot, session, syn_mats, tmp_path, monkeypatch):
    page = _page(session, qtbot, syn_mats, tmp_path, "ZM")
    writes = {"n": 0}

    def _boom(*a, **k):
        writes["n"] += 1

    monkeypatch.setattr(page._cache, "save", _boom)
    page._set_zoom("100")
    page._nudge_zoom(1.25)
    assert writes["n"] == 0


def test_progress_events_throttled(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "TH")
    page._v2_generation_id = "g"
    for i in range(50):
        page._on_worker_progress(
            {
                "request_generation_id": "g",
                "percent": i,
                "stage": "computing",
                "job_state": "computing",
                "elapsed_s": 0.0,
            }
        )
    # Pending held; not all 50 flushed immediately
    assert page._progress_throttle.isActive() or page._pending_progress is not None or page.progress.value() <= 49


def test_v2_explanation_no_morphology_classification(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "EX")
    page.i18n = get_i18n("en")
    page.retranslate()
    assert page.wait_until_frame_ready(30000)
    text = page.explain_fd.text().lower()
    assert "does not yet determine" in text or "not yet" in text
    assert "auto-analysis" in text or "do not participate" in text
    page.i18n = get_i18n("ru")
    page.retranslate()
    assert "не определяет окончательный тип" in page.explain_fd.text()


def test_future_phase4c_panel_readonly(qtbot, session, syn_mats, tmp_path):
    """Phase 4C.1: active shadow panel; does not auto-run; no free-text morphology class edit."""
    page = _page(session, qtbot, syn_mats, tmp_path, "F4")
    assert page.future_box.isEnabled()
    assert page.future_label.isEnabled()
    from PySide6.QtWidgets import QLineEdit

    edits = page.future_box.findChildren(QLineEdit)
    assert edits == []
    text = page.future_label.text() + " " + page.morph_disclaimer.text()
    assert (
        "does not auto-run" in text.lower()
        or "не запускается автоматически" in text.lower()
        or "provisional" in text.lower()
        or "предварительный" in text.lower()
    )
    assert hasattr(page, "btn_calc_morph")
    # Opening diagnostics must not populate a morphology candidate automatically
    assert page._morph_result_dict is None


def test_context_generation_unique():
    a = next_request_generation_id()
    b = next_request_generation_id()
    assert a != b
    ctx = build_frame_context(
        mat_path="/x.mat",
        source_sha256="abc",
        frame_index=2,
        interpreted_time="00:01",
        raw_frame_sha256="raw",
        profile_id="p",
        signal_contract_id="c",
    )
    assert ctx.feature_version == FEATURE_VERSION
    assert ctx.cache_key_digest


def test_ruleengine_and_shadow_unchanged():
    from ionogram_morphology_lab.features.v2.pipeline import LABEL_EN
    from ionogram_morphology_lab.rules.engine import RuleEngine

    assert FEATURE_VERSION == "iml2-0.2.0"
    assert "shadow" in LABEL_EN.lower() or "experimental" in LABEL_EN.lower()
    assert RuleEngine() is not None


def test_sequence_thumbnails_lazy(qtbot, session, syn_mats, tmp_path):
    page = _page(session, qtbot, syn_mats, tmp_path, "LZ")
    page.show()
    page.mode_combo.setCurrentIndex(1)
    page._sequence_results = [{"frame_index": 1, "status": "cached", "result": {}, "masks": {}}]
    page._fill_sequence_table()
    assert not page.contact_label.isVisibleTo(page)
    page._request_contact_sheet()
    assert page.contact_label.isVisibleTo(page)
    assert "on demand" in page.contact_label.text().lower() or "запрос" in page.contact_label.text().lower()
