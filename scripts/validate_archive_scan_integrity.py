#!/usr/bin/env python3
"""Fail if archive_variable_audit.json bytes do not match archive_scan_meta.result_json_sha256."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "workspaces" / "_phase4a_evidence" / "archive_variable_audit.json"
META = ROOT / "workspaces" / "_phase4a_evidence" / "archive_scan_meta.json"

REQUIRED_AUDIT_KEYS = {
    "script_version",
    "script_sha256",
    "scan_roots",
    "start_time_utc",
    "end_time_utc",
    "status",
    "scanned_mat_files",
    "unreadable_file_count",
    "error_count",
    "target_variable_counts",
    "records",
}


def main() -> int:
    errors: list[str] = []
    if not AUDIT.is_file():
        errors.append(f"missing {AUDIT}")
    if not META.is_file():
        errors.append(f"missing {META}")
    if errors:
        print("validate_archive_scan_integrity FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    meta = json.loads(META.read_text(encoding="utf-8"))
    expected = meta.get("result_json_sha256")
    actual = hashlib.sha256(AUDIT.read_bytes()).hexdigest()
    if not expected:
        errors.append("meta missing result_json_sha256")
    elif actual != expected:
        errors.append(f"SHA mismatch actual={actual} meta={expected}")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED_AUDIT_KEYS - set(audit))
    if missing:
        errors.append(f"audit missing keys: {missing}")
    if "result_json_sha256" in audit:
        errors.append("audit must not contain self-referential result_json_sha256 (store hash only in meta)")
    if errors:
        print("validate_archive_scan_integrity FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print("validate_archive_scan_integrity OK", actual[:16] + "…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
