#!/usr/bin/env python3
"""Validate release wording and relative Markdown links in README files."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors: list[str] = []
    readme_en = ROOT / "README.md"
    readme_ru = ROOT / "README_RU.md"

    if not readme_en.is_file():
        errors.append("missing README.md")
    if not readme_ru.is_file():
        errors.append("missing README_RU.md")

    for name, p in (("README.md", readme_en), ("README_RU.md", readme_ru)):
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        if "1.1.1" not in text:
            errors.append(f"{name}: missing 1.1.1")
        if re.search(r"(?i)E:\\\\", text) or re.search(r"(?i)C:\\\\Users\\\\", text):
            errors.append(f"{name}: contains absolute Windows path")
        if name == "README.md" and "README_RU.md" not in text:
            errors.append(f"{name}: missing reciprocal link to README_RU.md")
        if name == "README_RU.md" and "README.md" not in text:
            errors.append(f"{name}: missing reciprocal link to README.md")
        for link in re.findall(r"(?<!!)\[[^]]*\]\(([^)#]+)", text):
            if "://" in link or link.startswith("mailto:"):
                continue
            target = (p.parent / link).resolve()
            if not target.exists():
                errors.append(f"{name}: broken relative link {link}")

    if errors:
        print(*errors, sep="\n")
        return 1
    print("README validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
