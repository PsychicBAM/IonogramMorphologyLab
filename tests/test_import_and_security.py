from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from ionogram_morphology_lab.importers.adapters import extract_frame_kfu, load_amplitude_matrix, select_adapter
from ionogram_morphology_lab.importers.audit import audit_frame, audit_mat_path
from ionogram_morphology_lab.importers.mat_inventory import inventory_mat
from ionogram_morphology_lab.security import (
    ForbiddenPathError,
    ProtectedStudyConfig,
    default_blocklist,
    reset_protection,
    set_active_protection,
)
from ionogram_morphology_lab.synthetic.generator import generate_synthetic_case, write_synthetic_mat_library
from ionogram_morphology_lab.utils.paths import app_root


@pytest.fixture(scope="module")
def syn_dir(tmp_path_factory):
    d = app_root() / "synthetic_data"
    write_synthetic_mat_library(d)
    return d


@pytest.fixture(autouse=True)
def reset_optional_protection():
    reset_protection()
    yield
    reset_protection()


def test_optional_protection_allows_default_and_blocks_configured_path():
    ordinary = r"E:\ionog\conference_presentation\ordinary_project\data\x.csv"
    assert default_blocklist().assert_allowed(ordinary) == Path(ordinary)
    p = r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator\09_blinded_review_package\secret\x.csv"
    assert default_blocklist().assert_allowed(p) == Path(p)
    bl = set_active_protection(
        ProtectedStudyConfig(
            enabled=True,
            protected_path_fragments=["09_blinded_review_package"],
        )
    )
    with pytest.raises(ForbiddenPathError):
        bl.assert_allowed(p)


def test_mat_v5_inventory(syn_dir):
    path = syn_dir / "demo_smooth_trace.mat"
    inv = inventory_mat(path)
    assert inv.readable
    assert inv.status == "valid"
    assert any(v.name == "Amp_all" for v in inv.variables)


def test_missing_variable(tmp_path):
    p = tmp_path / "novar.mat"
    savemat(str(p), {"other": np.zeros((10, 10))})
    res = audit_mat_path(p, {"amplitude_variable_name": "Amp_all"})
    assert res.status == "insufficient_metadata"


def test_all_zero_and_nonfinite_frames():
    z = generate_synthetic_case("all_zero")
    assert audit_frame(z)["status"] == "all_zero"
    nf = generate_synthetic_case("nonfinite_corruption")
    assert audit_frame(nf)["status"] in ("nonfinite_data", "valid_with_warning", "valid")


def test_extract_frame_kfu_shape():
    amp = np.arange(3 * 256 * 400, dtype=np.float64).reshape(3 * 256, 400)
    frame = extract_frame_kfu(amp, 2)
    assert frame.shape == (256, 400)
    assert np.array_equal(frame, amp[256:512, :])
    assert np.shares_memory(frame, amp) is False


def test_cache_provenance(tmp_path, syn_dir):
    from ionogram_morphology_lab.cache.chunk_cache import ChunkedCache

    loaded = load_amplitude_matrix(syn_dir / "demo_smooth_trace.mat")
    cache = ChunkedCache(tmp_path / "cache")
    cdir = cache.build_from_array(loaded.data, syn_dir / "demo_smooth_trace.mat", "Amp_all")
    prov = cache.load_provenance(cdir)
    assert "Derived cache only" in prov["note"]
    assert prov["source_sha256"]
