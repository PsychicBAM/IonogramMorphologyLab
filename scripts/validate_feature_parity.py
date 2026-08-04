#!/usr/bin/env python3
"""Truthful Python/MATLAB V2 parity.

Cross-runtime means both Python and MATLAB executed and results compared.
`python_checked` is NOT cross-runtime.
"""
from __future__ import annotations

import argparse
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
OUT = ROOT / "workspaces" / "_phase4b_parity"

from ionogram_morphology_lab.features.v2.parity import (
    branch_separation,
    interference_stripe_burden,
    local_horizontal_width,
    local_vertical_width,
)


def _resolve_matlab(explicit: str = "") -> str | None:
    cands = [
        explicit,
        r"D:\MATLAB\R2019a\bin\matlab.exe",
        r"C:\Program Files\MATLAB\R2019a\bin\matlab.exe",
        shutil.which("matlab") or "",
        shutil.which("matlab.exe") or "",
    ]
    for settings in ROOT.glob("workspaces/**/settings.json"):
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
            exe = (data.get("matlab") or {}).get("matlab_executable") or ""
            if exe:
                cands.insert(0, exe)
        except Exception:
            pass
    for c in cands:
        if c and Path(c).is_file():
            return str(Path(c))
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matlab", choices=("optional", "required"), default="optional")
    ap.add_argument("--matlab-exe", default="")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    profile = np.array([0, 0, 1, 5, 10, 5, 1, 0, 0], dtype=float)
    mask = np.zeros((20, 30), dtype=bool)
    mask[:, 5:7] = True
    mask[:, 20] = True

    python_cases = {
        "vh_valid": local_vertical_width(profile),
        "hh_valid": local_horizontal_width(profile),
        "branch_valid": branch_separation(np.array([10.0, 11, 12]), np.array([20.0, 21, 22])),
        "interf_valid": interference_stripe_burden(mask),
        "vh_empty": local_vertical_width(np.array([])),
        "vh_zero": local_vertical_width(np.zeros(9)),
        "vh_nan": local_vertical_width(np.array([np.nan] * 9)),
        "vh_inf": local_vertical_width(np.array([np.inf] * 9)),
        "hh_empty": local_horizontal_width(np.array([])),
        "hh_nan": local_horizontal_width(np.array([np.nan] * 9)),
        "branch_empty": branch_separation(np.array([]), np.array([])),
        "branch_mismatch": branch_separation(np.array([1.0, 2]), np.array([1.0])),
        "interf_empty": interference_stripe_burden(np.zeros((0, 0), dtype=bool)),
        "interf_none": interference_stripe_burden(np.zeros((10, 10), dtype=bool)),
    }
    try:
        local_vertical_width(np.array(["x", "y"], dtype=object))  # type: ignore[arg-type]
        python_only = {"vh_nonnumeric": {"valid": True, "value": None, "reason_invalid": "unexpected"}}
    except Exception as exc:  # noqa: BLE001
        python_only = {
            "vh_nonnumeric": {
                "valid": False,
                "value": None,
                "reason_invalid": "nonnumeric",
                "exception": type(exc).__name__,
            }
        }

    matlab = _resolve_matlab(args.matlab_exe)
    matlab_map: dict = {}
    matlab_rc = None
    matlab_stdout = ""
    matlab_stderr = ""
    matlab_version = ""
    cases: list[dict] = []

    if not matlab:
        if args.matlab == "required":
            report = {"status": "fail", "reason": "matlab_required_but_unavailable", "cases": []}
            (OUT / "parity_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print("FAIL MATLAB required but unavailable")
            return 1
        for name, py in {**python_cases, **python_only}.items():
            cases.append(
                {
                    "name": name,
                    "runtime": "python_only",
                    "status": "skip" if name in python_cases else "python_only",
                    "pass": True,
                    "python": py,
                    "matlab": None,
                    "reason": "matlab_unavailable" if name in python_cases else "python_only_case",
                }
            )
        status = "skip"
    else:
        helpers = ROOT / "matlab_helpers"
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            out_json = td_path / "out.json"
            script = td_path / "run_parity.m"
            script.write_text(
                f"""
addpath('{helpers.as_posix()}');
try, vinfo = version; catch, vinfo = 'unknown'; end
p = [0 0 1 5 10 5 1 0 0];
v = iml_v2_local_vertical_width(p);
h = iml_v2_local_horizontal_width(p);
b = iml_v2_branch_separation([10 11 12],[20 21 22],[1 2 3]);
m = false(20,30); m(:,6:7)=true; m(:,21)=true;
i = iml_v2_interference_stripe_burden(m);
S = struct();
S.matlab_version = char(vinfo);
S.vh_valid_value = v.value; S.vh_valid_valid = v.valid;
S.hh_valid_value = h.value; S.hh_valid_valid = h.valid;
S.branch_valid_value = b.value; S.branch_valid_valid = b.valid;
S.interf_stripe_count = i.stripe_count;
S.interf_stripe_widths_median = i.stripe_widths_median;
S.interf_affected_frequency_fraction = i.affected_frequency_fraction;
S.interf_persistence = i.persistence;
S.interf_density = i.density;
% invalid probes
ve = iml_v2_local_vertical_width([]);
S.vh_empty_valid = ve.valid;
vz = iml_v2_local_vertical_width(zeros(1,9));
S.vh_zero_valid = vz.valid; S.vh_zero_value = vz.value;
vn = iml_v2_local_vertical_width(nan(1,9));
S.vh_nan_valid = vn.valid;
vi = iml_v2_local_vertical_width(inf(1,9));
S.vh_inf_valid = vi.valid;
he = iml_v2_local_horizontal_width([]);
S.hh_empty_valid = he.valid;
hn = iml_v2_local_horizontal_width(nan(1,9));
S.hh_nan_valid = hn.valid;
be = iml_v2_branch_separation([],[],[]);
S.branch_empty_valid = be.valid;
bm = iml_v2_branch_separation([1 2],[1],[1]);
S.branch_mismatch_valid = bm.valid;
ie = iml_v2_interference_stripe_burden([]);
S.interf_empty_stripe_count = ie.stripe_count;
inone = iml_v2_interference_stripe_burden(false(10,10));
S.interf_none_stripe_count = inone.stripe_count;
fid = fopen('{out_json.as_posix()}','w');
fprintf(fid,'%s',jsonencode(S));
fclose(fid);
""",
                encoding="utf-8",
            )
            try:
                proc = subprocess.run(
                    [matlab, "-batch", f"run('{script.as_posix()}')"],
                    capture_output=True, text=True, cwd=str(td_path), timeout=180, check=False,
                )
                matlab_rc = proc.returncode
                matlab_stdout = proc.stdout or ""
                matlab_stderr = proc.stderr or ""
                if proc.returncode != 0 or not out_json.is_file():
                    status = "fail"
                    for name, py in python_cases.items():
                        cases.append(
                            {
                                "name": name,
                                "runtime": "cross_runtime",
                                "status": "fail",
                                "pass": False,
                                "python": py,
                                "matlab": None,
                                "reason": "matlab_exception_or_missing_json",
                            }
                        )
                else:
                    matlab_map = json.loads(out_json.read_text(encoding="utf-8"))
                    matlab_version = str(matlab_map.get("matlab_version", ""))
                    status = "ok"

                    def add_valid(name: str, py, mv, mvalid, tol=1e-6):
                        ok = bool(py.get("valid")) and bool(mvalid) and mv is not None and abs(float(mv) - float(py["value"])) <= tol
                        cases.append(
                            {
                                "name": name,
                                "runtime": "cross_runtime",
                                "status": "match" if ok else "fail",
                                "pass": ok,
                                "python": py,
                                "matlab": {"value": mv, "valid": mvalid},
                                "abs_diff": abs(float(mv) - float(py["value"])) if mv is not None and py.get("value") is not None else None,
                                "tolerance": tol,
                            }
                        )

                    def add_invalid(name: str, py, mvalid):
                        # matched invalid rejection: both invalid
                        ok = (not py.get("valid")) and (not bool(mvalid))
                        cases.append(
                            {
                                "name": name,
                                "runtime": "cross_runtime",
                                "status": "both_reject" if ok else "fail",
                                "pass": ok,
                                "python": py,
                                "matlab": {"valid": mvalid},
                            }
                        )

                    add_valid("vh_valid", python_cases["vh_valid"], matlab_map.get("vh_valid_value"), matlab_map.get("vh_valid_valid"))
                    add_valid("hh_valid", python_cases["hh_valid"], matlab_map.get("hh_valid_value"), matlab_map.get("hh_valid_valid"))
                    add_valid("branch_valid", python_cases["branch_valid"], matlab_map.get("branch_valid_value"), matlab_map.get("branch_valid_valid"))
                    # interference multi-field
                    py_i = python_cases["interf_valid"]
                    fields = (
                        ("stripe_count", "interf_stripe_count"),
                        ("stripe_widths_median", "interf_stripe_widths_median"),
                        ("affected_frequency_fraction", "interf_affected_frequency_fraction"),
                        ("persistence", "interf_persistence"),
                        ("density", "interf_density"),
                    )
                    diffs = {a: abs(float(py_i.get(a, 0)) - float(matlab_map.get(b, 0))) for a, b in fields}
                    ok = all(d <= 1e-6 for d in diffs.values())
                    cases.append(
                        {
                            "name": "interf_valid",
                            "runtime": "cross_runtime",
                            "status": "match" if ok else "fail",
                            "pass": ok,
                            "python": py_i,
                            "matlab": {a: matlab_map.get(b) for a, b in fields},
                            "abs_diff": diffs,
                            "tolerance": 1e-6,
                        }
                    )

                    add_invalid("vh_empty", python_cases["vh_empty"], matlab_map.get("vh_empty_valid"))
                    # zero profile may be valid-zero-width or invalid — require agreement on validity
                    py_z, mv = python_cases["vh_zero"], matlab_map.get("vh_zero_valid")
                    cases.append(
                        {
                            "name": "vh_zero",
                            "runtime": "cross_runtime",
                            "status": "match" if bool(py_z.get("valid")) == bool(mv) else "fail",
                            "pass": bool(py_z.get("valid")) == bool(mv),
                            "python": py_z,
                            "matlab": {"valid": mv, "value": matlab_map.get("vh_zero_value")},
                        }
                    )
                    add_invalid("vh_nan", python_cases["vh_nan"], matlab_map.get("vh_nan_valid"))
                    add_invalid("vh_inf", python_cases["vh_inf"], matlab_map.get("vh_inf_valid"))
                    add_invalid("hh_empty", python_cases["hh_empty"], matlab_map.get("hh_empty_valid"))
                    add_invalid("hh_nan", python_cases["hh_nan"], matlab_map.get("hh_nan_valid"))
                    add_invalid("branch_empty", python_cases["branch_empty"], matlab_map.get("branch_empty_valid"))
                    add_invalid("branch_mismatch", python_cases["branch_mismatch"], matlab_map.get("branch_mismatch_valid"))
                    # empty/none interference: compare stripe_count==0
                    for name, key in (("interf_empty", "interf_empty_stripe_count"), ("interf_none", "interf_none_stripe_count")):
                        py = python_cases[name]
                        mv = float(matlab_map.get(key, -1))
                        ok = abs(float(py.get("stripe_count", 0)) - mv) <= 1e-9
                        cases.append(
                            {
                                "name": name,
                                "runtime": "cross_runtime",
                                "status": "match" if ok else "fail",
                                "pass": ok,
                                "python": py,
                                "matlab": {"stripe_count": mv},
                            }
                        )

                    for name, py in python_only.items():
                        cases.append(
                            {
                                "name": name,
                                "runtime": "python_only",
                                "status": "python_only",
                                "pass": True,
                                "python": py,
                                "matlab": None,
                            }
                        )
                    if any(c.get("pass") is False for c in cases):
                        status = "fail"
            except subprocess.TimeoutExpired:
                status = "fail"
                matlab_stderr = "timeout"
                cases = [{"name": "matlab", "runtime": "cross_runtime", "status": "fail", "pass": False, "reason": "timeout"}]
            except Exception as exc:  # noqa: BLE001
                status = "fail"
                matlab_stderr = str(exc)
                cases = [{"name": "matlab", "runtime": "cross_runtime", "status": "fail", "pass": False, "reason": str(exc)}]

    cross = [c for c in cases if c.get("runtime") == "cross_runtime"]
    counts = {
        "total_cases": len(cases),
        "actual_cross_runtime_comparisons": len(cross),
        "python_only_cases": sum(1 for c in cases if c.get("runtime") == "python_only"),
        "matlab_only_cases": 0,
        "skipped": sum(1 for c in cases if c.get("status") == "skip"),
        "matched_valid_values": sum(1 for c in cross if c.get("status") == "match" and c.get("pass")),
        "matched_invalid_rejections": sum(1 for c in cross if c.get("status") == "both_reject" and c.get("pass")),
        "failures": sum(1 for c in cases if c.get("pass") is False),
    }
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "4B.2",
        "status": status,
        "matlab_mode": args.matlab,
        "matlab_executable": matlab,
        "matlab_version": matlab_version,
        "matlab_returncode": matlab_rc,
        "stdout": matlab_stdout[-4000:],
        "stderr": matlab_stderr[-4000:],
        "counts": counts,
        "cases": cases,
        "note": "cross_runtime requires both Python and MATLAB results compared; python_checked is not used",
    }
    (OUT / "parity_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (OUT / "matlab_stdout.txt").write_text(matlab_stdout, encoding="utf-8")
    (OUT / "matlab_stderr.txt").write_text(matlab_stderr, encoding="utf-8")
    if status == "fail":
        print("FAIL feature_parity", counts)
        return 1
    print(status.upper() if status != "ok" else "OK", "feature_parity", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
