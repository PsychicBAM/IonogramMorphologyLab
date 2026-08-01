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
            measurable_features=["median_horizontal_width", "horizontal_broadening_persistence"],
            thresholds={"median_horizontal_width": 5.0, "horizontal_broadening_persistence": 0.25},
            threshold_origin="development_calibration",
            assumptions="Segmentation threshold adequate; axes comparable",
            applicable_domain="midlatitude_vertical_sounding",
            exclusions="interference_dominance>0.5; low_signal",
            limitations="Candidate morphology only; not confirmed physical Spread-F",
            explanation_ru="Горизонтальное уширение трассы визуально совместимо с частотным рассеянием.",
            explanation_en="Horizontal trace broadening is visually compatible with frequency spread.",
            claim_id="C03",
        ),
        Rule(
            rule_id="R002",
            category="range",
            source_id="A3L018",
            source_page="241",
            source_wording_summary="Range-diffuse aspect of midlatitude SF definition",
            measurable_features=["median_vertical_width", "vertical_broadening_persistence"],
            thresholds={"median_vertical_width": 8.0, "vertical_broadening_persistence": 0.25},
            threshold_origin="development_calibration",
            assumptions="Nominal virtual-height axis",
            applicable_domain="midlatitude_vertical_sounding",
            exclusions="vertical_stripe_density>0.3 (interference may mimic range)",
            limitations="Nominal height; interference may mimic range spread",
            explanation_ru="Вертикальное уширение совместимо с высотным/дальностным рассеянием (номинальная ось).",
            explanation_en="Vertical broadening is compatible with range/virtual-height spread (nominal axis).",
            claim_id="C03",
        ),
        Rule(
            rule_id="R003",
            category="mixed",
            source_id="A2_PROTOCOL",
            source_page="n/a",
            source_wording_summary="Article 2: mixed if both frequency and range flags",
            measurable_features=["mixed_width_score", "mixed_coverage"],
            thresholds={"mixed_width_score": 0.8, "mixed_coverage": 0.5},
            threshold_origin="derived_from_verified_definition",
            assumptions="Article 2 morphology protocol for human review",
            applicable_domain="project_article2_compatible",
            exclusions="",
            limitations="Development aggregation of compatible features",
            explanation_ru="Одновременные признаки частотного и высотного уширения → смешанное рассеяние (кандидат).",
            explanation_en="Simultaneous frequency- and range-compatible broadening → mixed (candidate).",
            claim_id="C03",
        ),
        Rule(
            rule_id="R004",
            category="none",
            source_id="A2_PROTOCOL",
            source_page="n/a",
            source_wording_summary="No confirmed compatible feature when widths low and coverage low",
            measurable_features=["trace_pixel_fraction", "median_horizontal_width", "median_vertical_width"],
            thresholds={
                "trace_pixel_fraction_max": 0.02,
                "median_horizontal_width_max": 3.0,
                "median_vertical_width_max": 4.0,
            },
            threshold_origin="development_calibration",
            assumptions="Adequate SNR",
            applicable_domain="general",
            exclusions="not_assessable quality",
            limitations="Absence of visible compatible feature ≠ physical proof of quiet ionosphere",
            explanation_ru="Убедительных признаков частотного/высотного рассеяния не выявлено.",
            explanation_en="No confirmed compatible frequency/range-spread feature detected.",
            claim_id="C03",
        ),
        Rule(
            rule_id="R005",
            category="artifact",
            source_id="A2_PROTOCOL",
            source_page="n/a",
            source_wording_summary="Interference-dominated frames",
            measurable_features=["interference_dominance", "vertical_stripe_density"],
            thresholds={"interference_dominance": 0.55, "vertical_stripe_density": 0.2},
            threshold_origin="engineering_default",
            assumptions="Vertical-stripe heuristic",
            applicable_domain="general",
            exclusions="",
            limitations="Heuristic interference detector",
            explanation_ru="Доминируют признаки артефакта/помехи; морфотип рассеяния не назначается автоматически.",
            explanation_en="Artifact/interference appears dominant; spread morphology not auto-assigned.",
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

        # Interference must not auto-become range
        if "range" in cats and features.get("vertical_stripe_density", 0) > 0.3:
            disagreement.append("range_vs_vertical_interference")
            cats.discard("range")
            activated = [r for r in activated if r.category != "range"]

        if "artifact" in cats and features.get("interference_dominance", 0) >= 0.55:
            candidate, status = "artifact", "proposed"
        elif any(r.category == "abstain" for r in activated) and features.get(
            "possible_ox_compatibility", 0
        ) >= 0.5:
            candidate, status = "abstain", "abstain"
            abstention_reason = "possible_ox_ambiguity"
        elif "mixed" in cats or (("frequency" in cats) and ("range" in cats)):
            candidate, status = "mixed", "proposed"
        elif "frequency" in cats:
            candidate, status = "frequency", "proposed"
        elif "range" in cats:
            candidate, status = "range", "proposed"
        elif "none" in cats:
            candidate, status = "none", "proposed"
        else:
            candidate, status = "abstain", "uncertain"
            abstention_reason = "no_rule_confidently_activated"
            disagreement.append("none_vs_low_signal")

        if disagreement and status == "proposed":
            status = "uncertain"

        # Contradictions: activated rules with different categories
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
            for r in activated
        ]
        return RuleResult(
            candidate_morphology=candidate,
            confidence_status=status,
            activated_rules=[r.rule_id for r in activated],
            contradicting_rules=contradicting,
            measured_features=features,
            source_citations=citations,
            alternative_categories=alternatives,
            disagreement_flags=disagreement,
            abstention_reason=abstention_reason,
            explanations_ru=[r.explanation_ru for r in activated],
            explanations_en=[r.explanation_en for r in activated],
        )

    def _fires(self, rule: Rule, features: dict[str, float]) -> bool:
        thr = rule.thresholds
        if rule.category == "none":
            return (
                features.get("trace_pixel_fraction", 1) <= thr.get("trace_pixel_fraction_max", 0.02)
                and features.get("median_horizontal_width", 99)
                <= thr.get("median_horizontal_width_max", 3.0)
                and features.get("median_vertical_width", 99)
                <= thr.get("median_vertical_width_max", 4.0)
            )
        if rule.category == "artifact":
            return features.get("interference_dominance", 0) >= thr.get(
                "interference_dominance", 0.55
            ) or features.get("vertical_stripe_density", 0) >= thr.get("vertical_stripe_density", 0.2)
        if rule.category == "abstain":
            return features.get("possible_ox_compatibility", 0) >= thr.get(
                "possible_ox_compatibility", 0.5
            ) and features.get("parallel_branch_count", 0) >= thr.get("parallel_branch_count", 2.0)
        # generic: all listed feature thresholds must be met as minimums
        ok = True
        for feat, tval in thr.items():
            if feat.endswith("_max"):
                continue
            if features.get(feat, -1) < tval:
                ok = False
                break
        return ok
