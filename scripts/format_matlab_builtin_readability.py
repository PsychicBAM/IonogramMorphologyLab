#!/usr/bin/env python3
"""Pretty-print matlab_builtin/*.m files for human readability (formatting only)."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
BUILTIN = ROOT / "matlab_builtin"

INDENT = "    "

REQUIRED_HEADER_KEYS = (
    "Purpose:",
    "Inputs:",
    "Outputs:",
    "Scientific status:",
    "Limitations:",
)

# Purpose overrides for well-known method names (humanized one-liners).
PURPOSE_OVERRIDES: dict[str, str] = {
    "iml_compare_branch_diffuseness": (
        "Measures differences in apparent diffuseness between candidate "
        "trace branches."
    ),
    "iml_compare_trace_methods": (
        "Compares candidate trace-detection heuristics on the current frame."
    ),
    "iml_validate_frame": (
        "Validates that a candidate ionogram frame is numeric, 2-D, and "
        "mostly finite."
    ),
    "iml_load_frame": "Loads a candidate ionogram frame from workspace or file.",
    "iml_load_sequence": "Loads a candidate ionogram frame sequence.",
    "iml_export_result": "Exports a candidate result struct to a MAT file.",
}

VERB_PHRASES: dict[str, str] = {
    "detect": "Detects candidate",
    "estimate": "Estimates candidate",
    "measure": "Measures",
    "compare": "Compares",
    "count": "Counts",
    "validate": "Validates",
    "load": "Loads",
    "render": "Renders",
    "export": "Exports",
    "build": "Builds",
    "write": "Writes",
    "segment": "Segments",
    "separate": "Separates",
    "classify": "Classifies",
    "extract": "Extracts",
    "trace": "Traces",
    "create": "Creates",
}


class MatlabScanner:
    """Scan MATLAB source respecting strings and nesting."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.i = 0
        self.n = len(text)

    def peek(self) -> str:
        return self.text[self.i] if self.i < self.n else ""

    def advance(self, n: int = 1) -> None:
        self.i += n

    def at_depth_zero(self, start: int, end: int) -> bool:
        depth = 0
        in_str = False
        quote = ""
        j = start
        while j < end:
            c = self.text[j]
            if in_str:
                if c == quote and (j == 0 or self.text[j - 1] != "\\"):
                    in_str = False
            elif c in "'\"":
                in_str = True
                quote = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            j += 1
        return depth == 0

    def find_depth_zero(self, chars: set[str], start: int = 0) -> int | None:
        depth = 0
        in_str = False
        quote = ""
        j = start
        while j < self.n:
            c = self.text[j]
            if in_str:
                if c == quote and (j == 0 or self.text[j - 1] != "\\"):
                    in_str = False
            elif c in "'\"":
                in_str = True
                quote = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif depth == 0 and c in chars:
                return j
            j += 1
        return None

    def split_at_depth_zero(self, chars: set[str]) -> list[str]:
        parts: list[str] = []
        start = 0
        j = 0
        depth = 0
        in_str = False
        quote = ""
        while j < self.n:
            c = self.text[j]
            if in_str:
                if c == quote and (j == 0 or self.text[j - 1] != "\\"):
                    in_str = False
            elif c in "'\"":
                in_str = True
                quote = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif depth == 0 and c in chars:
                parts.append(self.text[start:j].strip())
                start = j + 1
            j += 1
        tail = self.text[start:].strip()
        if tail:
            parts.append(tail)
        return [p for p in parts if p]


def find_comment_start(line: str) -> int | None:
    in_str = False
    quote = ""
    i = 0
    while i < len(line):
        c = line[i]
        if in_str:
            if c == quote and (i == 0 or line[i - 1] != "\\"):
                in_str = False
        elif c in "'\"":
            in_str = True
            quote = c
        elif c == "%":
            return i
        i += 1
    return None


def strip_comments_from_line(line: str) -> str:
    idx = find_comment_start(line)
    if idx is not None:
        return line[:idx].rstrip()
    return line.rstrip()


def is_comment_line(line: str) -> bool:
    return not line.strip() or line.lstrip().startswith("%")


def is_continuation_line(line: str) -> bool:
    return bool(re.search(r"\.\.\.\s*$", strip_comments_from_line(line)))


