"""Dataclasses for morphology review corpus records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ionogram_morphology_lab.morphology_candidate.types import CANDIDATE_ENGINE_VERSION
from ionogram_morphology_lab.morphology_review_corpus.constants import (
    ADJUDICATION_SCHEMA_VERSION,
    REVIEW_CORPUS_SCHEMA_VERSION,
    REVIEW_RECORD_SCHEMA_VERSION,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import (
    deterministic_hash,
    validate_sha256,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import (
    AMBIGUITY_CODES,
    ASSESSABILITY_CODES,
    CONFIDENCE_CODES,
    HUMAN_MORPHOLOGY_CODES,
    INTERFERENCE_CODES,
    rationale_required,
    validate_human_morphology,
)
from ionogram_morphology_lab.morphology_review_corpus.protocol import CohortProtocol


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _from_dict(cls, data: dict[str, Any]):
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ReviewerIdentity:
    reviewer_id: str
    display_alias: str
    role: str = "reviewer"  # reviewer | second_reviewer | adjudicator
    organization: str = ""
    reviewer_profile_version: str = "1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewerIdentity":
        return _from_dict(cls, data)


@dataclass
class ReviewItem:
    cohort_id: str
    item_id: str
    source_inventory_id: str
    source_display_name: str
    source_sha256: str
    frame_index: int
    frame_time: str = ""
    datetime_metadata: str = ""
    feature_version: str = ""
    diagnostics_cache_id: str = ""
    v2_result_hash: str = ""
    v2_quality_status: str = ""
    candidate_result_hash: str = ""
    candidate_engine_version: str = CANDIDATE_ENGINE_VERSION
    ruleset_id: str = "iml-morph-candidate-rules"
    ruleset_hash: str = ""
    evidence_ledger_hash: str = ""
    rendering_snapshot: dict[str, Any] = field(default_factory=dict)
    item_status: str = "item_pending"
    inclusion_reason: str = ""
    sampling_stratum: str = ""
    manifest_position: int = 0
    partition: str = "pilot_review"
    unavailable_reason: str = ""
    grouping: dict[str, str] = field(default_factory=dict)
    parent_item_id: str = ""

    def __post_init__(self) -> None:
        if self.source_sha256 and self.item_status != "item_unavailable":
            self.source_sha256 = validate_sha256(self.source_sha256)
        elif self.source_sha256:
            # Retain original (possibly invalid) SHA for unavailable import rows
            self.source_sha256 = str(self.source_sha256).lower()
        if self.partition not in ("pilot_review", "future_holdout", "excluded"):
            raise ValueError(f"Invalid partition: {self.partition!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewItem":
        return _from_dict(cls, data)

    def identity_key(self) -> tuple[str, int]:
        return (self.source_sha256.lower(), int(self.frame_index))


@dataclass
class CandidateSnapshot:
    cohort_id: str
    item_id: str
    source_sha256: str
    frame_index: int
    candidate_engine_version: str
    ruleset_id: str
    ruleset_hash: str
    result_contract_version: int
    diagnostics_cache_id: str
    candidate_state: str
    ordinal_strength: str
    assessability_state: str
    evidence_ledger: list[dict[str, Any]]
    result_hash: str
    ledger_hash: str
    generated_or_cached: str
    timestamp: str = field(default_factory=_utc_now)
    snapshot_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_hash(self) -> "CandidateSnapshot":
        payload = self.to_dict()
        payload.pop("snapshot_hash", None)
        return CandidateSnapshot(**{**payload, "snapshot_hash": deterministic_hash(payload)})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateSnapshot":
        return _from_dict(cls, data)


@dataclass
class BlindReviewRecord:
    review_id: str
    reviewer_id: str
    reviewer_role: str
    review_round: int
    cohort_id: str
    item_id: str
    morphology: str
    assessability: str
    interference: list[str]
    ambiguity: str
    confidence: str
    observations: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    created_at: str = field(default_factory=_utc_now)
    ui_language: str = "en"
    build_identity: str = "ML-A.1a.2"
    schema_version: int = REVIEW_RECORD_SCHEMA_VERSION
    record_hash: str = ""
    prior_review_id: str = ""
    revision_reason: str = ""
    locked: bool = True
    superseded: bool = False
    supersedes_review_id: str = ""
    post_reveal_revision: bool = False
    candidate_revealed_before_this_record: bool = False

    def __post_init__(self) -> None:
        validate_human_morphology(self.morphology)
        if self.assessability not in ASSESSABILITY_CODES:
            raise ValueError(f"Invalid assessability: {self.assessability!r}")
        for flag in self.interference:
            if flag not in INTERFERENCE_CODES:
                raise ValueError(f"Invalid interference flag: {flag!r}")
        if self.ambiguity not in AMBIGUITY_CODES:
            raise ValueError(f"Invalid ambiguity: {self.ambiguity!r}")
        if self.confidence not in CONFIDENCE_CODES:
            raise ValueError(f"Invalid confidence: {self.confidence!r}")
        if rationale_required(
            morphology=self.morphology,
            interference_flags=self.interference,
            is_revision=bool(self.prior_review_id),
            is_post_reveal_revision=self.post_reveal_revision,
        ) and not (self.rationale or "").strip():
            raise ValueError("Rationale is required for this blind review decision")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_hash(self) -> "BlindReviewRecord":
        payload = self.to_dict()
        payload.pop("record_hash", None)
        return BlindReviewRecord(**{**payload, "record_hash": deterministic_hash(payload)})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlindReviewRecord":
        return _from_dict(cls, data)

    @classmethod
    def create(
        cls,
        *,
        reviewer_id: str,
        reviewer_role: str,
        review_round: int,
        cohort_id: str,
        item_id: str,
        morphology: str,
        assessability: str,
        interference: list[str],
        ambiguity: str,
        confidence: str,
        rationale: str = "",
        observations: dict[str, Any] | None = None,
        ui_language: str = "en",
        build_identity: str = "ML-A.1a.2",
        prior_review_id: str = "",
        revision_reason: str = "",
        post_reveal_revision: bool = False,
        candidate_revealed_before_this_record: bool = False,
    ) -> "BlindReviewRecord":
        rec = cls(
            review_id=str(uuid4()),
            reviewer_id=reviewer_id,
            reviewer_role=reviewer_role,
            review_round=review_round,
            cohort_id=cohort_id,
            item_id=item_id,
            morphology=morphology,
            assessability=assessability,
            interference=list(interference),
            ambiguity=ambiguity,
            confidence=confidence,
            observations=dict(observations or {}),
            rationale=rationale,
            ui_language=ui_language,
            build_identity=build_identity,
            prior_review_id=prior_review_id,
            revision_reason=revision_reason,
            post_reveal_revision=post_reveal_revision,
            candidate_revealed_before_this_record=candidate_revealed_before_this_record,
            locked=True,
        )
        return rec.with_hash()


@dataclass
class RevealComparison:
    comparison_id: str
    cohort_id: str
    item_id: str
    review_id: str
    human_morphology: str
    candidate_state: str
    candidate_strength: str
    agreement_status: str
    reviewer_note_codes: list[str] = field(default_factory=list)
    comparison_comment: str = ""
    created_at: str = field(default_factory=_utc_now)
    build_identity: str = "ML-A.1a.2"
    record_hash: str = ""
    # Append-only revision linkage (Phase 4C.3)
    prior_comparison_id: str = ""
    supersedes_comparison_id: str = ""
    revision_reason: str = ""
    comparison_contract_version: int = 1
    candidate_result_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_hash(self) -> "RevealComparison":
        payload = self.to_dict()
        payload.pop("record_hash", None)
        return RevealComparison(**{**payload, "record_hash": deterministic_hash(payload)})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RevealComparison":
        return _from_dict(cls, data)


@dataclass
class AdjudicationRecord:
    adjudication_id: str
    adjudicator_id: str
    cohort_id: str
    item_id: str
    input_review_ids: list[str]
    adjudicated_morphology: str
    assessability: str
    interference: list[str]
    ambiguity: str
    rationale: str
    created_at: str = field(default_factory=_utc_now)
    schema_version: int = ADJUDICATION_SCHEMA_VERSION
    build_identity: str = "ML-A.1a.2"
    record_hash: str = ""
    locked: bool = True
    label: str = "adjudicated_expert_reference"

    def __post_init__(self) -> None:
        if self.adjudicated_morphology not in HUMAN_MORPHOLOGY_CODES:
            raise ValueError(f"Invalid adjudicated morphology: {self.adjudicated_morphology!r}")
        if not (self.rationale or "").strip():
            raise ValueError("Adjudication rationale is required")
        if self.label == "ground_truth":
            raise ValueError("Adjudication must not be labeled ground_truth")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_hash(self) -> "AdjudicationRecord":
        payload = self.to_dict()
        payload.pop("record_hash", None)
        return AdjudicationRecord(**{**payload, "record_hash": deterministic_hash(payload)})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdjudicationRecord":
        return _from_dict(cls, data)


@dataclass
class CohortManifest:
    cohort_id: str
    manifest_schema_version: int = REVIEW_CORPUS_SCHEMA_VERSION
    review_schema_version: int = REVIEW_RECORD_SCHEMA_VERSION
    created_at: str = field(default_factory=_utc_now)
    creation_tool_version: str = "ML-A.1a.2"
    candidate_engine_version: str = CANDIDATE_ENGINE_VERSION
    ruleset_id: str = "iml-morph-candidate-rules"
    ruleset_hash: str = ""
    feature_version: str = ""
    source_inventory_snapshot: dict[str, Any] = field(default_factory=dict)
    sampling_method: str = "manual"
    random_seed: int | None = None
    protocol_hash: str = ""
    manifest_hash: str = ""
    frozen: bool = False
    frozen_at: str = ""
    parent_cohort_id: str = ""
    revision_reason: str = ""
    revision_number: int = 0
    created_from_manifest_hash: str = ""
    created_from_protocol_hash: str = ""
    archived: bool = False  # scientific field unused for UI archive; workspace owns visibility
    item_count: int = 0
    designation_en: str = ""
    designation_ru: str = ""
    legacy_synthetic: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def compute_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("manifest_hash", None)
        return deterministic_hash(payload)

    def with_hash(self) -> "CohortManifest":
        return CohortManifest(**{**self.to_dict(), "manifest_hash": self.compute_hash()})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CohortManifest":
        return _from_dict(cls, data)


@dataclass
class AuditEvent:
    event_id: str
    event_type: str
    created_at: str
    cohort_id: str = ""
    item_id: str = ""
    actor_id: str = ""
    prior_record_hash: str = ""
    new_record_hash: str = ""
    build_identity: str = "ML-A.1a.2"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        event_type: str,
        *,
        cohort_id: str = "",
        item_id: str = "",
        actor_id: str = "",
        prior_record_hash: str = "",
        new_record_hash: str = "",
        details: dict[str, Any] | None = None,
        build_identity: str = "ML-A.1a.2",
    ) -> "AuditEvent":
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            created_at=_utc_now(),
            cohort_id=cohort_id,
            item_id=item_id,
            actor_id=actor_id,
            prior_record_hash=prior_record_hash,
            new_record_hash=new_record_hash,
            build_identity=build_identity,
            details=dict(details or {}),
        )


# Re-export protocol for convenience
__all__ = [
    "AdjudicationRecord",
    "AuditEvent",
    "BlindReviewRecord",
    "CandidateSnapshot",
    "CohortManifest",
    "CohortProtocol",
    "RevealComparison",
    "ReviewItem",
    "ReviewerIdentity",
]
