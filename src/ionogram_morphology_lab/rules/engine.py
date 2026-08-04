"""Source-traceable rule engine for candidate morphology (not physical confirmation)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.utils.paths import app_root

ALLOWED_AUTO_STATUS = ("proposed", "uncertain", "abstain", "not_assessable", "out_of_domain")
CANONICAL_MORPHOLOGY = (
    "frequency",
    "range",
    "mixed",
    "none",
    "diffuse",
    "indeterminate",
    "artifact",
    "not_assessable",
    "other",
    "abstain",
)

ACTIVE_THRESHOLD_ORIGINS = {
    "directly_from_source",
    "derived_from_verified_definition",
    "development_calibration",
    "engineering_default",
    "provisional",
}
DISABLED_THRESHOLD_ORIGINS = {"unsupported"}


@dataclass
class Rule:
    rule_id: str
    category: str
    source_id: str
    source_page: str
    source_wording_summary: str
    measurable_features: list[str]
    thresholds: dict[str, float]
    threshold_origin: str
    assumptions: str
    applicable_domain: str
    exclusions: str
    limitations: str
    explanation_ru: str
    explanation_en: str
    enabled: bool = True
    claim_id: str = ""


@dataclass
class RuleResult:
    candidate_morphology: str
    confidence_status: str
    activated_rules: list[str]
    contradicting_rules: list[str]
    measured_features: dict[str, float]
    source_citations: list[dict[str, str]]
    alternative_categories: list[str]
    disagreement_flags: list[str]
    abstention_reason: str | None
    explanations_ru: list[str] = field(default_factory=list)
    explanations_en: list[str] = field(default_factory=list)
    # Separate from morphology: none|present|significant|dominant|prevents_assessment
    interference_assessment: str = "none"
    near_threshold_rules: list[str] = field(default_factory=list)
    prohibited_causal_claims: list[str] = field(
        default_factory=lambda: [
            "confirmed physical mechanism",
            "proved solar cause",
            "confirmed Rayleigh–Taylor instability",
            "definite Spread-F event from image alone",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_interference(features: dict[str, float]) -> dict[str, Any]:
    """Separate interference presence from morphology blocking.

    Levels:
      none | present | significant | dominant | prevents_assessment
    Morphology must not be replaced by an interference label unless assessment
    is genuinely prevented.
    """
    inter_dom = float(features.get("interference_dominance", 0) or 0)
    stripe_den = float(features.get("vertical_stripe_density", 0) or 0)
    full_h = float(features.get("full_height_stripe_count", 0) or 0)
    tpf = float(features.get("trace_pixel_fraction", 0) or 0)
    stripe_interference = full_h >= 3.0 and inter_dom >= 0.25
    present = inter_dom >= 0.15 or stripe_den >= 0.08 or full_h >= 2.0
    significant = inter_dom >= 0.35 or stripe_den >= 0.20 or stripe_interference
    dominant = inter_dom >= 0.55
    # Prevent assessment only when interference leaves no reliable trace to score.
    prevents = (
        inter_dom >= 0.70
        or (dominant and tpf < 0.008)
        or (stripe_den > 0.45 and inter_dom >= 0.40 and tpf < 0.015)
    )
    if prevents:
        level = "prevents_assessment"
    elif dominant:
        level = "dominant"
    elif significant:
        level = "significant"
    elif present:
        level = "present"
    else:
        level = "none"
    return {
        "level": level,
        "interference_dominance": inter_dom,
        "vertical_stripe_density": stripe_den,
        "full_height_stripe_count": full_h,
        "stripe_interference": stripe_interference,
        "trace_pixel_fraction": tpf,
        "prevents_assessment": prevents,
        # Range-like vertical clutter can still invalidate range-only claims.
        "blocks_range_alone": prevents
        or (stripe_interference and inter_dom >= 0.30)
        or (stripe_den > 0.30 and inter_dom >= 0.40),
    }


def load_rule_pack(path: Path | str | None = None) -> list[Rule]:
    path = Path(path) if path else app_root() / "knowledge_base" / "RULE_PACK_IML1.csv"
    if not path.exists():
        return _builtin_rules()
    rules: list[Rule] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            thr_raw = row.get("thresholds_json") or "{}"
            feats = [x.strip() for x in (row.get("measurable_features") or "").split("|") if x.strip()]
            origin = row.get("threshold_origin", "provisional")
            enabled = row.get("enabled", "true").lower() == "true"
            if origin in DISABLED_THRESHOLD_ORIGINS:
                enabled = False
            rules.append(
                Rule(
                    rule_id=row["rule_id"],
                    category=row["category"],
                    source_id=row.get("source_id", ""),
                    source_page=row.get("source_page", ""),
                    source_wording_summary=row.get("source_wording_summary", ""),
                    measurable_features=feats,
                    thresholds=json.loads(thr_raw),
                    threshold_origin=origin,
                    assumptions=row.get("assumptions", ""),
                    applicable_domain=row.get("applicable_domain", ""),
                    exclusions=row.get("exclusions", ""),
                    limitations=row.get("limitations", ""),
                    explanation_ru=row.get("explanation_ru", ""),
                    explanation_en=row.get("explanation_en", ""),
                    enabled=enabled,
                    claim_id=row.get("claim_id", ""),
                )
            )
    return rules


def _builtin_rules() -> list[Rule]:
    """Fallback if CSV not yet written."""
    return [
        Rule(
            rule_id="R001",
            category="frequency",
            source_id="A3L018",
            source_page="241",
            source_wording_summary="Frequency-aspect of midlatitude SF observational definition",
            measurable_features=[
                "frequency_evidence_passed",
                "median_horizontal_width",
                "horizontal_broadening_persistence",
            ],
            thresholds={
                "frequency_evidence_passed": 1.0,
                "median_horizontal_width": 6.0,
                "horizontal_broadening_persistence": 0.35,
            },
            threshold_origin="development_calibration",
            assumptions="Local ridge thickness; axes comparable",
            applicable_domain="midlatitude_vertical_sounding",
            exclusions="interference_dominance>0.5; low_signal",
            limitations="Candidate morphology only; not confirmed physical Spread-F",
            explanation_ru="Горизонтальное локальное уширение трассы совместимо с частотным рассеянием.",
            explanation_en="Local horizontal ridge thickening is compatible with frequency spread.",
            claim_id="C03",
        ),
        Rule(
            rule_id="R002",
            category="range",
            source_id="A3L018",
            source_page="241",
            source_wording_summary="Range-diffuse aspect of midlatitude SF definition",
            measurable_features=[
                "range_evidence_passed",
                "median_vertical_width",
                "vertical_broadening_persistence",
            ],
            thresholds={
                "range_evidence_passed": 1.0,
                "median_vertical_width": 6.0,
                "vertical_broadening_persistence": 0.35,
            },
            threshold_origin="development_calibration",
            assumptions="Local ridge thickness; nominal virtual-height axis",
            applicable_domain="midlatitude_vertical_sounding",
            exclusions="vertical_stripe_density>0.3; interference_dominance>=0.55",
            limitations="Nominal height; interference must not satisfy range alone",
            explanation_ru="Вертикальное локальное уширение совместимо с высотным рассеянием (номинальная ось).",
            explanation_en="Local vertical ridge thickening is compatible with range/virtual-height spread.",
            claim_id="C03",
        ),
        Rule(
            rule_id="R003",
            category="mixed",
            source_id="A2_PROTOCOL",
            source_page="n/a",
            source_wording_summary="Mixed only when independent frequency AND range evidence co-locate",
            measurable_features=[
                "frequency_evidence_absolute",
                "range_evidence_absolute",
                "colocated_spread_fraction",
            ],
            thresholds={
                "frequency_evidence_absolute": 1.0,
                "range_evidence_absolute": 1.0,
                "colocated_spread_fraction": 0.20,
            },
            threshold_origin="derived_from_verified_definition",
            assumptions="Article 2: mixed requires both axes with co-location",
            applicable_domain="project_article2_compatible",
            exclusions="either axis evidence alone",
            limitations="Never emit mixed from slope-span or single-axis evidence",
            explanation_ru="Одновременные независимые признаки частотного и высотного уширения с со-локализацией → смешанное (кандидат).",
            explanation_en="Independent co-located frequency- and range-compatible broadening → mixed (candidate).",
            claim_id="C03",
        ),
        Rule(
            rule_id="R004",
            category="none",
            source_id="A2_PROTOCOL",
            source_page="n/a",
            source_wording_summary="Assessable frame without independent spread evidence (canonical: clean)",
            measurable_features=[
                "frequency_evidence_passed",
                "range_evidence_passed",
                "interference_dominance",
                "possible_ox_compatibility",
            ],
            thresholds={
                "frequency_evidence_passed_max": 0.0,
                "range_evidence_passed_max": 0.0,
                "interference_dominance_max": 0.55,
                "possible_ox_compatibility_max": 0.5,
            },
            threshold_origin="development_calibration",
            assumptions="Local thickness evidence gates",
            applicable_domain="general",
            exclusions="not_assessable quality",
            limitations="Canonical serialized morphology is clean (no visible spread)",
            explanation_ru="Явное рассеяние не обнаружено (чистая трасса или отсутствие уширения).",
            explanation_en="No visible spread feature detected (clean / no_visible_spread candidate).",
            claim_id="C03",
        ),
        Rule(
            rule_id="R005",
            category="artifact",
            source_id="A2_PROTOCOL",
            source_page="n/a",
            source_wording_summary="Interference indicators (separate from morphology)",
            measurable_features=[
                "interference_dominance",
                "vertical_stripe_density",
                "full_height_stripe_count",
            ],
            thresholds={
                "interference_dominance": 0.55,
                "vertical_stripe_density": 0.2,
                "full_height_stripe_count": 3.0,
                "stripe_interference_dominance_min": 0.25,
            },
            threshold_origin="engineering_default",
            assumptions="R005 marks interference evidence; morphology retained unless assessment prevented",
            applicable_domain="general",
            exclusions="",
            limitations="Heuristic; does not replace morphology when a trace remains assessable",
            explanation_ru="Признаки помехи (R005); морфология сохраняется если кадр оцениваем.",
            explanation_en="Interference indicators (R005); morphology retained when assessable.",
            claim_id="",
        ),
        Rule(
            rule_id="R006",
            category="abstain",
            source_id="A3L007",
            source_page="15-17",
            source_wording_summary="O/X ambiguity must not be auto-classified as spread",
            measurable_features=["possible_ox_compatibility", "parallel_branch_count"],
            thresholds={"possible_ox_compatibility": 0.5, "parallel_branch_count": 2.0},
            threshold_origin="derived_from_verified_definition",
            assumptions="No polarimetry in Amp_all",
            applicable_domain="archive_without_polarization",
            exclusions="",
            limitations="Possible O/X confusion — abstain from spread claim",
            explanation_ru="Возможная O/X-неоднозначность; алгоритм воздерживается от решения о рассеянии.",
            explanation_en="Possible O/X ambiguity; algorithm abstains from a spread decision.",
            claim_id="C02",
            enabled=True,
        ),
        Rule(
            rule_id="R099",
            category="disabled_example",
            source_id="",
            source_page="",
            source_wording_summary="Unsupported numeric URSI thresholds on Amp_all",
            measurable_features=[],
            thresholds={},
            threshold_origin="unsupported",
            assumptions="",
            applicable_domain="",
            exclusions="",
            limitations="URSI MHz/km thresholds not usable as metrology on this archive",
            explanation_ru="Отключено: неверифицированные пороги.",
            explanation_en="Disabled: unsupported thresholds.",
            enabled=False,
        ),
    ]


class RuleEngine:
    def __init__(self, rules: list[Rule] | None = None):
        self.rules = rules if rules is not None else load_rule_pack()

    def active_rules(self) -> list[Rule]:
        return [r for r in self.rules if r.enabled and r.threshold_origin not in DISABLED_THRESHOLD_ORIGINS]

    def evaluate(
        self,
        features: dict[str, float],
        quality_status: str = "valid",
        out_of_domain: bool = False,
    ) -> RuleResult:
        if quality_status in ("unreadable", "CRC_error", "nonfinite_data", "all_zero"):
            return RuleResult(
                candidate_morphology="not_assessable",
                confidence_status="not_assessable",
                activated_rules=[],
                contradicting_rules=[],
                measured_features=features,
                source_citations=[],
                alternative_categories=[],
                disagreement_flags=[],
                abstention_reason=f"quality:{quality_status}",
            )
        if out_of_domain:
            return RuleResult(
                candidate_morphology="abstain",
                confidence_status="out_of_domain",
                activated_rules=[],
                contradicting_rules=[],
                measured_features=features,
                source_citations=[],
                alternative_categories=[],
                disagreement_flags=["outside_reference_domain"],
                abstention_reason="out_of_domain",
            )

        activated: list[Rule] = []
        for rule in self.active_rules():
            if self._fires(rule, features):
                activated.append(rule)

        # Priority: artifact / ox-abstain before spread types; mixed over freq/range
        cats = {r.category for r in activated}
        disagreement: list[str] = []
        candidate = "abstain"
        status = "abstain"
        abstention_reason = None

        if "artifact" in cats and ("frequency" in cats or "range" in cats or "mixed" in cats):
            disagreement.append("artifact_vs_real_trace")
            disagreement.append("mixed_vs_interference")
        if "frequency" in cats and "range" in cats and "mixed" not in cats:
            disagreement.append("frequency_vs_range")
        if any(r.category == "abstain" for r in activated) and (
            "frequency" in cats or "range" in cats or "mixed" in cats
        ):
            disagreement.append("frequency_vs_ox_ambiguity")

        # Interference is assessed separately from morphology (R005 revisit).
        # Presence/significance → warning on the interference axis.
        # Morphology becomes not_assessable only when assessment is prevented.
        inter_info = assess_interference(features)
        inter_dom = float(inter_info["interference_dominance"])
        stripe_den = float(inter_info["vertical_stripe_density"])
        stripe_interference = bool(inter_info["stripe_interference"])
        interference_level = str(inter_info["level"])
        interference_prevents = bool(inter_info["prevents_assessment"])
        blocks_range_alone = bool(inter_info["blocks_range_alone"])
        if interference_level in ("present", "significant", "dominant"):
            disagreement.append(f"interference_{interference_level}")
        if "artifact" in cats and not interference_prevents:
            disagreement.append("interference_present_morphology_still_assessable")

        # Range-only claims remain vulnerable to vertical stripe clutter.
        if "range" in cats and (
            blocks_range_alone
            or float(features.get("range_evidence_passed", 0) or 0) < 1.0
        ):
            disagreement.append("range_vs_vertical_interference")
            cats.discard("range")
            activated = [r for r in activated if r.category != "range"]
        # Full-height stripe clutter can also fabricate horizontal ridge width.
        stripe_blocks_frequency = bool(
            stripe_interference and float(inter_info["full_height_stripe_count"]) >= 3.0
        )
        if "frequency" in cats and (interference_prevents or stripe_blocks_frequency):
            disagreement.append(
                "frequency_vs_blocking_interference"
                if interference_prevents
                else "frequency_vs_vertical_stripe_clutter"
            )
            cats.discard("frequency")
            activated = [r for r in activated if r.category != "frequency"]
        if "mixed" in cats and (interference_prevents or stripe_blocks_frequency):
            disagreement.append("mixed_vs_blocking_interference")
            cats.discard("mixed")
            activated = [r for r in activated if r.category != "mixed"]

        # Mixed requires substantial, comparable evidence on BOTH axes + co-location.
        # If one axis clearly dominates, prefer that single-axis morphology.
        freq_dom = (
            float(features.get("frequency_evidence_passed", 0) or 0) >= 1.0
            and not stripe_blocks_frequency
        )
        range_dom = float(features.get("range_evidence_passed", 0) or 0) >= 1.0
        freq_abs = (
            float(features.get("frequency_evidence_absolute", 0) or 0) >= 1.0
            and not stripe_blocks_frequency
        )
        range_abs = float(features.get("range_evidence_absolute", 0) or 0) >= 1.0
        colocated_ok = float(features.get("colocated_spread_fraction", 0) or 0) >= 0.20
        med_h = float(features.get("median_horizontal_width", 0) or 0)
        med_v = float(features.get("median_vertical_width", 0) or 0)
        axis_ratio = max(med_h, med_v) / max(min(med_h, med_v), 1e-6)
        balanced = axis_ratio <= 1.85
        mixed_ok = (
            not interference_prevents
            and not blocks_range_alone
            and freq_abs
            and range_abs
            and colocated_ok
            and balanced
            and min(med_h, med_v) >= 8.0
        )
        if "mixed" in cats and not mixed_ok:
            cats.discard("mixed")
            activated = [r for r in activated if r.category != "mixed"]
            disagreement.append("mixed_requires_both_balanced_axes")

        near_threshold: list[str] = []
        if interference_prevents:
            # Do not replace a visible morphology with "interference_dominated".
            candidate, status = "not_assessable", "not_assessable"
            abstention_reason = "interference_prevents_assessment"
            disagreement.append("interference_prevents_assessment")
        elif any(r.category == "abstain" for r in activated) and float(
            features.get("possible_ox_compatibility", 0) or 0
        ) >= 0.5:
            candidate, status = "abstain", "abstain"
            abstention_reason = "possible_ox_ambiguity"
        elif mixed_ok:
            candidate, status = "mixed", "proposed"
            if "mixed" not in cats:
                cats.add("mixed")
        elif freq_abs and range_abs and not balanced:
            candidate, status = "diffuse", "uncertain"
            abstention_reason = "dual_axis_thickening_unbalanced_not_mixed"
            disagreement.append("unbalanced_dual_axis_thickening")
            activated = [r for r in activated if r.category not in ("frequency", "range", "mixed", "none")]
            cats = {r.category for r in activated}
        elif (
            not interference_prevents
            and (
                ("frequency" in cats and freq_dom)
                or (freq_abs and not range_abs and med_h >= med_v * 1.15)
            )
        ):
            candidate, status = "frequency", "proposed"
        elif (
            not interference_prevents
            and not blocks_range_alone
            and (
                ("range" in cats and range_dom)
                or (range_abs and not freq_abs and med_v >= med_h * 1.15)
            )
        ):
            candidate, status = "range", "proposed"
        else:
            # Near-threshold / residual diffuseness: do not claim clean absence.
            h_persist = float(features.get("horizontal_broadening_persistence", 0) or 0)
            v_persist = float(features.get("vertical_broadening_persistence", 0) or 0)
            near_freq = (5.0 <= med_h < 6.0 and h_persist >= 0.25) or (
                med_h >= 6.0 and 0.20 <= h_persist < 0.35
            )
            near_range = (5.0 <= med_v < 6.0 and v_persist >= 0.25) or (
                med_v >= 6.0 and 0.20 <= v_persist < 0.35
            )
            colocated = float(features.get("colocated_spread_fraction", 0) or 0)
            diffuse_visible = (
                (max(med_h, med_v) >= 5.0 and max(h_persist, v_persist) >= 0.25)
                or colocated >= 0.12
                or (med_h >= 5.0 and h_persist >= 0.30)
                or (med_v >= 5.0 and v_persist >= 0.30)
            )
            if near_freq:
                near_threshold.append("R001_near_threshold")
            if near_range:
                near_threshold.append("R002_near_threshold")
            if near_freq or near_range:
                candidate, status = "diffuse", "uncertain"
                abstention_reason = (
                    "near_threshold_frequency"
                    if near_freq and not near_range
                    else ("near_threshold_range" if near_range and not near_freq else "near_threshold_spread")
                )
                disagreement.append(abstention_reason)
            elif diffuse_visible and not interference_prevents:
                candidate, status = "diffuse", "uncertain"
                abstention_reason = "diffuse_structure_type_undetermined"
                disagreement.append("diffuse_unspecified")
            elif "none" in cats or (not freq_abs and not range_abs and not interference_prevents):
                candidate, status = "none", "proposed"
                abstention_reason = None
            else:
                candidate, status = "abstain", "uncertain"
                abstention_reason = "no_rule_confidently_activated"
                disagreement.append("none_vs_low_signal")

        # Significant/dominant interference with a still-assessable morphology → uncertain.
        if (
            interference_level in ("significant", "dominant")
            and candidate not in ("not_assessable", "abstain")
            and status == "proposed"
        ):
            status = "uncertain"
            disagreement.append("interference_warning_with_morphology")

        if disagreement and status == "proposed":
            status = "uncertain"

        # Supporting rules match the final candidate; others are contradictions / rejected.
        supporting = [r for r in activated if r.category == candidate]
        if not supporting and candidate in ("none", "mixed", "artifact", "frequency", "range", "diffuse"):
            supporting = [r for r in self.active_rules() if r.category == candidate][:1]
        # R005 remains as contradicting/supporting interference evidence, not morphology winner.
        if "artifact" in cats and candidate != "artifact":
            for r in activated:
                if r.category == "artifact" and r.rule_id not in [
                    x.rule_id for x in supporting
                ]:
                    if r.rule_id not in [
                        rr.rule_id for rr in activated if rr.category != candidate
                    ]:
                        pass
        contradicting = [
            r.rule_id
            for r in activated
            if r.category != candidate and r.category not in ("abstain",)
        ]
        alternatives = sorted({r.category for r in activated if r.category != candidate})
        citations = [
            {
                "rule_id": r.rule_id,
                "claim_id": r.claim_id,
                "source_id": r.source_id,
                "source_page": r.source_page,
                "assumptions": r.assumptions,
                "applicability": r.applicable_domain,
                "limitations": r.limitations,
            }
            for r in (supporting or activated)
        ]
        return RuleResult(
            candidate_morphology=candidate,
            confidence_status=status,
            activated_rules=[r.rule_id for r in (supporting or activated)],
            contradicting_rules=contradicting,
            measured_features=features,
            source_citations=citations,
            alternative_categories=alternatives,
            disagreement_flags=disagreement,
            abstention_reason=abstention_reason,
            explanations_ru=[r.explanation_ru for r in (supporting or activated)],
            explanations_en=[r.explanation_en for r in (supporting or activated)],
            interference_assessment=interference_level,
            near_threshold_rules=near_threshold,
        )

    @staticmethod
    def _finite(features: dict[str, float], key: str, default: float) -> float | None:
        """Return finite feature value, or None if missing/non-finite (never treat NaN as evidence)."""
        if key not in features and default is None:  # pragma: no cover
            return None
        raw = features.get(key, default)
        try:
            val = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if val != val:  # NaN
            return None
        return val

    def _fires(self, rule: Rule, features: dict[str, float]) -> bool:
        thr = rule.thresholds
        if rule.category == "none":
            # Canonical non-spread path: no absolute frequency/range evidence,
            # and not interference/O-X dominated. Visible clean traces are allowed.
            f_ev = self._finite(features, "frequency_evidence_absolute", 0.0)
            r_ev = self._finite(features, "range_evidence_absolute", 0.0)
            # Fall back to dominance flags if absolute gates are absent (older vectors).
            if f_ev is None:
                f_ev = self._finite(features, "frequency_evidence_passed", 0.0)
            if r_ev is None:
                r_ev = self._finite(features, "range_evidence_passed", 0.0)
            inter = self._finite(features, "interference_dominance", 0.0)
            ox = self._finite(features, "possible_ox_compatibility", 0.0)
            if None in (f_ev, r_ev, inter, ox):
                return False
            return (
                f_ev <= thr.get("frequency_evidence_passed_max", 0.0)
                and r_ev <= thr.get("range_evidence_passed_max", 0.0)
                and inter < thr.get("interference_dominance_max", 0.55)
                and ox < thr.get("possible_ox_compatibility_max", 0.5)
            )
        if rule.category == "artifact":
            inter = self._finite(features, "interference_dominance", 0.0)
            stripe = self._finite(features, "vertical_stripe_density", 0.0)
            full_h = self._finite(features, "full_height_stripe_count", 0.0)
            if inter is None and stripe is None and full_h is None:
                return False
            stripe_combo = (
                full_h is not None
                and inter is not None
                and full_h >= thr.get("full_height_stripe_count", 3.0)
                and inter >= thr.get("stripe_interference_dominance_min", 0.25)
            )
            return (
                (inter is not None and inter >= thr.get("interference_dominance", 0.55))
                or (stripe is not None and stripe >= thr.get("vertical_stripe_density", 0.2))
                or stripe_combo
            )
        if rule.category == "abstain":
            ox = self._finite(features, "possible_ox_compatibility", 0.0)
            branches = self._finite(features, "parallel_branch_count", 0.0)
            if ox is None or branches is None:
                return False
            return ox >= thr.get("possible_ox_compatibility", 0.5) and branches >= thr.get(
                "parallel_branch_count", 2.0
            )
        # generic: all listed minimum thresholds must be met with finite values
        for feat, tval in thr.items():
            if feat.endswith("_max"):
                continue
            val = self._finite(features, feat, float("nan"))
            if val is None or val < tval:
                return False
        return True
