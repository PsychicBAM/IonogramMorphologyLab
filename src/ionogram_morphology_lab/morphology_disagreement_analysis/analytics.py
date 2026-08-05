"""Descriptive disagreement analytics — no accuracy / F1 / ground-truth claims."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ionogram_morphology_lab.morphology_disagreement_analysis.constants import (
    PILOT_DESIGNATION_EN,
    PILOT_DESIGNATION_RU,
    PROHIBITED_METRICS,
    SMALL_SAMPLE_THRESHOLD,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.eligibility import (
    humanize_candidate_label,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.models import SnapshotItemRecord
from ionogram_morphology_lab.morphology_review_corpus.labels import assert_no_prohibited_metrics


def _transition_key(expert: str, candidate: str) -> str:
    return f"{expert}→{candidate}"


def build_transition_matrix(
    rows: list[SnapshotItemRecord],
    *,
    comparable_only: bool = True,
) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {}
    for r in rows:
        if comparable_only and r.eligibility_bucket != "eligible_comparable":
            continue
        if not r.comparison_id:
            continue
        h = r.expert_morphology or ""
        c = r.candidate_state or ""
        matrix.setdefault(h, {})
        matrix[h][c] = matrix[h].get(c, 0) + 1
    return matrix


def filter_rows(
    rows: list[SnapshotItemRecord],
    *,
    filters: dict[str, Any] | None = None,
) -> list[SnapshotItemRecord]:
    if not filters:
        return list(rows)
    out: list[SnapshotItemRecord] = []
    for r in rows:
        ok = True
        for key, expected in filters.items():
            if expected in (None, "", [], ()):
                continue
            val = getattr(r, key, None)
            if key == "expert_interference":
                flags = set(r.expert_interference or [])
                if isinstance(expected, (list, tuple, set)):
                    if not flags.intersection(set(expected)):
                        ok = False
                elif expected not in flags:
                    ok = False
            elif key == "source_date":
                date = (r.frame_time or "")[:10]
                if date != str(expected):
                    ok = False
            elif isinstance(expected, (list, tuple, set)):
                if val not in expected:
                    ok = False
            else:
                if str(val) != str(expected):
                    ok = False
            if not ok:
                break
        if ok:
            out.append(r)
    return out


def descriptive_dashboard(
    rows: list[SnapshotItemRecord],
    *,
    exclusion_counts: dict[str, int] | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    filtered = filter_rows(rows, filters=filters)
    denom = len(filtered)
    buckets = Counter(r.eligibility_bucket for r in filtered)
    comparable = [r for r in filtered if r.eligibility_bucket == "eligible_comparable"]
    matches = sum(1 for r in comparable if r.comparison_status == "exact_agreement")
    disagreements = sum(
        1 for r in comparable if r.comparison_status == "morphology_disagreement"
    )
    # also count assessability disagreements as disagreements for dashboard
    disagreements += sum(
        1 for r in comparable if r.comparison_status == "assessability_disagreement"
    )

    expert_dist = Counter(r.expert_morphology for r in comparable if r.expert_morphology)
    cand_dist = Counter(r.candidate_state for r in comparable if r.candidate_state)
    assess = Counter(r.expert_assessability for r in filtered if r.expert_assessability)
    inter = Counter()
    for r in filtered:
        for flag in r.expert_interference or []:
            inter[flag] += 1
    support = Counter(r.candidate_strength for r in comparable if r.candidate_strength)
    sources = Counter(r.source_sha256 for r in filtered if r.source_sha256)
    transitions = Counter()
    for r in comparable:
        transitions[_transition_key(r.expert_morphology, r.candidate_state)] += 1

    matrix = build_transition_matrix(filtered, comparable_only=True)
    small = denom < SMALL_SAMPLE_THRESHOLD
    second = sum(1 for r in filtered if r.second_review_id)
    arb = sum(1 for r in filtered if r.arbitration_id)
    first = sum(1 for r in filtered if r.expert_review_id)

    summary: dict[str, Any] = {
        "kind": "disagreement_descriptive_dashboard",
        "scientific_claim": "none",
        "terminology": {
            "label_match": "label match",
            "label_disagreement": "label disagreement",
            "transition_count": "transition count",
            "descriptive_concordance": "descriptive concordance",
            "matrix_name": "Expert label → Candidate label transition matrix",
            "not_a": [
                "confusion matrix against ground truth",
                "error matrix",
                "accuracy matrix",
            ],
        },
        "note_en": PILOT_DESIGNATION_EN,
        "note_ru": PILOT_DESIGNATION_RU,
        "denominator": denom,
        "selected_unique_items": denom,
        "eligible_comparable_items": len(comparable),
        "exact_label_matches": matches,
        "morphology_disagreements": disagreements,
        "expert_abstentions": int(buckets.get("expert_abstention", 0)),
        "candidate_abstentions": int(buckets.get("candidate_abstention", 0)),
        "both_abstained": int(buckets.get("both_abstained", 0)),
        "non_comparable_items": int(buckets.get("non_comparable", 0)),
        "unavailable_items": int(
            buckets.get("unavailable_candidate", 0) + buckets.get("unavailable_source", 0)
        ),
        "first_reviews": first,
        "independent_second_reviews": second,
        "arbitration_records": arb,
        "exclusion_counts": dict(exclusion_counts or buckets),
        "bucket_counts": dict(buckets),
        "expert_morphology_distribution": dict(expert_dist),
        "candidate_morphology_distribution": dict(cand_dist),
        "expert_to_candidate_transitions": dict(transitions),
        "assessability_distribution": dict(assess),
        "interference_distribution": dict(inter),
        "source_distribution": {k: sources[k] for k in list(sources)[:50]},
        "candidate_support_distribution": dict(support),
        "transition_matrix": matrix,
        "small_sample": small,
        "small_sample_warning_en": (
            "Small sample — descriptive inspection only" if small else ""
        ),
        "small_sample_warning_ru": (
            "Малая выборка — только описательный просмотр" if small else ""
        ),
        "filters_applied": dict(filters or {}),
        "version_strata": {
            "engines": sorted({r.candidate_engine_version for r in filtered if r.candidate_engine_version}),
            "rulesets": sorted({r.candidate_ruleset_id for r in filtered if r.candidate_ruleset_id}),
        },
    }
    assert_no_prohibited_metrics(summary)
    for bad in PROHIBITED_METRICS:
        blob = str(summary).lower()
        if bad in ("f1",) and "f1" in blob:
            # only reject as claim keys
            pass
    return summary


def dominant_transitions(
    rows: list[SnapshotItemRecord], *, limit: int = 5
) -> list[dict[str, Any]]:
    comparable = [r for r in rows if r.eligibility_bucket == "eligible_comparable"]
    ctr: Counter[tuple[str, str]] = Counter(
        (r.expert_morphology, r.candidate_state) for r in comparable
    )
    out = []
    for (h, c), n in ctr.most_common(limit):
        out.append(
            {
                "expert_morphology": h,
                "candidate_state": c,
                "candidate_humanized": humanize_candidate_label(c),
                "transition_count": n,
                "denominator": len(comparable),
            }
        )
    return out
