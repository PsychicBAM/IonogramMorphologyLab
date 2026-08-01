#!/usr/bin/env python3
"""Make matlab_builtin / matlab_helpers R2019a-safe: ASCII comments, UTF-8 BOM, top-level function at column 1."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = [ROOT / "matlab_builtin", ROOT / "matlab_helpers"]


def to_ascii_comment_safe(text: str) -> str:
    # Common replacements
    repl = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
        "≠": "!=",
        "×": "x",
        "—": "-",
        "–": "-",
        "«": '"',
        "»": '"',
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    # Drop remaining non-ASCII (keep newlines/tabs)
    out = []
    for ch in text:
        o = ord(ch)
        if ch in "\n\r\t" or 32 <= o < 127:
            out.append(ch)
        else:
            # skip Cyrillic and other non-ASCII in comments/strings for R2019a default encoding
            continue
    return "".join(out)


def dedent_primary_function(text: str) -> str:
    """Ensure every file-level `function` / matching `end` style is parseable.

    R2019a requires the primary function and subfunctions at column 0.
    Nested functions remain indented inside the primary body.
    Heuristic: any line that is only indent + function|end at function-depth 0
    for `function` keywords that appear after a prior top-level end, or the first function.
    Simpler approach used here: unindent every line that matches `^\\s*function\\b`.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*function\b", line):
            lines[i] = re.sub(r"^\s+", "", line)
        # also unindent lone `end` that closes subfunctions when over-indented at EOF blocks
        elif re.match(r"^\s+end\s*$", line):
            # keep nested ends indented; only collapse extreme indent (>=8) at file-ish level
            if line.startswith("        end") and i > 0:
                # leave as-is; mismatched ends are rarer than nested ends
                pass
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def write_utf8_bom(path: Path, text: str) -> None:
    # R2019a on Windows often rejects UTF-8 BOM as "Invalid text character".
    # After ASCII sanitization, write plain UTF-8 without BOM.
    path.write_bytes(text.encode("utf-8"))


def main() -> int:
    n = 0
    for d in DIRS:
        if not d.exists():
            continue
        for path in sorted(d.rglob("*.m")):
            raw = path.read_text(encoding="utf-8", errors="replace")
            fixed = to_ascii_comment_safe(raw)
            fixed = dedent_primary_function(fixed)
            # Ensure file ends with newline
            if not fixed.endswith("\n"):
                fixed += "\n"
            write_utf8_bom(path, fixed)
            n += 1
    print(f"sanitized {n} .m files for R2019a")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
