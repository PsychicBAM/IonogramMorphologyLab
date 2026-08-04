#!/usr/bin/env python3
"""Fail if matlab_builtin/*.m files violate readability conventions."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILTIN = ROOT / "matlab_builtin"

from format_matlab_builtin_readability import (  # noqa: E402
    REQUIRED_HEADER_KEYS,
    count_column_zero_functions,
    count_top_level_semicolons,
    has_required_header,
)


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(ROOT).as_posix()
    errors: list[str] = []

    missing = has_required_header(text)
    if missing:
        errors.append(f"{rel}: missing header markers: {', '.join(missing)}")

    total, extra_mains, func_indices = count_column_zero_functions(text)
    if total == 0:
        errors.append(f"{rel}: no top-level function declaration")
    elif extra_mains > 0:
        errors.append(
            f"{rel}: multiple main function entries at column 0 "
            f"(found {extra_mains + 1} before main end)"
        )

    for i, line in enumerate(text.splitlines(), start=1):
        n_semi = count_top_level_semicolons(line)
        if n_semi >= 2:
            errors.append(
                f"{rel}:{i}: compressed line with {n_semi + 1} semicolon-joined statements"
            )

    return errors


def check_all(root: Path = BUILTIN) -> tuple[int, list[str]]:
    all_errors: list[str] = []
    n_files = 0
    for path in sorted(root.rglob("*.m")):
        n_files += 1
        all_errors.extend(check_file(path))
    return n_files, all_errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check matlab_builtin .m readability.")
    parser.add_argument("--root", type=Path, default=BUILTIN, help="Root directory to scan.")
    args = parser.parse_args()

    n_files, errors = check_all(args.root)
    if errors:
        print(f"FAIL: {len(errors)} issue(s) in {n_files} file(s)")
        for err in errors:
            print(err)
        return 1

    print(f"PASS: all {n_files} matlab_builtin .m files meet readability conventions")
    for key in REQUIRED_HEADER_KEYS:
        print(f"  - {key} present")
    print("  - one main function per file (local helpers allowed)")
    print("  - no compressed semicolon-joined statement lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
