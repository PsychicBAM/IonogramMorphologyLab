#!/usr/bin/env python3
"""Audit AmEsP / A_map_F / H_map_F where actually present (Phase 4A.1 / 4A.1b).

Fast whosmat-based scan. Meanings remain unresolved; automatic use disabled.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SCRIPT_VERSION = "4A.1b-whosmat-1"
TARGETS = ("AmEsP", "A_map_F", "H_map_F")
SEARCH_ROOTS = [
    Path(r"E:\ionog\conference_presentation\ion2013"),
    Path(r"E:\ionog\conference_presentation\ion2014"),
]


def _script_sha256() -> str:
    p = Path(__file__).resolve()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _whos(path: Path) -> list[tuple]:
    try:
        import scipy.io as sio

        return list(sio.whosmat(str(path)))
    except Exception:
        try:
            import h5py

            out = []
            with h5py.File(str(path), "r") as f:
                for name in f.keys():
                    if str(name).startswith("#"):
                        continue
                    ds = f[name]
                    try:
                        shape = tuple(ds.shape)
                        dtype = str(ds.dtype)
                    except Exception:
                        shape = ()
                        dtype = "unknown"
                    out.append((name, shape, dtype))
            return out
        except Exception:
            return []


def _load_var(path: Path, name: str) -> dict:
    try:
        import scipy.io as sio
        import numpy as np

        try:
            data = sio.loadmat(str(path), variable_names=[name], squeeze_me=False)
            arr = np.asarray(data[name])
            neighbors = [t[0] for t in sio.whosmat(str(path))]
            return {
                "shape": list(arr.shape),
                "dtype": str(arr.dtype),
                "file_type": "matlab_v5_or_v7",
                "neighbors": neighbors,
            }
        except NotImplementedError:
            import h5py

            with h5py.File(str(path), "r") as f:
                arr = np.asarray(f[name][()])
                neighbors = [k for k in f.keys() if not str(k).startswith("#")]
                return {
                    "shape": list(arr.shape),
                    "dtype": str(arr.dtype),
                    "file_type": "matlab_v73_hdf5",
                    "neighbors": neighbors,
                }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "file_type": "unreadable", "neighbors": []}


def main() -> int:
    start = datetime.now(timezone.utc)
    findings: dict[str, list] = defaultdict(list)
    scanned = 0
    unreadable = 0
    error_count = 0
    candidate_files = 0
    status = "completed"
    try:
        for root in SEARCH_ROOTS:
            if not root.is_dir():
                continue
            for path in root.rglob("*.mat"):
                scanned += 1
                try:
                    vars_ = _whos(path)
                except Exception:  # noqa: BLE001
                    unreadable += 1
                    error_count += 1
                    continue
                if not vars_ and path.stat().st_size > 0:
                    # empty whos may mean unreadable v7.3 without h5py success
                    pass
                names = {t[0] for t in vars_}
                hit = [n for n in TARGETS if n in names]
                if not hit:
                    continue
                candidate_files += 1
                for name in hit:
                    info = _load_var(path, name)
                    if info.get("error"):
                        error_count += 1
                        unreadable += 1
                    findings[name].append({"path": str(path), **info})
    except KeyboardInterrupt:
        status = "interrupted"
    end = datetime.now(timezone.utc)

    records = []
    for name in TARGETS:
        occ = findings.get(name) or []
        shapes: dict[str, int] = {}
        dtypes: dict[str, int] = {}
        neighbor_counts: dict[str, int] = defaultdict(int)
        file_types = set()
        for o in occ:
            shapes[str(o.get("shape"))] = shapes.get(str(o.get("shape")), 0) + 1
            dtypes[str(o.get("dtype"))] = dtypes.get(str(o.get("dtype")), 0) + 1
            file_types.add(o.get("file_type"))
            for n in o.get("neighbors") or []:
                neighbor_counts[str(n)] += 1
        top_neighbors = sorted(neighbor_counts.items(), key=lambda x: -x[1])[:20]
        records.append(
            {
                "variable_name": name,
                "file_type": sorted(t for t in file_types if t),
                "occurrence_count": len(occ),
                "shapes_observed": shapes,
                "dtypes_observed": dtypes,
                "neighboring_metadata_top": top_neighbors,
                "example_paths": [o["path"] for o in occ[:5]],
                "possible_role": "unresolved — name-based inference forbidden",
                "verified_meaning": None,
                "unresolved_questions": [
                    "What physical/archive quantity does this variable store?",
                    "Is the layout stable across years/products?",
                    "Is it safe for any automatic scientific use?",
                ],
                "automatic_use": "disabled",
            }
        )

    out_json = ROOT / "workspaces" / "_phase4a_evidence" / "archive_variable_audit.json"
    meta_json = out_json.parent / "archive_scan_meta.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    # Final payload — no self-referential hash field inside this file
    payload = {
        "script_version": SCRIPT_VERSION,
        "script_sha256": _script_sha256(),
        "scan_roots": [str(p) for p in SEARCH_ROOTS],
        "start_time_utc": start.isoformat(),
        "end_time_utc": end.isoformat(),
        "status": status,
        "prior_attempt_note": (
            "An earlier full-loadmat scan (Phase 4A.1 first attempt) was interrupted and must not be "
            "confused with this completed whosmat-based scan."
        ),
        "scanned_mat_files": scanned,
        "unreadable_file_count": unreadable,
        "error_count": error_count,
        "files_with_any_target": candidate_files,
        "target_variable_counts": {r["variable_name"]: r["occurrence_count"] for r in records},
        "records": records,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    out_json.write_text(text, encoding="utf-8")
    # Hash final bytes only after the last write; never rewrite archive_variable_audit.json after this
    result_sha = hashlib.sha256(out_json.read_bytes()).hexdigest()
    meta = {
        "result_json_path": str(out_json),
        "result_json_sha256": result_sha,
        "hash_policy": "sha256_of_final_archive_variable_audit_json_bytes; hash is NOT stored inside that file",
        "script_version": SCRIPT_VERSION,
        "script_sha256": payload["script_sha256"],
        "status": status,
        "scanned_mat_files": scanned,
        "unreadable_file_count": unreadable,
        "error_count": error_count,
        "target_variable_counts": payload["target_variable_counts"],
        "start_time_utc": payload["start_time_utc"],
        "end_time_utc": payload["end_time_utc"],
        "scan_roots": payload["scan_roots"],
        "prior_attempt_note": payload["prior_attempt_note"],
    }
    meta_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Re-read validation before packaging/docs
    actual = hashlib.sha256(out_json.read_bytes()).hexdigest()
    meta_reload = json.loads(meta_json.read_text(encoding="utf-8"))
    if actual != meta_reload.get("result_json_sha256"):
        raise RuntimeError(
            f"archive JSON hash mismatch after write: actual={actual} meta={meta_reload.get('result_json_sha256')}"
        )
    # keep meta for doc generation
    meta = meta_reload

    doc = ROOT / "docs" / "ARCHIVE_VARIABLE_AUDIT_4A1.md"
    lines = [
        "# Archive Variable Audit (Phase 4A.1 / 4A.1b)",
        "",
        "Do **not** infer meaning of `AmEsP`, `A_map_F`, or `H_map_F` from names alone.",
        "Automatic use remains **disabled** until interpretation is source-supported.",
        "",
        f"- script_version: `{SCRIPT_VERSION}`",
        f"- script_sha256: `{meta['script_sha256']}`",
        f"- status: **{status}** (completed whosmat scan; not the interrupted first attempt)",
        f"- scan_roots: `{meta['scan_roots']}`",
        f"- start/end UTC: `{meta['start_time_utc']}` → `{meta['end_time_utc']}`",
        f"- scanned_mat_files: **{scanned}**",
        f"- unreadable_file_count: **{unreadable}**",
        f"- error_count: **{error_count}**",
        f"- result_json_sha256: `{meta['result_json_sha256']}`",
        "",
    ]
    for r in records:
        lines.extend(
            [
                f"## `{r['variable_name']}`",
                "",
                f"- occurrence_count: **{r['occurrence_count']}**",
                f"- verified_meaning: `{r['verified_meaning']}`",
                f"- automatic_use: **{r['automatic_use']}**",
                f"- shapes_observed: `{r['shapes_observed']}`",
                f"- dtypes_observed: `{r['dtypes_observed']}`",
                "",
            ]
        )
        if r["example_paths"]:
            lines.append("- example_paths:")
            for p in r["example_paths"][:3]:
                lines.append(f"  - `{p}`")
        lines.append("")
    doc.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", out_json)
    print("Wrote", out_json.parent / "archive_scan_meta.json")
    print("status", status, "scanned", scanned)
    for r in records:
        print(r["variable_name"], "count=", r["occurrence_count"])
    return 0 if status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
