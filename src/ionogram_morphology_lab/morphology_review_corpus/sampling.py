"""Deterministic cohort sampling modes (manual / random / stratified / import)."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any, Callable, Iterable

from ionogram_morphology_lab.morphology_review_corpus.hashing import validate_sha256


PoolItem = dict[str, Any]


def _sort_pool(pool: Iterable[PoolItem]) -> list[PoolItem]:
    rows = list(pool)
    return sorted(
        rows,
        key=lambda r: (
            str(r.get("source_sha256") or "").lower(),
            int(r.get("frame_index") or 0),
            str(r.get("source_inventory_id") or ""),
        ),
    )


def manual_selection(selected: Iterable[PoolItem]) -> list[PoolItem]:
    """Owner-selected exact frames; order preserved after stable sort for identity checks."""
    out = []
    for i, row in enumerate(selected):
        item = dict(row)
        item["sampling_stratum"] = item.get("sampling_stratum") or "manual"
        item["inclusion_reason"] = item.get("inclusion_reason") or "manual_selection"
        item["_selection_order"] = i
        out.append(item)
    # Preserve owner order via selection_order, not SHA sort
    return out


def random_sample(
    pool: Iterable[PoolItem],
    *,
    count: int,
    seed: int,
) -> list[PoolItem]:
    sorted_pool = _sort_pool(pool)
    if count < 0:
        raise ValueError("count must be non-negative")
    if count > len(sorted_pool):
        raise ValueError(
            f"Requested {count} items but candidate pool has only {len(sorted_pool)}"
        )
    rng = random.Random(int(seed))
    indices = list(range(len(sorted_pool)))
    rng.shuffle(indices)
    chosen = [sorted_pool[i] for i in indices[:count]]
    # Stable manifest order by identity after selection
    chosen = _sort_pool(chosen)
    for row in chosen:
        row["sampling_stratum"] = row.get("sampling_stratum") or "random"
        row["inclusion_reason"] = row.get("inclusion_reason") or f"random_seed_{seed}"
    return chosen


def stratified_sample(
    pool: Iterable[PoolItem],
    *,
    strata_key: str,
    per_stratum: int,
    seed: int,
    total_cap: int | None = None,
) -> list[PoolItem]:
    """Sample up to per_stratum items from each stratum; deterministic within strata."""
    sorted_pool = _sort_pool(pool)
    buckets: dict[str, list[PoolItem]] = {}
    for row in sorted_pool:
        key = str(row.get(strata_key) or "unknown")
        buckets.setdefault(key, []).append(row)
    rng = random.Random(int(seed))
    selected: list[PoolItem] = []
    for stratum in sorted(buckets.keys()):
        rows = list(buckets[stratum])
        indices = list(range(len(rows)))
        rng.shuffle(indices)
        take = min(per_stratum, len(rows))
        for i in indices[:take]:
            item = dict(rows[i])
            item["sampling_stratum"] = f"{strata_key}={stratum}"
            item["inclusion_reason"] = (
                f"stratified:{strata_key}={stratum}:seed={seed}"
            )
            selected.append(item)
    selected = _sort_pool(selected)
    if total_cap is not None and len(selected) > total_cap:
        # Cap deterministically after identity sort
        selected = selected[: int(total_cap)]
    return selected


def import_manifest(path: Path | str) -> list[PoolItem]:
    """Import CSV/JSON manifest with exact source SHA and frame indices."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    text = p.read_text(encoding="utf-8")
    rows: list[PoolItem]
    if p.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        if not isinstance(data, list):
            raise ValueError("JSON manifest must be a list or {items: [...]}")
        rows = [dict(x) for x in data]
    else:
        reader = csv.DictReader(text.splitlines())
        rows = [dict(r) for r in reader]
    out: list[PoolItem] = []
    for i, row in enumerate(rows):
        sha = str(row.get("source_sha256") or row.get("source_sha") or "").strip()
        if not sha:
            raise ValueError(f"Manifest row {i}: missing source_sha256")
        try:
            sha = validate_sha256(sha)
        except ValueError:
            # Keep invalid SHA marked unavailable later rather than silently drop
            pass
        frame = int(row.get("frame_index") if row.get("frame_index") is not None else -1)
        item = {
            "source_sha256": sha,
            "frame_index": frame,
            "source_inventory_id": str(row.get("source_inventory_id") or ""),
            "source_display_name": str(
                row.get("source_display_name") or row.get("source_file") or ""
            ),
            "sampling_stratum": "import_manifest",
            "inclusion_reason": f"import_manifest:{p.name}",
            "frame_time": str(row.get("frame_time") or ""),
            "partition": str(row.get("partition") or "pilot_review"),
        }
        # Preserve original entry for unavailable retention
        item["original_manifest_entry"] = dict(row)
        out.append(item)
    return out


def mark_availability(
    items: list[PoolItem],
    *,
    sha_exists: Callable[[str], bool],
    frame_valid: Callable[[str, int], bool] | None = None,
) -> list[PoolItem]:
    """Mark unavailable items without silently replacing them."""
    out = []
    for row in items:
        item = dict(row)
        sha = str(item.get("source_sha256") or "")
        frame = int(item.get("frame_index") if item.get("frame_index") is not None else -1)
        reason = ""
        try:
            validate_sha256(sha)
        except ValueError:
            reason = "invalid_source_sha256"
        if not reason and not sha_exists(sha):
            reason = "source_missing"
        if not reason and frame < 0:
            reason = "invalid_frame_index"
        if not reason and frame_valid is not None and not frame_valid(sha, frame):
            reason = "frame_out_of_bounds"
        if reason:
            item["item_status"] = "item_unavailable"
            item["unavailable_reason"] = reason
        else:
            item["item_status"] = item.get("item_status") or "item_pending"
            item["unavailable_reason"] = item.get("unavailable_reason") or ""
        out.append(item)
    return out
