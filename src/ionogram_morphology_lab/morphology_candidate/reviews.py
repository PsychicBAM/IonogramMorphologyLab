"""Morphology candidate expert reviews (separate from geometry reviews)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.morphology_candidate.types import (
    MorphologyCandidateReview,
    REVIEW_DECISIONS,
    deterministic_hash,
)


def morphology_reviews_dir(project_root: Path | str) -> Path:
    return Path(project_root) / "feature_diagnostics" / "morphology_reviews"


def geometry_reviews_dir(project_root: Path | str) -> Path:
    return Path(project_root) / "feature_diagnostics" / "geometry_reviews"


def save_morphology_review(
    project_root: Path | str,
    review: MorphologyCandidateReview | dict[str, Any],
) -> Path:
    data = review.to_dict() if hasattr(review, "to_dict") else dict(review)
    if data.get("review_kind") != "morphology_candidate_review":
        raise ValueError("review_kind must be morphology_candidate_review")
    if data.get("confirmed_ground_truth") is True:
        # Allowed only if explicitly set; default false — never auto-promote
        pass
    decision = data.get("reviewer_decision") or ""
    if decision and decision not in REVIEW_DECISIONS:
        raise ValueError(f"invalid reviewer_decision: {decision}")

    out = morphology_reviews_dir(project_root)
    out.mkdir(parents=True, exist_ok=True)
    frame = int(data.get("frame_index") or 0)
    digest = (data.get("candidate_result_hash") or data.get("diagnostics_cache_id") or "na")[:12]
    path = out / f"morph_review_f{frame:04d}_{digest}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_morphology_reviews(project_root: Path | str) -> list[dict[str, Any]]:
    d = morphology_reviews_dir(project_root)
    if not d.is_dir():
        return []
    rows = []
    for p in sorted(d.glob("morph_review_*.json")):
        try:
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return rows


def ledger_hash(ledger: list[dict[str, Any]] | tuple) -> str:
    return deterministic_hash([dict(e) if not isinstance(e, dict) else e for e in ledger])


def assert_geometry_reviews_untouched(project_root: Path | str, before_names: set[str] | None = None) -> None:
    """Helper for tests: morphology save must not write into geometry_reviews."""
    geo = geometry_reviews_dir(project_root)
    if before_names is None:
        return
    after = {p.name for p in geo.glob("*.json")} if geo.is_dir() else set()
    if after != before_names:
        raise AssertionError("geometry_reviews directory was modified by morphology review path")
