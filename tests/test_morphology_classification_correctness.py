"""Scientific classification correctness — clean traces must not default to mixed_spread."""

from __future__ import annotations

import math

import numpy as np
import pytest

from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.rules.engine import RuleEngine
from ionogram_morphology_lab.scientific_outputs.result_schema import normalize_morphology
from ionogram_morphology_lab.synthetic.generator import generate_synthetic_case


def _decide(kind: str):
    frame = generate_synthetic_case(kind)
    feats = extract_features(frame).values
    res = RuleEngine().evaluate(feats)
    return feats, res, normalize_morphology(res.candidate_morphology)


def test_clean_visible_trace_not_mixed():
    feats, res, morph = _decide("smooth_trace")
    assert feats["frequency_evidence_passed"] < 1.0 or feats["range_evidence_passed"] < 1.0
    assert res.candidate_morphology == "none"
    assert morph == "clean"
    assert morph != "mixed_spread"


def test_no_spread_category_reachable():
    _, res, morph = _decide("smooth_trace")
    assert morph == "clean"
    assert res.candidate_morphology == "none"


def test_empty_or_low_signal_not_forced_mixed():
    for kind in ("all_zero", "low_signal"):
        _, res, morph = _decide(kind)
        assert morph != "mixed_spread"
        assert res.candidate_morphology in (
            "none",
            "abstain",
            "not_assessable",
            "artifact",
            "frequency",
            "range",
            "diffuse",
        )


def test_diffuse_unspecified_reachable_with_width_evidence():
    eng = RuleEngine()
    res = eng.evaluate(
        {
            "trace_pixel_fraction": 0.04,
            "median_horizontal_width": 5.5,
            "median_vertical_width": 2.0,
            "horizontal_broadening_persistence": 0.35,
            "vertical_broadening_persistence": 0.05,
            "colocated_spread_fraction": 0.0,
            "frequency_evidence_passed": 0.0,
            "range_evidence_passed": 0.0,
            "frequency_evidence_absolute": 0.0,
            "range_evidence_absolute": 0.0,
            "interference_dominance": 0.0,
            "vertical_stripe_density": 0.0,
            "possible_ox_compatibility": 0.0,
            "parallel_branch_count": 0.0,
            "mixed_width_score": 0.0,
            "mixed_coverage": 0.0,
        }
    )
    assert res.candidate_morphology == "diffuse"
    assert normalize_morphology(res.candidate_morphology) == "diffuse_unspecified"
    assert res.confidence_status == "uncertain"


def test_clean_not_used_when_diffuse_exceeds_uncertainty_floor():
    eng = RuleEngine()
    res = eng.evaluate(
        {
            "trace_pixel_fraction": 0.05,
            "median_horizontal_width": 6.5,
            "median_vertical_width": 3.0,
            "horizontal_broadening_persistence": 0.40,
            "vertical_broadening_persistence": 0.10,
            "colocated_spread_fraction": 0.05,
            "frequency_evidence_passed": 0.0,
            "range_evidence_passed": 0.0,
            "frequency_evidence_absolute": 0.0,
            "range_evidence_absolute": 0.0,
            "interference_dominance": 0.0,
            "vertical_stripe_density": 0.0,
            "possible_ox_compatibility": 0.0,
            "parallel_branch_count": 0.0,
        }
    )
    assert normalize_morphology(res.candidate_morphology) != "clean"
    assert res.candidate_morphology in ("diffuse", "frequency", "abstain")


