#!/usr/bin/env python3
"""Audit all matlab_builtin .m methods for v1.1 release hardening."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILTIN = ROOT / "matlab_builtin"
OUT_MD = ROOT / "docs" / "IML_V1_1_MATLAB_METHOD_IMPLEMENTATION_AUDIT.md"
OUT_JSON = ROOT / "docs" / "IML_V1_1_MATLAB_METHOD_IMPLEMENTATION_AUDIT.json"


def classify(path: Path, text: str) -> str:
    rel = path.relative_to(BUILTIN).as_posix()
    name = path.stem
    if "/examples/" in f"/{rel}" or name.startswith("iml_example_"):
        return "teaching_example"
    if "/tests/" in f"/{rel}" or name.startswith("iml_test_"):
        return "teaching_example"
    if "TODO" in text or "FIXME" in text or "placeholder" in text.lower():
        if "iml_register" not in text and "prctile" not in text and "sum(" not in text:
            return "placeholder"
    if "subtype" in name and ("disabled" in text.lower() or "abstain" in text.lower()):
        return "disabled"
    # wrappers that mostly call helpers / load without heavy analysis
    wrapper_names = {
        "iml_load_frame",
        "iml_load_sequence",
        "iml_export_result",
        "iml_write_candidate_summary",
        "iml_build_candidate_report",
    }
    if name in wrapper_names:
        return "executable_wrapper"
    # real computation heuristics
    compute_signals = (
        "prctile",
        "conv2",
        "mean(",
        "sum(",
        "std(",
        "mask",
        "imagesc",
        "bwlabel",
        "find(",
        "diff(",
        "corrcoef",
        "gradient",
    )
    has_compute = any(s in text for s in compute_signals)
    has_register = "iml_register_" in text or "iml_save_" in text
    if has_compute and has_register:
        return "fully_implemented"
    if has_compute or has_register:
        return "executable_wrapper"
    if len(text.strip()) < 80:
        return "placeholder"
    if "manifest" in text.lower() and "function" not in text:
        return "metadata_only"
    return "executable_wrapper"


def supported_inputs(text: str) -> str:
    ins = []
    if "iml_get_current_frame" in text or "local_frame" in text:
        ins.append("current_frame")
    if "iml_get_selected_frames" in text or "iml_get_sequence" in text:
        ins.append("sequence")
    if "iml_get_frequency_axis" in text:
        ins.append("frequency_axis")
    if "iml_get_range_axis" in text:
        ins.append("range_axis")
    if "varargin" in text:
        ins.append("optional_matrix")
    return ", ".join(ins) or "bridge_workspace"


def outputs(text: str) -> str:
    outs = []
    if "iml_register_feature" in text:
        outs.append("features")
    if "iml_register_candidate_result" in text:
        outs.append("candidate")
    if "iml_save_matrix" in text:
        outs.append("matrix")
    if "iml_save_plot" in text or "imagesc" in text or "print(" in text:
        outs.append("figure")
    if "iml_save_table" in text:
        outs.append("table")
    if "iml_add_provenance" in text:
        outs.append("provenance")
    if "struct(" in text or "result =" in text:
        outs.append("result_struct")
    return ", ".join(outs) or "side_effects_or_return"


def source_status(name: str, classification: str) -> str:
    if classification == "disabled":
        return "disabled_pending_registry"
    if "spread" in name or "interference" in name or "ox" in name:
        return "development_heuristic_with_project_terminology"
    if name.startswith("iml_detect_") or name.startswith("iml_estimate_"):
        return "development_heuristic"
    if classification == "teaching_example":
        return "teaching_only"
    return "engineering_utility"


def main() -> int:
    rows = []
    for path in sorted(BUILTIN.rglob("*.m")):
        text = path.read_text(encoding="utf-8", errors="replace")
        cls = classify(path, text)
        cat = path.parent.name
        man = BUILTIN / "manifests" / f"{cat}.iml-matlab.yaml"
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "entry_point": path.name,
                "manifest": man.relative_to(ROOT).as_posix() if man.exists() else "MISSING",
                "classification": cls,
                "real_computation_status": cls,
                "supported_inputs": supported_inputs(text),
                "outputs": outputs(text),
                "backend_test": "pending_smoke" if cls in {"fully_implemented", "executable_wrapper", "disabled"} else "n/a",
                "source_status": source_status(path.stem, cls),
                "limitations": "Candidate/heuristic only; profile-dependent; not causal; not a validated measurement.",
            }
        )

    counts = {}
    for r in rows:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    completed_scientific = counts.get("fully_implemented", 0)
    placeholders = counts.get("placeholder", 0)

    lines = [
        "# IML v1.1 MATLAB Method Implementation Audit",
        "",
        f"**Application version:** 1.1.0",
        f"**Total `.m` files:** {len(rows)}",
        "",
        "## Classification summary",
        "",
        "| Class | Count | Counts as completed scientific method? |",
        "|---|---:|---|",
        f"| fully_implemented | {counts.get('fully_implemented', 0)} | Yes (development heuristic) |",
        f"| executable_wrapper | {counts.get('executable_wrapper', 0)} | Utility only — not a morphology detector |",
        f"| teaching_example | {counts.get('teaching_example', 0)} | No |",
        f"| metadata_only | {counts.get('metadata_only', 0)} | No |",
        f"| placeholder | {counts.get('placeholder', 0)} | **No — rejected** |",
        f"| disabled | {counts.get('disabled', 0)} | No (intentionally inactive) |",
        "",
        f"**Completed scientific methods (fully_implemented only):** {completed_scientific}",
        f"**Placeholders:** {placeholders}",
        "",
        "Synthetic or heuristic execution is **not** scientific validation.",
        "",
        "## Per-method inventory",
        "",
        "| Path | Entry | Manifest | Class | Inputs | Outputs | Backend test | Source status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['path']}` | `{r['entry_point']}` | `{r['manifest']}` | {r['classification']} | "
            f"{r['supported_inputs']} | {r['outputs']} | {r['backend_test']} | {r['source_status']} |"
        )
    lines.extend(
        [
            "",
            "## Limitations (global)",
            "",
            "- Methods are candidate morphology / layer heuristics unless externally reviewed.",
            "- Height bands are provisional fractions of the nominal virtual-height axis.",
            "- Es subtype classifier remains disabled without registry activation.",
            "- Confirmed O/X mode identification from Amp_all alone is not claimed.",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"counts": counts, "methods": rows}, indent=2), encoding="utf-8")
    print(json.dumps(counts, indent=2))
    print("wrote", OUT_MD)
    if placeholders:
        print("FAIL: placeholders present")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
