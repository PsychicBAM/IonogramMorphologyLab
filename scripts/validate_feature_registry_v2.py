#!/usr/bin/env python3
"""Registry completeness: emitted IDs from synthetic + real packages ⊆ registered."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.registry import list_feature_ids, load_feature_registry_v2, validate_registry_completeness
from ionogram_morphology_lab.features.v2.synthetic_geometry import GEOMETRY_CASES, generate_geometry_case


def _collect_emitted() -> set[str]:
    emitted: set[str] = set()
    for name in GEOMETRY_CASES:
        res = run_feature_pipeline_v2(generate_geometry_case(name))
        emitted |= set(res.features.keys())
        for fid in res.features:
            if fid.startswith("v2_branch_") and len(fid) > 10 and fid[10].isdigit():
                raise SystemExit(f"Illegal per-branch feature ID: {fid}")
    for diag_name in ("_phase4b3_iml2-0.2.0_diagnostics", "_phase4b1_diagnostics"):
        diag = ROOT / "docs" / diag_name
        if not diag.is_dir():
            continue
        for fj in diag.glob("*/frame_*/features.json"):
            data = json.loads(fj.read_text(encoding="utf-8"))
            emitted |= set((data.get("features") or {}).keys())
    for perf_name in ("_phase4b3_iml2-0.2.0_fullfile_perf", "_phase4b1_fullfile_perf"):
        perf = ROOT / "docs" / perf_name / "per_frame"
        if not perf.is_dir():
            continue
        for fj in list(perf.glob("frame_*.json"))[:50]:
            data = json.loads(fj.read_text(encoding="utf-8"))
            if isinstance(data.get("features"), dict):
                emitted |= set(data["features"].keys())
    return emitted


def main() -> int:
    errors = validate_registry_completeness()
    reg_ids = set(list_feature_ids())
    emitted = _collect_emitted()
    missing = sorted(emitted - reg_ids)
    if missing:
        errors.append(f"emitted - registered = {missing}")
    banned = {"frequency_spread", "range_spread", "mixed_spread", "v2_frequency_spread", "v2_range_spread", "v2_mixed_spread"}
    if banned & emitted:
        errors.append(f"banned classification keys: {banned & emitted}")
    cl = None
    for f in (load_feature_registry_v2().get("features") or []):
        if f.get("feature_id") == "v2_centerline_count":
            cl = f
            break
    if cl and cl.get("expected_range") == [0, 64]:
        errors.append("v2_centerline_count still closed [0,64]")

    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print(f"OK registry={len(reg_ids)} emitted={len(emitted)} missing=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
