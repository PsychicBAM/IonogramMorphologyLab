"""Reproducible campaign sampling over real project item pools (Phase 4C.3)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ionogram_morphology_lab.morphology_review_campaign.models import (
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_corpus.project_items import (
    frames_from_time_range,
    item_dict_from_source_frame,
)
from ionogram_morphology_lab.morphology_review_corpus.sampling import (
    manual_selection,
    random_sample,
    stratified_sample,
)


def item_fingerprint(row: dict[str, Any]) -> str:
    return f"{str(row.get('source_sha256') or '').lower()}:{int(row.get('frame_index') or 0)}"


def build_eligible_pool(
    sources: list[SourceScopeEntry],
    windows: list[TimeWindow],
    *,
    path_resolver: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Build candidate-independent eligible frames from sources × windows.

    ``path_resolver`` maps source_sha256 → display path basename only (portable).
    Absolute paths must not be stored in campaign records.
    """
    path_resolver = path_resolver or {}
    pool: list[dict[str, Any]] = []
    seen: set[str] = set()
    for src in sources:
        sha = (src.source_sha256 or "").lower()
        if len(sha) != 64:
            continue
        # Portable placeholder path for availability (basename only)
        display = src.source_display_name or f"{sha[:12]}.mat"
        # Use a synthetic relative name — availability checked via src.available flag
        rel_name = path_resolver.get(sha) or display
        for win in windows:
            frames = frames_from_time_range(
                start_frame=win.start_frame,
                end_frame=win.end_frame,
                step=win.step,
            )
            for fi in frames:
                row = item_dict_from_source_frame(
                    source_path=rel_name,
                    source_sha256=sha,
                    frame_index=fi,
                    display_name=src.source_display_name or display,
                    inventory_id=src.source_inventory_id,
                    inclusion_reason="campaign_eligible",
                    sampling_stratum=win.label or f"{win.start_frame}-{win.end_frame}",
                    datetime_metadata=src.date_hint,
                    grouping={
                        "source": src.source_display_name or display,
                        "date": src.date_hint,
                        "sequence": src.source_inventory_id or sha[:12],
                        "time_block": win.label or f"{win.start_frame}-{win.end_frame}",
                    },
                )
                # Availability from campaign source scope, not filesystem absolute path
                if not src.available:
                    row["item_status"] = "item_unavailable"
                    row["unavailable_reason"] = "source_unavailable"
                else:
                    # Relative basename cannot prove file presence — mark pending
                    row["item_status"] = "item_pending"
                    row["unavailable_reason"] = ""
                fp = item_fingerprint(row)
                if fp in seen:
                    continue
                seen.add(fp)
                pool.append(row)
    return pool


def warn_adjacent_independence(pool: list[dict[str, Any]]) -> list[str]:
    """Warn when adjacent frames of the same sequence appear as independent items."""
    warnings: list[str] = []
    by_seq: dict[str, list[int]] = defaultdict(list)
    for row in pool:
        seq = str((row.get("grouping") or {}).get("sequence") or row.get("source_sha256"))
        by_seq[seq].append(int(row.get("frame_index") or 0))
    for seq, frames in by_seq.items():
        ordered = sorted(set(frames))
        for a, b in zip(ordered, ordered[1:]):
            if b - a <= 1:
                warnings.append(
                    f"Adjacent frames {a} and {b} in sequence {seq} "
                    "are not independent samples"
                )
                break
    return warnings


def apply_sampling(
    pool: list[dict[str, Any]],
    plan: SamplingPlan,
) -> dict[str, Any]:
    """Apply sampling plan; returns selection report (candidate-independent)."""
    available = [r for r in pool if r.get("item_status") != "item_unavailable"]
    unavailable = [r for r in pool if r.get("item_status") == "item_unavailable"]
    method = (plan.method or "deterministic_random").strip()
    selected: list[dict[str, Any]]
    if method in ("manual", "all_eligible"):
        selected = manual_selection(available if method == "all_eligible" else available)
        if method == "all_eligible":
            for row in selected:
                row["inclusion_reason"] = "all_eligible"
                row["sampling_stratum"] = row.get("sampling_stratum") or "all_eligible"
    elif method == "stratified":
        target = plan.target_count or len(available)
        per = plan.per_stratum
        selected = stratified_sample(
            available,
            strata_key=plan.strata_key,
            per_stratum=per,
            seed=plan.seed,
            total_cap=target if target > 0 else None,
        )
    elif method == "imported_manifest":
        selected = manual_selection(available)
        for row in selected:
            row["inclusion_reason"] = "imported_manifest"
    else:
        # deterministic_random
        count = plan.target_count if plan.target_count > 0 else len(available)
        count = min(count, len(available))
        selected = random_sample(available, count=count, seed=plan.seed)

    adj_warnings = warn_adjacent_independence(selected)
    related_groups: dict[str, list[str]] = defaultdict(list)
    for row in selected:
        seq = str((row.get("grouping") or {}).get("sequence") or "")
        related_groups[seq].append(item_fingerprint(row))

    return {
        "method": method,
        "seed": plan.seed,
        "requested_count": plan.target_count,
        "available_count": len(available),
        "unavailable_count": len(unavailable),
        "selected_count": len(selected),
        "selected": selected,
        "unavailable": unavailable,
        "adjacent_frame_warnings": adj_warnings,
        "keep_adjacent_frames_together": plan.keep_adjacent_frames_together,
        "related_frame_groups": dict(related_groups),
        "unique_sources": sorted(
            {str(r.get("source_display_name") or r.get("source_sha256")) for r in selected}
        ),
        "dates": sorted({str(r.get("datetime_metadata") or "") for r in selected if r.get("datetime_metadata")}),
        "time_blocks": sorted(
            {
                str((r.get("grouping") or {}).get("time_block") or "")
                for r in selected
                if (r.get("grouping") or {}).get("time_block")
            }
        ),
        "fingerprints": [item_fingerprint(r) for r in selected],
        "operational_target_note_en": plan.note_en,
        "operational_target_note_ru": plan.note_ru,
        # Never expose candidate state in blind campaign preview
        "candidate_fields_present": False,
    }
