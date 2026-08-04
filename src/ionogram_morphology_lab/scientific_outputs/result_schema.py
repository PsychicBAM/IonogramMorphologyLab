"""Frame result schema with separate scientific axes; never a single ionogram type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .taxonomy import (
    AMBIGUITY_VALUES,
    LAYER_VALUES,
    MORPHOLOGY_VALUES,
    QUALITY_VALUES,
    ParameterEstimate,
)

# Legacy IML1 morphology → (new morphology, layer remains indeterminate)
_LEGACY_MORPH = {
    "frequency": "frequency_spread",
    "range": "range_spread",
    "mixed": "mixed_spread",
    "none": "clean",
    "diffuse": "diffuse_unspecified",
    "diffuse_unspecified": "diffuse_unspecified",
    "spread_unspecified": "spread_unspecified",
    "artifact": "interference_dominated",
    "other": "other_morphology",
    "abstain": "indeterminate",
    "indeterminate": "indeterminate",
    "not_assessable": "not_assessable",
}


def migrate_legacy_morphology(value: str | None) -> tuple[str, str]:
    """Map IML1 labels to (morphology, layer); legacy labels carry no layer claim."""
    key = (value or "").strip().lower()
    morph = _LEGACY_MORPH.get(key, key if key in MORPHOLOGY_VALUES else "indeterminate")
    return morph, "indeterminate"


def normalize_morphology(value: str | None) -> str:
    key = (value or "indeterminate").strip()
    if key in MORPHOLOGY_VALUES:
        return _LEGACY_MORPH.get(key, key) if key in _LEGACY_MORPH else key
    return _LEGACY_MORPH.get(key.lower(), "indeterminate")


def normalize_ambiguity(value: str | None) -> str:
    key = (value or "indeterminate").strip()
    aliases = {
        "none": "no_visible_ambiguity",
        "possible_ox": "possible_O_X",
        "multiple_branches": "unresolved_branch_structure",
    }
    key = aliases.get(key, key)
    return key if key in AMBIGUITY_VALUES else "indeterminate"


@dataclass
class ScientificFrameResult:
    layer: str = "indeterminate"
    morphology: str = "indeterminate"
    ambiguity: str = "no_visible_ambiguity"
    quality: str = "not_assessable"
    parameter_estimates: list[ParameterEstimate] = field(default_factory=list)
    activated_rule_ids: list[str] = field(default_factory=list)
    contradicting_rule_ids: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    interference_status: str = "low"
    source_citations: list[dict[str, str]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    overlays: dict[str, Any] = field(default_factory=dict)
    method_comparison: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = "1.1"

    def __post_init__(self) -> None:
        self.morphology = normalize_morphology(self.morphology)
        self.ambiguity = normalize_ambiguity(self.ambiguity)
        if self.layer not in LAYER_VALUES:
            raise ValueError(f"Unsupported layer: {self.layer}")
        if self.morphology not in MORPHOLOGY_VALUES:
            raise ValueError(f"Unsupported morphology: {self.morphology}")
        if self.ambiguity not in AMBIGUITY_VALUES:
            raise ValueError(f"Unsupported ambiguity: {self.ambiguity}")
        if self.quality not in QUALITY_VALUES:
            # tolerate unknown quality strings from audit without crashing
            self.quality = "not_assessable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "morphology": self.morphology,
            "ambiguity": self.ambiguity,
            "quality": self.quality,
            "parameter_estimates": [p.to_dict() if hasattr(p, "to_dict") else p for p in self.parameter_estimates],
            "activated_rule_ids": list(self.activated_rule_ids),
            "contradicting_rule_ids": list(self.contradicting_rule_ids),
            "alternatives": list(self.alternatives),
            "interference_status": self.interference_status,
            "source_citations": list(self.source_citations),
            "limitations": list(self.limitations),
            "overlays": dict(self.overlays),
            "method_comparison": list(self.method_comparison),
            "schema_version": self.schema_version,
            # Backward-compatible mirror for older Results browser
            "candidate_morphology": self.morphology,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ScientificFrameResult":
        data = dict(value)
        if "morphology" not in data and "candidate_morphology" in data:
            data["morphology"], data.setdefault("layer", "indeterminate")
            data["morphology"], layer = migrate_legacy_morphology(data.pop("candidate_morphology"))
            data["layer"] = data.get("layer") or layer
        params = []
        for p in data.get("parameter_estimates", []):
            if isinstance(p, ParameterEstimate):
                params.append(p)
            elif isinstance(p, dict):
                # accept units→unit alias
                if "units" in p and "unit" not in p:
                    p = {**p, "unit": p.get("units", "")}
                known = {f.name for f in ParameterEstimate.__dataclass_fields__.values()}  # type: ignore[attr-defined]
                params.append(ParameterEstimate(**{k: v for k, v in p.items() if k in known}))
        data["parameter_estimates"] = params
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


def build_from_pipeline_record(record: dict[str, Any]) -> ScientificFrameResult:
    """Attach separated axes onto an existing analyze_frame record."""
    morph = record.get("morphology") or record.get("candidate_morphology")
    morphology, layer = migrate_legacy_morphology(morph)
    # Prefer explicit fields when present
    layer = record.get("layer", layer)
    morphology = normalize_morphology(record.get("morphology", morphology))
    ox = bool(record.get("possible_ox_confusion"))
    ambiguity = record.get("ambiguity") or ("possible_O_X" if ox else "no_visible_ambiguity")
    quality = record.get("data_quality_status") or record.get("quality") or "not_assessable"
    return ScientificFrameResult(
        layer=layer if layer in LAYER_VALUES else "indeterminate",
        morphology=morphology,
        ambiguity=normalize_ambiguity(ambiguity),
        quality=quality if quality in QUALITY_VALUES else "not_assessable",
        activated_rule_ids=list(record.get("activated_rules") or record.get("activated_rule_ids") or []),
        contradicting_rule_ids=list(record.get("contradicted_rules") or []),
        alternatives=[
            x
            for x in (record.get("top_alternative_1"), record.get("top_alternative_2"))
            if x
        ],
        interference_status=str(record.get("interference_status", "low")),
        source_citations=[
            {"source_id": s, "source_page": p}
            for s, p in zip(record.get("source_ids") or [], record.get("source_pages") or [])
        ],
        limitations=list(record.get("limitations") or []),
    )
