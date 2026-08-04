"""Build MorphologyCandidateInput from V2 serializable results (no pixel access)."""

from __future__ import annotations

from typing import Any, Mapping

from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.morphology_candidate.types import (
    FeatureValueRef,
    InterferenceAssessment,
    MorphologyCandidateInput,
    TemporalContext,
    deterministic_hash,
)


def _feat_ref(features: Mapping[str, Any], feature_id: str) -> FeatureValueRef:
    raw = features.get(feature_id)
    if raw is None:
        return FeatureValueRef(
            feature_id=feature_id,
            value=None,
            unit="",
            valid=False,
            missing=True,
        )
    if hasattr(raw, "to_dict"):
        d = raw.to_dict()
    elif isinstance(raw, Mapping):
        d = dict(raw)
    else:
        return FeatureValueRef(feature_id=feature_id, value=None, unit="", valid=False, missing=True)
    val = d.get("value")
    valid = bool(d.get("valid", True))
    # Explicit invalid / not_applicable entries are present (not missing).
    # Only treat as missing when the feature key itself is absent from the payload.
    missing = False
    return FeatureValueRef(
        feature_id=feature_id,
        value=val,
        unit=str(d.get("unit") or ""),
        valid=valid,
        missing=missing,
    )


def _num(ref: FeatureValueRef) -> float | None:
    if ref.missing or not ref.valid or ref.value is None:
        return None
    try:
        return float(ref.value)
    except (TypeError, ValueError):
        return None


def _flag_true(ref: FeatureValueRef) -> bool:
    if ref.missing or not ref.valid:
        return False
    v = ref.value
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v) != 0.0
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "suspected", "possible"}
    return False


def assess_interference(features: Mapping[str, FeatureValueRef]) -> InterferenceAssessment:
    level_ref = features.get(
        "v2_interference_level",
        FeatureValueRef("v2_interference_level", "", "", False, True),
    )
    if level_ref.missing:
        # Incomplete input: do not invent blocking interference
        return InterferenceAssessment(
            level="unavailable",
            raw_v2_interference_level="",
            notes=("interference_unavailable_missing_feature",),
        )
    level_raw = str(level_ref.value or "")
    # Map V2 categorical axis (none|present|significant|prevents_assessment)
    # onto candidate interference axis (none|low|moderate|high|blocking).
    level_map = {
        "none": "none",
        "low": "low",
        "present": "low",
        "moderate": "moderate",
        "significant": "high",
        "high": "high",
        "dominant": "blocking",
        "prevents_assessment": "blocking",
        "blocking": "blocking",
    }
    mapped = level_map.get(level_raw.lower(), "none" if not level_raw else "moderate")

    stripe = _num(features.get("v2_full_height_stripe_burden", FeatureValueRef("x", None, "", False, True))) or 0.0
    floor = _num(features.get("v2_floor_clutter_burden", FeatureValueRef("x", None, "", False, True))) or 0.0
    vert_count = _num(features.get("v2_vertical_stripe_count", FeatureValueRef("x", None, "", False, True))) or 0.0
    overseg = _flag_true(features.get("v2_oversegmentation_suspected", FeatureValueRef("x", False, "", True)))
    multi = _flag_true(features.get("v2_multiple_reflection_possibility", FeatureValueRef("x", False, "", True)))
    overlap = _num(features.get("v2_interference_trace_overlap", FeatureValueRef("x", None, "", False, True))) or 0.0

    notes: list[str] = []
    if mapped == "blocking":
        notes.append("blocking_interference_level")
    if stripe >= 0.25:
        notes.append("full_height_stripe_burden_high")
        if mapped != "blocking":
            mapped = "high"
    if floor >= 0.45:
        notes.append("floor_clutter_high")
    if overseg:
        notes.append("oversegmentation_suspected")
    if multi:
        notes.append("secondary_multiple_echo_suspicion")

    return InterferenceAssessment(
        level=mapped,
        vertical_interference=vert_count > 0 or stripe > 0.05,
        horizontal_interference=overlap > 0.2,
        floor_clutter=floor > 0.15,
        impulsive_noise=False,
        broad_artifact=stripe > 0.15,
        secondary_multiple_echo_suspicion=multi,
        oversegmentation=overseg,
        missing_data_regions=False,
        raw_v2_interference_level=level_raw,
        notes=tuple(notes),
    )


def v2_result_identity(ser: Mapping[str, Any]) -> str:
    payload = {
        "feature_version": ser.get("feature_version"),
        "source_mat_sha256": ser.get("source_mat_sha256"),
        "frame_index": ser.get("frame_index"),
        "profile_id": ser.get("profile_id"),
        "signal_contract_id": ser.get("signal_contract_id"),
        "processing_version": ser.get("processing_version"),
        "quality_status": ser.get("quality_status"),
        "features": {
            k: {
                "value": v.get("value") if isinstance(v, Mapping) else getattr(v, "value", None),
                "valid": v.get("valid") if isinstance(v, Mapping) else getattr(v, "valid", None),
            }
            for k, v in (ser.get("features") or {}).items()
        },
    }
    return deterministic_hash(payload)


