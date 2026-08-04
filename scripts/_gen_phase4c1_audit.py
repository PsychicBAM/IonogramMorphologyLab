"""One-shot generator for PHASE4C1_FEATURE_INPUT_AUDIT.md."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
reg = yaml.safe_load((ROOT / "knowledge_base/FEATURE_REGISTRY_V2.yaml").read_text(encoding="utf-8"))
feats = {f["feature_id"]: f for f in reg["features"]}

USED = {
    "v2_quality_status": ("trace-quality", True, "Primary quality gate before morphology rules."),
    "v2_trace_pixel_fraction": ("trace-quality", True, "Trace presence / blank-frame abstention."),
    "v2_accepted_support_above_floor_fraction": ("trace-quality", True, "Non-floor accepted support gate."),
    "v2_interference_level": ("interference", True, "Separate interference axis; blocking → not_assessable."),
    "v2_horizontal_width_elevated_fraction": ("H", True, "Primary H coverage evidence (not single max)."),
    "v2_horizontal_contiguous_broadening_length": ("H", True, "Persistence/contiguity for H support."),
    "v2_median_local_horizontal_width_bins": ("H", True, "Robust H width central tendency."),
    "v2_horizontal_axis_width_applicable_fraction": ("H", True, "Fraction of positions where H axis is applicable."),
    "v2_vertical_width_elevated_fraction": ("V", True, "Primary V coverage evidence."),
    "v2_vertical_contiguous_broadening_length": ("V", True, "Persistence/contiguity for V support."),
    "v2_median_local_vertical_width_bins": ("V", True, "Robust V width central tendency."),
    "v2_vertical_axis_width_applicable_fraction": ("V", True, "Fraction of positions where V axis is applicable."),
    "v2_coexistence_score": ("mixed", True, "Independent coexistence score for mixed."),
    "v2_coexistence_fraction": ("mixed", True, "Spatial coexistence fraction for mixed."),
    "v2_floor_clutter_burden": ("interference", True, "Reject V-as-range when floor dominates."),
    "v2_full_height_stripe_burden": ("interference", True, "Reject V-as-range when full-height stripes dominate."),
    "v2_oversegmentation_suspected": ("ambiguity", True, "Oversegmentation gate → abstention."),
    "v2_multiple_reflection_possibility": ("ambiguity", True, "Suppress automatic frequency candidate."),
    "v2_fragmentation_score": ("ambiguity", True, "Severe fragmentation → abstention."),
    "v2_consolidated_branch_count": ("trace-quality", True, "Branch context / oversegmentation signal."),
    "v2_branch_count": ("trace-quality", False, "Secondary; prefer consolidated count."),
    "v2_ox_ambiguity_possibility": ("ambiguity", True, "Ambiguity warning flag."),
    "v2_vertical_stripe_count": ("interference", True, "Vertical interference flagging."),
    "v2_interference_trace_overlap": ("interference", True, "Horizontal/overlap interference context."),
    "v2_usable_trace_fraction_outside_interference": ("trace-quality", False, "Supporting quality context; not sole gate."),
    "v2_trace_continuity": ("trace-quality", False, "Supporting continuity context."),
    "v2_width_aggregate_branches_agree": ("ambiguity", False, "Optional branch-consistency hint."),
    "v2_local_horizontal_width_max": ("H", False, "Rejected as sole rule input (single max)."),
    "v2_local_vertical_width_max": ("V", False, "Rejected as sole rule input (single max)."),
    "v2_temporal_width_persistence": ("temporal", False, "Future temporal layer; 0.1.0 uses TemporalContext object."),
    "v2_temporal_branch_persistence": ("temporal", False, "Eligible; not sole decision input in 0.1.0."),
    "v2_temporal_interference_persistence": ("temporal", False, "Eligible; interference remains separate axis."),
    "v2_interference_stripe_density": ("interference", False, "Supporting; burden/level preferred."),
    "v2_fixed_horizontal_axis_width_bins": ("H", False, "Aggregate; elevated fraction preferred for coverage."),
    "v2_fixed_vertical_axis_width_bins": ("V", False, "Aggregate; elevated fraction preferred."),
    "v2_true_slope_compensated_horizontal_residual_bins": ("H", False, "Future refinement; not required in 0.1.0 seed."),
    "v2_width_balance_ratio": ("mixed", False, "Not sufficient for mixed without coexistence."),
}


def mark(role: str, key: str) -> str:
    return "Y" if role == key else ""


lines = [
    "# PHASE4C1 Feature Input Audit",
    "",
    "Geometry Feature Pipeline version: **iml2-0.2.0** (93 registered features).",
    "Morphology candidate engine: **iml-morph-candidate-0.1.0** (shadow-only).",
    "",
    "## Method",
    "",
    "- Inventory uses canonical IDs from `knowledge_base/FEATURE_REGISTRY_V2.yaml`.",
    "- Candidate engine consumes registry IDs / typed V2 serializable results only.",
    "- No UI-label parsing, no direct pixel reads inside the candidate engine,",
    "  no hidden duplicate measurements bypassing Feature Registry V2.",
    "",
    "## Candidate-relevant features",
    "",
    "| feature ID | name EN | name RU | unit | expected range | missing policy | level | H | V | quality | interference | ambiguity | temporal/mixed | suitable | why |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
]

for fid, (role, suitable, why) in sorted(USED.items()):
    f = feats[fid]
    er = f.get("expected_range")
    er_s = f"{er[0]}..{er[1]}" if isinstance(er, list) and len(er) == 2 else str(er)
    lines.append(
        f"| `{fid}` | {f.get('name_en','')} | {f.get('name_ru','')} | {f.get('unit','')} | {er_s} | "
        f"{f.get('missing_value_policy','')} | frame | "
        f"{mark(role,'H')} | {mark(role,'V')} | {mark(role,'trace-quality')} | {mark(role,'interference')} | "
        f"{mark(role,'ambiguity')} | {mark(role,'temporal') or mark(role,'mixed')} | "
        f"{'yes' if suitable else 'no (rejected/deferred)'} | {why} |"
    )

unused = [f for f in reg["features"] if f["feature_id"] not in USED]
lines += [
    "",
    "## Features not used for candidate rules (registry remainder)",
    "",
    "Remaining registered features are geometry/diagnostic only for ruleset 0.1.0.",
    "",
]
for f in unused:
    lines.append(f"- `{f['feature_id']}`")

lines += [
    "",
    "## Explicit rejections",
    "",
    "- Do not use `v2_local_*_width_max` alone (single extremum).",
    "- Do not encode `v2_interference_level` as frequency/range/mixed.",
    "- Do not treat high `v2_branch_count` as mixed.",
    "- Do not treat geometry review JSON as morphology ground truth.",
    "",
    "## Scientific non-claims",
    "",
    "- This audit does not validate classification accuracy.",
    "- Eight geometry reviews are not morphology labels.",
]

out = ROOT / "docs" / "PHASE4C1_FEATURE_INPUT_AUDIT.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out)


if __name__ == "__main__":
    pass
