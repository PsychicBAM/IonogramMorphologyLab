"""Audit real frames for classification explainability (no hardcoded answers)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ionogram_morphology_lab.cache.frame_store import FrameStore
from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.features.temporal_context import temporal_conclusion
from ionogram_morphology_lab.importers.audit import audit_frame
from ionogram_morphology_lab.instrument_profiles.schema import load_profile, profiles_dir
from ionogram_morphology_lab.projects.time_mapping import format_hhmm, frame_to_minute, minute_to_frame
from ionogram_morphology_lab.rules.engine import RuleEngine, assess_interference
from ionogram_morphology_lab.scientific_outputs.result_schema import normalize_morphology
from ionogram_morphology_lab.segmentation.trace_interference import segment_frame
from ionogram_morphology_lab.ui.presenters import morphology_label

MATS = {
    "2014-09-25": Path(
        r"E:\ionog\conference_presentation\ion2014\maps201409sep\data\Am_all_2014-09-25.mat"
    ),
    "2014-10-15": Path(
        r"E:\ionog\conference_presentation\ion2014\maps201410oct\data\Am_all_2014-10-15.mat"
    ),
}
# Representative time windows (not hardcoded morphology answers)
WINDOWS = {
    "2014-09-25": list(range(7 * 60, 12 * 60, 30)),  # day survey sample
    "2014-10-15": list(range(20 * 60, 24 * 60, 10)),  # evening
}
OUT = Path("docs/CLASSIFICATION_VALIDATION_REPORT.md")
CACHE = Path("workspaces/_class_val_audit")


def _audit_frame(store: FrameStore, eng: RuleEngine, fid: int) -> dict:
    fr = store.get_frame(fid)
    seg = segment_frame(fr)
    feats = extract_features(fr, seg).values
    q = audit_frame(fr)
    res = eng.evaluate(feats, quality_status=q["status"])
    morph = normalize_morphology(res.candidate_morphology)
    inter = assess_interference(feats)
    # temporal neighbors ±1 when available
    masks = []
    for nfid in (fid - 1, fid, fid + 1):
        if 1 <= nfid <= store.n_frames():
            masks.append(segment_frame(store.get_frame(nfid)).trace_mask)
    temporal = temporal_conclusion(masks, single_frame_morphology=res.candidate_morphology)
    return {
        "frame": fid,
        "time": format_hhmm(frame_to_minute(fid)),
        "quality": q["status"],
        "trace_fraction": round(float(feats.get("trace_pixel_fraction", 0) or 0), 4),
        "h_width": round(float(feats.get("median_horizontal_width", 0) or 0), 3),
        "v_width": round(float(feats.get("median_vertical_width", 0) or 0), 3),
        "h_persist": round(float(feats.get("horizontal_broadening_persistence", 0) or 0), 3),
        "v_persist": round(float(feats.get("vertical_broadening_persistence", 0) or 0), 3),
        "freq_abs": float(feats.get("frequency_evidence_absolute", 0) or 0),
        "range_abs": float(feats.get("range_evidence_absolute", 0) or 0),
        "colocated": round(float(feats.get("colocated_spread_fraction", 0) or 0), 3),
        "interference_level": inter["level"],
        "inter_dom": round(inter["interference_dominance"], 3),
        "stripe_den": round(inter["vertical_stripe_density"], 3),
        "full_h_stripes": inter["full_height_stripe_count"],
        "rules_fired": list(res.activated_rules),
        "rules_rejected": list(res.contradicting_rules),
        "near_threshold": list(res.near_threshold_rules),
        "disagreement": list(res.disagreement_flags),
        "canonical": morph,
        "display_ru": morphology_label(morph, "ru"),
        "display_en": morphology_label(morph, "en"),
        "status": res.confidence_status,
        "abstention": res.abstention_reason,
        "temporal_note": temporal.get("temporal_note"),
        "review_state": "automatic candidate; visual owner review pending",
    }


def main() -> None:
    prof = load_profile(profiles_dir() / "kfu_cyclone_2013_2014.yaml").to_dict()
    eng = RuleEngine()
    all_rows: dict[str, list] = {}
    counts_all: dict[str, int] = {}
    r005_suppress_old_proxy = 0
    assessable_with_inter = 0

    for date, mat in MATS.items():
        if not mat.exists():
            print(f"SKIP missing {mat}")
            continue
        store = FrameStore(mat, prof, cache_root=CACHE / date)
        store.ensure_ready()
        rows = []
        for minute in WINDOWS[date]:
            fid = minute_to_frame(minute)
            if fid < 1 or fid > store.n_frames():
                continue
            row = _audit_frame(store, eng, fid)
            rows.append(row)
            counts_all[row["canonical"]] = counts_all.get(row["canonical"], 0) + 1
            if row["interference_level"] in ("significant", "dominant") and row["canonical"] not in (
                "not_assessable",
                "interference_dominated",
            ):
                assessable_with_inter += 1
            # Proxy: previously R005+moderate inter often forced interference_dominated
            if row["inter_dom"] < 0.55 and row["stripe_den"] >= 0.2 and row["canonical"] != "interference_dominated":
                r005_suppress_old_proxy += 1
        all_rows[date] = rows

    lines = [
        "# Classification Validation Report",
        "",
        "**Scientific status:** candidate / development-calibrated — **NOT** independently validated.",
        "**Acceptance:** FAIL for scientific PASS (insufficient owner-reviewed / expert-confirmed labels).",
        "",
        "## Active methods (default pipeline)",
        "",
        "| Component | Status |",
        "|---|---|",
        "| Preprocess / audit / segment / features | active |",
        "| RuleEngine (RULE_PACK_IML1) | active, development-calibrated / engineering_default |",
        "| Reference atlas | metadata-only similarity |",
        "| MATLAB methods | optional, off by default |",
        "| Development ML / ensemble | optional, off by default |",
        "| Multi-frame temporal conclusion | optional when neighbor masks supplied |",
        "",
        "## Labelled-frame count by category",
        "",
        "| Category | Expert-confirmed | Owner-reviewed | Automatic-only (this audit) |",
        "|---|---:|---:|---:|",
    ]
    for cat in (
        "clean",
        "diffuse_unspecified",
        "frequency_spread",
        "range_spread",
        "mixed_spread",
        "interference_dominated",
        "not_assessable",
        "indeterminate",
    ):
        lines.append(f"| `{cat}` | 0 | 0 | {counts_all.get(cat, 0)} |")
    lines.extend(
        [
            "",
            "**Verdict:** insufficient labelled examples for per-class precision/recall claims.",
            "",
            "## R005 changes",
            "",
            "- R005 still fires as interference *evidence*.",
            "- Morphology is **not** replaced by `interference_dominated` when a usable trace remains.",
            "- Morphology becomes `not_assessable` only when interference **prevents assessment**.",
            "- Interference level is recorded separately (`none|present|significant|dominant|prevents_assessment`).",
            f"- Frames in this audit with significant/dominant interference but assessable morphology: **{assessable_with_inter}**.",
            f"- Frames that would previously be R005-suppressed at moderate dominance but now keep morphology: **{r005_suppress_old_proxy}** (proxy count).",
            "",
            "## Metrics",
            "",
            "- Confusion matrix: **not reported** — insufficient labelled examples.",
            "- Per-class precision/recall: **insufficient labelled examples**.",
            "- Calibration status: **uncalibrated**.",
            "- Abstention / uncertain rate: see automatic tables below.",
            "",
            "## Automatic candidate counts",
            "",
            f"`{json.dumps(counts_all, ensure_ascii=False)}`",
            "",
        ]
    )
    for date, rows in all_rows.items():
        lines.extend(
            [
                f"## Audit table — {date}",
                "",
                "| Frame | Time | H | V | Inter level | Rules | Near-thr | Canonical | Display (RU) | Temporal | Review |",
                "|------:|:----:|--:|--:|:-----------|:------|:---------|:----------|:-------------|:---------|:-------|",
            ]
        )
        for r in rows:
            lines.append(
                f"| {r['frame']} | {r['time']} | {r['h_width']} | {r['v_width']} | "
                f"`{r['interference_level']}` | `{','.join(r['rules_fired']) or '—'}` | "
                f"`{','.join(r['near_threshold']) or '—'}` | `{r['canonical']}` | "
                f"{r['display_ru']} | `{r['temporal_note']}` | {r['review_state']} |"
            )
        lines.append("")
        # Highlight disagreement-prone rows
        focus = [
            r
            for r in rows
            if r["h_width"] >= 8 or r["v_width"] >= 8 or r["interference_level"] != "none"
        ]
        lines.append(f"### Focus rows ({date})")
        lines.append("")
        for r in focus[:40]:
            lines.append(
                f"- **f{r['frame']} {r['time']}** → `{r['canonical']}` "
                f"(H={r['h_width']}, V={r['v_width']}, inter={r['interference_level']}, "
                f"flags={r['disagreement'][:4]})"
            )
        lines.append("")

    lines.extend(
        [
            "## Remaining unsupported / incomplete",
            "",
            "- No expert-confirmed gold labels in-repo.",
            "- Reference atlas has no redistributed comparison images.",
            "- Temporal onset/termination are heuristic mask-overlap notes only.",
            "- Do not claim scientific PASS until owner-reviewed multi-class labels exist and are evaluated on a held-out date split.",
            "",
            "Machine dump: `workspaces/_class_val_audit/audit.json`",
            "",
        ]
    )
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "audit.json").write_text(
        json.dumps(all_rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {OUT} counts={counts_all}")


if __name__ == "__main__":
    main()