def build_candidate_input_from_v2(
    ser: Mapping[str, Any],
    *,
    diagnostics_cache_id: str,
    interpreted_time: str = "",
    profile_version: str = "",
    signal_contract_version: str = "",
    raw_frame_identity: str = "",
    temporal: TemporalContext | None = None,
    required_feature_ids: list[str] | None = None,
) -> MorphologyCandidateInput:
    """Build immutable input from V2 serializable dict or PipelineV2Result.to_serializable()."""
    if hasattr(ser, "to_serializable"):
        ser = ser.to_serializable()
    features_raw = ser.get("features") or {}
    all_ids = set(features_raw.keys())
    # Collect refs for known + required ids
    needed = set(required_feature_ids or []) | {
        "v2_quality_status",
        "v2_trace_pixel_fraction",
        "v2_interference_level",
        "v2_horizontal_width_elevated_fraction",
        "v2_vertical_width_elevated_fraction",
        "v2_coexistence_score",
        "v2_coexistence_fraction",
        "v2_horizontal_contiguous_broadening_length",
        "v2_vertical_contiguous_broadening_length",
        "v2_median_local_horizontal_width_bins",
        "v2_median_local_vertical_width_bins",
        "v2_horizontal_axis_width_applicable_fraction",
        "v2_vertical_axis_width_applicable_fraction",
        "v2_floor_clutter_burden",
        "v2_full_height_stripe_burden",
        "v2_oversegmentation_suspected",
        "v2_multiple_reflection_possibility",
        "v2_accepted_support_above_floor_fraction",
        "v2_fragmentation_score",
        "v2_branch_count",
        "v2_consolidated_branch_count",
        "v2_ox_ambiguity_possibility",
        "v2_vertical_stripe_count",
        "v2_interference_trace_overlap",
        "v2_usable_trace_fraction_outside_interference",
        "v2_trace_continuity",
        "v2_width_aggregate_branches_agree",
    }
    features = {fid: _feat_ref(features_raw, fid) for fid in needed | all_ids}

    missing = tuple(
        fid
        for fid in (required_feature_ids or [])
        if features[fid].missing or (not features[fid].valid and features[fid].value is None)
    )

    quality = str(ser.get("quality_status") or "")
    q_feat = features.get("v2_quality_status")
    if q_feat and q_feat.value is not None:
        quality = str(q_feat.value)

    trace_frac = _num(features["v2_trace_pixel_fraction"])
    support_above = _num(features["v2_accepted_support_above_floor_fraction"])
    trace_present = bool(trace_frac is not None and trace_frac > 0)
    trace_valid = bool(
        quality not in {"not_assessable", "failed", "invalid"}
        and trace_present
        and (support_above is None or support_above > 0)
    )

    branch_count = int(_num(features["v2_consolidated_branch_count"]) or _num(features["v2_branch_count"]) or 0)
    interference = assess_interference(features)

    ambiguity: list[str] = []
    if _flag_true(features["v2_ox_ambiguity_possibility"]):
        ambiguity.append("ox_ambiguity_possibility")
    if _flag_true(features["v2_multiple_reflection_possibility"]):
        ambiguity.append("multiple_reflection_possibility")
    if _flag_true(features["v2_oversegmentation_suspected"]):
        ambiguity.append("oversegmentation_suspected")

    geometry_status = "ok" if ser.get("centerlines") is not None else "unknown"
    if quality in {"not_assessable", "failed"}:
        geometry_status = "failed" if quality == "failed" else "not_assessable"

    identity = v2_result_identity(ser)
    return MorphologyCandidateInput(
        source_sha256=str(ser.get("source_mat_sha256") or ""),
        frame_index=int(ser.get("frame_index") or 0),
        interpreted_time=interpreted_time,
        profile_id=str(ser.get("profile_id") or ""),
        profile_version=profile_version,
        signal_contract_id=str(ser.get("signal_contract_id") or ""),
        signal_contract_version=signal_contract_version,
        feature_version=str(ser.get("feature_version") or FEATURE_VERSION),
        diagnostics_cache_id=diagnostics_cache_id,
        raw_frame_identity=raw_frame_identity or identity[:16],
        geometry_status=geometry_status,
        quality_status=quality,
        trace_present=trace_present,
        trace_valid=trace_valid,
        features=features,
        branch_count=branch_count,
        interference=interference,
        ambiguity_flags=tuple(ambiguity),
        missing_feature_ids=missing,
        temporal=temporal,
        v2_result_identity=identity,
        shadow_mode=True,
    )
