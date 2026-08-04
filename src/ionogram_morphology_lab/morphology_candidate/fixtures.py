"""Deterministic synthetic V2-feature fixtures for morphology candidate matrix."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.morphology_candidate.from_v2 import build_candidate_input_from_v2
from ionogram_morphology_lab.morphology_candidate.types import TemporalContext


def _f(value: Any, unit: str = "", valid: bool = True) -> dict[str, Any]:
    return {
        "feature_id": "",
        "value": value,
        "unit": unit,
        "valid": valid,
        "uncertainty": None,
        "confidence_status": "high" if valid else "none",
        "reason_invalid": "" if valid else "fixture_invalid",
        "affected_region": "",
        "missing_prerequisites": [],
        "estimator": "fixture",
        "metadata": {},
    }


def _base_features(**overrides: Any) -> dict[str, Any]:
    feats = {
        "v2_quality_status": _f("assessable", "categorical"),
        "v2_trace_pixel_fraction": _f(0.02, "fraction"),
        "v2_accepted_support_above_floor_fraction": _f(0.4, "fraction"),
        "v2_interference_level": _f("low", "categorical"),
        "v2_horizontal_width_elevated_fraction": _f(0.02, "fraction"),
        "v2_vertical_width_elevated_fraction": _f(0.02, "fraction"),
        "v2_coexistence_score": _f(0.05, "score"),
        "v2_coexistence_fraction": _f(0.02, "fraction"),
        "v2_horizontal_contiguous_broadening_length": _f(8.0, "bins"),
        "v2_vertical_contiguous_broadening_length": _f(8.0, "bins"),
        "v2_median_local_horizontal_width_bins": _f(3.0, "bins"),
        "v2_median_local_vertical_width_bins": _f(3.0, "bins"),
        "v2_horizontal_axis_width_applicable_fraction": _f(0.5, "fraction"),
        "v2_vertical_axis_width_applicable_fraction": _f(0.5, "fraction"),
        "v2_floor_clutter_burden": _f(0.05, "fraction"),
        "v2_full_height_stripe_burden": _f(0.02, "fraction"),
        "v2_oversegmentation_suspected": _f(0, "flag"),
        "v2_multiple_reflection_possibility": _f(0, "flag"),
        "v2_fragmentation_score": _f(0.1, "score"),
        "v2_branch_count": _f(1, "count"),
        "v2_consolidated_branch_count": _f(1, "count"),
        "v2_ox_ambiguity_possibility": _f(0, "flag"),
        "v2_vertical_stripe_count": _f(0, "count"),
        "v2_interference_trace_overlap": _f(0.05, "fraction"),
        "v2_usable_trace_fraction_outside_interference": _f(0.8, "fraction"),
        "v2_trace_continuity": _f(0.7, "fraction"),
        "v2_width_aggregate_branches_agree": _f(1, "flag"),
    }
    for k, v in overrides.items():
        if isinstance(v, dict) and "value" in v:
            feats[k] = v
        else:
            unit = feats.get(k, {}).get("unit", "")
            feats[k] = _f(v, unit)
    # stamp feature_id
    for fid, d in feats.items():
        d["feature_id"] = fid
    return feats


def make_v2_ser(
    *,
    frame_index: int = 1,
    source_sha: str = "a" * 64,
    features: dict[str, Any] | None = None,
    quality_status: str = "assessable",
    centerlines: list | None = None,
) -> dict[str, Any]:
    feats = features if features is not None else _base_features()
    return {
        "feature_version": FEATURE_VERSION,
        "signal_contract_id": "kfu_amp_all_v1",
        "profile_id": "kfu_cyclone_2013_2014",
        "frame_index": frame_index,
        "source_mat_sha256": source_sha,
        "processing_version": FEATURE_VERSION,
        "quality_status": quality_status,
        "features": feats,
        "centerlines": centerlines if centerlines is not None else [{"branch_id": 0}],
        "branch_records": [],
        "raw_centerlines": [],
        "component_decisions": {},
        "oversegmentation_suspected": bool((feats.get("v2_oversegmentation_suspected") or {}).get("value")),
        "mask_shapes": {},
        "representations": [],
        "experimental_label_en": "fixture",
        "experimental_label_ru": "fixture",
        "elapsed_s": 0.0,
        "notes": [],
        "shadow_mode": True,
        "affects_classification": False,
    }


def fixture_input(name: str):
    """Return (MorphologyCandidateInput, expected_candidate_substring_or_set)."""
    cache_id = "diag_" + name
    temporal = None
    expected: str | set[str]

    if name == "freq_strong_h":
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.40,
                v2_vertical_width_elevated_fraction=0.02,
                v2_horizontal_contiguous_broadening_length=10,
                v2_median_local_horizontal_width_bins=4,
            )
        )
        expected = "frequency_spread_candidate"
    elif name == "range_strong_v":
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.02,
                v2_vertical_width_elevated_fraction=0.40,
                v2_vertical_contiguous_broadening_length=10,
                v2_median_local_vertical_width_bins=4,
            )
        )
        expected = "range_spread_candidate"
    elif name == "mixed_independent":
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.40,
                v2_vertical_width_elevated_fraction=0.40,
                v2_coexistence_score=0.5,
                v2_coexistence_fraction=0.3,
            )
        )
        expected = "mixed_spread_candidate"
    elif name == "no_spread_clean":
        ser = make_v2_ser(features=_base_features())
        expected = "no_supported_visible_spread"
    elif name == "no_trace":
        ser = make_v2_ser(
            features=_base_features(
                v2_trace_pixel_fraction=0.0,
                v2_accepted_support_above_floor_fraction=0.0,
            ),
            quality_status="assessable",
            centerlines=[],
        )
        expected = "not_assessable"
    elif name == "missing_required":
        feats = _base_features()
        del feats["v2_coexistence_score"]
        ser = make_v2_ser(features=feats)
        expected = {"not_assessable", "indeterminate"}
    elif name == "vertical_interference":
        ser = make_v2_ser(
            features=_base_features(
                v2_vertical_width_elevated_fraction=0.45,
                v2_full_height_stripe_burden=0.40,
                v2_vertical_stripe_count=5,
                v2_interference_level="high",
            )
        )
        expected = {"not_assessable", "indeterminate", "no_supported_visible_spread"}
    elif name == "floor_clutter_v":
        ser = make_v2_ser(
            features=_base_features(
                v2_vertical_width_elevated_fraction=0.45,
                v2_floor_clutter_burden=0.55,
            )
        )
        expected = {"no_supported_visible_spread", "indeterminate", "not_assessable"}
    elif name == "secondary_echo_h":
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.40,
                v2_multiple_reflection_possibility=1,
            )
        )
        expected = {"no_supported_visible_spread", "indeterminate"}
    elif name == "oversegmentation":
        ser = make_v2_ser(
            features=_base_features(v2_oversegmentation_suspected=1, v2_fragmentation_score=0.9)
        )
        expected = {"not_assessable", "indeterminate"}
    elif name == "unrelated_hv":
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.40,
                v2_vertical_width_elevated_fraction=0.40,
                v2_coexistence_score=0.05,
                v2_coexistence_fraction=0.02,
            )
        )
        expected = "indeterminate"
    elif name == "weak_boundary":
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.10,
                v2_horizontal_contiguous_broadening_length=5,
            )
        )
        expected = "indeterminate"
    elif name == "blocking_interference":
        ser = make_v2_ser(
            features=_base_features(v2_interference_level="prevents_assessment")
        )
        expected = "not_assessable"
    elif name == "missing_neighbours":
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.40,
                v2_vertical_width_elevated_fraction=0.02,
            )
        )
        temporal = None
        expected = "frequency_spread_candidate"
    elif name == "consistent_neighbours":
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.20,
                v2_horizontal_contiguous_broadening_length=8,
                v2_median_local_horizontal_width_bins=3.5,
            )
        )
        temporal = TemporalContext(
            previous_frame_index=0,
            next_frame_index=2,
            same_source_sha=True,
            same_profile_contract_ruleset=True,
            neighbour_assessability=("assessable", "assessable"),
            neighbour_h_support=("moderate", "moderate"),
            neighbour_v_support=("none", "none"),
            persistence_count=2,
            temporal_context_signature="consistent_h",
        )
        expected = "frequency_spread_candidate"
    elif name == "contradictory_neighbours":
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.40,
            )
        )
        temporal = TemporalContext(
            previous_frame_index=0,
            same_source_sha=True,
            same_profile_contract_ruleset=True,
            persistence_count=0,
            isolated_candidate_flag=True,
            transition_flag=True,
            temporal_context_signature="contradict",
        )
        expected = "indeterminate"
    else:
        raise KeyError(name)

    # For missing_required, build without requiring coexistence in required list pass-through
    required = [
        "v2_quality_status",
        "v2_trace_pixel_fraction",
        "v2_interference_level",
        "v2_horizontal_width_elevated_fraction",
        "v2_vertical_width_elevated_fraction",
        "v2_coexistence_score",
    ]
    inp = build_candidate_input_from_v2(
        ser,
        diagnostics_cache_id=cache_id,
        interpreted_time="05:00",
        temporal=temporal,
        required_feature_ids=required,
    )
    # no_trace: force invalid trace
    if name == "no_trace":
        from dataclasses import replace

        inp = replace(inp, trace_present=False, trace_valid=False)
    return inp, expected


FIXTURE_NAMES = [
    "freq_strong_h",
    "range_strong_v",
    "mixed_independent",
    "no_spread_clean",
    "no_trace",
    "missing_required",
    "vertical_interference",
    "floor_clutter_v",
    "secondary_echo_h",
    "oversegmentation",
    "unrelated_hv",
    "weak_boundary",
    "blocking_interference",
    "missing_neighbours",
    "consistent_neighbours",
    "contradictory_neighbours",
]
