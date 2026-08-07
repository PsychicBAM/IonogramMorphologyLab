"""Integrity / overlap validation for ML-B.1 manifest sets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.ml_dataset_manifests.constants import GATE_F
from ionogram_morphology_lab.ml_dataset_manifests.metric_scan import scan_prohibited_metrics
from ionogram_morphology_lab.ml_dataset_manifests.models import AtomicGroup, ManifestItemRecord
from ionogram_morphology_lab.ml_dataset_manifests.planning import (
    role_class_coverage,
    role_group_counts_from_items,
    sync_group_roles_from_items,
)


def build_overlap_report(
    items: list[ManifestItemRecord], groups: list[AtomicGroup]
) -> dict[str, Any]:
    """Detect identity/group/sequence/date/exposure overlaps across roles."""
    errors: list[str] = []
    warnings: list[str] = []

    # Keep group.role aligned with item roles before overlap checks
    sync_group_roles_from_items(items, groups)

    # Exact role exclusivity for items
    seen_keys: dict[str, str] = {}
    for it in items:
        k = it.identity_key()
        if k in seen_keys and seen_keys[k] != it.role:
            errors.append(f"item_role_conflict:{k}:{seen_keys[k]}vs{it.role}")
        seen_keys[k] = it.role

    # Atomic group never split; group role must match member roles
    for g in groups:
        member_roles = {it.role for it in items if it.atomic_group_id == g.group_id}
        if len(member_roles) > 1:
            errors.append(f"atomic_group_split:{g.group_id}:roles={sorted(member_roles)}")
        elif member_roles and g.role not in member_roles:
            errors.append(
                f"atomic_group_role_mismatch:{g.group_id}:group={g.role}:"
                f"items={sorted(member_roles)}"
            )

    # Sequence never split across active roles
    seq_roles: dict[str, set[str]] = {}
    for it in items:
        if not it.sequence_id or it.role == "excluded":
            continue
        seq_roles.setdefault(it.sequence_id, set()).add(it.role)
    for seq, roles in seq_roles.items():
        if len(roles) > 1:
            errors.append(f"sequence_split:{seq}:roles={sorted(roles)}")

    # Related-frame group never split
    rel_roles: dict[str, set[str]] = {}
    for it in items:
        if not it.related_frame_group or it.role == "excluded":
            continue
        rel_roles.setdefault(it.related_frame_group, set()).add(it.role)
    for rel, roles in rel_roles.items():
        if len(roles) > 1:
            errors.append(f"related_frame_group_split:{rel}:roles={sorted(roles)}")

    # Holdout contamination conflicts
    holdout_conflicts: list[dict[str, Any]] = []
    for it in items:
        if it.role != "untouched_holdout":
            continue
        if it.contamination_state in {
            "development_exposed",
            "future_training_exposed",
            "holdout_revealed",
            "prohibited_invalid",
        }:
            chain = [
                f"item:{it.item_id}",
                f"related_frame_group:{it.related_frame_group}",
                f"sequence:{it.sequence_id}",
                f"contamination:{it.contamination_state}",
            ]
            errors.append("holdout_contamination_conflict:" + "→".join(chain))
            holdout_conflicts.append({"item_id": it.item_id, "chain": chain})

    # Group-count invariant: unique atomic_group_id per role equals group.role counts
    from_items = role_group_counts_from_items(items)
    from_groups = {}
    for g in groups:
        from_groups[g.role] = from_groups.get(g.role, 0) + 1
    for role in sorted(set(from_items) | set(from_groups)):
        if int(from_items.get(role, 0)) != int(from_groups.get(role, 0)):
            errors.append(
                f"role_group_count_mismatch:{role}:"
                f"items={from_items.get(role, 0)}:groups={from_groups.get(role, 0)}"
            )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "holdout_conflicts": holdout_conflicts,
        "item_count": len(items),
        "group_count": len(groups),
        "role_group_counts": from_items,
    }


def validate_freeze_eligibility(
    *,
    gate_outcome: str,
    authorizes_mlb_planning: bool,
    items: list[ManifestItemRecord],
    groups: list[AtomicGroup],
    overlap: dict[str, Any],
    required_classes: list[str] | None = None,
    protocol_exceptions: list[dict[str, str]] | None = None,
) -> list[str]:
    """Return freeze blockers (empty ⇒ freeze permitted)."""
    blockers: list[str] = []
    sync_group_roles_from_items(items, groups)

    if gate_outcome != GATE_F or not authorizes_mlb_planning:
        blockers.append(
            f"readiness_gate_not_F:outcome={gate_outcome or '(none)'}; "
            "draft simulation allowed; final freeze blocked"
        )
    if not overlap.get("ok", False):
        blockers.extend(f"integrity:{e}" for e in overlap.get("errors", []))

    holdout_items = [it for it in items if it.role == "untouched_holdout"]
    holdout_group_ids = {
        it.atomic_group_id for it in holdout_items if it.atomic_group_id
    }
    holdout_groups = [g for g in groups if g.role == "untouched_holdout"]
    eligible = [g for g in groups if g.eligible_untouched_holdout]
    if not eligible:
        blockers.append(
            "no_untouched_eligible_groups: all available groups are development-exposed "
            "or otherwise ineligible; do not randomly split frames"
        )

    if GATE_F == gate_outcome:
        if not holdout_items or not holdout_group_ids:
            blockers.append(
                "holdout_not_reserved: assign at least one untouched_holdout group before freeze"
            )
        else:
            # Every holdout item belongs to exactly one holdout group
            for it in holdout_items:
                if not it.atomic_group_id or it.atomic_group_id not in {
                    g.group_id for g in holdout_groups
                }:
                    blockers.append(
                        f"holdout_item_group_mismatch:item={it.item_id}:"
                        f"group={it.atomic_group_id or '(none)'}"
                    )
            # No holdout group has train/development members
            for g in holdout_groups:
                foreign = {
                    it.role
                    for it in items
                    if it.atomic_group_id == g.group_id
                    and it.role not in {"untouched_holdout", "excluded"}
                }
                if foreign:
                    blockers.append(
                        f"holdout_group_role_leak:{g.group_id}:roles={sorted(foreign)}"
                    )
                if not g.eligible_untouched_holdout:
                    blockers.append(f"holdout_group_not_eligible:{g.group_id}")
                exposed_states = {
                    "development_exposed",
                    "future_training_exposed",
                    "holdout_revealed",
                }
                if any(s in exposed_states for s in (g.contamination_states or [])):
                    blockers.append(f"holdout_group_development_exposed:{g.group_id}")

    gaps = role_class_coverage(items)
    for role in ("train", "development", "untouched_holdout"):
        missing = [
            c
            for c in (required_classes or [])
            if c not in gaps.get(role, {})
        ]
        if missing:
            excepted = {
                f"{role}:{c}"
                for ex in (protocol_exceptions or [])
                for c in [ex.get("class", "")]
                if ex.get("role") == role
            }
            still = [c for c in missing if f"{role}:{c}" not in excepted]
            if still:
                blockers.append(f"required_class_absent:{role}:{','.join(still)}")

    # Structural / token-aware metric scan (never substring-in-hash)
    for it in items:
        for hit in scan_prohibited_metrics(it.to_dict()):
            if hit not in blockers:
                blockers.append(hit)
    for g in groups:
        for hit in scan_prohibited_metrics(g.to_dict()):
            if hit not in blockers:
                blockers.append(hit)

    return blockers


def validate_manifest_dir(path: Path) -> dict[str, Any]:
    """Fail-closed directory integrity check."""
    errors: list[str] = []
    warnings: list[str] = []
    required = [
        "manifest_set.json",
        "input_readiness_snapshot.json",
        "item_index.jsonl",
        "atomic_groups.jsonl",
        "split_policy.json",
    ]
    for name in required:
        if not (path / name).exists():
            errors.append(f"missing:{name}")
    ms_path = path / "manifest_set.json"
    if ms_path.exists():
        ms = json.loads(ms_path.read_text(encoding="utf-8"))
        if ms.get("authorizes_training") or ms.get("authorizes_mlc"):
            errors.append("training_or_mlc_authorization_set")
        if ms.get("lifecycle_state") == "frozen":
            for name in (
                "train_manifest.jsonl",
                "development_manifest.jsonl",
                "holdout_public_manifest.jsonl",
                "holdout_lock.json",
                "integrity_report.json",
            ):
                if not (path / name).exists():
                    errors.append(f"frozen_missing:{name}")
            pub = path / "holdout_public_manifest.jsonl"
            if pub.exists():
                for line in pub.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    for forbidden in (
                        "target_label",
                        "morphology",
                        "assessability",
                        "ambiguity",
                        "interference",
                    ):
                        if forbidden in row:
                            errors.append(f"public_holdout_has_{forbidden}")
            ref = path / "holdout_reference_labels.jsonl"
            lock = path / "holdout_lock.json"
            if not ref.exists():
                errors.append("frozen_missing:holdout_reference_labels.jsonl")
            if lock.exists():
                lock_data = json.loads(lock.read_text(encoding="utf-8"))
                if lock_data.get("unlock_available_in_mlb"):
                    errors.append("holdout_unlock_available_in_mlb")
    return {"ok": not errors, "errors": errors, "warnings": warnings}
