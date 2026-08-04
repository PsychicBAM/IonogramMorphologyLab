#!/usr/bin/env python3
"""Generate docs/MATLAB_METHOD_OUTPUT_CONTRACT_AUDIT.md from live contracts + runtime evidence.

Fails if summary totals disagree with count_contracts() / registry.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.matlab_studio.method_contracts import (  # noqa: E402
    _load_category_index,
    count_contracts,
    get_method_contract,
)

OUT_MD = ROOT / "docs" / "MATLAB_METHOD_OUTPUT_CONTRACT_AUDIT.md"
OUT_JSON = ROOT / "docs" / "MATLAB_METHOD_OUTPUT_CONTRACT_AUDIT.json"
RUNTIME_JSON = ROOT / "workspaces" / "_phase3c_matlab_runtime" / "runtime_evidence.json"

KINDS = (
    "scalar_value",
    "registered_feature",
    "scientific_candidate",
    "figure",
    "table",
    "matrix",
    "output_file",
    "diagnostic_image",
    "warning_only",
)


def _yes(flag: bool) -> str:
    return "yes" if flag else "no"


def _load_runtime() -> dict:
    if RUNTIME_JSON.is_file():
        return json.loads(RUNTIME_JSON.read_text(encoding="utf-8"))
    return {"methods": {}, "tested_date": "", "source_mat_unchanged": None}


def build_registry() -> list[dict]:
    index = _load_category_index()
    ids = sorted(set(index) | set())
    # Include override-only ids via count_contracts source.
    from ionogram_morphology_lab.matlab_studio import method_contracts as mc

    ids = sorted(set(index) | set(mc._METHOD_OVERRIDES))
    runtime = _load_runtime().get("methods") or {}
    rows = []
    for mid in ids:
        c = get_method_contract(mid)
        kinds = set(c.expected_kinds)
        rt = runtime.get(mid) or {}
        status = rt.get("status", "contract_declared")
        rows.append(
            {
                "method_id": mid,
                "category": c.category,
                "expected_output_type": ", ".join(c.expected_kinds) or "—",
                "values": _yes("scalar_value" in kinds),
                "registered_features": _yes("registered_feature" in kinds),
                "scientific_candidates": _yes("scientific_candidate" in kinds),
                "figures": _yes("figure" in kinds or "diagnostic_image" in kinds),
                "tables": _yes("table" in kinds),
                "matrices": _yes("matrix" in kinds),
                "files": _yes("output_file" in kinds),
                "warning_only": _yes("warning_only" in kinds and len(kinds) == 1),
                "parameter_only": _yes(c.parameter_only),
                "diagnostic_image_expected": c.diagnostic_image_expected,
                "source_references": f"matlab_builtin/manifests/{c.category}.iml-matlab.yaml"
                if c.category
                else "method_contracts.py overrides",
                "limitations": (c.limitations_en or c.summary_en or "teaching / provisional")[:160],
                "smoke_test_status": rt.get("smoke_test_status", "not_yet_tested"),
                "real_matlab_r2019a_status": status
                if status
                in {
                    "contract_declared",
                    "automated_smoke_passed",
                    "real_matlab_passed",
                    "real_matlab_failed",
                    "not_yet_tested",
                }
                else "not_yet_tested",
                "last_tested_date": rt.get("last_tested_date", ""),
                "notes": rt.get("notes", ""),
            }
        )
    return rows


def write_audit(rows: list[dict], totals: dict[str, int], runtime: dict) -> None:
    today = date.today().isoformat()
    diag = sum(1 for r in rows if r["diagnostic_image_expected"])
    values_only = sum(1 for r in rows if r["parameter_only"] == "yes")
    declared = len(rows)
    real_passed = [
        r["method_id"]
        for r in rows
        if r["real_matlab_r2019a_status"] == "real_matlab_passed"
    ]
    fig_confirmed = [
        r["method_id"]
        for r in rows
        if r.get("notes") and "figure_confirmed" in r.get("notes", "")
    ]

    lines = [
        "# MATLAB Method Output Contract Audit (v1.1.1)",
        "",
        "This registry is generated from live method manifests and `method_contracts.py`.",
        "Declared metadata is **not** the same as runtime verification.",
        "",
        "## Summary (must match `count_contracts()`)",
        "",
        f"| Metric | Registry | `count_contracts()` |",
        f"|--------|----------|---------------------|",
        f"| Declared contracts | {declared} | {totals['declared']} |",
        f"| Expected diagnostic figures | {diag} | {totals['diagnostic_figures']} |",
        f"| Values-only / parameter-only | {values_only} | {totals['values_only']} |",
        "",
        f"- Generated: `{today}`",
        f"- Runtime evidence file: `{RUNTIME_JSON.relative_to(ROOT).as_posix() if RUNTIME_JSON.exists() else '(none yet)'}`",
        f"- Source MAT unchanged (last runtime session): `{runtime.get('source_mat_unchanged')}`",
        f"- Real MATLAB R2019a methods with `real_matlab_passed`: **{len(real_passed)}**",
        f"- Figure outputs confirmed at runtime (subset): **{len(fig_confirmed)}** — never equal to all {diag} declared figure methods unless each was executed.",
        "",
        "## Status vocabulary",
        "",
        "| Status | Meaning |",
        "|--------|---------|",
        "| `contract_declared` | Metadata only |",
        "| `automated_smoke_passed` | Non-MATLAB / synthetic automated check |",
        "| `real_matlab_passed` | Executed on external MATLAB R2019a with expected artefacts |",
        "| `real_matlab_failed` | Executed on R2019a; failed or missing expected artefacts |",
        "| `not_yet_tested` | No runtime session recorded |",
        "",
        "## Method registry",
        "",
        "| Method ID | Category | Expected types | Values | Features | Candidates | Figures | Tables | Matrices | Files | Warning-only | Parameter-only | Source | Limitations | Smoke | Real MATLAB R2019a | Last tested |",
        "|-----------|----------|----------------|--------|----------|------------|---------|--------|----------|-------|--------------|----------------|--------|-------------|-------|--------------------|-------------|",
    ]
    for r in rows:
        lines.append(
            "| {method_id} | {category} | {expected_output_type} | {values} | {registered_features} | "
            "{scientific_candidates} | {figures} | {tables} | {matrices} | {files} | {warning_only} | "
            "{parameter_only} | `{source_references}` | {limitations} | {smoke_test_status} | "
            "{real_matlab_r2019a_status} | {last_tested_date} |".format(**r)
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Do **not** mark all diagnostic-figure methods as `real_matlab_passed` from metadata alone.",
            "- Parameter-only methods must state that no separate image is expected (UI Expected Method Output panel).",
            "- A zero process exit code is insufficient for scientific success (see Studio Summary statuses).",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_JSON.write_text(
        json.dumps(
            {
                "summary": {
                    "declared": declared,
                    "diagnostic_figures": diag,
                    "values_only": values_only,
                    "count_contracts": totals,
                    "real_matlab_passed": real_passed,
                    "figure_outputs_confirmed": fig_confirmed,
                },
                "methods": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _values_only_count() -> int:
    """Mirror count_contracts() values_only definition exactly."""
    return count_contracts()["values_only"]


def validate_totals(rows: list[dict], totals: dict[str, int]) -> None:
    diag = sum(1 for r in rows if r["diagnostic_image_expected"])
    # Prefer the same aggregation as count_contracts for the summary row.
    values_only = _values_only_count()
    param_only = sum(1 for r in rows if r["parameter_only"] == "yes")
    declared = len(rows)
    errors = []
    if declared != totals["declared"]:
        errors.append(f"declared {declared} != count_contracts {totals['declared']}")
    if diag != totals["diagnostic_figures"]:
        errors.append(f"diagnostic_figures {diag} != {totals['diagnostic_figures']}")
    if values_only != totals["values_only"]:
        errors.append(f"values_only {values_only} != {totals['values_only']}")
    if param_only != totals["values_only"]:
        # Documented "5 values-only" equals parameter_only methods in v1.1.1.
        errors.append(
            f"parameter_only registry count {param_only} != values_only {totals['values_only']}"
        )
    if errors:
        raise SystemExit("Contract audit validation failed:\n- " + "\n- ".join(errors))


def main() -> int:
    totals = count_contracts()
    rows = build_registry()
    runtime = _load_runtime()
    validate_totals(rows, totals)
    write_audit(rows, totals, runtime)
    print(f"wrote {OUT_MD.relative_to(ROOT)} ({len(rows)} methods)")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print("totals", totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
