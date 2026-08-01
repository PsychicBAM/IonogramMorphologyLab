"""Scientific rule model — user-extensible, status-aware."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

RULE_STATUSES = (
    "draft",
    "imported_unverified",
    "source_metadata_complete",
    "source_verified",
    "user_tested",
    "project_approved",
    "externally_reviewed",
    "disabled",
    "rejected",
    # pack compatibility aliases
    "proposed",
    "unverified",
)

STRICT_STATUSES = frozenset({"project_approved", "source_verified", "externally_reviewed"})

RULE_TARGETS = (
    "layer",
    "morphology",
    "parameter",
    "interference",
    "ambiguity",
    "quality",
)


@dataclass
class ScientificRule:
    rule_id: str
    name_en: str = ""
    name_ru: str = ""
    category: str = "morphology"  # target axis
    conditions: list[dict[str, Any]] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    proposed_result: str = ""
    status: str = "draft"
    enabled: bool = True
    source_ids: list[str] = field(default_factory=list)
    source_pages: list[str] = field(default_factory=list)
    source_wording_en: str = ""
    source_wording_ru: str = ""
    feature_names: list[str] = field(default_factory=list)
    threshold_origin: str = "provisional"
    applicable_domain: str = ""
    applicable_profiles: list[str] = field(default_factory=list)
    applicable_instruments: list[str] = field(default_factory=list)
    frequency_range: list[float] = field(default_factory=list)
    height_range: list[float] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    abstention_condition: str = ""
    score: float = 0.0
    minimum_evidence: float = 0.0
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    verification_status: str = "unverified"
    implementation_status: str = "disabled"
    version: str = "1.1.1"
    authors: str = ""
    year: str = ""
    title: str = ""
    printed_page: str = ""
    pdf_page: str = ""
    quotation: str = ""
    rights_note: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ScientificRule":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        data = {k: v for k, v in (value or {}).items() if k in known}
        if not data.get("proposed_result") and data.get("outputs"):
            outs = data["outputs"]
            data["proposed_result"] = outs.get("morphology") or outs.get("layer") or outs.get("result") or ""
        if not data.get("name_en"):
            data["name_en"] = data.get("rule_id", "unnamed")
        return cls(**data)


def filter_rules_by_status(rules: list[ScientificRule], mode: str = "standard") -> list[ScientificRule]:
    """Scientific Strict exposes only approved / source-verified / externally reviewed rules."""
    mode_n = mode.lower().replace("-", "_").replace(" ", "_")
    if mode_n in {"scientific_strict", "strict"}:
        return [r for r in rules if r.enabled and r.status in STRICT_STATUSES and r.status != "disabled"]
    if mode_n == "fast_preview":
        return [r for r in rules if r.enabled and r.status in STRICT_STATUSES | {"project_approved", "user_tested"}]
    # standard / custom — experimental allowed with warning elsewhere
    return [r for r in rules if r.enabled and r.status not in {"disabled", "rejected"}]