def join_physical_lines(lines: Iterable[str]) -> list[str]:
    """Join MATLAB `...` continuation lines into logical lines."""
    logical: list[str] = []
    buf = ""
    for raw in lines:
        line = raw.rstrip()
        if not buf:
            buf = line
        else:
            buf = buf.rstrip()
            if buf.endswith("..."):
                buf = buf[:-3].rstrip() + " " + line.lstrip()
            else:
                logical.append(buf)
                buf = line
        if buf and not is_continuation_line(buf):
            logical.append(buf)
            buf = ""
    if buf:
        logical.append(buf)
    return logical


def split_semicolon_statements(text: str) -> list[str]:
    if ";" not in text:
        return [text.strip()] if text.strip() else []
    raw = MatlabScanner(text).split_at_depth_zero({";"})
    raw = [p.strip() for p in raw if p.strip()]
    if not raw:
        return []

    merged: list[str] = []
    i = 0
    while i < len(raw):
        part = raw[i]
        if re.match(r"^(if|for|while)\b", part):
            combined = part
            i += 1
            while i < len(raw):
                nxt = raw[i]
                combined = f"{combined}; {nxt}"
                i += 1
                if nxt == "end" or re.search(r"\bend\s*$", nxt):
                    break
                if parse_if_comma_form(combined) or parse_for_while_comma_form(combined):
                    break
            merged.append(combined)
            continue
        merged.append(part)
        i += 1
    return merged


def starts_with_keyword(text: str, kw: str) -> bool:
    return bool(re.match(rf"^{kw}\b", text.strip()))


def find_keyword_at_depth_zero(text: str, keyword: str, start: int = 0) -> int | None:
    pattern = re.compile(rf"\b{keyword}\b")
    for match in pattern.finditer(text, start):
        if MatlabScanner(text).at_depth_zero(0, match.start()):
            return match.start()
    return None


def _match_block_keyword(text: str, i: int) -> tuple[str, int] | None:
    for kw in ("function", "elseif", "else", "while", "switch", "parfor", "for", "try", "if", "end"):
        if text.startswith(kw, i) and (i + len(kw) >= len(text) or not (text[i + len(kw)].isalnum() or text[i + len(kw)] == "_")):
            return kw, len(kw)
    return None


def find_keyword_at_block_depth_zero(text: str, keyword: str, start: int = 0) -> int | None:
    """Find elseif/else/end (or openers) only at MATLAB block nesting depth zero."""
    block_depth = 0
    i = start
    n = len(text)
    in_str = False
    quote = ""
    while i < n:
        c = text[i]
        if in_str:
            if c == quote and (i == 0 or text[i - 1] != "\\"):
                in_str = False
            i += 1
            continue
        if c in "'\"":
            in_str = True
            quote = c
            i += 1
            continue
        matched = _match_block_keyword(text, i)
        if matched:
            kw, kw_len = matched
            if kw in ("if", "for", "while", "switch", "parfor", "try", "function"):
                if block_depth == 0 and kw == keyword:
                    return i
                block_depth += 1
            elif kw in ("elseif", "else") and block_depth == 0:
                return i
            elif kw == "end":
                block_depth = max(0, block_depth - 1)
                if block_depth == 0 and keyword == "end":
                    return i
            i += kw_len
            continue
        i += 1
    return None


def find_next_branch_boundary(text: str, start: int = 0, include_end: bool = False) -> int:
    """Return index of the next elseif/else (and optionally end) at block depth zero."""
    block_depth = 0
    i = start
    n = len(text)
    in_str = False
    quote = ""
    while i < n:
        c = text[i]
        if in_str:
            if c == quote and (i == 0 or text[i - 1] != "\\"):
                in_str = False
            i += 1
            continue
        if c in "'\"":
            in_str = True
            quote = c
            i += 1
            continue
        matched = _match_block_keyword(text, i)
        if matched:
            kw, kw_len = matched
            if kw in ("if", "for", "while", "switch", "parfor", "try", "function"):
                block_depth += 1
            elif kw in ("elseif", "else") and block_depth == 0:
                return i
            elif kw == "end":
                block_depth = max(0, block_depth - 1)
                if include_end and block_depth == 0:
                    return i
            i += kw_len
            continue
        i += 1
    return n


def strip_trailing_statement_end(body: str) -> str:
    return re.sub(r";\s*end\s*$", "", body.strip(), flags=re.IGNORECASE).strip()


