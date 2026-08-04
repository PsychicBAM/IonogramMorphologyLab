"""Phase 4A.1b — dtype honesty, extraction parity, strict invalid inputs."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from ionogram_morphology_lab.scientific_outputs.formulas.axes import bin_to_mhz, bin_to_nominal_height_km
from ionogram_morphology_lab.scientific_outputs.formulas.trace_metrics import local_width_bins
from ionogram_morphology_lab.scientific_outputs.formula_summary import SUMMARY_GROUP_KEYS, compute_formula_summary
from ionogram_morphology_lab.scientific_outputs.signal_contracts import (
    extract_frame_consistent,
    frame_stats,
)
from ionogram_morphology_lab.importers.adapters import extract_frame_kfu
from ionogram_morphology_lab.app.settings_store import DEFAULT_SETTINGS

ROOT = Path(__file__).resolve().parents[1]
MAT = Path(r"E:\ionog\conference_presentation\ion2013\maps201301jan\data\Am_all_2013-01-01.mat")


def test_observational_definitions_group_exists():
    assert "observational_definitions" in SUMMARY_GROUP_KEYS
    items = [
        {"formula_id": "F001", "classification": "exact_physical_formula"},
        {"formula_id": "F002", "classification": "observational_definition"},
    ]
    s = compute_formula_summary(items)
    assert s["exact_physical_formulas"] == ["F001"]
    assert s["observational_definitions"] == ["F002"]


def test_frame_stats_preserves_source_dtype():
    raw = np.array([[1, 2], [3, 4]], dtype=np.uint16)
    st = frame_stats(raw)
    assert st["source_dtype"] == "uint16"
    assert st["analysis_dtype"] == "float64"
    assert st["dtype"] == "uint16"  # alias must remain source
    assert st["source_shape"] == [2, 2]
    assert st["saturation_is_heuristic"] is True


def test_local_width_rejects_2d_no_ravel():
    q = local_width_bins(np.ones((3, 4)))
    assert q.valid is False
    assert "wrong_dimensionality" in q.reason_invalid


def test_bin_index_rejects_fractional_and_bool():
    q = bin_to_mhz(3.8, start_mhz=1.5, step_mhz=0.019, frequency_bins=400)
    assert q.valid is False
    assert q.value is None
    q2 = bin_to_mhz(True, start_mhz=1.5, step_mhz=0.019, frequency_bins=400)
    assert q2.valid is False
    q3 = bin_to_nominal_height_km(2.5, km_per_bin=2.5, height_bins=256)
    assert q3.valid is False


def test_pipelines_disabled():
    assert DEFAULT_SETTINGS["analysis"]["scientific_formula_pipeline_enabled"] is False
    assert DEFAULT_SETTINGS["analysis"]["scientific_feature_pipeline_v2_enabled"] is False


@pytest.mark.skipif(not MAT.is_file(), reason="approved Amp_all archive not present")
def test_caller_frame_parity_sha():
    from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
    from ionogram_morphology_lab.cache.frame_store import FrameStore
    from ionogram_morphology_lab.matlab_studio.api_bridge import prepare_run_workspace
    import tempfile
    import scipy.io as sio

    amp = load_amplitude_matrix(MAT, variable="Amp_all").data
    profile = {
        "profile_id": "kfu_cyclone_2013_2014",
        "amplitude_variable_name": "Amp_all",
        "height_bins": 256,
        "frequency_bins": 400,
        "frames_per_file": 1440,
        "matrix_layout": "frames_stacked_rows",
        "profile_verification_status": "provisional",
    }

    def sha(a: np.ndarray) -> str:
        return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()

    with tempfile.TemporaryDirectory() as td:
        store = FrameStore(MAT, profile, cache_root=td)
        store.ensure_ready()
        for fi in (1, 421, 1440):
            c, _ = extract_frame_consistent(amp, fi)
            k = extract_frame_kfu(amp, fi)
            v = store.get_frame(fi, prefetch=False)
            with tempfile.TemporaryDirectory() as wdir:
                prepare_run_workspace(Path(wdir), current_frame=v, metadata={"frame_index": fi})
                m = sio.loadmat(str(Path(wdir) / "iml_bridge_inputs.mat"))
                bridge = np.asarray(m["iml_current_frame"])
            for arr in (k, v, bridge):
                assert arr.shape == c.shape
                assert arr.dtype == c.dtype
                assert np.array_equal(arr, c)
                assert sha(arr) == sha(c)
