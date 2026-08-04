"""Feature Pipeline V2 — shadow-mode scientific measurements from numeric frames."""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from ionogram_morphology_lab.features.v2.branches import measure_branches
from ionogram_morphology_lab.features.v2.interference import measure_interference
from ionogram_morphology_lab.features.v2.quality import assess_frame_quality
from ionogram_morphology_lab.features.v2.representations import build_representations
from ionogram_morphology_lab.features.v2.temporal import measure_temporal
from ionogram_morphology_lab.features.v2.trace import extract_trace
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION, MeasuredFeature, PipelineV2Result
from ionogram_morphology_lab.features.v2.widths import measure_local_widths

LABEL_EN = "Experimental features — not used by the current classification"
LABEL_RU = "Экспериментальные признаки — не участвуют в текущей классификации"

# Unresolved contracts must not drive decisions
UNRESOLVED_BLOCKED = frozenset({"Phs_all", "Date_Time1", "AmEsP", "A_map_F", "H_map_F"})


def run_feature_pipeline_v2(
    raw_frame: np.ndarray,
    *,
    signal_contract_id: str = "Amp_all@iml-contract-0.1",
    profile_id: str = "",
    frame_index: int = 0,
    source_mat_sha256: str = "",
    processing_version: str = FEATURE_VERSION,
    frequency_axis: np.ndarray | None = None,
    height_axis: np.ndarray | None = None,
    neighbors: list[dict[str, Any]] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> PipelineV2Result:
    """
    Run Feature Pipeline V2 in measurement-only mode.

    Does not emit frequency_spread / range_spread / mixed_spread.
    Does not alter RuleEngine classification.
    """
    t0 = time.perf_counter()
    notes: list[str] = [LABEL_EN, LABEL_RU, "shadow_mode", "affects_classification=false"]

    # Guard unresolved signal names if mistakenly passed as contract id
    for blocked in UNRESOLVED_BLOCKED:
        if blocked in (signal_contract_id or ""):
            notes.append(f"blocked_unresolved_signal:{blocked}")

    raw = np.asarray(raw_frame)
    raw_copy_hash_input = raw.copy()  # preserve for identity check by callers

    if cancel_check and cancel_check():
        return _cancelled_result(
            signal_contract_id, profile_id, frame_index, source_mat_sha256, processing_version, t0
        )

    quality_status, q_feats, _qmeta = assess_frame_quality(raw)
    reps = build_representations(raw)
    # Ensure raw representation is unchanged
    if not np.array_equal(reps["raw"].array, raw_copy_hash_input):
        notes.append("ERROR_raw_mutated")

    score = reps["signal_background_score"].array
    assert score is not None
    if cancel_check and cancel_check():
        return _cancelled_result(
            signal_contract_id, profile_id, frame_index, source_mat_sha256, processing_version, t0
        )

    trace_res = extract_trace(raw, score, quality_status)
    overseg = bool(trace_res.oversegmentation_suspected)
    width_feats, width_maps, branch_width_records = measure_local_widths(
        raw,
        trace_res.masks["trace_accepted"],
        trace_res.masks["interference"],
        trace_res.centerlines,
        floor_clutter=trace_res.masks.get("floor_clutter"),
        branch_labels=trace_res.masks.get("branch_labels"),
        oversegmentation_suspected=overseg,
    )
    # Merge branch-local width evidence into structured branch_records
    by_bid = {int(r["branch_id"]): r for r in branch_width_records}
    merged_branch_records: list[dict[str, Any]] = []
    for br in trace_res.branch_records:
        bid = int(br.get("branch_id", -1))
        row = dict(br)
        if bid in by_bid:
            row["widths"] = by_bid[bid]
        merged_branch_records.append(row)
    if not merged_branch_records and branch_width_records:
        merged_branch_records = [{"branch_id": r["branch_id"], "widths": r} for r in branch_width_records]
    plausible_pre = trace_res.masks.get("plausible_pre_exclusion")
    if plausible_pre is None:
        plausible_pre = trace_res.masks.get("trace_candidate_before_exclusion")
    interf_feats = measure_interference(
        trace_res.masks["interference"],
        trace_res.masks["trace_accepted"],
        quality_status,
        plausible_pre_exclusion=plausible_pre,
    )
    # Prefer preconsolidation count; fall back to legacy alias
    raw_n = None
    for key in ("v2_preconsolidation_centerline_count", "v2_raw_component_count"):
        if key in trace_res.features and trace_res.features[key].value is not None:
            raw_n = int(float(trace_res.features[key].value))
            break
    branch_feats = measure_branches(
        trace_res.masks["branch_labels"],
        trace_res.centerlines,
        trace_res.masks["trace_accepted"],
        oversegmentation_suspected=overseg,
        raw_component_count=raw_n,
    )

    h_med = width_feats.get("v2_median_local_horizontal_width_bins")
    v_med = width_feats.get("v2_median_local_vertical_width_bins")
    temporal_feats = measure_temporal(
        trace_res.masks["trace_accepted"],
        trace_res.masks["interference"],
        trace_res.centerlines,
        float(h_med.value) if h_med and h_med.valid and h_med.value is not None else None,
        float(v_med.value) if v_med and v_med.valid and v_med.value is not None else None,
        neighbors,
        oversegmentation_suspected=overseg,
    )

    # Axis availability markers (measurements only when contract permits)
    axis_feats: dict[str, MeasuredFeature] = {}
    if frequency_axis is None:
        axis_feats["v2_frequency_axis_available"] = MeasuredFeature(
            "v2_frequency_axis_available", 0.0, unit="flag", valid=True, confidence_status="high",
            metadata={"converted_units_disabled": True},
        )
    else:
        axis_feats["v2_frequency_axis_available"] = MeasuredFeature(
            "v2_frequency_axis_available", 1.0, unit="flag", valid=True, confidence_status="high",
        )
    if height_axis is None:
        axis_feats["v2_height_axis_available"] = MeasuredFeature(
            "v2_height_axis_available", 0.0, unit="flag", valid=True, confidence_status="high",
            metadata={"nominal_only": True},
        )
    else:
        axis_feats["v2_height_axis_available"] = MeasuredFeature(
            "v2_height_axis_available", 1.0, unit="flag", valid=True, confidence_status="high",
        )

    features: dict[str, MeasuredFeature] = {}
    for part in (q_feats, trace_res.features, width_feats, interf_feats, branch_feats, temporal_feats, axis_feats):
        features.update(part)

    # Hard guard: never emit classification-like spread labels from V2
    for banned in ("frequency_spread", "range_spread", "mixed_spread"):
        features.pop(banned, None)
        features.pop(f"v2_{banned}", None)

    masks = dict(trace_res.masks)
    masks.update(width_maps)

    notes.extend(trace_res.notes)
    elapsed = time.perf_counter() - t0
    return PipelineV2Result(
        feature_version=FEATURE_VERSION,
        signal_contract_id=signal_contract_id,
        profile_id=profile_id,
        frame_index=frame_index,
        source_mat_sha256=source_mat_sha256,
        processing_version=processing_version,
        quality_status=quality_status,
        features=features,
        masks=masks,
        representations=reps,
        centerlines=trace_res.centerlines,
        experimental_label_en=LABEL_EN,
        experimental_label_ru=LABEL_RU,
        elapsed_s=elapsed,
        notes=notes,
        raw_centerlines=trace_res.raw_centerlines,
        component_decisions=trace_res.component_decisions,
        oversegmentation_suspected=overseg,
        branch_records=merged_branch_records,
    )


def _cancelled_result(
    signal_contract_id: str,
    profile_id: str,
    frame_index: int,
    source_mat_sha256: str,
    processing_version: str,
    t0: float,
) -> PipelineV2Result:
    return PipelineV2Result(
        feature_version=FEATURE_VERSION,
        signal_contract_id=signal_contract_id,
        profile_id=profile_id,
        frame_index=frame_index,
        source_mat_sha256=source_mat_sha256,
        processing_version=processing_version,
        quality_status="not_assessable",
        features={
            "v2_quality_status": MeasuredFeature(
                "v2_quality_status", "not_assessable", unit="categorical",
                valid=True, reason_invalid="cancelled", confidence_status="abstain",
            )
        },
        masks={},
        representations={},
        centerlines=[],
        experimental_label_en=LABEL_EN,
        experimental_label_ru=LABEL_RU,
        elapsed_s=time.perf_counter() - t0,
        notes=["cancelled"],
    )