def parse_if_comma_form(text: str) -> dict | None:
    """Parse `if cond, body [, else/elseif ...] end` when written on one logical line."""
    stripped = text.strip()
    if not starts_with_keyword(stripped, "if"):
        return None
    scanner = MatlabScanner(stripped)
    first_comma = scanner.find_depth_zero({","}, start=3)
    if first_comma is None:
        return None
    condition = stripped[3:first_comma].strip()
    rest = stripped[first_comma + 1 :].strip()
    clauses: list[tuple[str, str]] = [("if", condition)]
    pos = 0
    while pos < len(rest):
        rest_l = rest[pos:].lstrip()
        offset = pos + (len(rest[pos:]) - len(rest_l))
        if not rest_l:
            break
        if rest_l.startswith("elseif "):
            sub = rest_l[len("elseif ") :]
            comma = MatlabScanner(sub).find_depth_zero({","}, start=0)
            if comma is None:
                return None
            cond = sub[:comma].strip()
            body_rest = sub[comma + 1 :]
            cut = find_next_branch_boundary(body_rest, 0)
            body = strip_trailing_statement_end(body_rest[:cut].strip().rstrip(","))
            clauses.append(("elseif", cond))
            clauses.append(("body", body))
            pos = offset + len("elseif ") + comma + 1 + cut
            continue
        if rest_l.startswith("else"):
            remainder = rest_l[len("else") :].lstrip()
            if remainder.startswith(","):
                remainder = remainder[1:].lstrip()
            cut = find_next_branch_boundary(remainder, 0, include_end=True)
            body = strip_trailing_statement_end(remainder[:cut].strip().rstrip(","))
            clauses.append(("else", body))
            pos = offset + len(rest_l) - len(remainder) + cut
            continue
        if rest_l.startswith("end"):
            break
        cut = find_next_branch_boundary(rest_l, 0)
        body = strip_trailing_statement_end(rest_l[:cut].strip().rstrip(","))
        clauses.append(("body", body))
        pos = offset + cut
    if not re.search(r"\bend\b", stripped):
        return None
    return {"clauses": clauses}


def parse_for_while_comma_form(text: str) -> dict | None:
    stripped = text.strip()
    for kw in ("for", "while"):
        if starts_with_keyword(stripped, kw):
            scanner = MatlabScanner(stripped)
            first_comma = scanner.find_depth_zero({","}, start=len(kw) + 1)
            if first_comma is None:
                return None
            header = stripped[len(kw) + 1 : first_comma].strip()
            tail = stripped[first_comma + 1 :].strip()
            block_depth = 1
            end_pos = None
            i = 0
            in_str = False
            quote = ""
            while i < len(tail):
                c = tail[i]
                if in_str:
                    if c == quote and (i == 0 or tail[i - 1] != "\\"):
                        in_str = False
                    i += 1
                    continue
                if c in "'\"":
                    in_str = True
                    quote = c
                    i += 1
                    continue
                matched = _match_block_keyword(tail, i)
                if matched:
                    bkw, bkw_len = matched
                    if bkw in ("if", "for", "while", "switch", "parfor", "try", "function"):
                        block_depth += 1
                    elif bkw == "end":
                        block_depth -= 1
                        if block_depth == 0:
                            end_pos = i
                            break
                    i += bkw_len
                    continue
                i += 1
            if end_pos is None:
                return None
            body = tail[:end_pos].strip().rstrip(",")
            return {"kind": kw, "header": header, "body": body}
    return None


def finalize_statement(stmt: str) -> str:
    """Ensure executable statements retain trailing semicolons (MATLAB output suppression)."""
    stmt = stmt.rstrip()
    if not stmt or stmt.startswith("%"):
        return stmt
    if re.match(r"^(else|elseif|end|case|otherwise)\b", stmt):
        return stmt
    if re.match(r"^(if|for|while|switch|function)\b", stmt) and not stmt.rstrip().endswith(";"):
        return stmt
    if stmt.endswith("..."):
        return stmt
    if not stmt.endswith(";"):
        return stmt + ";"
    return stmt


def expand_statement(text: str, indent_level: int) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    if stripped.startswith("..."):
        return [INDENT * indent_level + stripped]

    if_form = parse_if_comma_form(stripped)
    if if_form:
        return expand_if_block(if_form, indent_level)

    loop_form = parse_for_while_comma_form(stripped)
    if loop_form:
        return expand_loop_block(loop_form, indent_level)

    if ";" in stripped:
        parts = split_semicolon_statements(stripped)
        if len(parts) > 1:
            out: list[str] = []
            for part in parts:
                out.extend(expand_statement(part, indent_level))
            return out

    return [INDENT * indent_level + finalize_statement(stripped)]