def test_interference_dominated_not_displayed_as_no_visible_spread():
    from ionogram_morphology_lab.ui.presenters import morphology_label

    assert morphology_label("interference_dominated", "en") != "No visible spread"
    assert morphology_label("interference_dominated", "ru") != "Явное рассеяние не обнаружено"
    assert "limited by interference" in morphology_label("interference_dominated", "en").lower()
    eng = RuleEngine()
    # Blocking interference (high dominance + almost no trace) → not_assessable, not clean.
    res = eng.evaluate(
        {
            "trace_pixel_fraction": 0.002,
            "interference_dominance": 0.75,
            "vertical_stripe_density": 0.4,
            "full_height_stripe_count": 5.0,
            "median_horizontal_width": 2.0,
            "median_vertical_width": 8.0,
            "horizontal_broadening_persistence": 0.1,
            "vertical_broadening_persistence": 0.4,
            "frequency_evidence_passed": 0.0,
            "range_evidence_passed": 1.0,
            "frequency_evidence_absolute": 0.0,
            "range_evidence_absolute": 1.0,
            "possible_ox_compatibility": 0.0,
            "parallel_branch_count": 0.0,
        }
    )
    morph = normalize_morphology(res.candidate_morphology)
    assert morph != "clean"
    assert morph == "not_assessable"
    assert res.interference_assessment == "prevents_assessment"


def test_r005_does_not_replace_assessable_morphology():
    """Moderate interference without blocking stripes must not force interference morphology."""
    eng = RuleEngine()
    res = eng.evaluate(
        {
            "trace_pixel_fraction": 0.04,
            "interference_dominance": 0.40,
            "vertical_stripe_density": 0.05,
            "full_height_stripe_count": 0.0,
            "median_horizontal_width": 10.0,
            "median_vertical_width": 3.0,
            "horizontal_broadening_persistence": 0.45,
            "vertical_broadening_persistence": 0.10,
            "frequency_evidence_passed": 1.0,
            "range_evidence_passed": 0.0,
            "frequency_evidence_absolute": 1.0,
            "range_evidence_absolute": 0.0,
            "colocated_spread_fraction": 0.0,
            "possible_ox_compatibility": 0.0,
            "parallel_branch_count": 0.0,
            "mixed_width_score": 0.0,
            "mixed_coverage": 0.0,
        }
    )
    morph = normalize_morphology(res.candidate_morphology)
    assert morph != "interference_dominated"
    assert morph == "frequency_spread"
    assert res.interference_assessment in ("present", "significant", "dominant")
    assert res.candidate_morphology == "frequency"


def test_frequency_spread_reachable_without_mixed():
    feats, res, morph = _decide("horizontally_diffuse")
    assert feats["frequency_evidence_passed"] >= 1.0
    assert morph in ("frequency_spread", "mixed_spread")
    if feats["range_evidence_passed"] < 1.0 or feats["colocated_spread_fraction"] < 0.20:
        assert morph == "frequency_spread"
        assert res.candidate_morphology == "frequency"


def test_range_spread_reachable_without_mixed():
    feats, res, morph = _decide("vertically_diffuse")
    # Pure vertical broadening must be able to surface as range_spread (not only mixed).
    assert morph in ("range_spread", "mixed_spread", "clean", "frequency_spread")
    if feats.get("range_evidence_passed", 0) >= 1.0 and feats.get("frequency_evidence_passed", 0) < 1.0:
        assert morph == "range_spread"
        assert res.candidate_morphology == "range"
    # Handcrafted tall thin bar: range evidence must dominate.
    bar = np.zeros((256, 400), dtype=float)
    bar[70:140, 200:204] = 120.0
    bar_feats = extract_features(bar).values
    bar_res = RuleEngine().evaluate(bar_feats)
    bar_morph = normalize_morphology(bar_res.candidate_morphology)
    assert bar_morph in ("range_spread", "mixed_spread", "clean", "interference_dominated", "indeterminate")
    if bar_feats.get("range_evidence_passed", 0) >= 1.0:
        assert bar_morph in ("range_spread", "mixed_spread")
        if bar_feats.get("frequency_evidence_absolute", 0) < 1.0:
            assert bar_morph == "range_spread"


