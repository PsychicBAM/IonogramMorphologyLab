"""Role assignment: manual groups or deterministic proposal."""

from __future__ import annotations

import random
from typing import Any

from ionogram_morphology_lab.ml_dataset_manifests.models import AtomicGroup, ManifestItemRecord
from ionogram_morphology_lab.ml_dataset_readiness.acquisition_date import (
    is_valid_acquisition_date,
)

ACTIVE_ROLES = ("train", "development", "untouched_holdout")


def _valid_dates(values) -> list[str]:
    return sorted({d for d in values if is_valid_acquisition_date(str(d or ""))})


def apply_manual_assignments(
    items: list[ManifestItemRecord],
    groups: list[AtomicGroup],
    group_role_map: dict[str, str],
) -> tuple[list[ManifestItemRecord], list[AtomicGroup], dict[str, Any]]:
    """Assign complete atomic groups to roles from an owner map."""
    report: dict[str, Any] = {"mode": "manual_atomic_group_assignment", "deviations": {}}
    gmap = {g.group_id: g for g in groups}
    for gid, role in group_role_map.items():
        if gid not in gmap:
            raise ValueError(f"Unknown atomic group: {gid}")
        if role not in {"train", "development", "untouched_holdout", "excluded"}:
            raise ValueError(f"Invalid role: {role}")
        g = gmap[gid]
        if role == "untouched_holdout" and not g.eligible_untouched_holdout:
            raise ValueError(
                f"Group {gid} is not eligible for untouched_holdout "
                f"(states={g.contamination_states})"
            )
        g.role = role

    # Default unassigned groups to excluded
    for g in groups:
        if g.group_id not in group_role_map:
            g.role = "excluded"

    _propagate_group_roles_to_items(items, groups)
    report["role_counts"] = _role_counts(items)
    report["group_role_counts"] = role_group_counts_from_items(items)
    return items, groups, report


def deterministic_proposal(
    items: list[ManifestItemRecord],
    groups: list[AtomicGroup],
    *,
    seed: int,
    train_share: float | None = None,
    development_share: float | None = None,
    holdout_share: float | None = None,
    required_classes: list[str] | None = None,
) -> tuple[list[ManifestItemRecord], list[AtomicGroup], dict[str, Any]]:
    """Assign complete atomic groups reproducibly; never split groups."""
    rng = random.Random(int(seed))
    # Sort groups deterministically, then shuffle with seed
    ordered = sorted(groups, key=lambda g: g.group_id)
    order_ids = [g.group_id for g in ordered]
    rng.shuffle(order_ids)
    by_id = {g.group_id: g for g in ordered}

    eligible_holdout = [gid for gid in order_ids if by_id[gid].eligible_untouched_holdout]
    ineligible = [gid for gid in order_ids if gid not in eligible_holdout]

    n = len(order_ids)
    # Operational preferences only — not scientific defaults
    t_share = 0.5 if train_share is None else float(train_share)
    d_share = 0.25 if development_share is None else float(development_share)
    h_share = 0.25 if holdout_share is None else float(holdout_share)
    total = t_share + d_share + h_share
    if total <= 0:
        t_share, d_share, h_share = 1.0, 0.0, 0.0
        total = 1.0
    t_share, d_share, h_share = t_share / total, d_share / total, h_share / total

    n_hold = int(round(n * h_share)) if eligible_holdout else 0
    n_hold = min(n_hold, len(eligible_holdout))
    # Prefer leaving at least one holdout group when any eligible and share > 0
    if h_share > 0 and eligible_holdout and n_hold == 0 and n >= 1:
        n_hold = 1 if len(eligible_holdout) >= 1 and n >= 3 else 0

    hold_ids = eligible_holdout[:n_hold]
    remain = [gid for gid in order_ids if gid not in hold_ids]
    n_rem = len(remain)
    n_train = int(round(n_rem * (t_share / (t_share + d_share)))) if (t_share + d_share) > 0 else n_rem
    n_train = max(0, min(n_train, n_rem))
    train_ids = remain[:n_train]
    dev_ids = remain[n_train:]

    # Mark ineligible holdout candidates that couldn't be used — they go to train/dev pool already
    for gid in order_ids:
        g = by_id[gid]
        if gid in hold_ids:
            g.role = "untouched_holdout"
        elif gid in train_ids:
            g.role = "train"
        elif gid in dev_ids:
            g.role = "development"
        else:
            g.role = "excluded"

    # Items with fail-closed identity issues stay excluded
    _propagate_group_roles_to_items(items, groups)
    for it in items:
        if "no_defensible_grouping" in (it.identity_issues or []):
            it.role = "excluded"
            it.exclusion_reason = it.exclusion_reason or "no_defensible_grouping"
        if it.contamination_state == "prohibited_invalid":
            it.role = "excluded"
            it.exclusion_reason = it.exclusion_reason or "prohibited_invalid"

    actual = _role_counts(items)
    active = sum(actual.get(r, 0) for r in ACTIVE_ROLES) or 1
    deviations = {
        "requested_train_share": t_share,
        "requested_development_share": d_share,
        "requested_holdout_share": h_share,
        "actual_train_share": actual.get("train", 0) / active,
        "actual_development_share": actual.get("development", 0) / active,
        "actual_holdout_share": actual.get("untouched_holdout", 0) / active,
        "holdout_eligible_groups": len(eligible_holdout),
        "holdout_assigned_groups": len(hold_ids),
        "ineligible_group_count": len(ineligible),
    }
    class_cov = role_class_coverage(items)
    report = {
        "mode": "deterministic_proposal",
        "seed": int(seed),
        "role_counts": actual,
        "group_role_counts": role_group_counts_from_items(items),
        "deviations": deviations,
        "class_coverage": class_cov,
        "required_classes": list(required_classes or []),
        "required_class_gaps": _required_class_gaps(class_cov, required_classes or []),
        "no_oversampling": True,
        "no_candidate_balancing": True,
    }
    return items, groups, report


