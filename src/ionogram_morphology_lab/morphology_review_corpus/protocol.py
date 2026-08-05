"""Frozen cohort protocol (created before review begins)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from ionogram_morphology_lab.morphology_candidate.types import CANDIDATE_ENGINE_VERSION
from ionogram_morphology_lab.morphology_review_corpus.constants import (
    PILOT_DESIGNATION_EN,
    PILOT_DESIGNATION_RU,
    PROTOCOL_SCHEMA_VERSION,
    PROHIBITED_METRICS,
    REVEAL_STRICT_COHORT,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash
from ionogram_morphology_lab.morphology_review_corpus.labels import HUMAN_MORPHOLOGY_CODES


@dataclass
class CohortProtocol:
    protocol_schema_version: int = PROTOCOL_SCHEMA_VERSION
    scientific_purpose: str = (
        "Collect independent expert morphology assessments for later evaluation "
        "of the shadow morphology candidate engine."
    )
    designation_en: str = PILOT_DESIGNATION_EN
    designation_ru: str = PILOT_DESIGNATION_RU
    inclusion_criteria: list[str] = field(
        default_factory=lambda: [
            "Source MAT present in project inventory with known SHA-256",
            "Frame index within source bounds",
            "Owner-selected pilot/evaluation cohort membership",
        ]
    )
    exclusion_criteria: list[str] = field(
        default_factory=lambda: [
            "Geometry reviews are not morphology labels",
            "Unavailable sources without explicit revision",
        ]
    )
    sampling_mode: str = "manual"
    strata: list[str] = field(default_factory=list)
    reviewer_blinding_rules: list[str] = field(
        default_factory=lambda: [
            "Hide candidate class, strength, evidence, thresholds, and agreement until blind lock",
            "Default strict cohort blinding: complete full first-round blind before any reveal",
            "Procedural UI blinding only — not cryptographic protection",
        ]
    )
    allowed_labels: list[str] = field(
        default_factory=lambda: sorted(HUMAN_MORPHOLOGY_CODES)
    )
    required_fields: list[str] = field(
        default_factory=lambda: [
            "morphology",
            "assessability",
            "interference",
            "ambiguity",
            "confidence",
        ]
    )
    # Default for new drafts: full round-one blind before any candidate reveal
    reveal_policy: str = REVEAL_STRICT_COHORT
    second_review_policy: str = "optional_independent"
    adjudication_policy: str = "optional_after_two_locked_reviews"
    descriptive_outputs_allowed: list[str] = field(
        default_factory=lambda: [
            "label_distribution",
            "assessability_distribution",
            "interference_distribution",
            "exact_agreement_count",
            "disagreement_matrix",
            "completion_progress",
        ]
    )
    metrics_prohibited: list[str] = field(
        default_factory=lambda: sorted(PROHIBITED_METRICS)
    )
    candidate_engine_version: str = CANDIDATE_ENGINE_VERSION
    ruleset_id: str = "iml-morph-candidate-rules"
    ruleset_version: str = "0.1.0"
    source_constraints: str = ""
    time_window_constraints: str = ""
    cohort_lock_state: str = "draft"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    protocol_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_hash(self) -> "CohortProtocol":
        payload = self.to_dict()
        payload.pop("protocol_hash", None)
        return CohortProtocol(**{**payload, "protocol_hash": deterministic_hash(payload)})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CohortProtocol":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        # dataclass fields access
        from dataclasses import fields as dc_fields

        known = {f.name for f in dc_fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)
