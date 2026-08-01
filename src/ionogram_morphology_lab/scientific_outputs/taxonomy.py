"""Taxonomy axes deliberately kept independent for scientific traceability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# A. Layer / trace identification (never merged into morphology)
LAYER_VALUES = (
    "E",
    "Es",
    "F1",
    "F2",
    "F_unspecified",
    "multiple_layer",
    "no_reliable_layer",
    "other_layer",
    "indeterminate",
)

# B. Morphological appearance (includes legacy IML1 tokens for compatibility)
MORPHOLOGY_VALUES = (
    "clean",
    "diffuse",
    "frequency_spread",
    "range_spread",
    "mixed_spread",
    "spread_unspecified",
    "multiple_branch",
    "possible_multiple_reflection",
    "interference_dominated",
    "low_signal",
    "not_assessable",
    "other_morphology",
    "indeterminate",
    # Legacy IML1 morphology tokens (still accepted; prefer *_spread / clean)
    "frequency",
    "range",
    "mixed",
    "none",
    "artifact",
    "other",
    "abstain",
)

# C. Magnetoionic / branch ambiguity
AMBIGUITY_VALUES = (
    "no_visible_ambiguity",
    "possible_O_X",
    "possible_multiple_reflection",
    "possible_multi_hop",
    "overlapping_layers",
    "unresolved_branch_structure",
    # Legacy aliases
    "none",
    "possible_ox",
    "multiple_branches",
    "source_metadata_incomplete",
    "indeterminate",
)

# D. Data-quality status (separate from layer and morphology)
QUALITY_VALUES = (
    "valid",
    "valid_with_warning",
    "degraded",
    "interference_dominated",
    "all_zero",
    "nonfinite_data",
    "insufficient_metadata",
    "unreadable",
    "not_assessable",
)


@dataclass
class ParameterEstimate:
    """Image-estimated ionogram parameter candidate — never called 'measured' by default."""

    name: str
    value: float | str | None
    unit: str = ""
    estimation_method: str = ""
    profile: str = ""
    calibration_status: str = "uncalibrated"
    confidence: float | None = None
    uncertainty: float | None = None
    source_rule: str = ""
    source_page: str = ""
    limitation: str = "Image-estimated candidate only; not a confirmed ionosonde measurement."
    expert_status: str = "pending"  # pending | accepted | edited | rejected | indeterminate
    metadata: dict[str, Any] = field(default_factory=dict)

    # backward-compatible aliases used by earlier v1.1 draft
    @property
    def units(self) -> str:
        return self.unit

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "estimation_method": self.estimation_method,
            "profile": self.profile,
            "calibration_status": self.calibration_status,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "source_rule": self.source_rule,
            "source_page": self.source_page,
            "limitation": self.limitation,
            "expert_status": self.expert_status,
            "metadata": self.metadata,
        }
