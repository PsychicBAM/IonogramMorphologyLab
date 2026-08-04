"""Explain why diffuse_unspecified was chosen instead of frequency/range/mixed."""

from __future__ import annotations

from typing import Any

# Display-only mirrors of RuleEngine gates (do not change engine thresholds here).
FREQ_WIDTH_THR = 6.0
FREQ_PERSIST_THR = 0.35
RANGE_WIDTH_THR = 6.0
RANGE_PERSIST_THR = 0.35
MIXED_COLOCATED_THR = 0.20
MIXED_MIN_WIDTH = 8.0
MIXED_BALANCE_RATIO = 1.85


def explain_diffuse_unspecified(record: dict[str, Any], lang: str = "en") -> str:
    feats = record.get("measured_features") or {}
    inter = (
        record.get("interference_status")
        or (record.get("rule_result") or {}).get("interference_assessment")
        or "none"
    )
    near = record.get("near_threshold_rules") or []
    flags = record.get("disagreement_flags") or []
    abs_reason = record.get("abstention_reason") or ""

    def f(key: str, default: float = 0.0) -> float:
        try:
            return float(feats.get(key, default) or default)
        except (TypeError, ValueError):
            return default

    med_h = f("median_horizontal_width")
    med_v = f("median_vertical_width")
    h_persist = f("horizontal_broadening_persistence")
    v_persist = f("vertical_broadening_persistence")
    freq_passed = f("frequency_evidence_passed")
    range_passed = f("range_evidence_passed")
    freq_abs = f("frequency_evidence_absolute")
    range_abs = f("range_evidence_absolute")
    colocated = f("colocated_spread_fraction")
    axis_ratio = max(med_h, med_v) / max(min(med_h, med_v), 1e-6)

    morph = str(
        (record.get("scientific_axes") or {}).get("morphology")
        or record.get("morphology")
        or record.get("candidate_morphology")
        or ""
    )
    if morph not in ("diffuse_unspecified", "diffuse"):
        return ""

    if lang == "ru":
        lines = [
            "Диффузная структура обнаружена, но тип не определён, потому что:",
            f"— признак частотного уширения: ширина={med_h:.2f} (порог {FREQ_WIDTH_THR}), "
            f"персистентность={h_persist:.2f} (порог {FREQ_PERSIST_THR}), "
            f"частотный gate={'пройден' if freq_passed >= 1 else 'не пройден'}, "
            f"абсолютный признак={'да' if freq_abs >= 1 else 'нет'};",
            f"— признак высотного уширения: ширина={med_v:.2f} (порог {RANGE_WIDTH_THR}), "
            f"персистентность={v_persist:.2f} (порог {RANGE_PERSIST_THR}), "
            f"высотный gate={'пройден' if range_passed >= 1 else 'не пройден'}, "
            f"абсолютный признак={'да' if range_abs >= 1 else 'нет'};",
            f"— смешанное рассеяние требует одновременных независимых осей и со-локализации "
            f"(доля со-локализации={colocated:.2f}, порог {MIXED_COLOCATED_THR}; "
            f"минимум ширины {MIXED_MIN_WIDTH}; баланс осей ratio={axis_ratio:.2f}, "
            f"допуск ≤{MIXED_BALANCE_RATIO});",
            f"— статус помех: {inter};",
        ]
        if near:
            lines.append(f"— правила почти у порога: {', '.join(map(str, near))};")
        if abs_reason:
            lines.append(f"— ближайшая причина неопределённости: {abs_reason};")
        if flags:
            lines.append(f"— флаги разногласий: {', '.join(map(str, flags[:8]))}.")
        lines.append(
            "Это автоматический кандидат, а не подтверждённая классификация."
        )
        return "\n".join(lines)

    lines = [
        "Diffuse structure is visible, but the spread type is undetermined because:",
        f"— frequency broadening evidence: width={med_h:.2f} (threshold {FREQ_WIDTH_THR}), "
        f"persistence={h_persist:.2f} (threshold {FREQ_PERSIST_THR}), "
        f"frequency gate={'passed' if freq_passed >= 1 else 'not passed'}, "
        f"absolute evidence={'yes' if freq_abs >= 1 else 'no'};",
        f"— range broadening evidence: width={med_v:.2f} (threshold {RANGE_WIDTH_THR}), "
        f"persistence={v_persist:.2f} (threshold {RANGE_PERSIST_THR}), "
        f"range gate={'passed' if range_passed >= 1 else 'not passed'}, "
        f"absolute evidence={'yes' if range_abs >= 1 else 'no'};",
        f"— mixed spread requires independent axes and coexistence "
        f"(colocated fraction={colocated:.2f}, threshold {MIXED_COLOCATED_THR}; "
        f"min width {MIXED_MIN_WIDTH}; axis balance ratio={axis_ratio:.2f}, "
        f"limit ≤{MIXED_BALANCE_RATIO});",
        f"— interference status: {inter};",
    ]
    if near:
        lines.append(f"— near-threshold rules: {', '.join(map(str, near))};")
    if abs_reason:
        lines.append(f"— nearest uncertainty reason: {abs_reason};")
    if flags:
        lines.append(f"— disagreement flags: {', '.join(map(str, flags[:8]))}.")
    lines.append("This is an automatic candidate, not a confirmed classification.")
    return "\n".join(lines)
