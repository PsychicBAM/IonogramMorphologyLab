#!/usr/bin/env python3
"""Fail on repository hygiene violations without reading generated outputs."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {
    ".git",
    ".venv",
    ".venv-sec",
    "venv",
    "build",
    "dist",
    "workspaces",
    "logs",
    "__pycache__",
    ".pytest_cache",
    "site-packages",
}
TEXT_EXT = {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".ps1", ".iss"}
SECRET = re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}")
ABS = re.compile(r"(?i)(?:[A-Z]:\\(?:Users|ionog|home)|/(?:home|Users)/)")


def tracked_files():
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
        for rel in out.splitlines():
            if rel.strip():
                yield ROOT / rel
        return
    except (OSError, subprocess.CalledProcessError):
        pass
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(part in SKIP for part in p.parts):
            continue
        yield p


def main():
    errors: list[str] = []
    counts = {
        "large_file": 0,
        "mat_outside_synthetic": 0,
        "possible_secret": 0,
        "absolute_local_path": 0,
        "tracked_zarr": 0,
        "tracked_key_material": 0,
        "matlab_crash_dump": 0,
        "workspace_db": 0,
    }

    for p in tracked_files():
        rel = p.relative_to(ROOT).as_posix()

        if p.stat().st_size > 50 * 1024 * 1024:
            counts["large_file"] += 1
            errors.append(f"large file (>50 MB): {rel}")

        if p.suffix.lower() == ".mat" and not rel.startswith("synthetic_data/"):
            counts["mat_outside_synthetic"] += 1
            errors.append(f"MAT outside synthetic_data: {rel}")

        if ".zarr" in p.parts or rel.endswith(".zarr") or "/.zarr/" in f"/{rel}/":
            counts["tracked_zarr"] += 1
            errors.append(f"tracked .zarr data: {rel}")

        if p.suffix.lower() in {".pem", ".key"}:
            counts["tracked_key_material"] += 1
            errors.append(f"tracked key material: {rel}")

        if p.name.startswith("matlab_crash_dump"):
            counts["matlab_crash_dump"] += 1
            errors.append(f"MATLAB crash dump: {rel}")

        if rel.startswith("workspaces/") and p.suffix.lower() == ".db":
            counts["workspace_db"] += 1
            errors.append(f"user workspace database: {rel}")

        if p.suffix.lower() in TEXT_EXT:
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if SECRET.search(text):
                counts["possible_secret"] += 1
                errors.append(f"possible secret: {rel}")
            if (rel.startswith("docs/") or rel.startswith("src/")) and ABS.search(text):
                counts["absolute_local_path"] += 1
                errors.append(f"absolute local path: {rel}")

    print("Repository hygiene summary:")
    for key, value in counts.items():
        print(f"  {key}: {value}")
    print(f"  total_violations: {len(errors)}")

    if errors:
        print("\nRepository hygiene failed:")
        print(*(" - " + x for x in errors), sep="\n")
        return 1
    print("Repository hygiene passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