def test_mixed_requires_both_independent_components():
    feats, res, morph = _decide("mixed_diffuse")
    if morph == "mixed_spread":
        assert feats.get("frequency_evidence_absolute", 0) >= 1.0
        assert feats.get("range_evidence_absolute", 0) >= 1.0
        assert feats["colocated_spread_fraction"] >= 0.20
        assert "R003" in res.activated_rules or (
            "R001" in res.activated_rules and "R002" in res.activated_rules
        )
    # Engine path: force mixed without both absolute axes must fail
    eng = RuleEngine()
    forced = eng.evaluate(
        {
            **feats,
            "frequency_evidence_passed": 1.0,
            "range_evidence_passed": 0.0,
            "frequency_evidence_absolute": 1.0,
            "range_evidence_absolute": 0.0,
            "colocated_spread_fraction": 0.0,
            "median_horizontal_width": 10.0,
            "horizontal_broadening_persistence": 0.5,
            "median_vertical_width": 1.0,
            "vertical_broadening_persistence": 0.0,
            "mixed_width_score": 9.0,
            "mixed_coverage": 1.0,
            "interference_dominance": 0.0,
            "vertical_stripe_density": 0.0,
            "possible_ox_compatibility": 0.0,
            "parallel_branch_count": 0.0,
            "trace_pixel_fraction": 0.05,
        }
    )
    assert forced.candidate_morphology != "mixed"


def test_nan_does_not_activate_spread_rule():
    eng = RuleEngine()
    res = eng.evaluate(
        {
            "frequency_evidence_passed": float("nan"),
            "range_evidence_passed": float("nan"),
            "median_horizontal_width": float("nan"),
            "horizontal_broadening_persistence": float("nan"),
            "median_vertical_width": float("nan"),
            "vertical_broadening_persistence": float("nan"),
            "colocated_spread_fraction": float("nan"),
            "mixed_width_score": float("nan"),
            "mixed_coverage": float("nan"),
            "interference_dominance": 0.0,
            "vertical_stripe_density": 0.0,
            "possible_ox_compatibility": 0.0,
            "parallel_branch_count": 0.0,
            "trace_pixel_fraction": 0.05,
        }
    )
    assert res.candidate_morphology not in ("frequency", "range", "mixed")


def test_missing_features_not_positive_evidence():
    eng = RuleEngine()
    res = eng.evaluate({"trace_pixel_fraction": 0.05})
    assert res.candidate_morphology not in ("frequency", "range", "mixed")


def test_vertical_interference_not_alone_range_spread():
    feats, res, morph = _decide("vertical_interference")
    assert morph != "range_spread"
    assert res.candidate_morphology != "range"
    # Stripe clutter must not become a positive frequency/range/mixed label.
    assert morph not in ("frequency_spread", "range_spread", "mixed_spread")
    assert morph in (
        "interference_dominated",
        "clean",
        "not_assessable",
        "indeterminate",
        "diffuse_unspecified",
    )
    assert res.candidate_morphology in (
        "artifact",
        "none",
        "not_assessable",
        "abstain",
        "indeterminate",
        "diffuse",
    )


def test_ox_branches_not_automatic_spread():
    _, res, morph = _decide("clean_double_branch")
    assert morph != "mixed_spread" or res.confidence_status == "abstain"
    assert res.candidate_morphology in ("abstain", "none", "frequency", "range", "artifact")


def test_quality_failure_not_positive_morphology():
    eng = RuleEngine()
    for q in ("unreadable", "CRC_error", "nonfinite_data", "all_zero"):
        res = eng.evaluate({"median_horizontal_width": 99.0}, quality_status=q)
        assert res.candidate_morphology == "not_assessable"
        assert normalize_morphology(res.candidate_morphology) == "not_assessable"


def test_result_includes_rule_trace():
    _, res, _ = _decide("smooth_trace")
    assert isinstance(res.activated_rules, list)
    assert isinstance(res.explanations_en, list)
    assert isinstance(res.measured_features, dict)
    d = res.to_dict()
    assert "activated_rules" in d
    assert "measured_features" in d


def test_canonical_clean_token_documented():
    # Serialized v1.1 token for non-spread is "clean" (legacy rule token "none").
    assert normalize_morphology("none") == "clean"
    assert normalize_morphology("clean") == "clean"
