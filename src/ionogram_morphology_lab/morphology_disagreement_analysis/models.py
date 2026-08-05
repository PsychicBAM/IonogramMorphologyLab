"""Dataclasses for disagreement analysis records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ionogram_morphology_lab.morphology_disagreement_analysis.constants import (
    ANALYSIS_MANIFEST_SCHEMA_VERSION,
    ANALYSIS_PROTOCOL_VERSION,
    ANALYSIS_SNAPSHOT_SCHEMA_VERSION,
    CONTAMINATION_SCHEMA_VERSION,
    DECISION_GATE_SCHEMA_VERSION,
    DECISION_OUTCOMES,
    HOLDOUT_PLAN_SCHEMA_VERSION,
    HYPOTHESIS_CATEGORIES,
    HYPOTHESIS_CONFIDENCE,
    LIFECYCLE_STATES,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _from_dict(cls, data: dict[str, Any]):
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class AnalysisSelection:
    cohort_ids: list[str] = field(default_factory=list)
    campaign_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisSelection":
        return _from_dict(cls, data or {})


@dataclass
class SnapshotItemRecord:
    """Immutable frozen case row for one current cohort/item identity."""

    cohort_id: str
    item_id: str
    cohort_revision_number: int
    parent_cohort_id: str
    campaign_id: str
    source_inventory_id: str
    source_display_name: str
    source_sha256: str
    frame_index: int
    frame_time: str
    sequence_id: str
    related_frame_group: str
    expert_review_id: str
    expert_morphology: str
    expert_assessability: str
    expert_interference: list[str]
    expert_comment: str
    second_review_id: str
    second_morphology: str
    arbitration_id: str
    candidate_snapshot_hash: str
    candidate_state: str
    candidate_strength: str
    candidate_engine_version: str
    candidate_ruleset_id: str
    candidate_ruleset_hash: str
    geometry_version: str
    evidence_categories: list[str]
    comparison_id: str
    comparison_status: str
    post_comparison_note: str
    eligibility_bucket: str
    exclusion_reason: str
    contamination_status: str
    item_status: str
    available: bool

    def identity_key(self) -> tuple[str, str]:
        return (self.cohort_id, self.item_id)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SnapshotItemRecord":
        return _from_dict(cls, data)


@dataclass
class AnalysisManifest:
    analysis_id: str
    title: str
    description: str
    created_at: str
    analysis_protocol_version: str = ANALYSIS_PROTOCOL_VERSION
    manifest_schema_version: int = ANALYSIS_MANIFEST_SCHEMA_VERSION
    snapshot_schema_version: int = ANALYSIS_SNAPSHOT_SCHEMA_VERSION
    lifecycle_state: str = "draft"
    selection: AnalysisSelection = field(default_factory=AnalysisSelection)
    selected_cohort_ids: list[str] = field(default_factory=list)
    selected_campaign_ids: list[str] = field(default_factory=list)
    cohort_revisions: dict[str, int] = field(default_factory=dict)
    candidate_engine_versions: list[str] = field(default_factory=list)
    candidate_ruleset_versions: list[str] = field(default_factory=list)
    geometry_versions: list[str] = field(default_factory=list)
    version_strata_required: bool = False
    compatibility_warnings: list[str] = field(default_factory=list)
    parent_analysis_id: str = ""
    revision_number: int = 1
    revision_reason: str = ""
    frozen_at: str = ""
    manifest_hash: str = ""
    snapshot_hash: str = ""
    contamination_status: str = "not_exposed"
    analyst_id: str = ""
    decision_outcome: str = ""
    holdout_plan_id: str = ""

    def __post_init__(self) -> None:
        if self.lifecycle_state not in LIFECYCLE_STATES:
            raise ValueError(f"Invalid lifecycle_state: {self.lifecycle_state!r}")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["selection"] = self.selection.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisManifest":
        payload = dict(data or {})
        sel = AnalysisSelection.from_dict(payload.pop("selection", {}) or {})
        obj = _from_dict(cls, payload)
        obj.selection = sel
        return obj

    def compute_manifest_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("manifest_hash", None)
        return deterministic_hash(payload)


@dataclass
class AnalystHypothesis:
    note_id: str
    analysis_id: str
    category: str
    analyst_id: str
    note: str
    supporting_observation: str = ""
    contradicting_observation: str = ""
    confidence: str = "low"
    affected_case_keys: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.category not in HYPOTHESIS_CATEGORIES:
            raise ValueError(f"Invalid hypothesis category: {self.category!r}")
        if self.confidence not in HYPOTHESIS_CONFIDENCE:
            raise ValueError(f"Invalid confidence: {self.confidence!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalystHypothesis":
        return _from_dict(cls, data)

    @classmethod
    def create(
        cls,
        *,
        analysis_id: str,
        category: str,
        analyst_id: str,
        note: str,
        confidence: str = "low",
        affected_case_keys: list[str] | None = None,
        supporting_observation: str = "",
        contradicting_observation: str = "",
    ) -> "AnalystHypothesis":
        return cls(
            note_id=f"note_{uuid4().hex[:16]}",
            analysis_id=analysis_id,
            category=category,
            analyst_id=analyst_id,
            note=note,
            supporting_observation=supporting_observation,
            contradicting_observation=contradicting_observation,
            confidence=confidence,
            affected_case_keys=list(affected_case_keys or []),
        )


@dataclass
class ContaminationRecord:
    analysis_id: str
    cohort_id: str
    item_id: str
    source_sha256: str
    source_date: str
    related_frame_group: str
    sequence_id: str
    status: str = "development_exposed"
    marked_at: str = field(default_factory=_utc_now)
    schema_version: int = CONTAMINATION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContaminationRecord":
        return _from_dict(cls, data)


@dataclass
class HoldoutPlan:
    holdout_plan_id: str
    analysis_id: str
    title: str
    created_at: str
    development_case_keys: list[str]
    holdout_case_keys: list[str]
    separation_basis: list[str]
    overlap_warnings: list[str]
    overlap_errors: list[str]
    candidate_reveal_blocked: bool = True
    schema_version: int = HOLDOUT_PLAN_SCHEMA_VERSION
    plan_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HoldoutPlan":
        return _from_dict(cls, data)

    def compute_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("plan_hash", None)
        return deterministic_hash(payload)


@dataclass
class DecisionGateRecord:
    analysis_id: str
    outcome: str
    snapshot_hash: str
    manifest_hash: str
    sample_size: int
    denominators: dict[str, int]
    dominant_transitions: list[dict[str, Any]]
    relevant_strata: list[str]
    limitations: list[str]
    independent_second_review_available: bool
    analyst_rationale: str
    alternative_explanations: list[str]
    development_exposed: bool
    holdout_required: bool
    holdout_plan_id: str
    analyst_id: str
    created_at: str = field(default_factory=_utc_now)
    schema_version: int = DECISION_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.outcome not in DECISION_OUTCOMES:
            raise ValueError(f"Invalid decision outcome: {self.outcome!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionGateRecord":
        return _from_dict(cls, data)
