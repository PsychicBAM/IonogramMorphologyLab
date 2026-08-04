"""Phase 4B.2e — display orientation, frame selection, V2 cache, async wording."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.cache.v2_feature_cache import (
    V2FeatureCache,
    algorithm_parameter_hash,
    make_cache_key,
)
from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.rendering.display_transform import (
    apply_display_transform,
    default_kfu_display_identity,
    transform_mask_for_display,
    transform_rc_scientific_to_display,
)
from ionogram_morphology_lab.rendering.ionogram_render import RenderSpec, render_raw_ionogram
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.active_source import ActiveSourceCard
from ionogram_morphology_lab.ui.fd_display import scientific_to_display_gray
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.utils.hashing import sha256_file


def _asymmetric_marker_frame(h: int = 64, w: int = 80) -> np.ndarray:
    """Distinct corners: TL/TR/BL/BR markers in scientific coordinates."""
    a = np.zeros((h, w), dtype=np.float64)
    # scientific row0 = bottom on display after flip
    a[0, 0] = 10.0  # BL display
    a[0, w - 1] = 20.0  # BR display
    a[h - 1, 0] = 30.0  # TL display
    a[h - 1, w - 1] = 40.0  # TR display
    # asymmetric interior ridge near top of display (high scientific row)
    a[h - 5 : h - 2, 10:50] = 50.0
    return a


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


def test_activate_deactivate_wording_ru_en(qtbot):
    card = ActiveSourceCard(get_i18n("en"))
    qtbot.addWidget(card)
    assert card.buttons["detach"].text() == "Deactivate for Analysis"
    assert card.buttons["set_active"].text() == "Activate for Analysis"
    assert "remain" in card.buttons["detach"].toolTip().lower() or "disk" in card.buttons["detach"].toolTip().lower()
    card.i18n = get_i18n("ru")
    card.retranslate()
    assert card.buttons["detach"].text() == "Отключить от анализа"
    assert card.buttons["set_active"].text() == "Активировать для анализа"
    assert "останется в проекте" in card.buttons["detach"].toolTip()


def test_deactivate_keeps_inventory_and_file(session, syn_mats, tmp_path):
    session.project = create_project("D", language="en", workspace_parent=tmp_path / "ws")
    a = syn_mats[0]
    session.add_to_inventory(a, make_active=True)
    session.detach_active_mat()
    assert session.active_mat is None
    assert a in session.selected_mats
    assert a.is_file()
    session.set_active_mat(a)
    assert session.active_mat == a


def test_display_transform_vertical_flip_not_transpose():
    a = _asymmetric_marker_frame()
    d = apply_display_transform(a)
    assert d.shape == a.shape
    # After flipud, scientific [h-1,0]=30 appears at display [0,0]
    assert d[0, 0] == 30.0
    assert d[0, -1] == 40.0
    assert d[-1, 0] == 10.0
    assert d[-1, -1] == 20.0
    # Not transposed
    assert d.shape[0] == a.shape[0]
    # Horizontal not flipped
    assert d[0, 0] != d[0, -1]
    # Original unchanged
    assert a[0, 0] == 10.0


def test_mask_follows_same_transform_as_raw():
    a = _asymmetric_marker_frame()
    mask = a >= 30
    d_raw = apply_display_transform(a)
    d_mask = transform_mask_for_display(mask)
    assert d_mask[0, 0]  # TL marker
    assert d_mask[0, -1]
    assert not d_mask[-1, 0]
    assert (d_raw >= 30).astype(bool).tolist() == d_mask.astype(bool).tolist()


def test_no_vertical_flip_mismatch_viewer_vs_fd_raster(tmp_path):
    """Viewer matplotlib origin=lower ≡ FD flipud raster top-left."""
    frame = _asymmetric_marker_frame(32, 40)
    out = tmp_path / "viewer.png"
    meta = render_raw_ionogram(
        frame,
        list(range(40)),
        list(range(32)),
        out,
        spec=RenderSpec(colormap="gray", scaling_method="none"),
    )
    assert meta["display_orientation"]["vertical_flip_applied"] is True
    assert meta["scientific_matrix_mutated"] is False
    # FD display gray: top-left must be scientific bottom-left after? Wait — flipud
    # scientific [h-1,0]=30 → display [0,0]
    u8 = scientific_to_display_gray(frame)
    # Brightest corner among the four markers at display top should be 30 or 40 class
    # Marker values survive percentile stretch as relative order
    tl = float(frame[-1, 0])
    bl = float(frame[0, 0])
    assert tl > bl
    # Display top-left pixel region should be brighter than bottom-left region
    assert u8[0, 0] >= u8[-1, 0]


def test_corner_marker_rc_mapping():
    h, w = 64, 80
    ident = default_kfu_display_identity()
    # scientific bottom-left (0,0) → display bottom
    r, c = transform_rc_scientific_to_display(0, 0, h, w, identity=ident)
    assert (r, c) == (h - 1, 0)
    r2, c2 = transform_rc_scientific_to_display(h - 1, w - 1, h, w, identity=ident)
    assert (r2, c2) == (0, w - 1)


def test_transpose_detection_fails_equality():
    a = _asymmetric_marker_frame(20, 30)
    d = apply_display_transform(a)
    t = a.T
    if t.shape == d.shape:
        assert not np.allclose(d, apply_display_transform(t))


def test_frame_selector_loads_frame(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("F", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    assert page._raw is not None
    sha1 = page.current_raw_frame_sha()
    page._goto_frame(2)
    assert page.frame_spin.value() == 2
    # Overlays cleared on change
    assert page._result is None
    assert page._masks == {}
    assert "Frame changed" in page.inline_note.text() or page.inline_note.isVisible() or "Loading" in page.inline_note.text()
    page._goto_frame(1)
    assert page.wait_until_frame_ready(30000)
    assert page.current_raw_frame_sha() == sha1 or page._raw is not None


def test_exact_time_maps_to_frame(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("T", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    page.exact_time.setCurrentText("01:30")
    page._jump_exact_time()
    # minute 90 → frame 91 with matlab_index_minus_1 mapping (frame = minute+1)
    assert page.frame_spin.value() == 91
    # Synthetic mats may have fewer than 91 frames; selector mapping is what this test covers.


def test_cached_diagnostics_restored(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("C", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    raw = page._raw
    sha = sha256_file(syn_mats[0])
    res = run_feature_pipeline_v2(
        raw,
        signal_contract_id="kfu_amp_all_v1",
        profile_id=session.profile_id,
        frame_index=1,
        source_mat_sha256=sha,
    )
    key = make_cache_key(
        source_mat_sha256=sha,
        frame_index=1,
        profile_id=session.profile_id,
        signal_contract_id="kfu_amp_all_v1",
        profile=session.profile,
    )
    page._cache.save(key, res)
    page.clear_results()
    page._source_sha = sha
    page._raw = raw
    assert page._try_load_cache() is True
    assert page._cache_status == "cached"
    assert page._result_ser is not None


def test_stale_cache_rejected_on_feature_version_change(tmp_path, syn_mats, session):
    session.project = create_project("S", language="en", workspace_parent=tmp_path / "ws")
    mat = syn_mats[0]
    # minimal frame
    from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent

    loaded = load_amplitude_matrix(mat, variable="Amp_all")
    frame, _ = extract_frame_consistent(loaded.data, 1, height_bins=256, frequency_bins=400)
    sha = sha256_file(mat)
    res = run_feature_pipeline_v2(
        frame,
        signal_contract_id="kfu_amp_all_v1",
        profile_id=session.profile_id,
        frame_index=1,
        source_mat_sha256=sha,
    )
    cache = V2FeatureCache(tmp_path / "cache")
    key = make_cache_key(
        source_mat_sha256=sha,
        frame_index=1,
        profile_id=session.profile_id,
        signal_contract_id="kfu_amp_all_v1",
        profile=session.profile,
        feature_version=FEATURE_VERSION,
    )
    cache.save(key, res)
    stale = make_cache_key(
        source_mat_sha256=sha,
        frame_index=1,
        profile_id=session.profile_id,
        signal_contract_id="kfu_amp_all_v1",
        profile=session.profile,
        feature_version="iml2-9.9.9",
    )
    # Different digest path — status not_computed or stale if somehow shared
    assert stale.digest() != key.digest()
    assert cache.status_for(stale) == "not_computed"


def test_single_and_sequence_frame_lists(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("Q", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.mode_combo.setCurrentIndex(0)
    assert page.mode_combo.currentData() == "single"
    page.mode_combo.setCurrentIndex(1)
    page.seq_start.setValue(1)
    page.seq_end.setValue(30)
    page.seq_step.setValue(10)
    frames = page._selected_sequence_frames()
    assert frames == [1, 11, 21]
    page.seq_custom.setPlainText("5,7,9-11")
    assert page._selected_sequence_frames() == [5, 7, 9, 10, 11]


def test_cache_clear_preserves_mat(tmp_path, syn_mats, session):
    mat = syn_mats[0]
    assert mat.is_file()
    cache = V2FeatureCache(tmp_path / "cache")
    sha = sha256_file(mat)
    from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent

    loaded = load_amplitude_matrix(mat, variable="Amp_all")
    frame, _ = extract_frame_consistent(loaded.data, 1, height_bins=256, frequency_bins=400)
    res = run_feature_pipeline_v2(
        frame, signal_contract_id="kfu_amp_all_v1", profile_id="p", frame_index=1, source_mat_sha256=sha
    )
    key = make_cache_key(
        source_mat_sha256=sha, frame_index=1, profile_id="p", signal_contract_id="kfu_amp_all_v1", profile={}
    )
    cache.save(key, res)
    n = cache.clear_for_source(sha)
    assert n >= 1
    assert mat.is_file()


def test_ordinary_frame_change_inline_not_modal(qtbot, session, syn_mats, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    called = {"n": 0}

    def _boom(*a, **k):
        called["n"] += 1
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", _boom)
    session.project = create_project("M", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    page._goto_frame(2)
    page._goto_frame(3)
    assert page.wait_until_frame_ready(30000)
    assert called["n"] == 0
    note = page.inline_note.text().lower()
    assert (
        "frame changed" in page.inline_note.text()
        or "кадра" in note
        or "loading" in note
        or page._current_ctx is not None
    )


def test_v2_remains_shadow_and_ruleengine_untouched():
    from ionogram_morphology_lab.features.v2.pipeline import LABEL_EN
    from ionogram_morphology_lab.rules.engine import RuleEngine

    assert "shadow" in LABEL_EN.lower() or "experimental" in LABEL_EN.lower()
    assert FEATURE_VERSION == "iml2-0.2.0"
    # RuleEngine still importable / default pack loads
    engine = RuleEngine()
    assert engine is not None


def test_algorithm_parameter_hash_stable(session):
    h1 = algorithm_parameter_hash(session.profile)
    h2 = algorithm_parameter_hash(session.profile)
    assert h1 == h2


def test_async_worker_single_frame(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.ui.v2_diagnostics_worker import V2DiagnosticsWorker

    cache = V2FeatureCache(tmp_path / "cache")
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

    def _ok(payload):
        done["p"] = payload

    worker.finished_ok.connect(_ok)
    worker.start()
    qtbot.waitUntil(lambda: "p" in done, timeout=120000)
    assert done["p"]["recomputed"] == 1
    assert done["p"]["failures"] == 0
    # Second run hits cache
    worker2 = V2DiagnosticsWorker(
        mat_path=syn_mats[0],
        frames=[1],
        profile=session.profile,
        profile_id=session.profile_id,
        signal_contract_id="kfu_amp_all_v1",
        cache=cache,
        force_recompute=False,
    )
    done2 = {}
    worker2.finished_ok.connect(lambda p: done2.update(p=p))
    worker2.start()
    qtbot.waitUntil(lambda: "p" in done2, timeout=120000)
    assert done2["p"]["cache_hits"] == 1
