#!/usr/bin/env python3
"""Validate Feature Diagnostics helpers and exported diagnostic packages."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

REQUIRED_FILES = [
    "identity.json",
    "raw.npy",
    "raw.png",
    "diagnostic_normalized.png",
    "candidate_trace_mask.npy",
    "candidate_before_exclusion_mask.npy",
    "candidate_before_exclusion_mask.png",
    "accepted_trace_mask.npy",
    "accepted_trace_mask.png",
    "accepted_nonfloor_trace_mask.npy",
    "accepted_nonfloor_trace_mask.png",
    "interference_mask.npy",
    "interference_mask.png",
    "floor_clutter_mask.npy",
    "floor_clutter_mask.png",
    "impulse_mask.npy",
    "impulse_mask.png",
    "background_mask.png",
    "uncertain_mask.png",
    "excluded_mask.png",
    "centerlines_before_consolidation.png",
    "centerlines_after_consolidation.png",
    "branch_labels.png",
    "vertical_width_map.npy",
    "vertical_width_map.png",
    "horizontal_width_map.npy",
    "horizontal_width_map.png",
    "normal_to_ridge_width_map.png",
    "temporal_overlay.png",
    "features.json",
    "component_decisions.json",
    "branch_width_summary.json",
]


def main() -> int:
    errors: list[str] = []
    from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage, _compose

    assert FEATURE_VERSION.startswith("iml2-")
    assert FeatureDiagnosticsPage is not None
    base = np.zeros((10, 20), dtype=float)
    rgb = _compose(base, [], 0.5)
    if rgb.shape != (10, 20, 3):
        errors.append(f"compose shape {rgb.shape}")

    diag_root = ROOT / "docs" / "_phase4b3_iml2-0.2.0_diagnostics"
    if not diag_root.is_dir():
        diag_root = ROOT / "docs" / "_phase4b1_diagnostics"
    if diag_root.is_dir():
        frame_dirs = sorted(diag_root.glob("*/frame_*"))
        if not frame_dirs:
            errors.append("diagnostics root exists but no frame_* packages")
        for d in frame_dirs:
            raw_p = d / "raw.npy"
            if not raw_p.is_file():
                errors.append(f"{d}: missing raw.npy")
                continue
            raw = np.load(raw_p)
            required = list(REQUIRED_FILES)
            # 4B.1 packages may lack branch_width_summary
            if "iml2-0.2.0" not in str(diag_root):
                required = [x for x in required if x != "branch_width_summary.json"]
            for name in required:
                if not (d / name).is_file():
                    errors.append(f"{d.name}: missing {name}")
            for mask_name in (
                "candidate_trace_mask.npy",
                "accepted_trace_mask.npy",
                "interference_mask.npy",
            ):
                m = np.load(d / mask_name)
                if m.shape != raw.shape:
                    errors.append(f"{d.name}: {mask_name} shape {m.shape} != raw {raw.shape}")
            ident = json.loads((d / "identity.json").read_text(encoding="utf-8"))
            for k in (
                "source_path",
                "source_sha256",
                "frame",
                "mapped_time",
                "profile",
                "signal_contract",
                "feature_version",
                "raw_frame_sha256",
                "axes_status",
            ):
                if k not in ident:
                    errors.append(f"{d.name}: identity missing {k}")
            if ident.get("feature_version") != FEATURE_VERSION and "iml2-0.2.0" in str(diag_root):
                errors.append(
                    f"{d.name}: identity feature_version {ident.get('feature_version')} != {FEATURE_VERSION}"
                )
            dec = json.loads((d / "component_decisions.json").read_text(encoding="utf-8"))
            if "decisions" not in dec:
                errors.append(f"{d.name}: component_decisions missing decisions")
        review = diag_root / "owner_geometry_review_table.json"
        if review.is_file():
            rev = json.loads(review.read_text(encoding="utf-8"))
            if rev.get("completed", 0) and all(
                (r.get("trace_mask_acceptable") or r.get("trace_extraction_acceptable") or "") == ""
                for r in rev.get("rows", [])
            ):
                errors.append("review table claims completed but fields empty")
            if rev.get("pending", 0) > 0:
                for r in rev.get("rows", []):
                    if r.get("status") == "owner-reviewed":
                        errors.append("row marked owner-reviewed while pending fields empty")
    else:
        print("NOTE: diagnostics not exported yet; helpers-only check")

    if errors:
        print("FAIL feature_diagnostics")
        for e in errors:
            print(" -", e)
        return 1
    print("OK feature_diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
