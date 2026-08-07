"""Dataclasses for ML-B.1 dataset manifest sets."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ionogram_morphology_lab.ml_dataset_manifests.constants import (
    DATASET_ROLES,
    DEFAULT_GROUPING_POLICY,
    GROUPING_POLICIES,
    LIFECYCLE_STATES,
    MANIFEST_PROTOCOL_VERSION,
    MANIFEST_SET_SCHEMA_VERSION,
    SPLIT_POLICY_VERSION,
    TASK_CONTRACTS,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _from_dict(cls, data: dict[str, Any]):
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in (data or {}).items() if k in known})


@dataclass
class SplitPolicy:
    policy_id: str = DEFAULT_GROUPING_POLICY
    policy_version: str = SPLIT_POLICY_VERSION
    included_relations: list[str] = field(default_factory=list)
    unavailable_relations: list[str] = field(default_factory=list)
    fallback_decisions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    deterministic_ordering: str = "sorted_item_identity_then_group_id"
    seed: int = 0
    requested_train_share: float | None = None
    requested_development_share: float | None = None
    requested_holdout_share: float | None = None
    required_target_classes: list[str] = field(default_factory=list)
    planning_mode: str = "deterministic_proposal"  # or manual_atomic_group_assignment
    protocol_exceptions: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.policy_id not in GROUPING_POLICIES:
            raise ValueError(f"Invalid grouping policy: {self.policy_id!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SplitPolicy":
        return _from_dict(cls, data or {})


@dataclass
class ManifestItemRecord:
    """Candidate-independent planning row projected from a readiness inventory item."""

    project_id: str
    cohort_id: str
    cohort_revision: int
    item_id: str
    task_contract: str
    source_inventory_id: str
    source_display_name: str
    source_sha256: str
    source_date: str
    frame_index: int
    frame_time: str
    related_frame_group: str
    sequence_id: str
    campaign_id: str
    acquisition_period: str
    morphology: str
    assessability: str
    ambiguity: str
    interference: list[str]
    reviewer_role: str
    reviewer_alias: str
    contamination_state: str
    eligible_future_development: bool
    eligible_untouched_holdout: bool
    exclusion_reason: str
    missingness_category: str
    independent_second_review_available: bool
    target_label: str
    atomic_group_id: str = ""
    role: str = "excluded"
    identity_issues: list[str] = field(default_factory=list)

    def identity_key(self) -> str:
        return (
            f"{self.project_id}|{self.cohort_id}|{self.cohort_revision}|"
            f"{self.item_id}|{self.task_contract}"
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ManifestItemRecord":
        return _from_dict(cls, data or {})

    def public_holdout_dict(self) -> dict[str, Any]:
        """Identity-only payload — no task target labels."""
        return {
            "project_id": self.project_id,
            "cohort_id": self.cohort_id,
            "cohort_revision": self.cohort_revision,
            "item_id": self.item_id,
            "task_contract": self.task_contract,
            "source_inventory_id": self.source_inventory_id,
            "source_display_name": self.source_display_name,
            "source_sha256": self.source_sha256,
            "source_date": self.source_date,
            "frame_index": self.frame_index,
            "frame_time": self.frame_time,
            "related_frame_group": self.related_frame_group,
            "sequence_id": self.sequence_id,
            "campaign_id": self.campaign_id,
            "atomic_group_id": self.atomic_group_id,
            "role": "untouched_holdout",
            "contamination_state": self.contamination_state,
        }

    def reference_label_dict(self) -> dict[str, Any]:
        return {
            "identity_key": self.identity_key(),
            "item_id": self.item_id,
            "cohort_id": self.cohort_id,
            "cohort_revision": self.cohort_revision,
            "task_contract": self.task_contract,
            "target_label": self.target_label,
            "morphology": self.morphology,
            "assessability": self.assessability,
            "ambiguity": self.ambiguity,
            "interference": list(self.interference),
        }


@dataclass
class AtomicGroup:
    group_id: str
    item_identity_keys: list[str]
    item_ids: list[str]
    source_shas: list[str]
    source_dates: list[str]
    sequence_ids: list[str]
    related_frame_groups: list[str]
    campaign_ids: list[str]
    target_labels: list[str]
    contamination_states: list[str]
    eligible_untouched_holdout: bool
    role: str = "excluded"
    grouping_edges: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AtomicGroup":
        return _from_dict(cls, data or {})


@dataclass
class ManifestSet:
    manifest_set_id: str
    title: str
    description: str
    project_id: str
    created_at: str
    analyst_id: str
    source_readiness_audit_id: str
    source_readiness_manifest_hash: str
    source_readiness_gate_outcome: str
    task_contract: str
    lifecycle_state: str = "draft"
    manifest_protocol_version: str = MANIFEST_PROTOCOL_VERSION
    schema_version: int = MANIFEST_SET_SCHEMA_VERSION
    split_policy_version: str = SPLIT_POLICY_VERSION
    grouping_policy: str = DEFAULT_GROUPING_POLICY
    seed: int = 0
    parent_manifest_set_id: str = ""
    revision_number: int = 1
    revision_reason: str = ""
    frozen_at: str = ""
    validated_at: str = ""
    validated_content_hash: str = ""
    last_validation_ok: bool = False
    item_count: int = 0
    group_count: int = 0
    role_counts: dict[str, int] = field(default_factory=dict)
    group_role_counts: dict[str, int] = field(default_factory=dict)
    manifest_set_hash: str = ""
    train_manifest_hash: str = ""
    development_manifest_hash: str = ""
    holdout_public_manifest_hash: str = ""
    holdout_reference_labels_hash: str = ""
    excluded_manifest_hash: str = ""
    holdout_lock_hash: str = ""
    authorizes_training: bool = False
    authorizes_mlc: bool = False
    authorizes_holdout_evaluation: bool = False
    holdout_sealed: bool = False
    freeze_blockers: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    compatibility_warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.lifecycle_state not in LIFECYCLE_STATES:
            raise ValueError(f"Invalid lifecycle_state: {self.lifecycle_state!r}")
        if self.task_contract not in TASK_CONTRACTS:
            raise ValueError(f"Invalid task_contract: {self.task_contract!r}")
        # Hard policy
        self.authorizes_training = False
        self.authorizes_mlc = False
        self.authorizes_holdout_evaluation = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ManifestSet":
        return _from_dict(cls, data or {})

    def compute_manifest_set_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("manifest_set_hash", None)
        return deterministic_hash(payload)


@dataclass
class HoldoutLockRecord:
    manifest_set_id: str
    public_manifest_hash: str
    reference_labels_hash: str
    sealed_at: str
    workflow_seal_note: str
    unlock_protocol: str = "future_ml_e_only"
    unlock_available_in_mlb: bool = False
    lock_hash: str = ""

    def __post_init__(self) -> None:
        self.unlock_available_in_mlb = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HoldoutLockRecord":
        return _from_dict(cls, data or {})

    def compute_lock_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("lock_hash", None)
        return deterministic_hash(payload)


def new_manifest_set_id() -> str:
    return f"manifest_{uuid4().hex[:12]}"
