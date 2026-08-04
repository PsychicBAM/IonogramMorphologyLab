"""Audit Am_all_2014-10-15.mat frames 20:00–23:59 at 10-minute intervals."""

from __future__ import annotations

import json
from pathlib import Path

from ionogram_morphology_lab.cache.frame_store import FrameStore
from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.importers.audit import audit_frame
from ionogram_morphology_lab.instrument_profiles.schema import load_profile, profiles_dir
from ionogram_morphology_lab.rules.engine import RuleEngine
from ionogram_morphology_lab.scientific_outputs.result_schema import normalize_morphology
from ionogram_morphology_lab.segmentation.trace_interference import segment_frame
from ionogram_morphology_lab.ui.presenters import morphology_label
from ionogram_morphology_lab.projects.time_mapping import format_hhmm, frame_to_minute, minute_to_frame

MAT = Path(r"E:\ionog\conference_presentation\ion2014\maps201410oct\data\Am_all_2014-10-15.mat")
OUT_MD = Path("docs/MORPHOLOGY_AUDIT_2014_10_15.md")
CACHE = Path("workspaces/_morph_audit_2014_10_15")
THUMB_DIR = CACHE / "thumbs"


def main() -> None:
    if not MAT.exists():
        raise SystemExit(f"MAT not found: {MAT}")
    prof = load_profile(profiles_dir() / "kfu_cyclone_2013_2014.yaml").to_dict()
    store = FrameStore(MAT, prof, cache_root=CACHE)
    store.ensure_ready()
    eng = RuleEngine()
    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    # 20:00–23:59 every 10 minutes → minutes 1200..1439 step 10
    minutes = list(range(20 * 60, 24 * 60, 10))
    rows = []
    counts: dict[str, int] = {}
    for minute in minutes:
        fid = minute_to_frame(minute)
        fr = store.get_frame(fid)
        seg = segment_frame(fr)
        feats = extract_features(fr, seg).values
        q = audit_frame(fr)
        res = eng.evaluate(feats, quality_status=q["status"])
        morph = normalize_morphology(res.candidate_morphology)
        counts[morph] = counts.get(morph, 0) + 1
        hhmm = format_hhmm(frame_to_minute(fid))
        # lightweight thumbnail note (path only; visual review pending)
        thumb = THUMB_DIR / f"f{fid:04d}_{hhmm.replace(':', '')}.npy"
        # store shape marker only for audit table (avoid heavy PNG dep here)
        thumb.write_bytes(b"")
        note = "visual owner review pending"
        if morph == "clean" and max(
            float(feats.get("median_horizontal_width", 0) or 0),
            float(feats.get("median_vertical_width", 0) or 0),
        ) >= 5.0:
            note = "auto clean but width≥5 — review for diffuse_unspecified"
        elif morph == "diffuse_unspecified":
            note = "automatic candidate: diffuse structure undetermined"
        rows.append(
            {
                "frame": fid,
                "time": hhmm,
                "thumb": str(thumb.relative_to(CACHE)),
                "trace_present": float(feats.get("trace_pixel_fraction", 0) or 0) >= 0.005,
                "diffuseness": round(
                    max(
                        float(feats.get("median_horizontal_width", 0) or 0),
                        float(feats.get("median_vertical_width", 0) or 0),
                    ),
                    3,
                ),
                "h_width": round(float(feats.get("median_horizontal_width", 0) or 0), 3),
                "v_width": round(float(feats.get("median_vertical_width", 0) or 0), 3),
                "h_persist": round(float(feats.get("horizontal_broadening_persistence", 0) or 0), 3),
                "v_persist": round(float(feats.get("vertical_broadening_persistence", 0) or 0), 3),
                "interference": round(float(feats.get("interference_dominance", 0) or 0), 3),
                "branches": float(feats.get("parallel_branch_count", 0) or 0),
                "rules_fired": list(res.activated_rules),
                "rules_rejected": list(res.contradicting_rules),
                "canonical": morph,
                "display_ru": morphology_label(morph, "ru"),
                "display_en": morphology_label(morph, "en"),
                "status": res.confidence_status,
                "abstention": res.abstention_reason,
                "expert_note": note,
                "review_state": "automatic candidate; visual owner review pending",
            }
        )

    changed_from_clean_proxy = sum(1 for r in rows if r["canonical"] == "diffuse_unspecified")
    lines = [
        "# Morphology audit — Am_all_2014-10-15 (20:00–23:59, 10 min)",
        "",
        "**Status:** automatic candidate · visual owner review pending · expert confirmed only when actually confirmed.",
        "",
        f"- Source MAT: `ion2014/maps201410oct/data/Am_all_2014-10-15.mat` (workspace sibling dataset; not packaged in the app tree)",
        f"- Profile: `kfu_cyclone_2013_2014`",
        f"- Frames audited: {len(rows)}",
        f"- Canonical morphology counts: `{json.dumps(counts, ensure_ascii=False)}`",
        f"- Frames classified `diffuse_unspecified`: {changed_from_clean_proxy}",
        "",
        "## Decision notes",
        "",
        "- Classifications are **automatic candidates** from the RuleEngine + feature vector.",
        "- No frame IDs were hardcoded.",
        "- `clean` / «Явное рассеяние не обнаружено» means assessable with no supported spread "
        "and no residual diffuseness above the uncertainty floor — not a proof of physical absence.",
        "- `diffuse_unspecified` is used when broadening/diffuseness is visible but evidence is "
        "insufficient for frequency / range / mixed.",
        "",
        "## Audit table",
        "",
        "| Frame | Time | Trace | Diffuseness | H width | V width | Interf. | Branches | Rules fired | Canonical | Display (RU) | Expert note | Review |",
        "|------:|:----:|:-----:|------------:|--------:|--------:|--------:|---------:|:------------|:----------|:-------------|:------------|:-------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['frame']} | {r['time']} | {'yes' if r['trace_present'] else 'no'} | "
            f"{r['diffuseness']} | {r['h_width']} | {r['v_width']} | {r['interference']} | "
            f"{r['branches']} | `{','.join(r['rules_fired']) or '—'}` | `{r['canonical']}` | "
            f"{r['display_ru']} | {r['expert_note']} | {r['review_state']} |"
        )
    lines.extend(
        [
            "",
            "## Frames with elevated width (visual focus)",
            "",
        ]
    )
    focus = [r for r in rows if r["diffuseness"] >= 5.0 or r["canonical"] != "clean"]
    if not focus:
        lines.append("_No frames exceeded the diffuseness focus threshold in this window._")
    else:
        for r in focus:
            lines.append(
                f"- **f{r['frame']} {r['time']}** → `{r['canonical']}` "
                f"(H={r['h_width']}, V={r['v_width']}, persist H/V={r['h_persist']}/{r['v_persist']}, "
                f"interf={r['interference']}) — {r['expert_note']}"
            )
    lines.extend(
        [
            "",
            "## Machine-readable dump",
            "",
            "See `workspaces/_morph_audit_2014_10_15/audit_rows.json`.",
            "",
        ]
    )
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (CACHE / "audit_rows.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_MD} rows={len(rows)} counts={counts}")


if __name__ == "__main__":
    main()