def expand_if_block(parsed: dict, indent_level: int) -> list[str]:
    out: list[str] = []
    clauses: list[tuple[str, str]] = parsed["clauses"]
    idx = 0
    while idx < len(clauses):
        kind, value = clauses[idx]
        if kind == "if":
            out.append(f"{INDENT * indent_level}if {value}")
            idx += 1
            if idx < len(clauses) and clauses[idx][0] == "body":
                body = clauses[idx][1]
                idx += 1
                out.extend(expand_body_text(body, indent_level + 1))
            continue
        if kind == "elseif":
            out.append(f"{INDENT * indent_level}elseif {value}")
            idx += 1
            if idx < len(clauses) and clauses[idx][0] == "body":
                body = clauses[idx][1]
                idx += 1
                out.extend(expand_body_text(body, indent_level + 1))
            continue
        if kind == "else":
            out.append(f"{INDENT * indent_level}else")
            out.extend(expand_body_text(value, indent_level + 1))
            idx += 1
            continue
        if kind == "body":
            out.extend(expand_body_text(value, indent_level + 1))
            idx += 1
            continue
        idx += 1
    out.append(f"{INDENT * indent_level}end")
    return out


def expand_loop_block(parsed: dict, indent_level: int) -> list[str]:
    kw = parsed["kind"]
    out = [f"{INDENT * indent_level}{kw} {parsed['header']}"]
    out.extend(expand_body_text(parsed["body"], indent_level + 1))
    out.append(f"{INDENT * indent_level}end")
    return out


def expand_body_text(text: str, indent_level: int) -> list[str]:
    parts = split_semicolon_statements(text)
    out: list[str] = []
    for part in parts:
        out.extend(expand_statement(part, indent_level))
    return out


def extract_function_name(signature: str) -> str:
    match = re.search(r"function\s+(?:\[[^\]]+\]|\w+)\s*=\s*(\w+)", signature)
    if match:
        return match.group(1)
    match = re.search(r"function\s+(\w+)", signature)
    return match.group(1) if match else "unknown_method"


def humanize_purpose(name: str) -> str:
    if name in PURPOSE_OVERRIDES:
        return PURPOSE_OVERRIDES[name]
    stem = name[4:] if name.startswith("iml_") else name
    words = stem.split("_")
    if not words:
        return "Processes ionogram candidate data."
    first = words[0]
    rest = " ".join(words[1:])
    phrase = VERB_PHRASES.get(first, first.capitalize())
    if first in VERB_PHRASES:
        text = f"{phrase} {rest}".strip()
    else:
        text = " ".join(words)
    text = text[0].upper() + text[1:] if text else "Processes ionogram candidate data."
    if not text.endswith("."):
        text += "."
    return text


def extract_legacy_disclaimer(comment_lines: list[str]) -> tuple[str, str, str]:
    en_lines: list[str] = []
    limitation_lines: list[str] = []
    source_basis = "Engineering utility / project method catalog (candidate-only)."
    in_en = False
    in_lim = False
    for line in comment_lines:
        stripped = line.strip()
        if stripped.startswith("% EN:"):
            in_en = True
            in_lim = False
            en_lines.append(stripped[2:].strip())
            continue
        if stripped.lower().startswith("% limitations:"):
            in_lim = True
            in_en = False
            limitation_lines.append(stripped[2:].strip())
            continue
        if stripped.startswith("% RU:"):
            in_en = False
            in_lim = False
            continue
        if in_en and stripped.startswith("%"):
            en_lines.append(stripped[2:].strip())
        elif in_lim and stripped.startswith("%"):
            limitation_lines.append(stripped[2:].strip())
        elif "engineering" in stripped.lower() or "project method" in stripped.lower():
            source_basis = stripped.lstrip("% ").strip()
    en_text = " ".join(en_lines).replace("EN:", "", 1).strip()
    lim_text = " ".join(limitation_lines).replace("Limitations:", "", 1).strip()
    if not en_text:
        en_text = (
            "Candidate-only, non-causal development/teaching method. Results depend on "
            "the selected ionogram profile, calibration, preprocessing, and thresholds."
        )
    if not lim_text:
        lim_text = (
            "This is a heuristic diagnostic aid, not a validated geophysical "
            "interpretation or a statement about true layer height."
        )
    return en_text, lim_text, source_basis


