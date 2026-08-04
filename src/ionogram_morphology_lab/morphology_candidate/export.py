"""Candidate result exports (frame JSON, sequence CSV, review JSON, markdown summary)."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


def export_frame_json(result: dict[str, Any] | Any, path: Path | str) -> Path:
    p = Path(path)
    payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return p


def export_sequence_csv(rows: Iterable[dict[str, Any]], path: Path | str) -> Path:
    p = Path(path)
    fieldnames = [
        "source_sha256",
        "frame_index",
        "interpreted_time",
        "candidate",
        "assessability",
        "evidence_strength",
        "h_supported",
        "h_strength",
        "v_supported",
        "v_strength",
        "interference_level",
        "temporal_support",
        "abstained",
        "abstention_reasons",
        "ruleset_version",
        "ruleset_hash",
        "review_status",
        "cache_status",
    ]
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return p


def export_review_json(review: dict[str, Any], path: Path | str) -> Path:
    p = Path(path)
    p.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def export_markdown_summary(
    results: list[dict[str, Any]],
    path: Path | str,
    *,
    reviewed_hashes: set[str] | None = None,
) -> Path:
    reviewed_hashes = reviewed_hashes or set()
    counts = Counter(r.get("candidate") for r in results)
    assess = Counter(r.get("assessability") for r in results)
    inter = Counter((r.get("interference") or {}).get("level") if isinstance(r.get("interference"), dict) else r.get("interference_level") for r in results)
    n_reviewed = sum(1 for r in results if r.get("result_hash") in reviewed_hashes)
    lines = [
        "# Morphology candidate shadow summary",
        "",
        "**Scientific non-claims:** These counts are provisional shadow-mode candidates,",
        "not confirmed expert classifications. No accuracy, sensitivity, specificity, or F1",
        "is claimed. Geometry reviews are not morphology labels.",
        "",
        "## Counts by candidate",
    ]
    for k, v in sorted(counts.items(), key=lambda x: str(x[0])):
        lines.append(f"- `{k}`: {v}")
    lines += ["", "## Assessability"]
    for k, v in sorted(assess.items(), key=lambda x: str(x[0])):
        lines.append(f"- `{k}`: {v}")
    lines += ["", "## Interference"]
    for k, v in sorted(inter.items(), key=lambda x: str(x[0])):
        lines.append(f"- `{k}`: {v}")
    lines += [
        "",
        "## Review status",
        f"- reviewed: {n_reviewed}",
        f"- unreviewed: {len(results) - n_reviewed}",
        "",
        "Do not call unreviewed candidates “labels”.",
    ]
    p = Path(path)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p
