#!/usr/bin/env python3
"""Ensure Feature Pipeline V2 cannot change RuleEngine morphology results."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.synthetic_geometry import thin_sloping_ridge, vertically_broadened_ridge
from ionogram_morphology_lab.rules.engine import RuleEngine
from ionogram_morphology_lab.segmentation.trace_interference import segment_frame


def _morph(frame: np.ndarray) -> str:
    seg = segment_frame(frame)
    feats = extract_features(frame, seg)
    return RuleEngine().evaluate(feats.values, quality_status="valid").candidate_morphology


def main() -> int:
    errors = []
    for name, gen in (("slope", thin_sloping_ridge), ("vbroad", vertically_broadened_ridge)):
        frame = gen()
        before = _morph(frame)
        v2 = run_feature_pipeline_v2(frame)
        after = _morph(frame)
        if before != after:
            errors.append(f"{name}: RuleEngine changed {before} -> {after}")
        if v2.to_serializable().get("affects_classification") is not False:
            errors.append(f"{name}: affects_classification not False")
        ser = v2.to_serializable()
        if "frequency_spread" in ser.get("features", {}) or "range_spread" in ser.get("features", {}):
            errors.append(f"{name}: banned spread keys in serialization")
        # Settings default must be false
        from ionogram_morphology_lab.app.settings_store import DEFAULT_SETTINGS

        if DEFAULT_SETTINGS["analysis"].get("scientific_feature_pipeline_v2_enabled", True):
            errors.append("default scientific_feature_pipeline_v2_enabled is not False")
        # V2 outputs are separate from V1 feature dict
        v1 = extract_features(frame, segment_frame(frame)).to_dict()
        for k in v2.features:
            if k in v1 and k.startswith("v2_"):
                errors.append(f"{name}: v2 key unexpectedly inside v1 extract_features")
        if "raw_centerlines" not in v2.to_serializable():
            errors.append(f"{name}: missing raw_centerlines in V2 serialization")
        if "component_decisions" not in v2.to_serializable():
            errors.append(f"{name}: missing component_decisions in V2 serialization")
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("OK shadow_mode_isolation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