def infer_inputs(name: str, signature: str, body: str) -> list[tuple[str, str]]:
    inputs: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(key: str, desc: str) -> None:
        if key not in seen:
            seen.add(key)
            inputs.append((key, desc))

    if "result," in signature.replace(" ", "") or "result," in signature:
        add("result", "Candidate result struct or matrix to export.")
    if "varargin" in signature:
        if "iscell(varargin{1})" in body or "iscell(args{1})" in body:
            add("frames", "Optional cell array of ionogram frames.")
        elif "isnumeric(varargin{1})" in body or "isnumeric(args{1})" in body:
            add("frame", "Current ionogram amplitude matrix (optional override).")
        else:
            add("varargin", "Optional method-specific inputs.")
    if "iml_get_current_frame" in body or "local_frame" in body:
        add("frame", "Current ionogram amplitude matrix.")
    if "iml_get_sequence" in body:
        add("sequence", "Time-ordered ionogram frame sequence.")
    if "iml_get_frequency_axis" in body or "local_axis('frequency'" in body:
        add("frequency_axis", "Frequency values for columns.")
    if "iml_get_range_axis" in body or "local_axis('range'" in body:
        add("range_axis", "Nominal virtual-height values for rows.")
    if name.startswith("iml_test_") or name.startswith("iml_example_"):
        add("frame", "Optional synthetic or workspace frame for demonstration.")
    if not inputs:
        add("workspace", "Uses IML bridge workspace context.")
    return inputs


def infer_outputs(name: str, signature: str, body: str) -> list[tuple[str, str]]:
    outputs: list[tuple[str, str]] = []
    match = re.search(r"function\s+(\w+)\s*=", signature)
    if match:
        var = match.group(1)
        if var == "result":
            outputs.append(("result", "Candidate measurements and provenance."))
        elif var == "frame":
            outputs.append(("frame", "Loaded candidate ionogram amplitude matrix."))
        elif var == "frames":
            outputs.append(("frames", "Loaded candidate ionogram frame sequence."))
        elif var == "output_file":
            outputs.append(("output_file", "Path to exported MAT file."))
        else:
            outputs.append((var, f"{var} return value from {name}."))
    if "iml_save_matrix" in body:
        outputs.append(("saved_matrix", "Side-effect matrix saved via IML bridge."))
    if "iml_save_plot" in body or "imagesc" in body:
        outputs.append(("figure", "Optional rendered figure artifact."))
    if not outputs:
        outputs.append(("result", "Method outputs and side effects."))
    return outputs


def infer_source_basis(name: str, body: str) -> str:
    if name.startswith("iml_test_"):
        return "Synthetic regression / teaching test (candidate-only)."
    if name.startswith("iml_example_"):
        return "Teaching walkthrough / project method catalog (candidate-only)."
    if "v11 base MATLAB measurement" in body:
        return "Engineering utility / project method catalog (candidate-only)."
    if "v11 built-in heuristic" in body:
        return "Development heuristic / project method catalog (candidate-only)."
    if "v11 temporal heuristic" in body:
        return "Development heuristic / project method catalog (candidate-only)."
    if "safety abstention" in body:
        return "Safety abstention / project method catalog (candidate-only)."
    if "Base validation" in body:
        return "Core validation utility / project method catalog."
    return "Engineering utility / project method catalog (candidate-only)."


def infer_limitations(name: str, legacy_lim: str) -> str:
    extra = ""
    lower = name.lower()
    if "ox" in lower:
        extra = " Cannot confirm O/X modes from Amp_all alone."
    if legacy_lim and extra and extra.strip().lower() not in legacy_lim.lower():
        return legacy_lim.rstrip(".") + "." + extra
    if extra and not legacy_lim:
        return extra.strip()
    return legacy_lim


