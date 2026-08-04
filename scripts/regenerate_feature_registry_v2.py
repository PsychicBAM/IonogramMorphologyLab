#!/usr/bin/env python3
"""Regenerate FEATURE_REGISTRY_V2.yaml — aggregate IDs only; branches in branch_records."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.synthetic_geometry import GEOMETRY_CASES, generate_geometry_case
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION

OPEN_ENDED = {
    "v2_centerline_count": 16,
    "v2_consolidated_branch_count": 16,
    "v2_preconsolidation_centerline_count": 128,
    "v2_raw_component_count": 128,
    "v2_total_connected_component_count": 512,
    "v2_branch_count": 16,
    "v2_component_count": 128,
}


def _guess_range(fid: str, unit: str):
    if fid in OPEN_ENDED:
        return None
    if "background_burden" in fid or "disagreement" in fid:
        return [0, 1e12]
    if unit in ("fraction", "flag", "score"):
        return [0, 1]
    if unit == "ratio":
        return [0, 1e12]
    if unit == "count":
        return [0, 400]
    if unit in ("bins", "samples"):
        return [0, 400]
    if unit == "categorical":
        return []
    if unit == "amplitude":
        return [0, 1e9]
    if unit == "bins/bin":
        return [-100, 100]
    if unit == "text":
        return []
    return [0, 1e6]


def main() -> int:
    emitted: set[str] = set()
    for name in GEOMETRY_CASES:
        res = run_feature_pipeline_v2(generate_geometry_case(name))
        emitted |= set(res.features)
        # Ensure no per-branch global IDs
        for fid in res.features:
            if fid.startswith("v2_branch_") and fid[10:11].isdigit():
                raise SystemExit(f"Illegal per-branch global feature ID emitted: {fid}")

    features = []
    for fid in sorted(emitted):
        # probe a value from thin ridge when possible
        features.append(
            {
                "feature_id": fid,
                "name_en": fid.replace("v2_", "").replace("_", " "),
                "name_ru": fid.replace("v2_", "").replace("_", " "),
                "scientific_meaning": f"V2 aggregate measurement {fid}",
                "algorithm": "feature_pipeline_v2",
                "formula_registry_ref": None,
                "unit": "dimensionless",
                "expected_range": _guess_range(fid, "fraction" if "fraction" in fid else "count" if "count" in fid else ""),
                "plausibility_warning_above": OPEN_ENDED.get(fid),
                "missing_value_policy": "invalid_not_zero",
                "uncertainty_method": "estimator_or_sample_stats",
                "exclusions": "not a morphology classification",
                "diagnostic_image": None,
                "implementation_version": FEATURE_VERSION,
                "source_basis": "engineering",
                "status": "experimental",
                "input_signal_contract": "kfu_amp_all_v1",
                "emitted_by_fixture": "synthetic_geometry_suite",
                "conditional": False,
            }
        )

    # Fill units from a live sample
    sample = run_feature_pipeline_v2(generate_geometry_case("thin_sloping_ridge"))
    by_id = {f["feature_id"]: f for f in features}
    for fid, mf in sample.features.items():
        if fid in by_id:
            by_id[fid]["unit"] = mf.unit or by_id[fid]["unit"]
            by_id[fid]["expected_range"] = _guess_range(fid, mf.unit or "")

    doc = {
        "version": FEATURE_VERSION,
        "feature_flag": "scientific_feature_pipeline_v2_enabled",
        "default_enabled": False,
        "label_en": "Experimental features — not used by the current classification",
        "label_ru": "Экспериментальные признаки — не участвуют в текущей классификации",
        "input_signal_contract": "kfu_amp_all_v1",
        "unresolved_signals_excluded": ["Phs_all", "Date_Time1", "AmEsP", "A_map_F", "H_map_F"],
        "branch_geometry_storage": "branch_records list in PipelineV2Result / features.json — not v2_branch_N_* global IDs",
        "width_coordinate_systems": {
            "fixed_vertical_axis_width_bins": "vertical cut along fixed row axis (invalid if axis_tangent_to_trace)",
            "fixed_horizontal_axis_width_bins": "horizontal cut along fixed column axis (invalid if axis_tangent_to_trace)",
            "normal_to_ridge_width_bins": "local normal from local tangent",
            "normal_width_baseline_residual_bins": "max(normal_width - thin_baseline, 0)",
            "true_slope_compensated_horizontal_residual_bins": "fixed-H minus projected thin thickness (only when H applicable)",
            "along_ridge_support_length_bins": "supported length along ridge",
        },
        "geometry_heuristics": {
            "ANGLE_NEAR_AXIS_DEG": 30,
            "MULTI_INTERSECTION_MIN_SUPPORT": 3,
            "ALONG_RIDGE_SUPPORT_RATIO": 2.5,
            "note": "Project geometry heuristics — not physical ionogram thresholds",
        },
        "branch_width_storage": "per-branch widths under branch_records[].widths; aggregates from valid branch-local samples only",
        "count_policy": {
            "open_ended_features": list(OPEN_ENDED.keys()),
            "note": "Do not silently clip counts; emit plausibility_warning when above threshold",
        },
        "features": sorted(by_id.values(), key=lambda x: x["feature_id"]),
    }
    out = ROOT / "knowledge_base" / "FEATURE_REGISTRY_V2.yaml"
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8")
    print("Wrote", out, "features=", len(doc["features"]), "emitted_union=", len(emitted))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