def _propagate_group_roles_to_items(
    items: list[ManifestItemRecord], groups: list[AtomicGroup]
) -> None:
    gid_role = {g.group_id: g.role for g in groups}
    for it in items:
        role = gid_role.get(it.atomic_group_id, "excluded")
        if it.contamination_state == "prohibited_invalid":
            it.role = "excluded"
            continue
        if role == "untouched_holdout" and not it.eligible_untouched_holdout:
            # Should not happen if group eligibility enforced; fail closed to excluded
            it.role = "excluded"
            it.exclusion_reason = it.exclusion_reason or "holdout_ineligible_item"
            continue
        it.role = role


def sync_group_roles_from_items(
    items: list[ManifestItemRecord], groups: list[AtomicGroup]
) -> None:
    """Authoritative: group.role follows unique member item roles (by atomic_group_id)."""
    by_gid: dict[str, set[str]] = {}
    for it in items:
        if not it.atomic_group_id:
            continue
        by_gid.setdefault(it.atomic_group_id, set()).add(it.role)
    for g in groups:
        roles = by_gid.get(g.group_id) or set()
        if not roles:
            g.role = "excluded"
        elif len(roles) == 1:
            g.role = next(iter(roles))
        # else leave as-is; overlap report will flag atomic_group_split


def role_group_counts_from_items(items: list[ManifestItemRecord]) -> dict[str, int]:
    """Count unique atomic_group_id values per item role (authoritative group counts)."""
    by_role: dict[str, set[str]] = {}
    for it in items:
        if not it.atomic_group_id:
            continue
        by_role.setdefault(it.role, set()).add(it.atomic_group_id)
    return {role: len(gids) for role, gids in by_role.items()}


def _role_counts(items: list[ManifestItemRecord]) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        out[it.role] = out.get(it.role, 0) + 1
    return out


def _group_role_counts(groups: list[AtomicGroup]) -> dict[str, int]:
    out: dict[str, int] = {}
    for g in groups:
        out[g.role] = out.get(g.role, 0) + 1
    return out


def role_class_coverage(items: list[ManifestItemRecord]) -> dict[str, dict[str, int]]:
    cov: dict[str, dict[str, int]] = {}
    for it in items:
        cov.setdefault(it.role, {})
        label = it.target_label or "(empty)"
        cov[it.role][label] = cov[it.role].get(label, 0) + 1
    return cov


def _required_class_gaps(
    class_cov: dict[str, dict[str, int]], required: list[str]
) -> dict[str, list[str]]:
    gaps: dict[str, list[str]] = {}
    for role in ACTIVE_ROLES:
        present = set(class_cov.get(role, {}))
        missing = [c for c in required if c not in present]
        if missing:
            gaps[role] = missing
    return gaps


def build_coverage_report(
    items: list[ManifestItemRecord], groups: list[AtomicGroup]
) -> dict[str, Any]:
    """Item-level and group-level coverage per role."""
    sync_group_roles_from_items(items, groups)
    roles = sorted({it.role for it in items} | set(ACTIVE_ROLES) | {"excluded"})
    report: dict[str, Any] = {"item_level": {}, "group_level": {}}
    for role in roles:
        role_items = [it for it in items if it.role == role]
        role_groups = [g for g in groups if g.role == role]
        item_group_n = len({it.atomic_group_id for it in role_items if it.atomic_group_id})
        report["item_level"][role] = {
            "unique_items": len(role_items),
            "atomic_groups": item_group_n,
            "sequences": sorted({it.sequence_id for it in role_items if it.sequence_id}),
            "related_frame_groups": sorted(
                {it.related_frame_group for it in role_items if it.related_frame_group}
            ),
            "sources": sorted({it.source_sha256 for it in role_items if it.source_sha256}),
            "acquisition_dates": _valid_dates(it.source_date for it in role_items),
            "frame_times": sorted(
                {it.frame_time for it in role_items if str(it.frame_time or "").strip()}
            ),
            "campaigns": sorted({it.campaign_id for it in role_items if it.campaign_id}),
            "first_review_count": len(role_items),
            "independent_second_review_available": sum(
                1 for it in role_items if it.independent_second_review_available
            ),
            "target_distribution": role_class_coverage(role_items).get(role, {}),
            "assessability": _count_attr(role_items, "assessability"),
            "interference": _count_list_attr(role_items, "interference"),
            "missingness": _count_attr(role_items, "missingness_category"),
            "contamination": _count_attr(role_items, "contamination_state"),
        }
        report["group_level"][role] = {
            "atomic_groups": len(role_groups),
            "items_in_groups": sum(len(g.item_identity_keys) for g in role_groups),
            "sequences": sorted({s for g in role_groups for s in g.sequence_ids}),
            "sources": sorted({s for g in role_groups for s in g.source_shas}),
            "acquisition_dates": _valid_dates(d for g in role_groups for d in g.source_dates),
            "target_labels": sorted({t for g in role_groups for t in g.target_labels}),
        }
    return report


def _count_attr(items: list[ManifestItemRecord], attr: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        v = getattr(it, attr, "") or "(empty)"
        out[str(v)] = out.get(str(v), 0) + 1
    return out


def _count_list_attr(items: list[ManifestItemRecord], attr: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        vals = getattr(it, attr, None) or []
        if not vals:
            out["(none)"] = out.get("(none)", 0) + 1
        for v in vals:
            out[str(v)] = out.get(str(v), 0) + 1
    return out
