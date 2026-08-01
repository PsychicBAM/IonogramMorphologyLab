"""Source-traceable reference atlas (metadata-first; no restricted figures by default)."""

from __future__ import annotations

import csv
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import numpy as np

from ionogram_morphology_lab.similarity.compare import compare_ionograms
from ionogram_morphology_lab.utils.paths import app_root


@dataclass
class ReferenceCase:
    reference_case_id: str
    source_id: str
    authors: str
    year: str
    title: str
    exact_page: str
    figure: str
    panel: str
    original_terminology: str
    canonical_terminology: str
    instrument: str
    station_regime: str
    frequency_range: str
    range_height_axis: str
    morphology_described: str
    interpretation_strength: str
    limitations: str
    rights_status: str
    internal_image_availability: str
    applicability_notes: str
    domain_restrictions: str
    descriptor_vector_json: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReferenceMatch:
    case: ReferenceCase
    similarity_metrics: dict[str, float]
    registration_confidence: float
    wording_en: str
    wording_ru: str
    domain_mismatch_warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "reference_case_id": self.case.reference_case_id,
            "citation": f"{self.case.authors} ({self.case.year}) p.{self.case.exact_page}",
            "source_id": self.case.source_id,
            "source_page": self.case.exact_page,
            "source_terminology": self.case.original_terminology,
            "canonical_terminology": self.case.canonical_terminology,
            "similarity_metrics": self.similarity_metrics,
            "registration_confidence": self.registration_confidence,
            "applicable_regime": self.case.station_regime,
            "rights_status": self.case.rights_status,
            "wording_en": self.wording_en,
            "wording_ru": self.wording_ru,
            "domain_mismatch_warning": self.domain_mismatch_warning,
            "limitations": self.case.limitations,
        }
        return d


def load_atlas(path: Path | str | None = None) -> list[ReferenceCase]:
    path = Path(path) if path else app_root() / "knowledge_base" / "REFERENCE_ATLAS_CASES.csv"
    if not path.exists():
        return []
    cases: list[ReferenceCase] = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            cases.append(ReferenceCase(**{k: row.get(k, "") for k in ReferenceCase.__dataclass_fields__}))
    return cases


class ReferenceAtlas:
    def __init__(self, cases: list[ReferenceCase] | None = None):
        self.cases = cases if cases is not None else load_atlas()

    def by_canonical(self, term: str) -> list[ReferenceCase]:
        return [c for c in self.cases if c.canonical_terminology == term]

    def find_nearest(
        self,
        features: dict[str, float],
        candidate_morphology: str | None = None,
        top_k: int = 5,
        user_regime: str = "midlatitude",
    ) -> list[ReferenceMatch]:
        """
        Metadata/descriptor matching when images are rights-restricted.
        Wording: structurally similar — never 'same physical event'.
        """
        scored: list[tuple[float, ReferenceCase]] = []
        for case in self.cases:
            score = 0.0
            if candidate_morphology and case.canonical_terminology == candidate_morphology:
                score += 2.0
            # descriptor soft match on a few features if encoded
            if "frequency" in case.canonical_terminology:
                score += min(features.get("median_horizontal_width", 0) / 10.0, 1.0)
            if case.canonical_terminology == "range":
                score += min(features.get("median_vertical_width", 0) / 12.0, 1.0)
            if case.canonical_terminology == "mixed":
                score += min(features.get("mixed_width_score", 0), 1.0)
            if user_regime not in case.station_regime and case.station_regime:
                score *= 0.5
            scored.append((score, case))
        scored.sort(key=lambda x: x[0], reverse=True)
        matches: list[ReferenceMatch] = []
        for score, case in scored[:top_k]:
            mismatch = None
            if "equatorial" in case.station_regime.lower() and user_regime == "midlatitude":
                mismatch = "Equatorial reference — do not transfer causal mechanisms to Kazan (C04)"
            matches.append(
                ReferenceMatch(
                    case=case,
                    similarity_metrics={"descriptor_score": score},
                    registration_confidence=0.0
                    if case.internal_image_availability != "available"
                    else 0.5,
                    wording_en="The visible morphology is structurally similar to…",
                    wording_ru="Видимая морфология структурно похожа на…",
                    domain_mismatch_warning=mismatch,
                )
            )
        return matches
