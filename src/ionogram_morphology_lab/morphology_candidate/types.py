"""Immutable morphology-candidate input/result contracts (Phase 4C.1)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping

CANDIDATE_ENGINE_VERSION = "iml-morph-candidate-0.1.1"
CANDIDATE_CACHE_SCHEMA_VERSION = 2
EVIDENCE_LEDGER_SCHEMA_VERSION = 2
CANDIDATE_RESULT_CONTRACT_VERSION = 2

# Legacy combined gate that must never be accepted under ledger schema ≥ 2
LEGACY_COMBINED_OVERSEG_RULE = "gate_oversegmentation"
SPLIT_FRAGMENTATION_RULE_IDS = frozenset(
    {"gate_oversegmentation_flag", "gate_fragmentation_score"}
)

ALLOWED_CANDIDATES = frozenset(
    {
        "frequency_spread_candidate",
        "range_spread_candidate",
        "mixed_spread_candidate",
        "no_supported_visible_spread",
        "indeterminate",
        "not_assessable",
    }
)

EVIDENCE_STRENGTHS = frozenset({"none", "weak", "moderate", "strong"})
ASSESSABILITY = frozenset({"assessable", "not_assessable", "indeterminate"})
INTERFERENCE_LEVELS = frozenset(
    {"none", "low", "moderate", "high", "blocking", "unavailable", "unknown"}
)
SUPPORT_DIRECTIONS = frozenset(
    {
        "supports_frequency",
        "supports_range",
        "supports_both",
        "opposes",
        "neutral",
        "blocks",
    }
)


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def deterministic_hash(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FeatureValueRef:
    feature_id: str
    value: Any
    unit: str
    valid: bool
    missing: bool = False


@dataclass(frozen=True)
class InterferenceAssessment:
    level: str  # none|low|moderate|high|blocking
    vertical_interference: bool = False
    horizontal_interference: bool = False
    floor_clutter: bool = False
    impulsive_noise: bool = False
    broad_artifact: bool = False
    secondary_multiple_echo_suspicion: bool = False
    oversegmentation: bool = False
    missing_data_regions: bool = False
    raw_v2_interference_level: str = ""
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TemporalContext:
    previous_frame_index: int | None = None
    next_frame_index: int | None = None
    time_distance_prev_s: float | None = None
    time_distance_next_s: float | None = None
    same_source_sha: bool = True
    same_profile_contract_ruleset: bool = True
    neighbour_assessability: tuple[str, ...] = ()
    neighbour_h_support: tuple[str, ...] = ()
    neighbour_v_support: tuple[str, ...] = ()
    persistence_count: int = 0
    isolated_candidate_flag: bool = False
    transition_flag: bool = False
    temporal_context_signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MorphologyCandidateInput:
    source_sha256: str
    frame_index: int
    interpreted_time: str
    profile_id: str
    profile_version: str
    signal_contract_id: str
    signal_contract_version: str
    feature_version: str
    diagnostics_cache_id: str
    raw_frame_identity: str
    geometry_status: str
    quality_status: str
    trace_present: bool
    trace_valid: bool
    features: Mapping[str, FeatureValueRef]
    branch_count: int
    interference: InterferenceAssessment
    ambiguity_flags: tuple[str, ...]
    missing_feature_ids: tuple[str, ...]
    temporal: TemporalContext | None = None
    v2_result_identity: str = ""
    shadow_mode: bool = True

    def identity_payload(self) -> dict[str, Any]:
        return {
            "source_sha256": self.source_sha256,
            "frame_index": self.frame_index,
            "interpreted_time": self.interpreted_time,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "signal_contract_id": self.signal_contract_id,
            "signal_contract_version": self.signal_contract_version,
            "feature_version": self.feature_version,
            "diagnostics_cache_id": self.diagnostics_cache_id,
            "raw_frame_identity": self.raw_frame_identity,
            "v2_result_identity": self.v2_result_identity,
            "geometry_status": self.geometry_status,
            "quality_status": self.quality_status,
        }

    def identity_hash(self) -> str:
        return deterministic_hash(self.identity_payload())


@dataclass(frozen=True)
class EvidenceLedgerEntry:
    rule_id: str
    feature_id: str
    measured_value: Any
    unit: str
    validity: str
    threshold_or_interval: Any
    comparison: str
    support_direction: str
    evidence_strength: str
    spatial_support_identity: str = ""
    branch_identity: str = ""
    interference_adjustment: str = "none"
    quality_adjustment: str = "none"
    temporal_adjustment: str = "none"
    human_explanation_en: str = ""
    human_explanation_ru: str = ""
    technical_explanation: str = ""
    comparison_result: str = ""  # threshold_exceeded|condition_not_met|…

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AxisEvidenceSummary:
    supported: bool
    strength: str
    primary_features: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MorphologyCandidateResult:
    candidate: str
    candidate_engine_version: str
    ruleset_id: str
    ruleset_version: str
    ruleset_hash: str
    feature_version: str
    source_sha256: str
    frame_index: int
    interpreted_time: str
    diagnostics_cache_id: str
    input_identity_hash: str
    assessability: str
    abstained: bool
    abstention_reasons: tuple[str, ...]
    evidence_strength: str
    h_evidence: AxisEvidenceSummary
    v_evidence: AxisEvidenceSummary
    coexistence_summary: Mapping[str, Any]
    interference: InterferenceAssessment
    quality_summary: Mapping[str, Any]
    ambiguity_summary: Mapping[str, Any]
    temporal_summary: Mapping[str, Any]
    evidence_ledger: tuple[EvidenceLedgerEntry, ...]
    warnings: tuple[str, ...]
    provisional: bool
    shadow_mode: bool
    scientifically_validated: bool
    production_applied: bool
    created_at: str
    human_explanation_en: str
    human_explanation_ru: str
    result_hash: str = ""
    candidate_cache_schema_version: int = CANDIDATE_CACHE_SCHEMA_VERSION
    evidence_ledger_schema_version: int = EVIDENCE_LEDGER_SCHEMA_VERSION
    candidate_result_contract_version: int = CANDIDATE_RESULT_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def with_result_hash(self) -> MorphologyCandidateResult:
        payload = self.to_dict()
        payload.pop("result_hash", None)
        # created_at is wall-clock; exclude so repeated evaluation is stable
        payload.pop("created_at", None)
        h = deterministic_hash(payload)
        return replace(self, result_hash=h)


REVIEW_DECISIONS = frozenset(
    {
        "agree_frequency",
        "agree_range",
        "agree_mixed",
        "agree_no_supported_visible_spread",
        "override_frequency",
        "override_range",
        "override_mixed",
        "override_no_supported_visible_spread",
        "mark_indeterminate",
        "mark_not_assessable",
        "needs_second_review",
    }
)


@dataclass
class MorphologyCandidateReview:
    review_kind: str = "morphology_candidate_review"
    source_sha256: str = ""
    frame_index: int = 0
    interpreted_time: str = ""
    feature_version: str = ""
    diagnostics_cache_id: str = ""
    candidate_engine_version: str = CANDIDATE_ENGINE_VERSION
    ruleset_version: str = ""
    ruleset_hash: str = ""
    candidate_result_hash: str = ""
    displayed_candidate: str = ""
    reviewer_decision: str = ""
    reviewer_selected_morphology_label: str = ""
    assessable_for_morphology: str = ""
    interference_handled_correctly: str = ""
    horizontal_evidence_reasonable: str = ""
    vertical_evidence_reasonable: str = ""
    final_candidate_reasonable: str = ""
    comment: str = ""
    reviewed_evidence_ledger_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    provisional_expert_review: bool = True
    confirmed_ground_truth: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