def build_header_block(
    name: str,
    signature: str,
    body: str,
    legacy_comments: list[str],
) -> list[str]:
    en_text, lim_text, _legacy_source = extract_legacy_disclaimer(legacy_comments)
    purpose = humanize_purpose(name)
    inputs = infer_inputs(name, signature, body)
    outputs = infer_outputs(name, signature, body)
    source_basis = infer_source_basis(name, body)
    limitations = infer_limitations(name, lim_text)

    lines = [
        f"% {name.upper()}",
        "% Purpose:",
        f"%   {purpose}",
        "%",
        "% Inputs:",
    ]
    for key, desc in inputs:
        pad = " " * max(1, 16 - len(key))
        lines.append(f"%   {key}{pad}- {desc}")
    lines.extend(
        [
            "%",
            "% Outputs:",
        ]
    )
    for key, desc in outputs:
        pad = " " * max(1, 16 - len(key))
        lines.append(f"%   {key}{pad}- {desc}")
    lines.extend(
        [
            "%",
            "% Scientific status:",
            "%   Development heuristic. Not an independently validated physical",
            "%   measurement.",
            "%",
            "% Limitations:",
        ]
    )
    # Wrap limitations text
    lim_wrapped = limitations.replace("  ", " ").strip()
    if lim_wrapped and lim_wrapped[0].islower():
        lim_wrapped = lim_wrapped[0].upper() + lim_wrapped[1:]
    if "Cannot confirm O/X" in lim_wrapped:
        parts = lim_wrapped.split("Cannot confirm O/X modes from Amp_all alone.")
        main = parts[0].strip()
        if main:
            lines.append(f"%   {main}")
        lines.append("%   Cannot confirm O/X modes from Amp_all alone.")
    else:
        lines.append(f"%   {lim_wrapped}")
    lines.extend(
        [
            "%",
            "% Source basis:",
            f"%   {source_basis}",
        ]
    )
    return lines


SECTION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Validation", ("local_valid", "invalidFrame", "iml_validate_frame", "nargin == 0")),
    ("Normalization", ("double(frame", "double(frames", "prctile(X(:)", "(X - lo)")),
    ("Region selection", ("band_fraction =", "floor(band_fraction", "Provisional E/Es", "Provisional F display")),
    ("Measurement", ("score =", "[value, column]", "max(profile)", "persistence =", "change =")),
    ("Provenance", ("iml_register_feature", "iml_register_candidate_result", "iml_add_provenance")),
    ("Warnings", ("iml_add_warning",)),
]


def insert_section_comments(lines: list[str], complex_fn: bool) -> list[str]:
    if not complex_fn:
        return lines
    present = {ln.strip().lower() for ln in lines if ln.strip().startswith("% ---")}
    out: list[str] = []
    used: set[str] = set()
    for line in lines:
        if line.strip().startswith("%"):
            out.append(line)
            continue
        for section, keys in SECTION_RULES:
            label = f"% --- {section} ---"
            if section in used or label.lower() in present:
                continue
            if any(k in line for k in keys):
                out.append(INDENT + label)
                used.add(section)
                break
        out.append(line)
    return out


def is_complex_function(body_lines: list[str]) -> bool:
    code_lines = [ln for ln in body_lines if ln.strip() and not ln.lstrip().startswith("%")]
    return len(code_lines) >= 8


def strip_trailing_end(lines: list[str]) -> list[str]:
    """Remove a trailing function-closing `end` from a body chunk."""
    trimmed = list(lines)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    if trimmed and re.match(r"^\s*end\s*$", trimmed[-1]):
        trimmed.pop()
    return trimmed


def parse_file_sections(text: str) -> tuple[str, list[str], list[str], list[tuple[str, list[str]]]]:
    """Return (main_signature, legacy_comments, main_body_lines, [(helper_sig, helper_body)...])."""
    raw_lines = text.splitlines()
    func_indices: list[int] = []
    for i, ln in enumerate(raw_lines):
        if re.match(r"^function\b", ln.lstrip()) and ln == ln.lstrip():
            func_indices.append(i)
    if not func_indices:
        raise ValueError("No function declaration found")
    main_start = func_indices[0]
    main_sig = raw_lines[main_start].lstrip()

    # Split helpers: subsequent function lines at column 0
    helper_starts = [i for i in func_indices[1:] if raw_lines[i] == raw_lines[i].lstrip()]

    if helper_starts:
        main_end = helper_starts[0]
    else:
        main_end = len(raw_lines)

    main_chunk = raw_lines[main_start + 1 : main_end]
    legacy: list[str] = []
    body_raw: list[str] = []
    for ln in main_chunk:
        if not body_raw and (ln.lstrip().startswith("%") or not ln.strip()):
            legacy.append(ln.lstrip() if ln.lstrip().startswith("%") else ln)
        else:
            body_raw.append(ln)
    body_raw = strip_trailing_end(body_raw)

    helpers: list[tuple[str, list[str]]] = []
    for hi, hstart in enumerate(helper_starts):
        hend = helper_starts[hi + 1] if hi + 1 < len(helper_starts) else len(raw_lines)
        hsig = raw_lines[hstart].lstrip()
        hbody = strip_trailing_end(raw_lines[hstart + 1 : hend])
        helpers.append((hsig, hbody))

    return main_sig, legacy, body_raw, helpers


