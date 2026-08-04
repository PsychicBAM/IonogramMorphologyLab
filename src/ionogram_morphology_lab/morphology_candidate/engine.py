"""Deterministic shadow morphology candidate engine (Phase 4C.1)."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from ionogram_morphology_lab.morphology_candidate.labels import (
    candidate_label,
    disclaimer,
    strength_label,
)
from ionogram_morphology_lab.morphology_candidate.presentation import (
    abstention_label,
    format_abstention_sentence,
    interference_label,
)
from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset, ruleset_hash, threshold
from ionogram_morphology_lab.morphology_candidate.types import (
    ALLOWED_CANDIDATES,
    AxisEvidenceSummary,
    CANDIDATE_ENGINE_VERSION,
    EvidenceLedgerEntry,
    MorphologyCandidateInput,
    MorphologyCandidateResult,
)

# Re-export for callers
__all__ = ["CANDIDATE_ENGINE_VERSION", "evaluate_morphology_candidate"]


def _num(inp: MorphologyCandidateInput, fid: str) -> float | None:
    ref = inp.features.get(fid)
    if ref is None or ref.missing or not ref.valid or ref.value is None:
        return None
    try:
        return float(ref.value)
    except (TypeError, ValueError):
        return None


def _flag(inp: MorphologyCandidateInput, fid: str) -> bool | None:
    ref = inp.features.get(fid)
    if ref is None or ref.missing:
        return None
    if not ref.valid:
        return None
    v = ref.value
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v) != 0.0
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "suspected", "possible"}
    return None


def _ledger(
    *,
    rule_id: str,
    feature_id: str,
    measured_value: Any,
    unit: str,
    validity: str,
    threshold_or_interval: Any,
    comparison: str,
    support_direction: str,
    evidence_strength: str,
    human_en: str = "",
    human_ru: str = "",
    technical: str = "",
    interference_adjustment: str = "none",
    quality_adjustment: str = "none",
    temporal_adjustment: str = "none",
    spatial: str = "",
    branch: str = "",
    comparison_result: str = "",
) -> EvidenceLedgerEntry:
    from ionogram_morphology_lab.morphology_candidate.comparison_result import derive_comparison_result

    cmp_res = comparison_result or derive_comparison_result(
        validity=validity,
        comparison=comparison,
        measured_value=measured_value,
        threshold_or_interval=threshold_or_interval,
        support_direction=support_direction,
    )
    return EvidenceLedgerEntry(
        rule_id=rule_id,
        feature_id=feature_id,
        measured_value=measured_value,
        unit=unit,
        validity=validity,
        threshold_or_interval=threshold_or_interval,
        comparison=comparison,
        support_direction=support_direction,
        evidence_strength=evidence_strength,
        spatial_support_identity=spatial,
        branch_identity=branch,
        interference_adjustment=interference_adjustment,
        quality_adjustment=quality_adjustment,
        temporal_adjustment=temporal_adjustment,
        human_explanation_en=human_en,
        human_explanation_ru=human_ru,
        technical_explanation=technical,
        comparison_result=cmp_res,
    )


def _strength_from_fraction(frac: float | None, weak: float, mod: float, strong: float) -> str:
    if frac is None:
        return "none"
    if frac >= strong:
        return "strong"
    if frac >= mod:
        return "moderate"
    if frac >= weak:
        return "weak"
    return "none"


def _rank(s: str) -> int:
    return {"none": 0, "weak": 1, "moderate": 2, "strong": 3}.get(s, 0)


def _bump(s: str, delta: int) -> str:
    order = ["none", "weak", "moderate", "strong"]
    i = max(0, min(3, order.index(s) + delta))
    return order[i]


def evaluate_morphology_candidate(
    inp: MorphologyCandidateInput,
    *,
    ruleset: dict[str, Any] | None = None,
    expected_v2_identity: str | None = None,
) -> MorphologyCandidateResult:
    """Evaluate provisional shadow candidate. Never mutates ``inp``."""
    # Defensive copy check — engine must not mutate input
    _ = deepcopy(inp.features)  # ensure features mapping is readable; input remains frozen

    rs = ruleset if ruleset is not None else load_ruleset()
    rs_hash = ruleset_hash(rs)
    ledger: list[EvidenceLedgerEntry] = []
    warnings: list[str] = []
    abstention_reasons: list[str] = []

    # --- 1. Identity / compatibility gates ---
    if inp.feature_version not in rs.get("compatible_feature_versions", []):
        abstention_reasons.append("incompatible_feature_version")
        ledger.append(
            _ledger(
                rule_id="gate_feature_version",
                feature_id="feature_version",
                measured_value=inp.feature_version,
                unit="version",
                validity="invalid",
                threshold_or_interval=rs.get("compatible_feature_versions"),
                comparison="not_in",
                support_direction="blocks",
                evidence_strength="none",
                human_en="Feature version incompatible with ruleset.",
                human_ru="Версия признаков несовместима с набором правил.",
                technical=f"feature_version={inp.feature_version}",
            )
        )
        return _finalize(
            inp, rs, rs_hash, "not_assessable", True, abstention_reasons, "none",
            AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
            {"coexistence_supported": False, "reason": "incompatible"},
            ledger, warnings, "not_assessable",
        )

    if expected_v2_identity and inp.v2_result_identity and expected_v2_identity != inp.v2_result_identity:
        abstention_reasons.append("geometry_result_identity_mismatch")
        ledger.append(
            _ledger(
                rule_id="gate_v2_identity",
                feature_id="v2_result_identity",
                measured_value=inp.v2_result_identity,
                unit="hash",
                validity="invalid",
                threshold_or_interval=expected_v2_identity,
                comparison="!=" ,
                support_direction="blocks",
                evidence_strength="none",
                human_en="V2 geometry identity mismatch; candidate rejected.",
                human_ru="Несовпадение идентичности геометрии V2; кандидат отклонён.",
                technical="stale_or_mismatched_v2_identity",
            )
        )
        return _finalize(
            inp, rs, rs_hash, "not_assessable", True, abstention_reasons, "none",
            AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
            {"coexistence_supported": False, "reason": "identity_mismatch"},
            ledger, warnings, "not_assessable",
        )

    if not inp.source_sha256 or inp.diagnostics_cache_id is None:
        abstention_reasons.append("incomplete_identity")
        return _finalize(
            inp, rs, rs_hash, "not_assessable", True, abstention_reasons, "none",
            AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
            {"coexistence_supported": False},
            ledger, warnings + ["incomplete_identity"], "not_assessable",
        )

    # --- 2. Required features ---
    # Only key-absent features are "missing". Explicit invalid/not_applicable values
    # remain present so blank/no-trace frames can reach the no-trace gate.
    required = list(rs.get("required_feature_ids") or [])
    missing: list[str] = []
    for fid in required:
        ref = inp.features.get(fid)
        if ref is None or ref.missing:
            missing.append(fid)
    if missing:
        abstention_reasons.append("missing_required_features")
        for fid in missing:
            ledger.append(
                _ledger(
                    rule_id="gate_required_feature",
                    feature_id=fid,
                    measured_value=None,
                    unit="",
                    validity="missing",
                    threshold_or_interval="required",
                    comparison="missing",
                    support_direction="blocks",
                    evidence_strength="none",
                    human_en=f"Required feature missing: {fid}",
                    human_ru=f"Отсутствует обязательный признак: {fid}",
                    technical="no silent zero substitution",
                )
            )
        return _finalize(
            inp, rs, rs_hash, "not_assessable", True, abstention_reasons + [f"missing:{m}" for m in missing],
            "none", AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
            {"coexistence_supported": False, "reason": "missing_features"},
            ledger, warnings, "not_assessable",
        )

    # --- 3–5. Frame / geometry / trace assessability ---
    quality = (inp.quality_status or "").lower()
    ledger.append(
        _ledger(
            rule_id="gate_quality_status",
            feature_id="v2_quality_status",
            measured_value=quality,
            unit="categorical",
            validity="valid",
            threshold_or_interval=["assessable", "usable", "ok", "good", "marginal"],
            comparison="membership",
            support_direction="neutral",
            evidence_strength="none",
            quality_adjustment=quality,
            human_en=f"Quality status: {quality}",
            human_ru=f"Статус качества: {quality}",
        )
    )
    if quality in {"not_assessable", "failed", "invalid", "error"} or inp.geometry_status in {
        "failed", "not_assessable",
    }:
        abstention_reasons.append("geometry_or_quality_not_assessable")
        return _finalize(
            inp, rs, rs_hash, "not_assessable", True, abstention_reasons, "none",
            AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
            {"coexistence_supported": False},
            ledger, warnings, "not_assessable",
        )

    if not inp.trace_present or not inp.trace_valid:
        abstention_reasons.append("no_valid_ionospheric_trace")
        ledger.append(
            _ledger(
                rule_id="gate_trace_presence",
                feature_id="v2_trace_pixel_fraction",
                measured_value=_num(inp, "v2_trace_pixel_fraction"),
                unit="fraction",
                validity="valid" if inp.trace_present else "insufficient",
                threshold_or_interval=threshold(rs, "min_trace_pixel_fraction"),
                comparison="<",
                support_direction="blocks",
                evidence_strength="none",
                human_en="No usable ionospheric trace for morphology assessment.",
                human_ru="Нет допустимого ионосферного следа для оценки морфологии.",
                technical="blank_or_no_trace_frame_may_be_geometry_ok_but_morphology_not_assessable",
            )
        )
        return _finalize(
            inp, rs, rs_hash, "not_assessable", True, abstention_reasons, "none",
            AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
            {"coexistence_supported": False, "reason": "no_trace"},
            ledger, warnings, "not_assessable",
        )

    tpf = _num(inp, "v2_trace_pixel_fraction")
    min_tpf = float(threshold(rs, "min_trace_pixel_fraction"))
    if tpf is not None and tpf < min_tpf:
        abstention_reasons.append("trace_pixel_fraction_below_minimum")
        return _finalize(
            inp, rs, rs_hash, "not_assessable", True, abstention_reasons, "none",
            AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
            {"coexistence_supported": False},
            ledger, warnings, "not_assessable",
        )

    support_above = _num(inp, "v2_accepted_support_above_floor_fraction")
    min_support = float(threshold(rs, "min_accepted_support_above_floor"))
    if support_above is not None and support_above < min_support:
        warnings.append("low_accepted_support_above_floor")
        if support_above < min_support * 0.5:
            abstention_reasons.append("insufficient_accepted_support_above_floor")
            return _finalize(
                inp, rs, rs_hash, "not_assessable", True, abstention_reasons, "none",
                AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
                {"coexistence_supported": False},
                ledger, warnings, "not_assessable",
            )

    # --- 6. Blocking interference / artifact gates ---
    if inp.interference.level == "blocking":
        abstention_reasons.append("blocking_interference")
        ledger.append(
            _ledger(
                rule_id="gate_blocking_interference",
                feature_id="v2_interference_level",
                measured_value=inp.interference.raw_v2_interference_level,
                unit="categorical",
                validity="valid",
                threshold_or_interval=threshold(rs, "blocking_interference_levels"),
                comparison="in_blocking",
                support_direction="blocks",
                evidence_strength="none",
                interference_adjustment="blocking",
                human_en="Blocking interference prevents morphology assessment.",
                human_ru="Блокирующие помехи не позволяют оценить морфологию.",
            )
        )
        return _finalize(
            inp, rs, rs_hash, "not_assessable", True, abstention_reasons, "none",
            AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
            {"coexistence_supported": False},
            ledger, warnings, "not_assessable",
        )

    frag = _num(inp, "v2_fragmentation_score")
    max_frag = float(threshold(rs, "max_fragmentation_for_assessable"))
    overseg = _flag(inp, "v2_oversegmentation_suspected")
    overseg_true = bool(overseg)
    frag_blocks = frag is not None and frag >= max_frag

    # Always record separate explainable entries (never attribute a false flag as the block).
    ledger.append(
        _ledger(
            rule_id="gate_oversegmentation_flag",
            feature_id="v2_oversegmentation_suspected",
            measured_value=bool(overseg) if overseg is not None else False,
            unit="flag",
            validity="valid" if overseg is not None else "missing",
            threshold_or_interval=True,
            comparison="==true",
            support_direction="blocks" if overseg_true else "neutral",
            evidence_strength="strong" if overseg_true else "none",
            human_en=(
                "Oversegmentation flag is true; blocks morphology assessment."
                if overseg_true
                else "Oversegmentation flag is false; does not block by itself."
            ),
            human_ru=(
                "Флаг пересегментации истинен; блокирует оценку морфологии."
                if overseg_true
                else "Флаг пересегментации ложен; сам по себе не блокирует."
            ),
            technical=f"overseg={overseg}",
        )
    )
    ledger.append(
        _ledger(
            rule_id="gate_fragmentation_score",
            feature_id="v2_fragmentation_score",
            measured_value=frag,
            unit="score",
            validity="valid" if frag is not None else "missing",
            threshold_or_interval=max_frag,
            comparison=f">={max_frag}",
            support_direction="blocks" if frag_blocks else "neutral",
            evidence_strength="strong" if frag_blocks else "none",
            human_en=(
                f"Fragmentation score {frag} ≥ {max_frag}; blocks reliable morphology."
                if frag_blocks
                else f"Fragmentation score {frag} below threshold {max_frag}."
            ),
            human_ru=(
                f"Оценка фрагментации {frag} ≥ {max_frag}; блокирует надёжную морфологию."
                if frag_blocks
                else f"Оценка фрагментации {frag} ниже порога {max_frag}."
            ),
            technical=f"fragmentation_score={frag}; max_fragmentation_for_assessable={max_frag}",
        )
    )

    if overseg_true or frag_blocks:
        if overseg_true and frag_blocks:
            reason = "both_oversegmentation_and_fragmentation"
        elif overseg_true:
            reason = "oversegmentation_suspected"
        else:
            reason = "severe_fragmentation"
        abstention_reasons.append(reason)
        cand = "not_assessable" if overseg_true else "indeterminate"
        return _finalize(
            inp, rs, rs_hash, cand, True, abstention_reasons, "none",
            AxisEvidenceSummary(False, "none"), AxisEvidenceSummary(False, "none"),
            {"coexistence_supported": False},
            ledger, warnings, "indeterminate" if cand == "indeterminate" else "not_assessable",
        )

    # --- 7–8. H / V evidence ---
    h_summary, h_ledger = _eval_h(inp, rs)
    ledger.extend(h_ledger)
    v_summary, v_ledger = _eval_v(inp, rs)
    ledger.extend(v_ledger)

    # Interference may reduce but never increase strength
    if inp.interference.level in {"high", "moderate"}:
        if h_summary.supported:
            new_s = _bump(h_summary.strength, -1)
            if new_s != h_summary.strength:
                warnings.append("h_strength_reduced_by_interference")
                h_summary = AxisEvidenceSummary(h_summary.supported and new_s != "none", new_s, h_summary.primary_features, h_summary.notes + ("interference_reduced",))
        if v_summary.supported:
            new_s = _bump(v_summary.strength, -1)
            if new_s != v_summary.strength:
                warnings.append("v_strength_reduced_by_interference")
                v_summary = AxisEvidenceSummary(v_summary.supported and new_s != "none", new_s, v_summary.primary_features, v_summary.notes + ("interference_reduced",))

    # Secondary / multiple reflection: do not auto frequency
    multi = _flag(inp, "v2_multiple_reflection_possibility")
    if multi and h_summary.supported:
        warnings.append("multiple_reflection_suppresses_auto_frequency")
        ledger.append(
            _ledger(
                rule_id="exclude_secondary_echo_h",
                feature_id="v2_multiple_reflection_possibility",
                measured_value=True,
                unit="flag",
                validity="valid",
                threshold_or_interval=False,
                comparison="==true→suppress_frequency",
                support_direction="opposes",
                evidence_strength="moderate",
                human_en="Secondary/multiple echo suspicion prevents automatic frequency candidate.",
                human_ru="Подозрение на вторичное/кратное отражение не даёт автоматически назначить частотного кандидата.",
            )
        )
        h_summary = AxisEvidenceSummary(False, "none", h_summary.primary_features, h_summary.notes + ("secondary_echo_excluded",))

    # Floor / stripes: never range from apparent V
    floor = _num(inp, "v2_floor_clutter_burden") or 0.0
    stripe = _num(inp, "v2_full_height_stripe_burden") or 0.0
    if v_summary.supported and (
        floor >= float(threshold(rs, "max_floor_burden_for_v"))
        or stripe >= float(threshold(rs, "max_full_height_stripe_burden"))
        or inp.interference.vertical_interference and stripe > 0.1
    ):
        warnings.append("v_support_rejected_as_interference_or_floor")
        ledger.append(
            _ledger(
                rule_id="exclude_v_interference_floor",
                feature_id="v2_full_height_stripe_burden",
                measured_value={"floor": floor, "stripe": stripe},
                unit="fraction",
                validity="valid",
                threshold_or_interval={
                    "max_floor": threshold(rs, "max_floor_burden_for_v"),
                    "max_stripe": threshold(rs, "max_full_height_stripe_burden"),
                },
                comparison=">=",
                support_direction="opposes",
                evidence_strength="strong",
                interference_adjustment="reject_v",
                human_en="Apparent vertical width attributed to interference/floor; not range-spread support.",
                human_ru="Кажущаяся вертикальная ширина отнесена к помехам/полу; не поддержка высотного рассеяния.",
            )
        )
        v_summary = AxisEvidenceSummary(False, "none", v_summary.primary_features, v_summary.notes + ("interference_or_floor",))

    # --- 9. Coexistence / mixed ---
    coexist = _eval_coexistence(inp, rs, h_summary, v_summary)
    ledger.extend(coexist["ledger"])

    # --- 10. Temporal ---
    temporal_summary, temp_adj, temp_ledger = _eval_temporal(inp, h_summary, v_summary)
    ledger.extend(temp_ledger)
    if temp_adj.get("force_indeterminate"):
        abstention_reasons.append("temporal_contradiction")
        return _finalize(
            inp, rs, rs_hash, "indeterminate", True, abstention_reasons, "weak",
            h_summary, v_summary, coexist, ledger, warnings + list(temp_adj.get("warnings", [])),
            "indeterminate", temporal_summary,
        )
    if temp_adj.get("strengthen_h"):
        h_summary = AxisEvidenceSummary(True, _bump(h_summary.strength, 1), h_summary.primary_features, h_summary.notes + ("temporal_support",))
    if temp_adj.get("strengthen_v"):
        v_summary = AxisEvidenceSummary(True, _bump(v_summary.strength, 1), v_summary.primary_features, v_summary.notes + ("temporal_support",))
    warnings.extend(temp_adj.get("warnings", []))

    # --- 11–12. Decision + strength ---
    candidate, strength, assessability, abstained, more_reasons = _decide(
        h_summary, v_summary, coexist, inp
    )
    abstention_reasons.extend(more_reasons)

    # Boundary weak → indeterminate
    if candidate in {
        "frequency_spread_candidate",
        "range_spread_candidate",
        "mixed_spread_candidate",
    } and strength == "weak":
        abstention_reasons.append("weak_boundary_evidence")
        candidate = "indeterminate"
        abstained = True
        assessability = "indeterminate"
        strength = "weak"

    if candidate not in ALLOWED_CANDIDATES:
        raise RuntimeError(f"illegal candidate: {candidate}")

    return _finalize(
        inp, rs, rs_hash, candidate, abstained, abstention_reasons, strength,
        h_summary, v_summary, coexist, ledger, warnings, assessability, temporal_summary,
    )


def _eval_h(inp: MorphologyCandidateInput, rs: dict[str, Any]) -> tuple[AxisEvidenceSummary, list[EvidenceLedgerEntry]]:
    ledger: list[EvidenceLedgerEntry] = []
    elev = _num(inp, "v2_horizontal_width_elevated_fraction")
    contig = _num(inp, "v2_horizontal_contiguous_broadening_length")
    med = _num(inp, "v2_median_local_horizontal_width_bins")
    appl = _num(inp, "v2_horizontal_axis_width_applicable_fraction")

    weak = float(threshold(rs, "h_elevated_fraction_weak"))
    mod = float(threshold(rs, "h_elevated_fraction_moderate"))
    strong = float(threshold(rs, "h_elevated_fraction_strong"))
    min_contig = float(threshold(rs, "h_contiguous_length_min_bins"))
    min_med = float(threshold(rs, "h_median_width_min_bins"))

    strength = _strength_from_fraction(elev, weak, mod, strong)
    supported = strength != "none"

    # Require coverage/persistence: contiguous length OR applicable fraction
    if supported:
        if contig is not None and contig < min_contig and (appl is None or appl < 0.1):
            ledger.append(
                _ledger(
                    rule_id="h_persistence_gate",
                    feature_id="v2_horizontal_contiguous_broadening_length",
                    measured_value=contig,
                    unit="bins",
                    validity="valid",
                    threshold_or_interval=min_contig,
                    comparison="<",
                    support_direction="opposes",
                    evidence_strength="moderate",
                    human_en="Horizontal elevated fraction lacks contiguous persistence.",
                    human_ru="Горизонтальное расширение не имеет достаточной непрерывности.",
                )
            )
            supported = False
            strength = "none"
        if med is not None and med < min_med and strength in {"weak", "moderate"}:
            strength = "weak" if supported else "none"
            if strength == "none":
                supported = False

    ledger.append(
        _ledger(
            rule_id="h_elevated_fraction",
            feature_id="v2_horizontal_width_elevated_fraction",
            measured_value=elev,
            unit="fraction",
            validity="valid" if elev is not None else "missing",
            threshold_or_interval={"weak": weak, "moderate": mod, "strong": strong},
            comparison=">=_band",
            support_direction="supports_frequency" if supported else "neutral",
            evidence_strength=strength,
            human_en=f"H elevated fraction → strength {strength}",
            human_ru=f"Доля повышенных H-ширин → сила {strength}",
        )
    )
    notes = []
    if not supported and elev is not None and elev > 0:
        notes.append("below_support_threshold")
    return AxisEvidenceSummary(supported, strength, ("v2_horizontal_width_elevated_fraction",), tuple(notes)), ledger


def _eval_v(inp: MorphologyCandidateInput, rs: dict[str, Any]) -> tuple[AxisEvidenceSummary, list[EvidenceLedgerEntry]]:
    ledger: list[EvidenceLedgerEntry] = []
    elev = _num(inp, "v2_vertical_width_elevated_fraction")
    contig = _num(inp, "v2_vertical_contiguous_broadening_length")
    med = _num(inp, "v2_median_local_vertical_width_bins")
    appl = _num(inp, "v2_vertical_axis_width_applicable_fraction")

    weak = float(threshold(rs, "v_elevated_fraction_weak"))
    mod = float(threshold(rs, "v_elevated_fraction_moderate"))
    strong = float(threshold(rs, "v_elevated_fraction_strong"))
    min_contig = float(threshold(rs, "v_contiguous_length_min_bins"))
    min_med = float(threshold(rs, "v_median_width_min_bins"))

    strength = _strength_from_fraction(elev, weak, mod, strong)
    supported = strength != "none"

    if supported:
        if contig is not None and contig < min_contig and (appl is None or appl < 0.1):
            ledger.append(
                _ledger(
                    rule_id="v_persistence_gate",
                    feature_id="v2_vertical_contiguous_broadening_length",
                    measured_value=contig,
                    unit="bins",
                    validity="valid",
                    threshold_or_interval=min_contig,
                    comparison="<",
                    support_direction="opposes",
                    evidence_strength="moderate",
                    human_en="Vertical elevated fraction lacks contiguous persistence.",
                    human_ru="Вертикальное расширение не имеет достаточной непрерывности.",
                )
            )
            supported = False
            strength = "none"

    ledger.append(
        _ledger(
            rule_id="v_elevated_fraction",
            feature_id="v2_vertical_width_elevated_fraction",
            measured_value=elev,
            unit="fraction",
            validity="valid" if elev is not None else "missing",
            threshold_or_interval={"weak": weak, "moderate": mod, "strong": strong},
            comparison=">=_band",
            support_direction="supports_range" if supported else "neutral",
            evidence_strength=strength,
            human_en=f"V elevated fraction → strength {strength}",
            human_ru=f"Доля повышенных V-ширин → сила {strength}",
        )
    )
    return AxisEvidenceSummary(supported, strength, ("v2_vertical_width_elevated_fraction",), ()), ledger


def _eval_coexistence(
    inp: MorphologyCandidateInput,
    rs: dict[str, Any],
    h: AxisEvidenceSummary,
    v: AxisEvidenceSummary,
) -> dict[str, Any]:
    ledger: list[EvidenceLedgerEntry] = []
    score = _num(inp, "v2_coexistence_score")
    frac = _num(inp, "v2_coexistence_fraction")
    min_score = float(threshold(rs, "coexistence_score_min"))
    min_frac = float(threshold(rs, "coexistence_fraction_min"))

    spatial_ok = (score is not None and score >= min_score) or (frac is not None and frac >= min_frac)
    independent = h.supported and v.supported and _rank(h.strength) >= 2 and _rank(v.strength) >= 2
    coexistence_supported = bool(independent and spatial_ok)

    unrelated = h.supported and v.supported and not spatial_ok
    reason = "ok" if coexistence_supported else ("unrelated_regions" if unrelated else "insufficient")

    ledger.append(
        _ledger(
            rule_id="coexistence_test",
            feature_id="v2_coexistence_score",
            measured_value={"score": score, "fraction": frac, "h": h.strength, "v": v.strength},
            unit="score",
            validity="valid",
            threshold_or_interval={"min_score": min_score, "min_frac": min_frac, "min_axis": "moderate"},
            comparison="independent_and_colocated",
            support_direction="supports_both" if coexistence_supported else ("opposes" if unrelated else "neutral"),
            evidence_strength="moderate" if coexistence_supported else "none",
            human_en="Mixed requires independent moderate+ H and V with spatial coexistence.",
            human_ru="Смешанный кандидат требует независимых H и V (умеренная+) и сосуществования.",
            technical=reason,
        )
    )
    return {
        "coexistence_supported": coexistence_supported,
        "unrelated_hv": unrelated,
        "score": score,
        "fraction": frac,
        "reason": reason,
        "ledger": ledger,
    }


def _eval_temporal(
    inp: MorphologyCandidateInput,
    h: AxisEvidenceSummary,
    v: AxisEvidenceSummary,
) -> tuple[dict[str, Any], dict[str, Any], list[EvidenceLedgerEntry]]:
    ledger: list[EvidenceLedgerEntry] = []
    adj: dict[str, Any] = {"warnings": []}
    if inp.temporal is None:
        summary = {
            "present": False,
            "note": "single_frame_mode_no_temporal_penalty",
            "persistence_count": 0,
            "isolated_candidate_flag": False,
        }
        ledger.append(
            _ledger(
                rule_id="temporal_absent",
                feature_id="temporal_context",
                measured_value=None,
                unit="",
                validity="absent",
                threshold_or_interval="optional",
                comparison="missing_neighbours_not_negative",
                support_direction="neutral",
                evidence_strength="none",
                temporal_adjustment="none",
                human_en="No temporal context; single-frame result retained without penalty.",
                human_ru="Нет временного контекста; результат одного кадра без штрафа.",
            )
        )
        return summary, adj, ledger

    t = inp.temporal
    summary = t.to_dict()
    summary["present"] = True
    if not t.same_source_sha or not t.same_profile_contract_ruleset:
        adj["warnings"].append("temporal_identity_mismatch_ignored")
        return summary, adj, ledger

    if t.transition_flag and t.isolated_candidate_flag:
        adj["force_indeterminate"] = True
        ledger.append(
            _ledger(
                rule_id="temporal_contradiction",
                feature_id="temporal_context",
                measured_value=summary,
                unit="",
                validity="valid",
                threshold_or_interval="contradiction",
                comparison="contradicts",
                support_direction="opposes",
                evidence_strength="moderate",
                temporal_adjustment="indeterminate",
                human_en="Neighbour frames contradict isolated-frame candidate.",
                human_ru="Соседние кадры противоречат изолированному кандидату.",
            )
        )
        return summary, adj, ledger

    if t.persistence_count >= 1:
        if h.supported and _rank(h.strength) == 2:
            adj["strengthen_h"] = True
        if v.supported and _rank(v.strength) == 2:
            adj["strengthen_v"] = True
        ledger.append(
            _ledger(
                rule_id="temporal_persistence",
                feature_id="temporal_context",
                measured_value=t.persistence_count,
                unit="count",
                validity="valid",
                threshold_or_interval=1,
                comparison=">=",
                support_direction="supports_both",
                evidence_strength="moderate",
                temporal_adjustment="strengthen_moderate",
                human_en="Consistent neighbours may strengthen moderate evidence.",
                human_ru="Согласованные соседи могут усилить умеренные доказательства.",
            )
        )
    return summary, adj, ledger


def _decide(
    h: AxisEvidenceSummary,
    v: AxisEvidenceSummary,
    coexist: dict[str, Any],
    inp: MorphologyCandidateInput,
) -> tuple[str, str, str, bool, list[str]]:
    reasons: list[str] = []
    # Unrelated H/V → not mixed; indeterminate
    if coexist.get("unrelated_hv"):
        return "indeterminate", "weak", "indeterminate", True, ["unrelated_h_v_regions"]

    if coexist.get("coexistence_supported"):
        strength = ["none", "weak", "moderate", "strong"][min(_rank(h.strength), _rank(v.strength))]
        return "mixed_spread_candidate", strength, "assessable", False, []

    if h.supported and not v.supported and _rank(h.strength) >= 2:
        return "frequency_spread_candidate", h.strength, "assessable", False, []

    if v.supported and not h.supported and _rank(v.strength) >= 2:
        return "range_spread_candidate", v.strength, "assessable", False, []

    # Both weakly supported or conflict near boundary
    if h.supported and v.supported and not coexist.get("coexistence_supported"):
        return "indeterminate", "weak", "indeterminate", True, ["h_v_without_coexistence"]

    if (h.supported and _rank(h.strength) == 1) or (v.supported and _rank(v.strength) == 1):
        return "indeterminate", "weak", "indeterminate", True, ["weak_axis_evidence"]

    if inp.interference.level == "high":
        reasons.append("high_interference_residual_uncertainty")
        return "indeterminate", "none", "indeterminate", True, reasons

    # Clean assessable: no supported spread
    return "no_supported_visible_spread", "none", "assessable", False, []


def _build_explanations(
    candidate: str,
    strength: str,
    h: AxisEvidenceSummary,
    v: AxisEvidenceSummary,
    interference_level: str,
    abstained: bool,
    abstention_reasons: list[str],
) -> tuple[str, str]:
    """Localized explanations. Canonical enums never appear in these strings."""
    disc_en = disclaimer("en")
    disc_ru = disclaimer("ru")
    if candidate == "not_assessable":
        en = (
            f"{format_abstention_sentence(abstention_reasons, 'en')} "
            "Geometry may be acceptable without a classifiable spread morphology. "
            f"{disc_en}"
        )
        ru = (
            f"{format_abstention_sentence(abstention_reasons, 'ru')} "
            "Алгоритм геометрии мог корректно не построить ложный след, "
            "но тип рассеяния по этому кадру определить нельзя. "
            f"{disc_ru}"
        )
        return en, ru

    en = (
        f"{candidate_label(candidate, 'en')}, evidence strength: {strength_label(strength, 'en')}. "
        f"Horizontal support: {'yes' if h.supported else 'no'} ({strength_label(h.strength, 'en')}). "
        f"Vertical support: {'yes' if v.supported else 'no'} ({strength_label(v.strength, 'en')}). "
        f"Interference level: {interference_label(interference_level, 'en')}. "
        f"{disc_en}"
    )
    ru = (
        f"{candidate_label(candidate, 'ru')}, сила доказательств: {strength_label(strength, 'ru')}. "
        f"Горизонтальная поддержка: {'да' if h.supported else 'нет'} ({strength_label(h.strength, 'ru')}). "
        f"Вертикальная поддержка: {'да' if v.supported else 'нет'} ({strength_label(v.strength, 'ru')}). "
        f"Уровень помех: {interference_label(interference_level, 'ru')}. "
        f"{disc_ru}"
    )
    if abstained and abstention_reasons:
        en += " Abstention: " + "; ".join(abstention_label(r, "en") for r in abstention_reasons) + "."
        ru += " Воздержание: " + "; ".join(abstention_label(r, "ru") for r in abstention_reasons) + "."
    return en, ru


def _finalize(
    inp: MorphologyCandidateInput,
    rs: dict[str, Any],
    rs_hash: str,
    candidate: str,
    abstained: bool,
    abstention_reasons: list[str],
    strength: str,
    h: AxisEvidenceSummary,
    v: AxisEvidenceSummary,
    coexist: dict[str, Any],
    ledger: list[EvidenceLedgerEntry],
    warnings: list[str],
    assessability: str,
    temporal_summary: dict[str, Any] | None = None,
) -> MorphologyCandidateResult:
    en, ru = _build_explanations(
        candidate, strength, h, v, inp.interference.level, abstained, abstention_reasons
    )
    coexist_out = {
        "coexistence_supported": bool(coexist.get("coexistence_supported")),
        "unrelated_hv": bool(coexist.get("unrelated_hv")),
        "score": coexist.get("score"),
        "fraction": coexist.get("fraction"),
        "reason": coexist.get("reason"),
    }
    result = MorphologyCandidateResult(
        candidate=candidate,
        candidate_engine_version=CANDIDATE_ENGINE_VERSION,
        ruleset_id=str(rs.get("ruleset_id")),
        ruleset_version=str(rs.get("ruleset_version")),
        ruleset_hash=rs_hash,
        feature_version=inp.feature_version,
        source_sha256=inp.source_sha256,
        frame_index=inp.frame_index,
        interpreted_time=inp.interpreted_time,
        diagnostics_cache_id=inp.diagnostics_cache_id,
        input_identity_hash=inp.identity_hash(),
        assessability=assessability,
        abstained=abstained,
        abstention_reasons=tuple(abstention_reasons),
        evidence_strength=strength,
        h_evidence=h,
        v_evidence=v,
        coexistence_summary=coexist_out,
        interference=inp.interference,
        quality_summary={
            "quality_status": inp.quality_status,
            "geometry_status": inp.geometry_status,
            "trace_present": inp.trace_present,
            "trace_valid": inp.trace_valid,
        },
        ambiguity_summary={"flags": list(inp.ambiguity_flags)},
        temporal_summary=temporal_summary or {"present": False},
        evidence_ledger=tuple(ledger),
        warnings=tuple(warnings),
        provisional=True,
        shadow_mode=True,
        scientifically_validated=False,
        production_applied=False,
        created_at=datetime.now(timezone.utc).isoformat(),
        human_explanation_en=en,
        human_explanation_ru=ru,
    )
    return result.with_result_hash()
