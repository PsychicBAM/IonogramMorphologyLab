"""Campaign domain records (Phase 4C.3)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ionogram_morphology_lab.morphology_review_campaign.constants import (
    BUILD_IDENTITY_DEFAULT,
    CAMPAIGN_DESIGNATION_EN,
    CAMPAIGN_DESIGNATION_RU,
    CAMPAIGN_PROTOCOL_SCHEMA_VERSION,
    CAMPAIGN_SCHEMA_VERSION,
    CAMPAIGN_STATES,
    COHORT_ROLES,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TimeWindow:
    start_frame: int
    end_frame: int
    step: int = 1
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TimeWindow":
        return cls(
            start_frame=int(d.get("start_frame") or 1),
            end_frame=int(d.get("end_frame") or 1),
            step=max(1, int(d.get("step") or 1)),
            label=str(d.get("label") or ""),
        )


@dataclass
class SourceScopeEntry:
    source_sha256: str
    source_display_name: str = ""
    source_inventory_id: str = ""
    date_hint: str = ""
    available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_sha256": (self.source_sha256 or "").lower(),
            "source_display_name": self.source_display_name,
            "source_inventory_id": self.source_inventory_id,
            "date_hint": self.date_hint,
            "available": bool(self.available),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SourceScopeEntry":
        return cls(
            source_sha256=str(d.get("source_sha256") or "").lower(),
            source_display_name=str(d.get("source_display_name") or ""),
            source_inventory_id=str(d.get("source_inventory_id") or ""),
            date_hint=str(d.get("date_hint") or ""),
            available=bool(d.get("available", True)),
        )


@dataclass
class ReviewerPlan:
    first_reviewer_id: str = ""
    first_reviewer_alias: str = ""
    second_reviewer_id: str = ""
    second_reviewer_alias: str = ""
    second_reviewer_optional: bool = True
    adjudicator_id: str = ""
    adjudicator_alias: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "ReviewerPlan":
        d = d or {}
        return cls(
            first_reviewer_id=str(d.get("first_reviewer_id") or ""),
            first_reviewer_alias=str(d.get("first_reviewer_alias") or ""),
            second_reviewer_id=str(d.get("second_reviewer_id") or ""),
            second_reviewer_alias=str(d.get("second_reviewer_alias") or ""),
            second_reviewer_optional=bool(d.get("second_reviewer_optional", True)),
            adjudicator_id=str(d.get("adjudicator_id") or ""),
            adjudicator_alias=str(d.get("adjudicator_alias") or ""),
        )


@dataclass
class SamplingPlan:
    method: str = "deterministic_random"  # manual|all_eligible|deterministic_random|stratified|imported_manifest
    seed: int = 42
    target_count: int = 0
    strata_key: str = "date_hint"
    per_stratum: int = 1
    keep_adjacent_frames_together: bool = True
    note_en: str = "Operational planning target only — not a scientifically required sample size."
    note_ru: str = (
        "Только операционная цель планирования — не научно обязательный объём выборки."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "SamplingPlan":
        d = d or {}
        return cls(
            method=str(d.get("method") or "deterministic_random"),
            seed=int(d.get("seed") or 42),
            target_count=int(d.get("target_count") or 0),
            strata_key=str(d.get("strata_key") or "date_hint"),
            per_stratum=max(1, int(d.get("per_stratum") or 1)),
            keep_adjacent_frames_together=bool(
                d.get("keep_adjacent_frames_together", True)
            ),
            note_en=str(d.get("note_en") or cls.note_en),
            note_ru=str(d.get("note_ru") or cls.note_ru),
        )


@dataclass
class CampaignProtocol:
    protocol_version: int = CAMPAIGN_PROTOCOL_SCHEMA_VERSION
    reveal_policy: str = "strict_cohort_blinding"
    designation_en: str = CAMPAIGN_DESIGNATION_EN
    designation_ru: str = CAMPAIGN_DESIGNATION_RU
    second_reviewer_optional: bool = True
    candidate_shadow_only: bool = True
    scientifically_validated: bool = False
    protocol_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_hash(self) -> "CampaignProtocol":
        payload = self.to_dict()
        payload.pop("protocol_hash", None)
        self.protocol_hash = deterministic_hash(payload)
        return self

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CampaignProtocol":
        return cls(
            protocol_version=int(
                d.get("protocol_version") or CAMPAIGN_PROTOCOL_SCHEMA_VERSION
            ),
            reveal_policy=str(d.get("reveal_policy") or "strict_cohort_blinding"),
            designation_en=str(d.get("designation_en") or CAMPAIGN_DESIGNATION_EN),
            designation_ru=str(d.get("designation_ru") or CAMPAIGN_DESIGNATION_RU),
            second_reviewer_optional=bool(d.get("second_reviewer_optional", True)),
            candidate_shadow_only=bool(d.get("candidate_shadow_only", True)),
            scientifically_validated=bool(d.get("scientifically_validated", False)),
            protocol_hash=str(d.get("protocol_hash") or ""),
        )


@dataclass
class CampaignManifest:
    campaign_id: str
    display_name: str
    designation_en: str = CAMPAIGN_DESIGNATION_EN
    designation_ru: str = CAMPAIGN_DESIGNATION_RU
    description: str = ""
    state: str = "draft"
    created_at_utc: str = ""
    created_by: str = ""
    schema_version: int = CAMPAIGN_SCHEMA_VERSION
    protocol_version: int = CAMPAIGN_PROTOCOL_SCHEMA_VERSION
    project_identity: str = ""
    source_scope: list[dict[str, Any]] = field(default_factory=list)
    time_windows: list[dict[str, Any]] = field(default_factory=list)
    target_review_count: int = 0
    actual_item_count: int = 0
    reviewer_plan: dict[str, Any] = field(default_factory=dict)
    reveal_policy: str = "strict_cohort_blinding"
    sampling_plan: dict[str, Any] = field(default_factory=dict)
    grouping_plan: dict[str, Any] = field(default_factory=dict)
    selected_item_fingerprints: list[str] = field(default_factory=list)
    protocol_hash: str = ""
    campaign_hash: str = ""
    build_identity: str = BUILD_IDENTITY_DEFAULT
    shadow_only: bool = True
    scientifically_validated: bool = False

    def __post_init__(self) -> None:
        if self.state not in CAMPAIGN_STATES:
            raise ValueError(f"Invalid campaign state: {self.state!r}")
        if not self.created_at_utc:
            self.created_at_utc = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_hash(self) -> "CampaignManifest":
        payload = self.to_dict()
        payload.pop("campaign_hash", None)
        self.campaign_hash = deterministic_hash(payload)
        return self

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CampaignManifest":
        return cls(
            campaign_id=str(d.get("campaign_id") or ""),
            display_name=str(d.get("display_name") or ""),
            designation_en=str(d.get("designation_en") or CAMPAIGN_DESIGNATION_EN),
            designation_ru=str(d.get("designation_ru") or CAMPAIGN_DESIGNATION_RU),
            description=str(d.get("description") or ""),
            state=str(d.get("state") or "draft"),
            created_at_utc=str(d.get("created_at_utc") or ""),
            created_by=str(d.get("created_by") or ""),
            schema_version=int(d.get("schema_version") or CAMPAIGN_SCHEMA_VERSION),
            protocol_version=int(
                d.get("protocol_version") or CAMPAIGN_PROTOCOL_SCHEMA_VERSION
            ),
            project_identity=str(d.get("project_identity") or ""),
            source_scope=list(d.get("source_scope") or []),
            time_windows=list(d.get("time_windows") or []),
            target_review_count=int(d.get("target_review_count") or 0),
            actual_item_count=int(d.get("actual_item_count") or 0),
            reviewer_plan=dict(d.get("reviewer_plan") or {}),
            reveal_policy=str(d.get("reveal_policy") or "strict_cohort_blinding"),
            sampling_plan=dict(d.get("sampling_plan") or {}),
            grouping_plan=dict(d.get("grouping_plan") or {}),
            selected_item_fingerprints=list(d.get("selected_item_fingerprints") or []),
            protocol_hash=str(d.get("protocol_hash") or ""),
            campaign_hash=str(d.get("campaign_hash") or ""),
            build_identity=str(d.get("build_identity") or BUILD_IDENTITY_DEFAULT),
            shadow_only=bool(d.get("shadow_only", True)),
            scientifically_validated=bool(d.get("scientifically_validated", False)),
        )


@dataclass
class CohortLink:
    link_id: str
    campaign_id: str
    cohort_id: str
    cohort_role: str
    manifest_hash: str
    linked_at_utc: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if self.cohort_role not in COHORT_ROLES:
            raise ValueError(f"Invalid cohort role: {self.cohort_role!r}")
        if not self.linked_at_utc:
            self.linked_at_utc = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        *,
        campaign_id: str,
        cohort_id: str,
        cohort_role: str,
        manifest_hash: str,
        note: str = "",
    ) -> "CohortLink":
        return cls(
            link_id=str(uuid4()),
            campaign_id=campaign_id,
            cohort_id=cohort_id,
            cohort_role=cohort_role,
            manifest_hash=manifest_hash,
            note=note,
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CohortLink":
        return cls(
            link_id=str(d.get("link_id") or ""),
            campaign_id=str(d.get("campaign_id") or ""),
            cohort_id=str(d.get("cohort_id") or ""),
            cohort_role=str(d.get("cohort_role") or "first_review"),
            manifest_hash=str(d.get("manifest_hash") or ""),
            linked_at_utc=str(d.get("linked_at_utc") or ""),
            note=str(d.get("note") or ""),
        )


@dataclass
class AssignmentRecord:
    assignment_id: str
    campaign_id: str
    reviewer_id: str
    reviewer_alias: str
    role: str  # first_reviewer | second_reviewer | adjudicator
    cohort_id: str = ""
    created_at_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        *,
        campaign_id: str,
        reviewer_id: str,
        reviewer_alias: str,
        role: str,
        cohort_id: str = "",
    ) -> "AssignmentRecord":
        return cls(
            assignment_id=str(uuid4()),
            campaign_id=campaign_id,
            reviewer_id=reviewer_id,
            reviewer_alias=reviewer_alias,
            role=role,
            cohort_id=cohort_id,
            created_at_utc=_utc_now(),
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AssignmentRecord":
        return cls(
            assignment_id=str(d.get("assignment_id") or ""),
            campaign_id=str(d.get("campaign_id") or ""),
            reviewer_id=str(d.get("reviewer_id") or ""),
            reviewer_alias=str(d.get("reviewer_alias") or ""),
            role=str(d.get("role") or ""),
            cohort_id=str(d.get("cohort_id") or ""),
            created_at_utc=str(d.get("created_at_utc") or ""),
        )


@dataclass
class CampaignAuditEvent:
    event_id: str
    event_type: str
    campaign_id: str
    details: dict[str, Any] = field(default_factory=dict)
    created_at_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        event_type: str,
        *,
        campaign_id: str,
        details: dict[str, Any] | None = None,
    ) -> "CampaignAuditEvent":
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            campaign_id=campaign_id,
            details=dict(details or {}),
            created_at_utc=_utc_now(),
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CampaignAuditEvent":
        return cls(
            event_id=str(d.get("event_id") or ""),
            event_type=str(d.get("event_type") or ""),
            campaign_id=str(d.get("campaign_id") or ""),
            details=dict(d.get("details") or {}),
            created_at_utc=str(d.get("created_at_utc") or ""),
        )
