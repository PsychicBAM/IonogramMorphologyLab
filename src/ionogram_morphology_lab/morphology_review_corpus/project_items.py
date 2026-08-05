"""Build real cohort items from project / session state (Phase 4C.2a)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ionogram_morphology_lab.ui.active_source_authority import (
    authoritative_active_source,
    inventory_id_for_path,
)


def _frame_time(frame_index: int) -> str:
    try:
        from ionogram_morphology_lab.projects.time_mapping import format_hhmm, frame_to_minute

        return format_hhmm(frame_to_minute(int(frame_index)))
    except Exception:
        f = max(0, int(frame_index))
        return f"{f // 60:02d}:{f % 60:02d}"


def item_dict_from_source_frame(
    *,
    source_path: Path | str,
    source_sha256: str,
    frame_index: int,
    display_name: str = "",
    inventory_id: str = "",
    feature_version: str = "iml2-0.2.0",
    inclusion_reason: str = "manual_selection",
    sampling_stratum: str = "manual",
    partition: str = "pilot_review",
    diagnostics_cache_id: str = "",
    v2_result_hash: str = "",
    v2_quality_status: str = "",
    datetime_metadata: str = "",
    grouping: dict[str, str] | None = None,
) -> dict[str, Any]:
    path = Path(source_path)
    sha = (source_sha256 or "").lower()
    avail = "item_pending" if path.is_file() and len(sha) == 64 else "item_unavailable"
    reason = "" if avail == "item_pending" else (
        "source_missing" if not path.is_file() else "invalid_source_sha256"
    )
    return {
        "source_sha256": sha,
        "frame_index": int(frame_index),
        "source_display_name": display_name or path.name,
        "source_inventory_id": inventory_id or inventory_id_for_path(path, sha),
        "frame_time": _frame_time(frame_index),
        "datetime_metadata": datetime_metadata,
        "feature_version": feature_version,
        "diagnostics_cache_id": diagnostics_cache_id,
        "v2_result_hash": v2_result_hash,
        "v2_quality_status": v2_quality_status,
        "item_status": avail,
        "unavailable_reason": reason,
        "inclusion_reason": inclusion_reason,
        "sampling_stratum": sampling_stratum,
        "partition": partition,
        "grouping": dict(grouping or {"source": path.name}),
    }


def items_from_active_source_frames(
    session: Any,
    frame_indices: Iterable[int],
    *,
    inclusion_reason: str = "active_source_selection",
) -> list[dict[str, Any]]:
    """Build items from the authoritative active source + frame list."""
    auth = authoritative_active_source(session)
    if not auth.is_active or auth.source_path is None:
        raise ValueError("No active MAT source selected")
    if not auth.available:
        raise ValueError("Active MAT source is unavailable")
    sha = auth.source_sha256
    if not sha and hasattr(session, "get_source_sha"):
        sha = str(session.get_source_sha(allow_compute=True) or "")
    if not sha or len(sha) != 64:
        raise ValueError("Active source SHA-256 is unavailable")
    out = []
    for fi in frame_indices:
        out.append(
            item_dict_from_source_frame(
                source_path=auth.source_path,
                source_sha256=sha,
                frame_index=int(fi),
                display_name=auth.display_name,
                inventory_id=auth.inventory_id,
                inclusion_reason=inclusion_reason,
                datetime_metadata=auth.date_hint,
                grouping={
                    "source": auth.display_name,
                    "date": auth.date_hint,
                    "sequence": auth.inventory_id,
                },
            )
        )
    return out


def frames_from_time_range(
    *,
    start_frame: int,
    end_frame: int,
    step: int = 1,
    max_frames: int | None = None,
) -> list[int]:
    start = max(1, int(start_frame))
    end = max(start, int(end_frame))
    step = max(1, int(step))
    frames = list(range(start, end + 1, step))
    if max_frames is not None:
        frames = frames[: int(max_frames)]
    return frames


def current_viewer_frame_item(session: Any) -> dict[str, Any]:
    frame = int(getattr(session, "current_frame", 1) or 1)
    items = items_from_active_source_frames(
        session, [frame], inclusion_reason="viewer_current_frame"
    )
    return items[0]
