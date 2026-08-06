"""Coverage, class distribution, and correlation-aware counts."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ionogram_morphology_lab.ml_dataset_readiness.acquisition_date import (
    diagnose_invalid_date_projection,
    is_valid_acquisition_date,
)
from ionogram_morphology_lab.ml_dataset_readiness.constants import (
    ADJACENT_FRAME_WARNING_EN,
    ADJACENT_FRAME_WARNING_RU,
    LIMITED_COVERAGE_WARNING_EN,
    LIMITED_COVERAGE_WARNING_RU,
    PARAMETER_SCALING_UNSUPPORTED_EN,
    PARAMETER_SCALING_UNSUPPORTED_RU,
)
from ionogram_morphology_lab.ml_dataset_readiness.display_labels import (
    REVIEW_NOTE,
    SEQUENCE_CORRELATION_NOTE,
    SYNTHETIC_GROUP_NOTE,
)
from ionogram_morphology_lab.ml_dataset_readiness.models import InventoryItemRecord
from ionogram_morphology_lab.morphology_review_corpus.labels import (
    AMBIGUITY_CODES,
    ASSESSABILITY_CODES,
    HUMAN_MORPHOLOGY_CODES,
    INTERFERENCE_CODES,
)


def _cross(rows: list[InventoryItemRecord], a_attr: str, b_getter) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        a = str(getattr(r, a_attr, "") or "(empty)")
        b = str(b_getter(r) or "(empty)")
        out[a][b] += 1
    return {k: dict(v) for k, v in out.items()}


def _canonical_source_date(raw: str) -> str:
    """Only valid YYYY-MM-DD counts as acquisition date identity."""
    s = str(raw or "").strip()
    return s if is_valid_acquisition_date(s) else ""


def _source_date_rows(rows: list[InventoryItemRecord]) -> list[dict[str, Any]]:
    """Group by source identity + acquisition date (not morphology / frame time)."""
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for r in rows:
        src_name = str(r.source_display_name or "").strip() or (
            r.source_sha256[:12] if r.source_sha256 else "(unknown)"
        )
        inv = str(r.source_inventory_id or "")
        sha = str(r.source_sha256 or "")
        # Invalid legacy time-as-date values do not form date identity
        date = _canonical_source_date(r.source_date)
        key = (src_name, inv, sha, date)
        slot = groups.get(key)
        if slot is None:
            slot = {
                "source": src_name,
                "source_inventory_id": inv,
                "source_sha256": sha,
                "source_sha_short": sha[:12] if sha else "",
                "source_date": date,
                "source_date_raw": str(r.source_date or ""),
                "label_count": 0,
                "frame_times": [],
            }
            groups[key] = slot
        slot["label_count"] += 1
        ft = str(r.frame_time or "").strip()
        if ft and ft not in slot["frame_times"]:
            slot["frame_times"].append(ft)
    out = sorted(
        groups.values(),
        key=lambda d: (d["source"], d["source_date"], d["source_sha_short"]),
    )
    return out


def _target_distribution(
    rows: list[InventoryItemRecord],
    task_contract: str,
) -> dict[str, Any]:
    morph_counts = Counter(r.morphology or "(empty)" for r in rows if r.locked_first_review_id)
    assess_counts = Counter(r.assessability or "(empty)" for r in rows)
    amb_counts = Counter(r.ambiguity or "(empty)" for r in rows if r.ambiguity)
    interf_counts: Counter[str] = Counter()
    for r in rows:
        flags = r.interference or ["(empty)"]
        for f in flags:
            interf_counts[f] += 1

    if task_contract == "spread_f_morphology_classification":
        return {
            "target_kind": "morphology",
            "target_label_counts": dict(morph_counts),
            "absent_target_classes": sorted(HUMAN_MORPHOLOGY_CODES - set(morph_counts.keys())),
            "underrepresented_classes": sorted(
                c for c, n in morph_counts.items() if n > 0 and n < 3
            ),
            "unsupported": False,
            "unsupported_note_en": "",
            "unsupported_note_ru": "",
        }
    if task_contract == "assessability_quality_classification":
        # Assessability + applicable quality/ambiguity states
        merged = dict(assess_counts)
        for k, n in amb_counts.items():
            if k in AMBIGUITY_CODES or k == "(empty)":
                merged[f"ambiguity:{k}"] = n
        present_assess = set(assess_counts.keys()) - {"(empty)"}
        absent = sorted(ASSESSABILITY_CODES - present_assess)
        return {
            "target_kind": "assessability_quality",
            "target_label_counts": merged,
            "absent_target_classes": absent,
            "underrepresented_classes": sorted(
                c for c, n in assess_counts.items() if n > 0 and n < 3
            ),
            "unsupported": False,
            "unsupported_note_en": "",
            "unsupported_note_ru": "",
        }
    if task_contract == "interference_classification":
        present = set(interf_counts.keys()) - {"(empty)"}
        return {
            "target_kind": "interference",
            "target_label_counts": dict(interf_counts),
            "absent_target_classes": sorted(INTERFERENCE_CODES - present),
            "underrepresented_classes": sorted(
                c for c, n in interf_counts.items() if n > 0 and n < 3
            ),
            "unsupported": False,
            "unsupported_note_en": "",
            "unsupported_note_ru": "",
        }
    # ionogram_parameter_scaling — no parameter labels in current corpus
    return {
        "target_kind": "parameter_scaling",
        "target_label_counts": {},
        "absent_target_classes": [],
        "underrepresented_classes": [],
        "unsupported": True,
        "unsupported_note_en": PARAMETER_SCALING_UNSUPPORTED_EN,
        "unsupported_note_ru": PARAMETER_SCALING_UNSUPPORTED_RU,
    }


def build_coverage_summary(
    rows: list[InventoryItemRecord],
    *,
    task_contract: str = "spread_f_morphology_classification",
) -> dict[str, Any]:
    morph_counts = Counter(r.morphology or "(empty)" for r in rows if r.locked_first_review_id)
    assess_counts = Counter(r.assessability or "(empty)" for r in rows)
    interf_counts: Counter[str] = Counter()
    for r in rows:
        flags = r.interference or ["(empty)"]
        for f in flags:
            interf_counts[f] += 1

    target = _target_distribution(rows, task_contract)

    unique_items = len(rows)
    unique_groups = len({r.related_frame_group for r in rows if r.related_frame_group})
    synthetic_groups = sum(1 for r in rows if getattr(r, "related_frame_group_synthetic", False))
    unique_seqs = len({r.sequence_id for r in rows if r.sequence_id})
    # Invariant: frame times must not inflate unique_source_dates
    unique_dates = len(
        {_canonical_source_date(r.source_date) for r in rows if _canonical_source_date(r.source_date)}
    )
    unique_frame_times = len(
        {str(r.frame_time or "").strip() for r in rows if str(r.frame_time or "").strip()}
    )
    unique_sources = len({r.source_sha256 for r in rows if r.source_sha256})
    unique_campaigns = len({r.campaign_id for r in rows if r.campaign_id})
    date_diag = diagnose_invalid_date_projection(rows)

    exposed = sum(1 for r in rows if r.contamination_state == "development_exposed")
    untouched = sum(1 for r in rows if r.eligible_untouched_holdout)
    second = sum(1 for r in rows if r.independent_second_review_available)
    paired = sum(
        1
        for r in rows
        if r.locked_first_review_id and r.independent_second_review_available
    )
    arbitration = sum(1 for r in rows if r.arbitration_available)
    corrected_first = sum(1 for r in rows if r.first_review_corrected)
    corrected_second = sum(1 for r in rows if r.second_review_corrected)

    limited = unique_dates <= 2 or unique_sources <= 2 or len(target["target_label_counts"]) <= 2
    correlated = unique_groups < unique_items or unique_seqs < unique_items
    sequence_correlated = unique_seqs > 0 and unique_seqs < unique_items

    warnings_en: list[str] = []
    warnings_ru: list[str] = []
    if correlated:
        warnings_en.append(ADJACENT_FRAME_WARNING_EN)
        warnings_ru.append(ADJACENT_FRAME_WARNING_RU)
    if limited:
        warnings_en.append(LIMITED_COVERAGE_WARNING_EN)
        warnings_ru.append(LIMITED_COVERAGE_WARNING_RU)
    if synthetic_groups:
        warnings_en.append(SYNTHETIC_GROUP_NOTE["en"])
        warnings_ru.append(SYNTHETIC_GROUP_NOTE["ru"])
    if sequence_correlated:
        warnings_en.append(SEQUENCE_CORRELATION_NOTE["en"])
        warnings_ru.append(SEQUENCE_CORRELATION_NOTE["ru"])
    if date_diag.get("legacy_invalid_date_projection"):
        if date_diag.get("warning_en"):
            warnings_en.append(str(date_diag["warning_en"]))
        if date_diag.get("warning_ru"):
            warnings_ru.append(str(date_diag["warning_ru"]))

    reviewer_by_class: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r.morphology and r.reviewer_alias:
            reviewer_by_class[r.morphology].add(r.reviewer_alias)
    multi_expert = sorted(c for c, s in reviewer_by_class.items() if len(s) > 1)
    single_expert = sorted(c for c, s in reviewer_by_class.items() if len(s) == 1)
    arbitration_classes = sorted(
        {r.morphology for r in rows if r.arbitration_available and r.morphology}
    )

    source_date_rows = _source_date_rows(rows)

    return {
        "task_contract": task_contract,
        "denominators": {
            "selected_records": unique_items,
            "unique_current_items": unique_items,
            "raw_frame_count": unique_items,
            "unique_related_frame_groups": unique_groups,
            "unique_sequences": unique_seqs,
            "unique_source_dates": unique_dates,
            "unique_frame_times": unique_frame_times,
            "unique_sources": unique_sources,
            "unique_campaigns": unique_campaigns,
            "locked_first_reviews": sum(1 for r in rows if r.locked_first_review_id),
            "independent_second_reviews": second,
            "items_with_paired_independent_reviews": paired,
            "arbitration_records": arbitration,
            "corrected_first_reviews": corrected_first,
            "corrected_second_reviews": corrected_second,
            "assessable": sum(1 for r in rows if r.assessability == "assessable"),
            "partially_assessable": sum(
                1 for r in rows if r.assessability == "partially_assessable"
            ),
            "not_assessable": sum(1 for r in rows if r.assessability == "not_assessable"),
            "indeterminate_labels": sum(1 for r in rows if r.morphology == "indeterminate"),
            "abstentions": sum(
                1 for r in rows if r.morphology in ("indeterminate", "not_assessable")
            ),
            "missing_required_fields": sum(
                1 for r in rows if r.missingness_category == "structurally_missing"
            ),
            "unavailable_sources": sum(1 for r in rows if "unavailable_source" in r.identity_issues),
            "development_exposed_items": exposed,
            "untouched_eligible_items": untouched,
            "synthetic_related_frame_groups": synthetic_groups,
        },
        "target_kind": target["target_kind"],
        "target_label_counts": target["target_label_counts"],
        "absent_target_classes": target["absent_target_classes"],
        "underrepresented_classes": target["underrepresented_classes"],
        "target_unsupported": target["unsupported"],
        "target_unsupported_note_en": target["unsupported_note_en"],
        "target_unsupported_note_ru": target["unsupported_note_ru"],
        # Legacy keys retained for frozen JSON / older readers (morphology always filled)
        "morphology_label_counts": dict(morph_counts),
        "absent_morphology_classes": sorted(HUMAN_MORPHOLOGY_CODES - set(morph_counts.keys())),
        "assessability_counts": dict(assess_counts),
        "interference_counts": dict(interf_counts),
        "source_date_rows": source_date_rows,
        "acquisition_date_diagnostics": date_diag,
        "cross_tables": {
            "morphology_x_source_date": _cross(rows, "morphology", lambda r: r.source_date),
            "morphology_x_assessability": _cross(rows, "morphology", lambda r: r.assessability),
            "morphology_x_interference": _cross(
                rows, "morphology", lambda r: ",".join(r.interference or [])
            ),
            "morphology_x_reviewer": _cross(rows, "morphology", lambda r: r.reviewer_alias),
            "morphology_x_contamination": _cross(
                rows, "morphology", lambda r: r.contamination_state
            ),
        },
        "reviewer_independence": {
            "first_review_count": sum(1 for r in rows if r.locked_first_review_id),
            "independent_second_review_count": second,
            "items_with_paired_independent_reviews": paired,
            "arbitration_count": arbitration,
            "corrected_first_reviews": corrected_first,
            "corrected_second_reviews": corrected_second,
            "classes_one_expert_only": single_expert,
            "classes_multiple_independent_experts": multi_expert,
            "classes_with_arbitration": arbitration_classes,
            "note_en": REVIEW_NOTE["en"],
            "note_ru": REVIEW_NOTE["ru"],
        },
        "correlation_warnings": {
            "en": warnings_en,
            "ru": warnings_ru,
            "limited_coverage": limited,
            "adjacent_frame_correlation": correlated,
            "sequence_correlation": sequence_correlated,
            "synthetic_related_frame_groups": synthetic_groups > 0,
        },
        "overlap_note": {
            "en": (
                "Indeterminate labels and abstentions may overlap as different fields "
                "of the same records and must not automatically be summed as disjoint samples."
            ),
            "ru": (
                "Неопределённые метки и воздержания могут пересекаться как разные поля "
                "одних и тех же записей и не должны автоматически суммироваться как "
                "непересекающиеся выборки."
            ),
        },
        "wording": {
            "en": "label count / coverage / representation / missingness / review availability",
            "note": "Class imbalance is reported as coverage, not as a model-performance problem.",
        },
    }
