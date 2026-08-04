#!/usr/bin/env python3
"""Python↔MATLAB parity for Phase 4A/4A.1b — valid and invalid cases.

Current evidence: workspaces/_phase4a_parity/parity_report.json (+ matlab logs).
Markdown alone is not current evidence.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.scientific_outputs.formulas.axes import (  # noqa: E402
    bin_to_mhz,
    bin_to_nominal_height_km,
)
from ionogram_morphology_lab.scientific_outputs.formulas.trace_metrics import local_width_bins  # noqa: E402
from ionogram_morphology_lab.scientific_outputs.formulas.virtual_height import (  # noqa: E402
    virtual_height_from_group_delay,
)

TOL = 1e-9
OUT_DIR = ROOT / "workspaces" / "_phase4a_parity"


def _find_matlab() -> str | None:
    for cand in (
        shutil.which("matlab"),
        r"D:\MATLAB\R2019a\bin\matlab.exe",
        r"C:\Program Files\MATLAB\R2019a\bin\matlab.exe",
    ):
        if cand and Path(cand).is_file():
            return cand
    return None


def _run_matlab_batch(script_body: str, matlab: str) -> tuple[int, str, str, Path]:
    helpers = ROOT / "matlab_helpers"
    td = tempfile.mkdtemp(prefix="iml_parity_")
    td_path = Path(td)
    for p in helpers.glob("iml_formula_*.m"):
        shutil.copy2(p, td_path / p.name)
    script = td_path / "run_parity_batch.m"
    script.write_text(
        f"addpath('{helpers.as_posix()}');\naddpath('{td_path.as_posix()}');\n" + script_body,
        encoding="utf-8",
    )
    cmd = [matlab, "-batch", f"cd('{td_path.as_posix()}'); run_parity_batch"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return proc.returncode, proc.stdout or "", proc.stderr or "", td_path


def _py_record(name: str, kind: str, expected: str, fn) -> dict:
    try:
        q = fn()
        return {
            "name": name,
            "kind": kind,
            "expected_behavior": expected,
            "python_exception": None,
            "python_valid": bool(getattr(q, "valid", True)),
            "python_value": getattr(q, "value", None),
            "python_reason": getattr(q, "reason_invalid", "") or None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "name": name,
            "kind": kind,
            "expected_behavior": expected,
            "python_exception": f"{type(exc).__name__}: {exc}",
            "python_valid": False,
            "python_value": None,
            "python_reason": "exception",
        }


def main() -> int:
    errors: list[str] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()

    valid = [
        ("vh_normal", "valid finite result", lambda: virtual_height_from_group_delay(0.001), "iml_formula_virtual_height_from_group_delay(0.001)"),
        ("vh_zero", "valid zero delay", lambda: virtual_height_from_group_delay(0.0), "iml_formula_virtual_height_from_group_delay(0)"),
        ("mhz_first_bin", "valid first bin", lambda: bin_to_mhz(0, start_mhz=1.5, step_mhz=0.019, frequency_bins=400), "iml_formula_bin_to_mhz(0,1.5,0.019,400)"),
        ("mhz_final_bin", "valid final bin", lambda: bin_to_mhz(399, start_mhz=1.5, step_mhz=0.019, frequency_bins=400), "iml_formula_bin_to_mhz(399,1.5,0.019,400)"),
        ("h_nom_first", "valid first height bin", lambda: bin_to_nominal_height_km(0, km_per_bin=2.5, height_bins=256), "iml_formula_bin_to_nominal_height_km(0,2.5,256)"),
        ("h_nom_final", "valid final height bin", lambda: bin_to_nominal_height_km(255, km_per_bin=2.5, height_bins=256), "iml_formula_bin_to_nominal_height_km(255,2.5,256)"),
        ("width_normal", "valid width", lambda: local_width_bins(np.array([0, 1, 1, 1, 0, 1])), "iml_formula_local_width_bins([0 1 1 1 0 1])"),
        ("width_zero_mask", "valid measured zero", lambda: local_width_bins(np.array([0, 0, 0])), "iml_formula_local_width_bins([0 0 0])"),
    ]

    invalid = [
        ("vh_nan", "reject NaN", lambda: virtual_height_from_group_delay(float("nan")), "iml_formula_virtual_height_from_group_delay(NaN)"),
        ("vh_inf", "reject Inf", lambda: virtual_height_from_group_delay(float("inf")), "iml_formula_virtual_height_from_group_delay(Inf)"),
        ("vh_negative", "reject negative", lambda: virtual_height_from_group_delay(-0.1), "iml_formula_virtual_height_from_group_delay(-0.1)"),
        ("mhz_negative_index", "reject negative bin", lambda: bin_to_mhz(-1, start_mhz=1.5, step_mhz=0.019, frequency_bins=400), "iml_formula_bin_to_mhz(-1,1.5,0.019,400)"),
        ("mhz_above_max", "reject bin >= bins", lambda: bin_to_mhz(400, start_mhz=1.5, step_mhz=0.019, frequency_bins=400), "iml_formula_bin_to_mhz(400,1.5,0.019,400)"),
        ("mhz_zero_axis_length", "reject zero axis length", lambda: bin_to_mhz(0, start_mhz=1.5, step_mhz=0.019, frequency_bins=0), "iml_formula_bin_to_mhz(0,1.5,0.019,0)"),
        ("mhz_fractional_bin", "reject fractional bin (no truncate)", lambda: bin_to_mhz(3.8, start_mhz=1.5, step_mhz=0.019, frequency_bins=400), "iml_formula_bin_to_mhz(3.8,1.5,0.019,400)"),
        ("mhz_boolean_bin", "reject boolean bin index", lambda: bin_to_mhz(True, start_mhz=1.5, step_mhz=0.019, frequency_bins=400), "iml_formula_bin_to_mhz(true,1.5,0.019,400)"),
        ("mhz_malformed_step", "reject non-finite step", lambda: bin_to_mhz(0, start_mhz=1.5, step_mhz=float("nan"), frequency_bins=400), "iml_formula_bin_to_mhz(0,1.5,NaN,400)"),
        ("h_nom_above_max", "reject bin >= height_bins", lambda: bin_to_nominal_height_km(256, km_per_bin=2.5, height_bins=256), "iml_formula_bin_to_nominal_height_km(256,2.5,256)"),
        ("h_nom_fractional_bin", "reject fractional height bin", lambda: bin_to_nominal_height_km(2.5, km_per_bin=2.5, height_bins=256), "iml_formula_bin_to_nominal_height_km(2.5,2.5,256)"),
        ("h_nom_boolean_bin", "reject boolean height bin", lambda: bin_to_nominal_height_km(False, km_per_bin=2.5, height_bins=256), "iml_formula_bin_to_nominal_height_km(false,2.5,256)"),
        ("h_nom_zero_axis", "reject zero height axis", lambda: bin_to_nominal_height_km(0, km_per_bin=2.5, height_bins=0), "iml_formula_bin_to_nominal_height_km(0,2.5,0)"),
        ("width_empty", "reject empty", lambda: local_width_bins(np.array([])), "iml_formula_local_width_bins([])"),
        ("width_2d", "reject 2-D input (no silent ravel)", lambda: local_width_bins(np.ones((3, 4))), "iml_formula_local_width_bins(ones(3,4))"),
        ("width_wrong_dim_3d", "reject 3-D input", lambda: local_width_bins(np.ones((2, 2, 2))), "iml_formula_local_width_bins(ones(2,2,2))"),
        ("vh_nonnumeric", "reject / raise on nonnumeric", lambda: virtual_height_from_group_delay("not-a-number"), None),  # Python-only
    ]

    records = []
    for name, expected, fn, m_expr in valid:
        rec = _py_record(name, "valid", expected, fn)
        rec["matlab_expr"] = m_expr
        if not rec["python_valid"] or rec["python_value"] is None:
            errors.append(f"{name}: python valid case failed")
            rec["pass"] = False
        else:
            rec["pass"] = None  # pending matlab
        records.append(rec)

    for name, expected, fn, m_expr in invalid:
        rec = _py_record(name, "invalid", expected, fn)
        rec["matlab_expr"] = m_expr
        # Invalid: must be invalid or raise
        ok_py = (not rec["python_valid"]) or (rec["python_exception"] is not None)
        if not ok_py:
            errors.append(f"{name}: Python must reject")
        rec["python_pass"] = ok_py
        records.append(rec)

    matlab = _find_matlab()
    matlab_stdout = ""
    matlab_stderr = ""
    matlab_rc = None
    matlab_map: dict[str, float] = {}

    if matlab:
        lines = ["fid = fopen('matlab_results.txt','w');"]
        for rec in records:
            m_expr = rec.get("matlab_expr")
            if not m_expr:
                continue
            lines.append(f"try, v = {m_expr}; catch, v = NaN; end")
            lines.append(f"fprintf(fid, '%s\\t%.17g\\n', '{rec['name']}', v);")
        lines.append("fclose(fid);")
        try:
            matlab_rc, matlab_stdout, matlab_stderr, td_path = _run_matlab_batch("\n".join(lines) + "\n", matlab)
            results_path = td_path / "matlab_results.txt"
            if results_path.is_file():
                for line in results_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if not line.strip():
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        try:
                            matlab_map[parts[0]] = float(parts[1])
                        except ValueError:
                            matlab_map[parts[0]] = float("nan")
            else:
                errors.append("matlab_results.txt missing")
        except Exception as exc:  # noqa: BLE001
            matlab_rc = -1
            matlab_stderr = str(exc)
            errors.append(f"matlab_batch_failed:{exc}")

    for rec in records:
        name = rec["name"]
        mv = matlab_map.get(name) if rec.get("matlab_expr") else None
        rec["matlab_value"] = mv
        rec["matlab_is_nan"] = (mv is not None and not np.isfinite(mv)) if mv is not None else None
        rec["matlab_exception"] = None if rec.get("matlab_expr") else "python_only_case"
        if rec["kind"] == "valid":
            if not matlab:
                rec["status"] = "python_only"
                rec["pass"] = bool(rec["python_valid"])
            elif mv is None or not np.isfinite(mv):
                rec["status"] = "matlab_failed"
                rec["pass"] = False
                errors.append(f"{name}: matlab failed on valid")
            else:
                diff = abs(float(rec["python_value"]) - float(mv))
                rec["diff"] = diff
                rec["status"] = "match" if diff <= TOL else "mismatch"
                rec["pass"] = diff <= TOL
                if diff > TOL:
                    errors.append(f"{name}: mismatch {diff}")
        else:
            # invalid
            if not rec.get("matlab_expr"):
                rec["status"] = "python_only_invalid"
                rec["pass"] = bool(rec.get("python_pass"))
                continue
            if not matlab:
                rec["status"] = "python_invalid_matlab_unavailable"
                rec["pass"] = bool(rec.get("python_pass"))
                continue
            matlab_rejects = mv is None or not np.isfinite(float(mv))
            rec["matlab_pass"] = matlab_rejects
            rec["pass"] = bool(rec.get("python_pass")) and matlab_rejects
            rec["status"] = "both_reject" if rec["pass"] else "fail"
            if not matlab_rejects:
                errors.append(f"{name}: MATLAB accepted invalid with {mv}")

    (OUT_DIR / "matlab_stdout.txt").write_text(matlab_stdout, encoding="utf-8")
    (OUT_DIR / "matlab_stderr.txt").write_text(matlab_stderr, encoding="utf-8")
    total_cases = len(records)
    cross_runtime = [r for r in records if r.get("matlab_expr")]
    python_only = [r for r in records if not r.get("matlab_expr")]
    matlab_only: list = []  # none defined in this suite
    valid_cross_matches = sum(
        1 for r in cross_runtime if r.get("kind") == "valid" and r.get("status") == "match" and r.get("pass")
    )
    invalid_cross_rejections = sum(
        1 for r in cross_runtime if r.get("kind") == "invalid" and r.get("status") == "both_reject" and r.get("pass")
    )
    counts = {
        "total_cases": total_cases,
        "cross_runtime_cases": len(cross_runtime),
        "python_only_cases": len(python_only),
        "matlab_only_cases": len(matlab_only),
        "valid_cross_runtime_matches": valid_cross_matches,
        "invalid_cross_runtime_rejections": invalid_cross_rejections,
        "n_valid": sum(1 for r in records if r["kind"] == "valid"),
        "n_invalid": sum(1 for r in records if r["kind"] == "invalid"),
    }
    # Human summary must match calculated counts
    summary_line = (
        f"total_cases={counts['total_cases']}; "
        f"cross_runtime_cases={counts['cross_runtime_cases']}; "
        f"python_only_cases={counts['python_only_cases']}; "
        f"matlab_only_cases={counts['matlab_only_cases']}; "
        f"valid_cross_runtime_matches={counts['valid_cross_runtime_matches']}; "
        f"invalid_cross_runtime_rejections={counts['invalid_cross_runtime_rejections']}"
    )
    report = {
        "generated_at_utc": generated_at,
        "phase": "4A.1b",
        "tolerance": TOL,
        "matlab_executable": matlab,
        "matlab_returncode": matlab_rc,
        "parity": records,
        "counts": counts,
        "human_summary": summary_line,
        "errors": errors,
        "markdown_is_not_current_evidence": True,
        "current_evidence_paths": [
            "workspaces/_phase4a_parity/parity_report.json",
            "workspaces/_phase4a_parity/matlab_stdout.txt",
            "workspaces/_phase4a_parity/matlab_stderr.txt",
        ],
    }
    (OUT_DIR / "parity_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    md = ROOT / "docs" / "PYTHON_MATLAB_FORMULA_PARITY.md"
    lines = [
        "# Python / MATLAB Formula Parity (Phase 4A.1b)",
        "",
        f"Generated: `{generated_at}`",
        "",
        "**Current evidence:** `workspaces/_phase4a_parity/parity_report.json` "
        "(plus matlab stdout/stderr). This Markdown is a human mirror only.",
        "",
        f"**Counts:** {summary_line}",
        "",
        "Do not describe all total_cases as Python↔MATLAB comparisons when python_only_cases > 0.",
        "",
        f"| Case | Kind | Runtime | Python | MATLAB | Pass |",
        "|------|------|---------|--------|--------|------|",
    ]
    for e in records:
        runtime = "cross_runtime" if e.get("matlab_expr") else "python_only"
        lines.append(
            f"| {e['name']} | {e['kind']} | {runtime} | valid={e.get('python_valid')} / "
            f"{e.get('python_value') or e.get('python_reason') or e.get('python_exception')} | "
            f"{e.get('matlab_value')} | {e.get('pass')} |"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Validator: human summary must match calculated counts
    for key, val in counts.items():
        if f"{key}={val}" not in summary_line and key.startswith(("total_", "cross_", "python_", "matlab_", "valid_", "invalid_")):
            if f"{key}=" not in summary_line:
                errors.append(f"human_summary missing {key}")
            elif f"{key}={val}" not in summary_line:
                errors.append(f"human_summary mismatch for {key}")

    if errors:
        print("validate_formula_parity FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print(
        "validate_formula_parity OK",
        f"total={counts['total_cases']} cross={counts['cross_runtime_cases']} "
        f"python_only={counts['python_only_cases']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