def adjust_block_depth(code: str, depth: int) -> int:
    for tok in re.findall(r"\b(if|for|while|switch|parfor|try|function|end)\b", code):
        if tok in ("if", "for", "while", "switch", "parfor", "try", "function"):
            depth += 1
        elif tok == "end":
            depth -= 1
    return depth


def is_multiline_control_start(code: str) -> bool:
    code = code.strip()
    if not re.match(r"^(if|for|while)\b", code):
        return False
    return adjust_block_depth(code, 0) > 0


def join_block_parts(parts: list[str]) -> str:
    if not parts:
        return ""
    out = parts[0]
    for code in parts[1:]:
        prev = out.rstrip()
        if re.match(r"^(elseif|else|end)\b", code):
            out += " " + code
        elif re.search(r"\belseif\s+[^,]+$", prev) and not re.match(r"^(else|elseif|end)\b", code):
            out += ", " + code
        elif prev.endswith(";"):
            out += " " + code
        else:
            out += "; " + code
    combined = out
    combined = re.sub(r"\belse\s+(?=[^\s,])", "else, ", combined, count=1)
    return combined


def normalize_multiline_control_block(block_lines: list[str]) -> str:
    parts: list[str] = []
    for ln in block_lines:
        code = strip_comments_from_line(ln).strip()
        if code:
            parts.append(code)
    return join_block_parts(parts)


def collect_multiline_control_block(code_lines: list[str], start: int) -> tuple[str, int]:
    block = [code_lines[start]]
    depth = adjust_block_depth(strip_comments_from_line(code_lines[start]).strip(), 0)
    i = start + 1
    while i < len(code_lines) and depth > 0:
        block.append(code_lines[i])
        code = strip_comments_from_line(code_lines[i]).strip()
        if code:
            depth = adjust_block_depth(code, depth)
        i += 1
    return normalize_multiline_control_block(block), i


def format_single_line(code: str, indent_level: int) -> list[str]:
    """Expand one logical line when safe; otherwise split simple semicolon chains."""
    code = code.strip()
    if not code:
        return []
    if code.endswith("..."):
        return [INDENT * indent_level + code]
    else_match = re.match(r"^else,\s*(.+);\s*end\s*$", code, re.IGNORECASE)
    if else_match:
        body = else_match.group(1).strip()
        return [
            INDENT * indent_level + "else",
            *format_single_line(body, indent_level + 1),
            INDENT * indent_level + "end",
        ]
    partial_if = re.match(r"^if\s+(.+),\s*(.+)$", code, re.IGNORECASE)
    if partial_if and not re.search(r"\b(end|else|elseif)\b", code, re.IGNORECASE):
        return [
            INDENT * indent_level + f"if {partial_if.group(1)}",
            *format_single_line(partial_if.group(2).strip(), indent_level + 1),
        ]
    if parse_if_comma_form(code):
        return expand_statement(code, indent_level)
    if parse_for_while_comma_form(code):
        return expand_statement(code, indent_level)
    parts = split_semicolon_statements(code)
    if len(parts) <= 1:
        return [INDENT * indent_level + finalize_statement(code)]
    out: list[str] = []
    for part in parts:
        out.extend(format_single_line(part, indent_level))
    return out


def format_body_lines(body_raw: list[str], complex_fn: bool) -> list[str]:
    logical = join_physical_lines(body_raw)
    code_lines: list[str] = []
    for ln in logical:
        stripped = ln.strip()
        if stripped.startswith("% IML_") or stripped.startswith("% EN:") or stripped.startswith("% RU:"):
            continue
        if re.match(r"^%\s*Limitations:", stripped, re.I):
            continue
        code_lines.append(ln)

    expanded: list[str] = []
    block_depth = 0
    for ln in code_lines:
        if not ln.strip():
            expanded.append("")
            continue
        if ln.lstrip().startswith("%"):
            expanded.append(INDENT * (1 + block_depth) + ln.lstrip())
            continue
        code = strip_comments_from_line(ln).strip()
        comment_idx = find_comment_start(ln)
        trailing_comment = ""
        if comment_idx is not None:
            trailing_comment = " " + ln[comment_idx:].rstrip()
        if not code:
            continue
        if re.match(r"^(elseif|else|end)\b", code, re.IGNORECASE):
            indent_level = 1 + max(0, block_depth - 1)
        else:
            indent_level = 1 + block_depth
        pieces = format_single_line(code, indent_level)
        if trailing_comment and pieces:
            pieces[-1] = pieces[-1] + trailing_comment
        expanded.extend(pieces)
        block_depth = max(0, adjust_block_depth(code, block_depth))

    expanded = insert_section_comments(expanded, complex_fn)
    return expanded


