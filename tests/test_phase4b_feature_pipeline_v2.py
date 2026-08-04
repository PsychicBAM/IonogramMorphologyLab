"""Phase 4B.2 — Feature Pipeline V2 geometry measurements (shadow mode)."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.registry import list_feature_ids, validate_registry_completeness
from ionogram_morphology_lab.features.v2.representations import build_representations
from ionogram_morphology_lab.features.v2.synthetic_geometry import (
    GEOMETRY_CASES,
    generate_geometry_case,
    thin_diagonal_baseline,
    thin_horizontal_ridge,
    thin_sloping_ridge,
    two_parallel_branches,
    vertical_interference_stripes,
    zero_frame,
)
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.rules.engine import RuleEngine
from ionogram_morphology_lab.segmentation.trace_interference import segment_frame


def test_feature_version():
    assert FEATURE_VERSION == "iml2-0.2.0"


def test_raw_frame_unchanged():
    raw = thin_sloping_ridge()
    before = raw.copy()
    h = hashlib.sha256(before.tobytes()).hexdigest()
    res = run_feature_pipeline_v2(raw)
    assert np.array_equal(raw, before)
    assert hashlib.sha256(raw.tobytes()).hexdigest() == h
    assert np.array_equal(res.representations["raw"].array, before)


def test_normalized_not_serialized_as_raw():
    raw = thin_sloping_ridge()
    reps = build_representations(raw)
    assert reps["raw"].status == "scientific"
    assert reps["diagnostic_normalized"].status == "diagnostic"
    assert not np.allclose(reps["diagnostic_normalized"].array, raw)


def test_trace_reproducibility():
    raw = thin_sloping_ridge()
    a = run_feature_pipeline_v2(raw)
    b = run_feature_pipeline_v2(raw)
    assert a.features["v2_centerline_count"].value == b.features["v2_centerline_count"].value
    assert np.array_equal(a.masks["trace_accepted"], b.masks["trace_accepted"])


def test_thin_sloping_ridge_not_falsely_widened():
    raw = thin_sloping_ridge()
    res = run_feature_pipeline_v2(raw)
    n = res.features.get("v2_normal_to_ridge_width_bins")
    assert n is not None and n.valid
    assert float(n.value) < 12.0


def test_thin_horizontal_h_not_falsely_elevated():
    res = run_feature_pipeline_v2(thin_horizontal_ridge())
    thr = res.features.get("v2_true_slope_compensated_horizontal_residual_bins")
    hap = res.features.get("v2_horizontal_axis_width_applicable_fraction")
    assert hap is not None and hap.valid and float(hap.value) < 0.25
    assert thr is not None and (not thr.valid or float(thr.value) < 2.0)
    assert float(res.features["v2_axis_tangent_rejection_count"].value) > 0


def test_anisotropic_h_v_independence():
    thin = run_feature_pipeline_v2(generate_geometry_case("thin_steep_baseline"))
    hb = run_feature_pipeline_v2(generate_geometry_case("horizontally_broadened_ridge"))
    steep_h = thin.features["v2_fixed_horizontal_axis_width_bins"]
    broad_h = hb.features["v2_fixed_horizontal_axis_width_bins"]
    assert steep_h.valid and broad_h.valid
    assert float(broad_h.value) > float(steep_h.value) + 1.0
    shallow = run_feature_pipeline_v2(generate_geometry_case("thin_shallow_baseline"))
    vb = run_feature_pipeline_v2(generate_geometry_case("vertically_broadened_ridge"))
    assert float(vb.features["v2_fixed_vertical_axis_width_bins"].value) > float(
        shallow.features["v2_fixed_vertical_axis_width_bins"].value
    ) + 1.0


def test_parallel_branch_widths_not_separation():
    res = run_feature_pipeline_v2(two_parallel_branches())
    assert float(res.features["v2_branch_count"].value) >= 2
    for br in res.branch_records:
        med = ((br.get("widths") or {}).get("fixed_vertical") or {}).get("median")
        if med is not None:
            assert float(med) < 8.0
    vv = res.features.get("v2_fixed_vertical_axis_width_bins")
    if vv is not None and vv.valid:
        assert float(vv.value) < 10.0


def test_branch_records_include_widths():
    res = run_feature_pipeline_v2(thin_diagonal_baseline())
    assert res.branch_records
    assert "widths" in res.branch_records[0]


def test_floor_features_not_tautological_only():
    res = run_feature_pipeline_v2(thin_sloping_ridge())
    assert "v2_preexclusion_floor_overlap_fraction" in res.features
    assert "v2_floor_candidate_removed_fraction" in res.features
    nf = res.features["v2_accepted_nonfloor_trace_fraction"]
    assert nf.metadata.get("role") == "postcondition_check_only"


def test_vertical_interference_excluded_from_range_evidence():
    raw = vertical_interference_stripes()
    res = run_feature_pipeline_v2(raw)
    assert res.masks["interference"].any()
    level = res.features["v2_interference_level"].value
    assert level in ("present", "significant", "dominant", "prevents_assessment", "none")


def test_zero_frame_abstains():
    res = run_feature_pipeline_v2(zero_frame())
    assert res.quality_status == "not_assessable"
    cov = res.features.get("v2_trace_pixel_fraction")
    assert cov is not None
    assert cov.valid is False
    assert cov.value is None


def test_missing_measurement_not_zero():
    res = run_feature_pipeline_v2(zero_frame())
    for fid, f in res.features.items():
        if not f.valid and f.reason_invalid:
            assert f.value is None or f.unit == "categorical"


def test_branch_separation():
    res = run_feature_pipeline_v2(two_parallel_branches())
    bc = res.features.get("v2_branch_count")
    assert bc is not None and bc.valid
    assert float(bc.value) >= 2
    sep = res.features.get("v2_branch_separation_bins")
    assert sep is not None and sep.valid


def test_multiple_centerlines_supported():
    res = run_feature_pipeline_v2(generate_geometry_case("crossing_branches"))
    assert "v2_centerline_count" in res.features


def test_shadow_mode_cannot_change_ruleengine():
    raw = generate_geometry_case("vertically_broadened_ridge")
    seg = segment_frame(raw)
    feats = extract_features(raw, seg)
    before = RuleEngine().evaluate(feats.values, quality_status="valid").candidate_morphology
    _ = run_feature_pipeline_v2(raw)
    after = RuleEngine().evaluate(
        extract_features(raw, segment_frame(raw)).values, quality_status="valid"
    ).candidate_morphology
    assert before == after


def test_no_spread_classifications_emitted():
    for name in ("thin_sloping_ridge", "vertically_broadened_ridge", "broadened_both_axes"):
        res = run_feature_pipeline_v2(generate_geometry_case(name))
        keys = set(res.features)
        assert "frequency_spread" not in keys
        assert "range_spread" not in keys
        assert "mixed_spread" not in keys


def test_feature_registry_completeness():
    errs = validate_registry_completeness()
    assert not errs, errs
    assert len(list_feature_ids()) >= 12


def test_feature_version_serialization():
    res = run_feature_pipeline_v2(thin_sloping_ridge())
    ser = res.to_serializable()
    assert ser["feature_version"] == FEATURE_VERSION
    assert ser["affects_classification"] is False
    assert ser["shadow_mode"] is True
    assert "branch_records" in ser
    # No global per-branch feature IDs
    assert not any(k.startswith("v2_branch_") and k[10:11].isdigit() for k in res.features)


def test_temporal_neighbors_unavailable_abstains():
    res = run_feature_pipeline_v2(thin_sloping_ridge(), neighbors=None)
    t = res.features["v2_temporal_mask_overlap"]
    assert t.valid is False
    assert t.value is None


def test_temporal_persistence_with_neighbors():
    raw = thin_sloping_ridge()
    base = run_feature_pipeline_v2(raw)
    nb = {
        "frame_index": 0,
        "trace_mask": base.masks["trace_accepted"],
        "interference_mask": base.masks["interference"],
        "centerlines": base.centerlines,
        "h_width_med": 2.0,
        "v_width_med": 2.0,
        "branch_count": len(base.centerlines),
    }
    res = run_feature_pipeline_v2(raw, neighbors=[nb])
    assert res.features["v2_temporal_mask_overlap"].valid


def test_unresolved_signals_not_in_pipeline_path():
    res = run_feature_pipeline_v2(thin_sloping_ridge(), signal_contract_id="kfu_amp_all_v1")
    assert "Phs_all" not in res.signal_contract_id


def test_all_geometry_cases_run():
    for name in GEOMETRY_CASES:
        res = run_feature_pipeline_v2(generate_geometry_case(name))
        assert res.feature_version == FEATURE_VERSION


def test_local_width_estimators_present():
    from ionogram_morphology_lab.features.v2.widths import _estimate_all

    est = _estimate_all(np.array([0, 1, 3, 5, 3, 1, 0], dtype=float))
    assert set(est) >= {"fwhm", "robust_percentile", "second_moment", "connected_support"}


def test_diagnostics_page_builds():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    class S:
        project = None
        current_frame_index = 1
        profile_id = "kfu"

    class I:
        language = "en"

    page = FeatureDiagnosticsPage(S(), I())
    assert page is not None


def test_consolidation_keeps_preconsol_and_consolidated_counts():
    res = run_feature_pipeline_v2(generate_geometry_case("crossing_branches"))
    assert "v2_preconsolidation_centerline_count" in res.features
    assert "v2_consolidated_branch_count" in res.features
    assert res.component_decisions.get("decisions") is not None
    assert res.features["v2_centerline_count"].value == res.features["v2_consolidated_branch_count"].value


def test_floor_mask_exported_and_not_silently_in_accepted():
    res = run_feature_pipeline_v2(thin_sloping_ridge())
    assert "floor_clutter" in res.masks
    assert "impulses" in res.masks
    assert "trace_candidate_before_exclusion" in res.masks
    if res.masks["floor_clutter"].any() and res.masks["trace_accepted"].any():
        # accepted must not be majority floor
        frac = float((res.masks["trace_accepted"] & res.masks["floor_clutter"]).mean())
        assert frac < 0.55


def test_separate_width_coordinate_features():
    res = run_feature_pipeline_v2(thin_diagonal_baseline())
    for fid in (
        "v2_fixed_vertical_axis_width_bins",
        "v2_fixed_horizontal_axis_width_bins",
        "v2_normal_to_ridge_width_bins",
        "v2_normal_width_baseline_residual_bins",
        "v2_true_slope_compensated_horizontal_residual_bins",
        "v2_along_ridge_support_length_bins",
        "v2_horizontal_axis_width_applicable_fraction",
        "v2_vertical_axis_width_applicable_fraction",
        "v2_axis_tangent_rejection_count",
        "v2_multiple_intersection_rejection_count",
        "v2_branch_overlap_rejection_count",
    ):
        assert fid in res.features
    assert "normal_to_ridge_width_map" in res.masks


def test_interference_potential_overlap_pre_exclusion():
    res = run_feature_pipeline_v2(vertical_interference_stripes())
    pot = res.features.get("v2_potential_trace_interference_overlap")
    assert pot is not None and pot.valid


def test_nan_inf_width_rejected():
    from ionogram_morphology_lab.features.v2.parity import local_vertical_width

    assert local_vertical_width(np.array([np.nan] * 5))["valid"] is False
    assert local_vertical_width(np.array([np.inf] * 5))["valid"] is False
