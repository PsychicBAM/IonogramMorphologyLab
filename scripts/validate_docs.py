#!/usr/bin/env python3
"""Fail CI when release documentation is incomplete, broken, or placeholder."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

REQUIRED_ROOT = [
    ROOT / "README.md",
    ROOT / "README_RU.md",
]

REQUIRED_DOCS = [
    DOCS / "USER_GUIDE_EN.md",
    DOCS / "USER_GUIDE_RU.md",
    DOCS / "SCIENTIFIC_GUIDE_EN.md",
    DOCS / "SCIENTIFIC_GUIDE_RU.md",
    DOCS / "DEVELOPER_GUIDE.md",
    DOCS / "SECURITY_AND_TRUST.md",
    DOCS / "PRODUCT_SIMPLIFICATION_QA.md",
    DOCS / "SCIENTIFIC_CLASSIFICATION_QA.md",
]

EN_RU_PAIRS = [
    (DOCS / "USER_GUIDE_EN.md", DOCS / "USER_GUIDE_RU.md"),
    (DOCS / "SCIENTIFIC_GUIDE_EN.md", DOCS / "SCIENTIFIC_GUIDE_RU.md"),
    (ROOT / "README.md", ROOT / "README_RU.md"),
]

MOJIBAKE_PATTERNS = [
    re.compile(r"\?\?\?\?"),
    re.compile(r"Ð"),
    re.compile(r"Ñ"),
    re.compile(r"провенance", re.IGNORECASE),
    re.compile(r"Контamination"),
]

PLACEHOLDER_PATTERNS = [
    re.compile(r"Last run: pending", re.IGNORECASE),
    re.compile(r"SVG placeholder", re.IGNORECASE),
    re.compile(r"_pending_"),
    re.compile(r"TODO: fill", re.IGNORECASE),
]

LINK_RE = re.compile(r"(?<!!)\[[^]]*\]\(([^)#]+)")

MIN_LINES_DEFAULT = 40
MIN_LINES_EXCEPTIONS = {
    ROOT / "CHANGELOG.md": 0,  # historical sections allowed to be short overall
    DOCS / "USER_GUIDE_EN.md": 20,
    DOCS / "USER_GUIDE_RU.md": 20,
    DOCS / "SCIENTIFIC_GUIDE_EN.md": 20,
    DOCS / "SCIENTIFIC_GUIDE_RU.md": 20,
    DOCS / "DEVELOPER_GUIDE.md": 20,
    DOCS / "SECURITY_AND_TRUST.md": 12,
    DOCS / "PRODUCT_SIMPLIFICATION_QA.md": 0,
    DOCS / "SCIENTIFIC_CLASSIFICATION_QA.md": 0,
}

SCAN_MARKDOWN = [
    ROOT / "README.md",
    ROOT / "README_RU.md",
    *sorted(p for p in DOCS.rglob("*.md") if "archive" not in p.parts),
]

VERSION_FILES = [ROOT / "README.md", ROOT / "CHANGELOG.md"]


def _non_empty_lines(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return 0
    return sum(1 for line in text.splitlines() if line.strip())


def _check_links(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for link in LINK_RE.findall(text):
        if "://" in link or link.startswith("mailto:"):
            continue
        target = (path.parent / link).resolve()
        if not target.exists():
            errors.append(f"{path.relative_to(ROOT)}: broken relative link {link}")


def _check_mojibake(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern in MOJIBAKE_PATTERNS:
        if pattern.search(text):
            errors.append(f"{path.relative_to(ROOT)}: mojibake pattern {pattern.pattern!r}")


def _check_placeholders(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(text):
            errors.append(f"{path.relative_to(ROOT)}: placeholder phrase {pattern.pattern!r}")


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_ROOT + REQUIRED_DOCS:
        if not path.is_file():
            errors.append(f"missing required doc: {path.relative_to(ROOT)}")

    for en_path, ru_path in EN_RU_PAIRS:
        if en_path.is_file() and not ru_path.is_file():
            errors.append(f"missing RU pair for {en_path.relative_to(ROOT)}")
        if ru_path.is_file() and not en_path.is_file():
            errors.append(f"missing EN pair for {ru_path.relative_to(ROOT)}")

    for path in VERSION_FILES:
        if path.is_file() and "1.1.1" not in path.read_text(encoding="utf-8"):
            errors.append(f"{path.relative_to(ROOT)}: missing version 1.1.1")

    for path in REQUIRED_ROOT + REQUIRED_DOCS:
        if not path.is_file():
            continue
        min_lines = MIN_LINES_EXCEPTIONS.get(path, MIN_LINES_DEFAULT)
        count = _non_empty_lines(path)
        if count < min_lines:
            errors.append(
                f"{path.relative_to(ROOT)}: only {count} non-empty lines (minimum {min_lines})"
            )

    for path in SCAN_MARKDOWN:
        if not path.is_file():
            continue
        _check_links(path, errors)
        if path in REQUIRED_ROOT or path in REQUIRED_DOCS:
            _check_mojibake(path, errors)
            _check_placeholders(path, errors)

    if errors:
        sys.stdout.buffer.write(b"Documentation validation FAILED:\n")
        for err in errors:
            sys.stdout.buffer.write(f"  - {err}\n".encode("utf-8", errors="replace"))
        return 1

    sys.stdout.buffer.write(b"Documentation validation passed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
