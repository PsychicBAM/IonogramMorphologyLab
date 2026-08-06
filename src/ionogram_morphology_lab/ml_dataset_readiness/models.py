"""Dataclasses for ML-A.1 dataset readiness audits."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ionogram_morphology_lab.ml_dataset_readiness.constants import (
    CONTAMINATION_STATES,
    GATE_OUTCOMES,
    LIFECYCLE_STATES,
    READINESS_MANIFEST_SCHEMA_VERSION,
    READINESS_PROTOCOL_VERSION,
    TASK_CONTRACTS,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _from_dict(cls, data: dict[str, Any]):
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ReadinessSelection:
    cohort_ids: list[str] = field(default_factory=list)
    campaign_ids: list[str] = field(default_factory=list)
    project_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReadinessSelection":
        return _from_dict(cls, data or {})


@dataclass
class InventoryItemRecord:
    """Candidate-independent expert-label inventory row (current state)."""

    project_id: str
    campaign_id: str
    cohort_id: str
    cohort_revision: int
    item_id: str
    source_inventory_id: str
    source_display_name: str
    source_sha256: str
    source_date: str
    frame_index: int
    frame_time: str
    time_window: str
    morphology: str
    assessability: str
    ambiguity: str
    interference: list[str]
    reviewer_role: str
    reviewer_alias: str
    review_timestamp: str
    locked_first_review_id: str
    independent_second_review_id: str
    independent_second_review_available: bool
    arbitration_id: str
    arbitration_available: bool
    comment_available: bool
    related_frame_group: str
    sequence_id: str
    contamination_state: str
    eligible_future_development: bool
    eligible_untouched_holdout: bool
    exclusion_reason: str
    missingness_category: str
    identity_issues: list[str]
    first_review_corrected: bool
    second_review_corrected: bool
    # Never populated from candidate labels for distributions
    candidate_consulted_for_exposure_only: bool = False
    # True when related_frame_group was synthesized (not an expert/source identity)
    related_frame_group_synthetic: bool = False

    def identity_key(self) -> str:
        return (
            f"{self.project_id}|{self.cohort_id}|{self.cohort_revision}|"
            f"{self.item_id}|{self.reviewer_role}"
        )

    def group_key(self) -> str:
        return self.related_frame_group or f"{self.source_sha256}:{self.frame_index}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InventoryItemRecord":
        return _from_dict(cls, data)


@dataclass
class ReadinessManifest:
    audit_id: str
    title: str
    description: str
    created_at: str
    task_contract: str
    audit_protocol_version: str = READINESS_PROTOCOL_VERSION
    manifest_schema_version: int = READINESS_MANIFEST_SCHEMA_VERSION
    lifecycle_state: str = "draft"
    selection: ReadinessSelection = field(default_factory=ReadinessSelection)
    selected_cohort_ids: list[str] = field(default_factory=list)
    selected_campaign_ids: list[str] = field(default_factory=list)
    cohort_revisions: dict[str, int] = field(default_factory=dict)
    parent_audit_id: str = ""
    revision_number: int = 1
    revision_reason: str = ""
    frozen_at: str = ""
    manifest_hash: str = ""
    inventory_hash: str = ""
    analyst_id: str = ""
    gate_outcome: str = ""
    parameter_scaling_supported: bool = False
    contract_status_note: str = ""
    compatibility_warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.lifecycle_state not in LIFECYCLE_STATES:
            raise ValueError(f"Invalid lifecycle_state: {self.lifecycle_state!r}")
        if self.task_contract not in TASK_CONTRACTS:
            raise ValueError(f"Invalid task_contract: {self.task_contract!r}")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["selection"] = self.selection.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReadinessManifest":
        payload = dict(data or {})
        sel = ReadinessSelection.from_dict(payload.pop("selection", {}) or {})
        obj = _from_dict(cls, payload)
        obj.selection = sel
        return obj

    def compute_manifest_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("manifest_hash", None)
        return deterministic_hash(payload)


@dataclass
class ReadinessGateRecord:
    audit_id: str
    outcome: str
    blockers: list[str]
    task_contract: str
    audit_snapshot_hash: str
    manifest_hash: str
    unique_item_count: int
    unique_related_frame_groups: int
    unique_sequences: int
    unique_dates: int
    class_distribution: dict[str, int]
    missingness: dict[str, int]
    reviewer_independence: dict[str, Any]
    contamination: dict[str, Any]
    holdout_feasibility: dict[str, Any]
    limitations: list[str]
    required_next_actions: list[str]
    analyst_id: str
    analyst_rationale: str
    authorizes_training: bool = False
    authorizes_architecture_selection: bool = False
    authorizes_holdout_evaluation: bool = False
    authorizes_production_integration: bool = False
    authorizes_mlb_manifest_planning_only: bool = False
    created_at: str = field(default_factory=_utc_now)
    schema_version: int = 1
    gate_id: str = ""

    def __post_init__(self) -> None:
        if self.outcome not in GATE_OUTCOMES:
            raise ValueError(f"Invalid gate outcome: {self.outcome!r}")
        if not self.gate_id:
            self.gate_id = f"gate_{uuid4().hex[:12]}"
        # Hard policy: never authorize training/architecture/holdout eval/production
        self.authorizes_training = False
        self.authorizes_architecture_selection = False
        self.authorizes_holdout_evaluation = False
        self.authorizes_production_integration = False
        self.authorizes_mlb_manifest_planning_only = (
            self.outcome == "F_ready_for_mlb_manifest_planning_only"
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReadinessGateRecord":
        return _from_dict(cls, data)


@dataclass
class HoldoutFeasibilityReport:
    audit_id: str
    assessment_kind: str = "holdout_feasibility_assessment"
    grouping_units: list[str] = field(
        default_factory=lambda: [
            "source",
            "source_date",
            "acquisition_period",
            "sequence",
            "related_frame_group",
            "campaign",
        ]
    )
    untouched_eligible_groups: list[str] = field(default_factory=list)
    development_exposed_groups: list[str] = field(default_factory=list)
    overlapping_groups: list[str] = field(default_factory=list)
    classes_in_untouched: dict[str, int] = field(default_factory=dict)
    classes_absent_from_untouched: list[str] = field(default_factory=list)
    dates_only_in_exposed: list[str] = field(default_factory=list)
    sources_only_in_exposed: list[str] = field(default_factory=list)
    class_aware_group_separated_holdout_appears_possible: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    note_en: str = (
        "This is a holdout feasibility assessment, not a holdout dataset. "
        "Final train/development/holdout manifests belong to ML-B."
    )
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HoldoutFeasibilityReport":
        return _from_dict(cls, data)


def assert_contamination_state(state: str) -> None:
    if state not in CONTAMINATION_STATES:
        raise ValueError(f"Invalid contamination state: {state!r}")
