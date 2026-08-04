"""Rebuild eight-frame shadow audit from exact geometry-review JSON identities."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.morphology_candidate.engine import evaluate_morphology_candidate
from ionogram_morphology_lab.morphology_candidate.from_v2 import build_candidate_input_from_v2
from ionogram_morphology_lab.morphology_candidate.compatibility import classify_v2_for_candidate
from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset

REVIEW_DIR = (
    ROOT
    / "workspaces"
    / "IML_Project_65064ddf202b"
    / "feature_diagnostics"
    / "geometry_reviews"
)
DIAG_ROOT = ROOT / "docs" / "_phase4b3_iml2-0.2.0_diagnostics"
SHA_TO_MAT = {
    "a19fd113f61160a55fd761d89c9dd448932cc4b4b84aaeabd68ff74d680f6473": "Am_all_2014-10-15",
    "a1185a173fdb429b4358e1f3d569170652462722ef20adc17bac2e1e4c77e4f6": "Am_all_2014-09-25",
    "873ba4729e6f1df8d059126efedbfc247c7960d7687e907740c24872c5e541f8": None,  # unresolved export
}


def load_reviews() -> list[dict]:
    rows = []
    if not REVIEW_DIR.is_dir():
        return rows
    for p in sorted(REVIEW_DIR.glob("review_f*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        rows.append(
            {
                "review_file": p.name,
                "source_sha256": str(data.get("source_sha256") or ""),
                "frame_index": int(data.get("frame_index") or 0),
                "diagnostics_cache_id": str(data.get("diagnostics_cache_id") or ""),
                "feature_version": str(data.get("feature_version") or ""),
                "status": str(data.get("status") or ""),
            }
        )
    return rows


def find_v2_export(source_sha: str, frame: int) -> Path | None:
    mat = SHA_TO_MAT.get(source_sha)
    if not mat:
        # search all exports for matching sha+frame
        for path in DIAG_ROOT.glob("*/frame_*/features.json"):
            try:
                ser = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if str(ser.get("source_mat_sha256")) == source_sha and int(ser.get("frame_index") or -1) == frame:
                return path
        return None
    path = DIAG_ROOT / mat / f"frame_{frame:04d}" / "features.json"
    return path if path.is_file() else None


def main() -> None:
    reviews = load_reviews()
    rs = load_ruleset()
    rows = []
    for rev in reviews:
        path = find_v2_export(rev["source_sha256"], rev["frame_index"])
        base = {
            **rev,
            "geometry_review_exists": True,
            "geometry_review_is_morphology_gt": False,
        }
        if path is None:
            rows.append(
                {
                    **base,
                    "audit_status": "source_identity_unresolved_or_export_missing",
                    "candidate": None,
                    "note": "Corresponding V2 export not located; audit not run for this review.",
                }
            )
            continue
        ser = json.loads(path.read_text(encoding="utf-8"))
        # Prefer review identity over filename inference
        if str(ser.get("source_mat_sha256") or "") != rev["source_sha256"]:
            rows.append(
                {
                    **base,
                    "audit_status": "source_identity_mismatch_with_export",
                    "export_path": str(path.relative_to(ROOT)),
                    "candidate": None,
                }
            )
            continue
        compat = classify_v2_for_candidate(ser, ruleset=rs)
        if not compat.get("can_evaluate"):
            rows.append(
                {
                    **base,
                    "audit_status": "v2_incompatible_or_incomplete",
                    "compatibility": compat.get("state"),
                    "export_path": str(path.relative_to(ROOT)),
                    "candidate": None,
                    "note": "Not evaluated as a normal morphology result.",
                }
            )
            continue
        t0 = time.perf_counter()
        inp = build_candidate_input_from_v2(
            ser,
            diagnostics_cache_id=rev["diagnostics_cache_id"],
            required_feature_ids=list(rs.get("required_feature_ids") or []),
        )
        result = evaluate_morphology_candidate(inp, ruleset=rs)
        ms = (time.perf_counter() - t0) * 1000
        rows.append(
            {
                **base,
                "audit_status": "evaluated",
                "export_path": str(path.relative_to(ROOT)),
                "candidate": result.candidate,
                "assessability": result.assessability,
                "evidence_strength": result.evidence_strength,
                "interference": result.interference.level,
                "abstained": result.abstained,
                "abstention_reasons": list(result.abstention_reasons),
                "ledger_entries": len(result.evidence_ledger),
                "elapsed_ms": round(ms, 2),
                "result_hash": result.result_hash,
            }
        )

    lines = [
        "# PHASE4C1 Eight-Frame Shadow Audit (identity-corrected)",
        "",
        "**Smoke audit only.** Identities are taken from exact geometry-review JSON files",
        f"under `{REVIEW_DIR.relative_to(ROOT).as_posix()}`.",
        "Geometry reviews are **not** morphology ground truth. Do **not** write “8/8 correct”.",
        "",
        f"Geometry-review JSON count: **{len(reviews)}**",
        "",
        "| review_file | source_sha (12) | frame | diagnostics_cache_id (12) | audit_status | candidate | assessability | interference | abstention |",
        "|---|---|---:|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['review_file']}` | `{r['source_sha256'][:12]}` | {r['frame_index']} | "
            f"`{r['diagnostics_cache_id'][:12]}` | {r.get('audit_status')} | "
            f"`{r.get('candidate')}` | {r.get('assessability', '—')} | {r.get('interference', '—')} | "
            f"{';'.join(r.get('abstention_reasons') or []) or '—'} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Empty / no-trace / incomplete-legacy frames may be `not_assessable` or unevaluated.",
        "- That is not a contradiction with geometry review acceptance.",
        "- No accuracy / sensitivity / specificity / F1 claimed.",
        "",
        "## Machine-readable",
        "",
        "```json",
        json.dumps(rows, indent=2, ensure_ascii=False),
        "```",
    ]
    out = ROOT / "docs" / "PHASE4C1_EIGHT_FRAME_SHADOW_AUDIT.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", out, "reviews=", len(reviews), "rows=", len(rows))


if __name__ == "__main__":
    main()
