"""Shared types for Feature Pipeline V2 — measurements with uncertainty."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

FEATURE_VERSION = "iml2-0.2.0"


@dataclass
class MeasuredFeature:
    feature_id: str
    value: float | str | None
    unit: str = ""
    valid: bool = True
    uncertainty: float | None = None
    confidence_status: str = "unknown"
    reason_invalid: str = ""
    affected_region: str = ""
    missing_prerequisites: list[str] = field(default_factory=list)
    estimator: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DerivedRepresentation:
    name: str
    method: str
    version: str
    parameters: dict[str, Any]
    input_hash: str
    output_hash: str
    status: str  # diagnostic | scientific
    array: np.ndarray | None = None

    def meta_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("array", None)
        d["shape"] = list(self.array.shape) if self.array is not None else None
        return d


@dataclass
class CenterlineRecord:
    branch_id: int
    component_id: int
    points_rc: list[tuple[int, int]]  # (row, col)
    frequency_span_bins: tuple[int, int]
    height_span_bins: tuple[int, int]
    point_count: int
    continuity: float
    gap_fraction: float
    slope: float
    curvature: float
    interference_overlap: float
    quality_status: str
    member_component_ids: list[int] = field(default_factory=list)
    component_confidence: float = 0.0
    floor_overlap_fraction: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineV2Result:
    feature_version: str
    signal_contract_id: str
    profile_id: str
    frame_index: int
    source_mat_sha256: str
    processing_version: str
    quality_status: str
    features: dict[str, MeasuredFeature]
    masks: dict[str, np.ndarray]
    representations: dict[str, DerivedRepresentation]
    centerlines: list[CenterlineRecord]
    experimental_label_en: str
    experimental_label_ru: str
    elapsed_s: float = 0.0
    notes: list[str] = field(default_factory=list)
    raw_centerlines: list[CenterlineRecord] = field(default_factory=list)
    component_decisions: dict[str, Any] = field(default_factory=dict)
    oversegmentation_suspected: bool = False
    branch_records: list[dict[str, Any]] = field(default_factory=list)

    def feature_table(self) -> list[dict[str, Any]]:
        return [f.to_dict() for f in self.features.values()]

    def to_serializable(self) -> dict[str, Any]:
        return {
            "feature_version": self.feature_version,
            "signal_contract_id": self.signal_contract_id,
            "profile_id": self.profile_id,
            "frame_index": self.frame_index,
            "source_mat_sha256": self.source_mat_sha256,
            "processing_version": self.processing_version,
            "quality_status": self.quality_status,
            "features": {k: v.to_dict() for k, v in self.features.items()},
            "centerlines": [c.to_dict() for c in self.centerlines],
            "branch_records": list(self.branch_records),
            "raw_centerlines": [c.to_dict() for c in self.raw_centerlines],
            "component_decisions": self.component_decisions,
            "oversegmentation_suspected": self.oversegmentation_suspected,
            "mask_shapes": {k: list(v.shape) for k, v in self.masks.items()},
            "representations": [r.meta_dict() for r in self.representations.values()],
            "experimental_label_en": self.experimental_label_en,
            "experimental_label_ru": self.experimental_label_ru,
            "elapsed_s": self.elapsed_s,
            "notes": list(self.notes),
            "shadow_mode": True,
            "affects_classification": False,
        }
