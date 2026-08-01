"""Disagreement and alternative-interpretation engine."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

DISAGREEMENT_TYPES = [
    "frequency_vs_range",
    "frequency_vs_ox_ambiguity",
    "range_vs_vertical_interference",
    "range_vs_multiple_reflection",
    "mixed_vs_interference",
    "none_vs_low_signal",
    "artifact_vs_real_trace",
    "frame_vs_sequence_context",
    "rule_vs_reference",
    "rule_vs_model",
    "source_terminology_conflict",
    "instrument_domain_mismatch",
    "outside_reference_domain",
]


@dataclass
class DisagreementReport:
    flags: list[str]
    pairs: list[dict[str, Any]] = field(default_factory=list)
    recommended_expert_action: str = "requires expert review"
    can_abstain: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DisagreementEngine:
    def analyze(
        self,
        rule_category: str,
        rule_flags: list[str],
        reference_categories: list[str] | None = None,
        interference_status: str | None = None,
        possible_ox: bool = False,
        low_signal: bool = False,
        sequence_category: str | None = None,
        model_category: str | None = None,
        domain_mismatch: bool = False,
    ) -> DisagreementReport:
        flags = list(rule_flags)
        pairs: list[dict[str, Any]] = []

        if possible_ox and rule_category in ("frequency", "range", "mixed"):
            flags.append("frequency_vs_ox_ambiguity")
            pairs.append(
                self._pair(
                    "A",
                    rule_category,
                    "rule-based spread-compatible features",
                    "possible O/X / multi-branch ambiguity without polarimetry",
                    "B",
                    "abstain",
                    "clean double-branch heuristic / C02",
                    "may still be true spread with coincidental branches",
                    "O/X not confirmed; expert review required",
                )
            )

        if interference_status == "dominant" and rule_category == "range":
            flags.append("range_vs_vertical_interference")
            pairs.append(
                self._pair(
                    "A",
                    "range",
                    "vertical width features",
                    "vertical stripes can inflate vertical width",
                    "B",
                    "artifact",
                    "interference detector",
                    "true range spread may coexist with interference",
                    "Do not auto-convert interference to range spread",
                )
            )

        if low_signal and rule_category == "none":
            flags.append("none_vs_low_signal")

        if reference_categories:
            top = reference_categories[0]
            if top != rule_category and top not in ("indeterminate",):
                flags.append("rule_vs_reference")
                pairs.append(
                    self._pair(
                        "A",
                        rule_category,
                        "activated rules",
                        "reference atlas may be out of domain",
                        "B",
                        top,
                        "nearest reference similarity",
                        "similarity is image-diagnostic only",
                        "Compare citations; consider abstain if domain mismatch",
                    )
                )

        if sequence_category and sequence_category != rule_category:
            flags.append("frame_vs_sequence_context")

        if model_category and model_category != rule_category:
            flags.append("rule_vs_model")

        if domain_mismatch:
            flags.append("instrument_domain_mismatch")
            flags.append("outside_reference_domain")

        # unique preserve order
        seen = set()
        uniq = []
        for f in flags:
            if f in DISAGREEMENT_TYPES and f not in seen:
                seen.add(f)
                uniq.append(f)

        action = "requires expert review"
        if uniq:
            action = "Expert may accept, change, mark uncertain/not_assessable, or leave automatic result and document reason. Algorithm may abstain."

        return DisagreementReport(flags=uniq, pairs=pairs, recommended_expert_action=action)

    @staticmethod
    def _pair(
        a_label: str,
        a_interp: str,
        a_for: str,
        a_against: str,
        b_label: str,
        b_interp: str,
        b_for: str,
        b_against: str,
        unresolved: str,
    ) -> dict[str, Any]:
        return {
            "interpretation_A": a_interp,
            "evidence_supporting_A": a_for,
            "evidence_against_A": a_against,
            "interpretation_B": b_interp,
            "evidence_supporting_B": b_for,
            "evidence_against_B": b_against,
            "unresolved_reason": unresolved,
            "recommended_expert_action": "requires expert review",
        }
