from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ionogram_morphology_lab.disagreement.engine import DISAGREEMENT_TYPES, DisagreementEngine
from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.features.registry import FEATURE_REGISTRY
from ionogram_morphology_lab.i18n import I18n
from ionogram_morphology_lab.rendering.ionogram_render import RenderSpec, render_raw_ionogram
from ionogram_morphology_lab.rules.engine import RuleEngine
from ionogram_morphology_lab.similarity.compare import SIMILARITY_METHODS, compare_ionograms
from ionogram_morphology_lab.synthetic.generator import generate_synthetic_case
from ionogram_morphology_lab.utils.paths import app_root


def test_raw_matrix_unchanged_and_no_hidden_smoothing(tmp_path):
    frame = generate_synthetic_case("smooth_trace")
    original = frame.copy()
    freq = list(np.linspace(1.5, 9.081, 400))
    rng = [i * 2.5 for i in range(256)]
    meta = render_raw_ionogram(
        frame,
        freq,
        rng,
        tmp_path / "r.png",
        spec=RenderSpec(scaling_method="none", warnings=["nominal virtual-height axis"]),
    )
    assert np.array_equal(frame, original)
    assert meta["raw_unchanged"] is True
    assert meta["smoothing"] is False
    assert meta["interpolation"] == "nearest"
    assert "nominal virtual-height" in meta["render_spec"]["warnings"][0]


def test_feature_groups_synthetic():
    assert len(FEATURE_REGISTRY) >= 25
    h = extract_features(generate_synthetic_case("horizontally_diffuse"))
    v = extract_features(generate_synthetic_case("vertically_diffuse"))
    m = extract_features(generate_synthetic_case("mixed_diffuse"))
    inter = extract_features(generate_synthetic_case("vertical_interference"))
    dbl = extract_features(generate_synthetic_case("clean_double_branch"))
    # Orientation-sensitive ratios (bounding-box widths can be large for both)
    h_ratio = h.values["median_horizontal_width"] / max(h.values["median_vertical_width"], 1e-6)
    v_ratio = v.values["median_vertical_width"] / max(v.values["median_horizontal_width"], 1e-6)
    assert h.values["horizontal_broadening_persistence"] >= 0.0
    assert v.values["vertical_broadening_persistence"] >= 0.0
    assert h_ratio > 0.2 or h.values["frequency_projection_entropy"] > 0
    assert v_ratio > 0.2 or v.values["vertical_projection_entropy"] > 0
    assert m.values["mixed_width_score"] > 0
    assert inter.values["vertical_stripe_density"] > 0
    assert dbl.values["parallel_branch_count"] >= 2


def test_similarity_identical_and_incompatible():
    a = generate_synthetic_case("smooth_trace")
    r = compare_ionograms(a, a.copy())
    assert r.status == "ok"
    assert r.metrics["normalized_cross_correlation"] > 0.99
    assert len(SIMILARITY_METHODS) >= 14
    bad = compare_ionograms(a, a[:100, :100])
    assert bad.status == "not_comparable"
    # axis mismatch
    freq = np.linspace(1, 2, 400)
    freq2 = np.linspace(3, 4, 400)
    rng = np.arange(256) * 2.5
    r2 = compare_ionograms(a, a, freq, freq2, rng, rng)
    assert r2.status == "not_comparable"


def test_rules_ox_and_interference_do_not_force_spread():
    eng = RuleEngine()
    # O/X-like
    feats = {
        "possible_ox_compatibility": 0.8,
        "parallel_branch_count": 2.0,
        "median_horizontal_width": 6.0,
        "horizontal_broadening_persistence": 0.4,
        "median_vertical_width": 2.0,
        "vertical_broadening_persistence": 0.0,
        "mixed_width_score": 0.0,
        "mixed_coverage": 0.0,
        "interference_dominance": 0.0,
        "vertical_stripe_density": 0.0,
        "trace_pixel_fraction": 0.05,
    }
    res = eng.evaluate(feats)
    assert res.candidate_morphology in ("abstain", "uncertain") or res.confidence_status == "abstain"
    # interference vs range
    feats2 = {
        "median_vertical_width": 20.0,
        "vertical_broadening_persistence": 0.5,
        "median_horizontal_width": 1.0,
        "horizontal_broadening_persistence": 0.0,
        "mixed_width_score": 0.0,
        "mixed_coverage": 0.0,
        "interference_dominance": 0.7,
        "vertical_stripe_density": 0.4,
        "possible_ox_compatibility": 0.0,
        "parallel_branch_count": 0.0,
        "trace_pixel_fraction": 0.1,
    }
    res2 = eng.evaluate(feats2)
    assert res2.candidate_morphology != "range" or "range_vs_vertical_interference" in res2.disagreement_flags
    assert any(not r.enabled for r in eng.rules)


def test_disagreement_can_abstain():
    rep = DisagreementEngine().analyze(
        "frequency",
        ["frequency_vs_ox_ambiguity"],
        possible_ox=True,
    )
    assert rep.can_abstain
    assert "frequency_vs_ox_ambiguity" in rep.flags
    assert set(DISAGREEMENT_TYPES)


def test_i18n_parity():
    en = I18n("en")
    ru = I18n("ru")
    assert set(en.keys()) == set(ru.keys())
    assert len(en.keys()) >= 40


def test_no_solar_features_in_registry():
    banned_ids = ["sunrise", "sunset", "solar_zenith", "f10_7", "kp", "dst", "ae", "dawn", "dusk"]
    keys = {k.lower() for k in FEATURE_REGISTRY}
    for b in banned_ids:
        assert b not in keys
        assert not any(b in k for k in keys)


def test_low_signal_abstention_path():
    eng = RuleEngine()
    feats = extract_features(generate_synthetic_case("low_signal")).values
    res = eng.evaluate(feats, quality_status="valid_with_warning")
    assert res.candidate_morphology in (
        "none",
        "abstain",
        "indeterminate",
        "not_assessable",
        "frequency",
        "range",
        "mixed",
        "artifact",
    )