def format_helper_function(signature: str, body_raw: list[str]) -> list[str]:
    out = [signature]
    logical = join_physical_lines(body_raw)
    block_depth = 0
    for ln in logical:
        if not ln.strip():
            out.append("")
            continue
        code = strip_comments_from_line(ln).strip()
        comment_idx = find_comment_start(ln)
        trailing_comment = ""
        if comment_idx is not None:
            trailing_comment = " " + ln[comment_idx:].rstrip()
        if not code:
            continue
        if re.match(r"^(elseif|else|end)\b", code, re.IGNORECASE):
            indent_level = 1 + max(0, block_depth - 1)
        else:
            indent_level = 1 + block_depth
        pieces = format_single_line(code, indent_level)
        if trailing_comment and pieces:
            pieces[-1] = pieces[-1] + trailing_comment
        out.extend(pieces)
        block_depth = max(0, adjust_block_depth(code, block_depth))
    out.append("end")
    return out


def format_file(text: str) -> str:
    main_sig, legacy, body_raw, helpers = parse_file_sections(text)
    name = extract_function_name(main_sig)
    body_joined = "\n".join(body_raw)
    header = build_header_block(name, main_sig, body_joined, legacy)
    complex_fn = is_complex_function(body_raw) or bool(helpers)
    body_fmt = format_body_lines(body_raw, complex_fn)

    out_lines = [main_sig, *header, *body_fmt, "end"]
    for hsig, hbody in helpers:
        out_lines.append("")
        out_lines.extend(format_helper_function(hsig, hbody))

    result = "\n".join(out_lines)
    if not result.endswith("\n"):
        result += "\n"
    return result


def count_top_level_semicolons(line: str) -> int:
    """Return number of statement-separating semicolons on a non-comment code line."""
    if is_comment_line(line):
        return 0
    code = strip_comments_from_line(line)
    if not code.strip():
        return 0
    parts = split_semicolon_statements(code)
    return max(0, len(parts) - 1)


def has_required_header(text: str) -> list[str]:
    missing = [k for k in REQUIRED_HEADER_KEYS if k not in text]
    return missing


def find_main_function_end_line(lines: list[str]) -> int | None:
    depth = 0
    started = False
    for i, ln in enumerate(lines):
        code = strip_comments_from_line(ln).strip()
        if not code:
            continue
        if re.match(r"^function\b", code):
            if not started:
                started = True
                depth = 1
            continue
        for kw in ("if", "for", "while", "switch", "parfor", "try", "function"):
            if re.search(rf"\b{kw}\b", code):
                if kw == "function" and not started:
                    depth += 1
                elif kw != "function":
                    depth += len(re.findall(rf"\b{kw}\b", code))
        if re.search(r"\bend\b", code):
            depth -= len(re.findall(r"\bend\b", code))
        if started and depth <= 0:
            return i
    return None


def count_column_zero_functions(text: str) -> tuple[int, int, list[int]]:
    lines = text.splitlines()
    indices = [i for i, ln in enumerate(lines) if re.match(r"^function\b", ln)]
    if not indices:
        return 0, 0, indices
    main_end = find_main_function_end_line(lines)
    if main_end is None:
        return len(indices), 0, indices
    before = [i for i in indices if i <= main_end]
    after = [i for i in indices if i > main_end]
    # Main is first; extras before main_end are problematic
    extra_mains = max(0, len(before) - 1)
    return len(indices), extra_mains, indices


def format_all(root: Path = BUILTIN, dry_run: bool = False) -> int:
    count = 0
    for path in sorted(root.rglob("*.m")):
        original = path.read_text(encoding="utf-8", errors="replace")
        formatted = format_file(original)
        if formatted != original:
            count += 1
            if not dry_run:
                path.write_text(formatted, encoding="utf-8")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Format matlab_builtin .m files for readability.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing.")
    args = parser.parse_args()
    n = format_all(dry_run=args.dry_run)
    print(f"reformatted {n} matlab_builtin .m files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
